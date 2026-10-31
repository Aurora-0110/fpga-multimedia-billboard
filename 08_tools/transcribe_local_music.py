"""Offline transcription of user-provided local MUSIC.WAV; no audio upload."""
from pathlib import Path
import os,sys,json,hashlib,time
rt=Path(r'D:\FPGA_Billboard\90_tools\media\asr')
os.environ.update(HF_HOME=str(rt/'cache/hf'),HF_HUB_CACHE=str(rt/'cache/hf/hub'),HF_XET_CACHE=str(rt/'cache/xet'),HF_HUB_DISABLE_XET='1',HF_HUB_DISABLE_SYMLINKS_WARNING='1',TEMP=str(rt/'tmp'),TMP=str(rt/'tmp'),TMPDIR=str(rt/'tmp'),PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0,str(rt/'packages'))
from faster_whisper import WhisperModel
src=Path(r'D:\FPGA_Billboard\media\music_natianxiayule_20261026\02_audio\MUSIC.WAV')
out=Path(r'D:\FPGA_Billboard\work\v127_sample_captions_20261030\06_test_media\captions_music');out.mkdir(exist_ok=True)
print('Loading multilingual small model for LOCAL CPU int8 preparation; model files only on D.',flush=True)
t=time.monotonic();model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=4,num_workers=1,download_root=str(rt/'models'))
print('Model ready',round(time.monotonic()-t,1),'s. Transcribing user WAV locally.',flush=True)
# Decode using the installed PyAV interface explicitly; no deprecated metadata_errors argument.
import av,numpy as np
resampler=av.AudioResampler(format='s16',layout='mono',rate=16000);chunks=[]
with av.open(str(src))as container:
 for frame in container.decode(audio=0):
  chunks.extend(f.to_ndarray().reshape(-1) for f in resampler.resample(frame))
chunks.extend(f.to_ndarray().reshape(-1) for f in resampler.resample(None))
audio=np.concatenate(chunks).astype(np.float32)/32768.0
segments,info=model.transcribe(audio,language='zh',task='transcribe',beam_size=5,word_timestamps=True,condition_on_previous_text=False,vad_filter=False,temperature=0,initial_prompt='简体中文歌曲歌词。')
rows=[]
for seg in segments:
 row=dict(id=seg.id,start=seg.start,end=seg.end,text=seg.text,avg_logprob=seg.avg_logprob,no_speech_prob=seg.no_speech_prob,words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability)for w in seg.words or []]);rows.append(row)
 (out/'recognition_draft.json').write_text(json.dumps(dict(local_only=True,human_verified=False,source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),model='Systran/faster-whisper-small',duration=info.duration,segments=rows,complete=False),ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'{seg.start:.2f}--{seg.end:.2f} {seg.text} [logp={seg.avg_logprob:.2f},no_speech={seg.no_speech_prob:.2f}]',flush=True)
rec=dict(local_only=True,human_verified=False,source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),model='Systran/faster-whisper-small',duration=info.duration,segments=rows,complete=True,elapsed_seconds=time.monotonic()-t)
(out/'recognition_draft.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8');print('DONE',out,flush=True)
