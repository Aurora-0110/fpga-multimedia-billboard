from pathlib import Path
import os,sys,json,hashlib,subprocess,datetime
r=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=r/'01_project/rtl'
out=r/'04_evidence'/('v123_volume_packets_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
env=dict(os.environ);env.update(TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'),TMPDIR=str(r/'00_tmp'),PYTHONDONTWRITEBYTECODE='1');env['PATH']=str(b)+os.pathsep+env.get('PATH','')
records=[]
for name in ['packets']:
 top='tb_v123_'+name;src=[t/(top+'.sv'),rtl/'audio/i2s_test_tone.v',rtl/'visual/audio_pcm_frontend.v',rtl/'audio/hdmi_audio_packets.v',rtl/'video/video_timing.v']
 exe=out/(name+'.vvp');c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s',top,'-o',str(exe),*map(str,src)],env=env,capture_output=True,text=True,timeout=45);log=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  s=subprocess.run([str(b/'vvp.exe'),str(exe)],env=env,capture_output=True,text=True,timeout=240);log+=s.stdout+s.stderr;rc=s.returncode
 (out/(name+'.log')).write_text(log,encoding='utf8');passed=c.returncode==0 and rc==0 and 'PASS' in log and 'FATAL' not in log and 'ERROR' not in log
 records.append(dict(name=name,passed=passed,source_sha256={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in src+[rtl/'visual/dft_cos_q10.vh',Path(__file__)]},log=log))
 print(name,passed,log[-1600:],flush=True)
summary=dict(passed=all(x['passed']for x in records),complete=True,tests=records,scope='Active volume into actual720p HDMI sample packet FIFO at48k cadence; sample payload/order/gating checked, not electrical acceptance')
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(out);raise SystemExit(0 if summary['passed'] else 1)
