from pathlib import Path
import os,subprocess,datetime,json,hashlib
r=Path(__file__).resolve().parents[1];b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
out=r/'04_evidence'/('v079_clock_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
src=[r/'02_tests/tb_v079_clock.sv',r/'01_project/rtl/video/osd_layers.v',r/'01_project/rtl/video/official_logo.v']
c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(r/'01_project/rtl'),'-s','tb_v079_clock','-o',str(out/'clock.vvp'),*map(str,src)],env=env,capture_output=True,text=True,timeout=30)
text=c.stdout+c.stderr;rc=None
if c.returncode==0:
 v=subprocess.run([str(b/'vvp.exe'),str(out/'clock.vvp')],env=env,capture_output=True,text=True,timeout=120);text+=v.stdout+v.stderr;rc=v.returncode
(out/'run.log').write_text(text,encoding='utf8');ok=c.returncode==0 and rc==0 and 'PASS clock' in text
(out/'summary.json').write_text(json.dumps({'passed':ok,'scope':'Accelerated FRAMES_PER_SECOND=1 BCD/scroll/mode/reset; real-time accuracy depends on 60Hz video clock, not RTC','sha256':{p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}},indent=2),encoding='utf8')
print(text);print(out);raise SystemExit(0 if ok else 1)
