from pathlib import Path
import os,json,hashlib,subprocess,datetime
root=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
out=root/'04_evidence'/('v114_boundary_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
old=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v112_audio_pingpong_20261027\01_project\01_project\rtl\audio\tf_wav_playback.v')
p=out/'old_tf_wav_playback.v';p.write_text(old.read_text(encoding='utf8').replace('module tf_wav_playback','module old_tf_wav_playback'),encoding='utf8')
src=[t/'tb_v114_boundary.sv',t/'v114_pcm_producer_stub.sv',rtl/'audio/tf_wav_playback.v',rtl/'audio/audio_choice_cdc.v',rtl/'mem/async_fifo.v',rtl/'common/reset_release.v',p]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bound={p.relative_to(root).as_posix():sha(p)for p in src+[Path(__file__)]}
env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'))
exe=out/'boundary.vvp';c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-s','tb_v114_boundary','-o',str(exe),*map(str,src)],env=env,capture_output=True,text=True);text=c.stdout+c.stderr
rc=None
if c.returncode==0:
 try:
  c2=subprocess.run([str(b/'vvp.exe'),str(exe)],env=env,capture_output=True,text=True,timeout=300);text+=c2.stdout+c2.stderr;rc=c2.returncode
 except subprocess.TimeoutExpired as e:
  text+='\nTIMEOUT300\n'+str(e.stdout or '')
(out/'run.log').write_text(text,encoding='utf8')
rec=dict(passed=c.returncode==0 and rc==0 and 'PASS' in text and 'FATAL' not in text,source_sha256=bound,baseline_original=str(old),baseline_original_sha256=sha(old),scope='Actual async FIFO / CDC / playback at49.5/74.25MHz and48k sample cadence; controlled one-shot PCM producer, small32-word FIFO/PREFILL1 and short files1..17, sweep around sample edge. Proves a boundary defect, does NOT establish cause of actual long-track A3.')
(out/'summary.json').write_text(json.dumps(rec,indent=2),encoding='utf8');print(text[-3000:]);print(out);raise SystemExit(0 if rec['passed']else 1)
