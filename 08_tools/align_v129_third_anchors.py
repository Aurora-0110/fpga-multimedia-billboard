"""Local cached ASR anchors ONLY; exact display text comes from user, not ASR."""
from pathlib import Path
import os,sys,json,hashlib,time
import argparse
r=Path(__file__).resolve().parents[1];assert '01_versions' not in r.parts
rt=Path(r'D:\FPGA_Billboard\90_tools\media\asr')
os.environ.update(HF_HOME=str(rt/'cache/hf'),HF_HUB_CACHE=str(rt/'cache/hf/hub'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TEMP=str(rt/'tmp'),TMP=str(rt/'tmp'),TMPDIR=str(rt/'tmp'),PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0,str(rt/'packages'))
import av,numpy as np
from faster_whisper import WhisperModel
pa=argparse.ArgumentParser();pa.add_argument('--attempt',type=int,default=2);args=pa.parse_args()
source=json.loads((r/'06_test_media/captions_third_user/SOURCE.json').read_text(encoding='utf-8'));wav=Path(source['audio_path'])
assert hashlib.sha256(wav.read_bytes()).hexdigest()==source['audio_expected_sha256']
out=r/f'04_evidence/v129_third_asr_anchors_attempt{args.attempt}';assert not out.exists();out.mkdir()
start=time.monotonic();model=WhisperModel('turbo',device='cpu',compute_type='int8',cpu_threads=4,num_workers=1,download_root=str(rt/'models'),local_files_only=True)
resampler=av.AudioResampler(format='s16',layout='mono',rate=16000);chunks=[]
with av.open(str(wav)) as container:
 for frame in container.decode(audio=0):chunks.extend(f.to_ndarray().reshape(-1)for f in resampler.resample(frame))
chunks.extend(f.to_ndarray().reshape(-1)for f in resampler.resample(None))
audio=np.concatenate(chunks).astype(np.float32)/32768.
segments,info=model.transcribe(audio,language='zh',beam_size=3,word_timestamps=True,condition_on_previous_text=False,vad_filter=False)
rows=[]
for s in segments:
 row=dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob,words=[dict(word=w.word,start=w.start,end=w.end,probability=w.probability)for w in (s.words or [])]);rows.append(row)
 print(f'{s.start:7.2f}--{s.end:7.2f} {s.text}',flush=True)
 (out/'anchors.json').write_text(json.dumps(dict(complete=False,rows=rows),ensure_ascii=False,indent=2),encoding='utf-8')
record=dict(complete=True,local_only=True,source=str(wav),source_sha256=source['audio_expected_sha256'],duration_seconds=source['duration_seconds'],human_timing_verified=False,not_display_text=True,elapsed_seconds=round(time.monotonic()-start,3),rows=rows,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(out/'anchors.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');print('DONE',record['elapsed_seconds'],flush=True)
