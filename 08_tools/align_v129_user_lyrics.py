"""Offline forced alignment of the exact USER-PROVIDED lyrics to preserved WAV.
No audio upload, no model download, no runtime FPGA ASR. All evidence retained.
Cross-attention alignment is only a preparation estimate, not human listening QA.
"""
from pathlib import Path
import argparse,os,sys,json,hashlib,time,re
root=Path(__file__).resolve().parents[1]
assert '01_versions' not in root.parts,'Never write into a frozen version'
rt=Path(r'D:\FPGA_Billboard\90_tools\media\asr')
os.environ.update(HF_HOME=str(rt/'cache/hf'),HF_HUB_CACHE=str(rt/'cache/hf/hub'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TEMP=str(rt/'tmp'),TMP=str(rt/'tmp'),TMPDIR=str(rt/'tmp'),PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0,str(rt/'packages'))
import av,numpy as np
from faster_whisper import WhisperModel
from faster_whisper.tokenizer import Tokenizer
from faster_whisper.transcribe import pad_or_trim
pa=argparse.ArgumentParser();pa.add_argument('--model',choices=['turbo','small'],required=True);args=pa.parse_args()
source=root/'06_test_media/captions_third_user'
info=json.loads((source/'SOURCE.json').read_text(encoding='utf-8'))
wav=Path(info['audio_path']);digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(wav)==info['audio_expected_sha256']
lyrics=(source/'TURANDETUOLUO_用户提供完整歌词.txt').read_text(encoding='utf-8').splitlines()
assert len(lyrics)==16 and digest(source/'TURANDETUOLUO_用户提供完整歌词.txt')==info['user_text_sha256']
out=root/'04_evidence'/f'v129_forced_alignment_{args.model}_attempt1'
assert not out.exists(),'Never overwrite alignment evidence'
out.mkdir()
# Bounded <30s windows anchored by the two already-preserved local ASR passes.
windows=[(1,4,29.50,55.20),(5,8,55.50,82.00),(9,12,81.00,107.00),(13,16,105.50,131.00)]
resampler=av.AudioResampler(format='s16',layout='mono',rate=16000);chunks=[]
with av.open(str(wav))as container:
 for frame in container.decode(audio=0):chunks.extend(f.to_ndarray().reshape(-1)for f in resampler.resample(frame))
chunks.extend(f.to_ndarray().reshape(-1)for f in resampler.resample(None))
audio=np.concatenate(chunks).astype(np.float32)/32768.
start=time.monotonic()
model=WhisperModel(args.model,device='cpu',compute_type='int8',cpu_threads=4,num_workers=1,download_root=str(rt/'models'),local_files_only=True)
tokenizer=Tokenizer(model.hf_tokenizer,model.model.is_multilingual,task='transcribe',language='zh')
all_rows=[];word_records=[]
for lo,hi,t0,t1 in windows:
 groups=[];tokens=[]
 for line in range(lo,hi+1):
  spoken=re.sub(r'[^\u3400-\u9fffA-Za-z0-9]','',lyrics[line-1])
  tt=tokenizer.encode(' '+spoken)
  groups.append(dict(line=line,text=lyrics[line-1],spoken=spoken,token_start=len(tokens),token_end=len(tokens)+len(tt),words=[]))
  tokens.extend(tt)
 assert len(tokens)<440 and t1-t0<30
 segment=audio[round(t0*16000):round(t1*16000)]
 features=model.feature_extractor(segment)
 num_frames=features.shape[-1]-1
 encoded=model.encode(pad_or_trim(features))
 alignment=model.find_alignment(tokenizer,[tokens],encoded,[num_frames])[0]
 cursor=0;window_words=[]
 for w in alignment:
  before=cursor;cursor+=len(w['tokens'])
  rec=dict(word=w['word'],start=round(t0+float(w['start']),3),end=round(t0+float(w['end']),3),probability=float(w['probability']),token_start=before,token_end=cursor)
  window_words.append(rec)
  for g in groups:
   if before<g['token_end'] and cursor>g['token_start'] and re.search(r'[\u3400-\u9fffA-Za-z0-9]',w['word']):g['words'].append(rec)
 assert cursor==len(tokens),(cursor,len(tokens))
 for g in groups:
  assert g['words'],g
  g.update(start=g['words'][0]['start'],end=g['words'][-1]['end'],mean_probability=float(np.mean([w['probability']for w in g['words']])),zero_duration_words=sum(w['end']<=w['start']for w in g['words']),window=[t0,t1],model=args.model)
  all_rows.append(g)
  print(f"{args.model} line{g['line']:02d} {g['start']:7.3f}--{g['end']:7.3f} p={g['mean_probability']:.3f} z={g['zero_duration_words']} {g['text']}",flush=True)
 word_records.append(dict(lines=[lo,hi],window=[t0,t1],tokens=len(tokens),num_frames=num_frames,words=window_words))
 (out/'alignment.json').write_text(json.dumps(dict(complete=False,rows=all_rows,windows=word_records),ensure_ascii=False,indent=2),encoding='utf-8')
record=dict(complete=True,source_wav=str(wav),source_sha256=digest(wav),user_text_sha256=info['user_text_sha256'],source_is_user_provided=True,local_only=True,human_timing_verified=False,model=args.model,elapsed_seconds=round(time.monotonic()-start,3),rows=all_rows,windows=word_records,script_sha256=digest(Path(__file__)))
(out/'alignment.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('DONE',out,'seconds',record['elapsed_seconds'],flush=True)
