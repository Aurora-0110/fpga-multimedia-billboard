from pathlib import Path
import shutil,json,datetime
root=Path(r'D:\FPGA_Billboard\99_archive\version_history')
versions=json.loads((root/'versions.json').read_text(encoding='utf-8-sig'))
assert versions[-1]['id']=='v115_tf_wav_audit_20261027'
src=root/'01_versions/v115_tf_wav_audit_20261027/01_project'
dst=Path(r'D:\FPGA_Billboard\work\v116_audio_refill_arbitration_20261027')
assert not dst.exists(),str(dst)
shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.vvp','*.vcd'))
for name in ['README_先看这里.md','VERSION_STATUS.json','README_归档位置.md']:
 p=dst/name
 if p.exists():p.rename(dst/('BASELINE_v115_'+name))
image=Path(r'D:\xwechat_files\wxid_r67uywesbbr822_5a66\temp\RWTemp\2026-10\646966ded34a794aab2a3bfd820b6472\89b8b91d13bd92dde36b968aa1fad14e.jpg')
ev=dst/'04_evidence/v116_hardware_feedback';ev.mkdir()
shutil.copy2(image,ev/image.name)
rec={'date':datetime.datetime.now().astimezone().isoformat(),'source':'User photo and report; not an agent measurement','bit_identity':'OSD V114 visible; full hash of actually programmed bit not read back','report':'进入音频播放后一秒左右，音频卡顿、A3、L6亮；左上角和UI均有错误','photo_transcription':{'top':'V114 UF=0 OF=0 AU=0 TF=00','history':'UF=0 OF=0 AU=0 TF=A3 SDR=0','audio':'Q=0000 MIN=1FFF A3Q=0000 S=00 B=3'},'interpretation':'A3 was latched in history. Audio telemetry is back at per-source-reset values; cannot use zero A3Q/S as first-underflow evidence. Current screenshot does not identify the original refill stall.','a3_root_cause_closed':False,'original_wav_damage':'v115 excluded compared to originals; card electrical/latency not excluded'}
(ev/'feedback.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
(dst/'08_tools/prepare_v116.py').write_text(Path(r'D:\FPGA_Billboard\work\prepare_v116_20261027.py').read_text(encoding='utf-8'),encoding='utf-8')
print(dst)
