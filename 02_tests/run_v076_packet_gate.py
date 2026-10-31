from pathlib import Path
import subprocess,os,json,hashlib,datetime
r=Path(__file__).resolve().parents[1];b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
out=r/'04_evidence'/('v076_packet_gate_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
src=[r/'02_tests/tb_v076_packet_gate.sv',r/'01_project/rtl/audio/hdmi_audio_packets.v']
c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-Wall','-s','tb_v076_packet_gate','-o',str(out/'test.vvp'),*map(str,src)],env=env,capture_output=True,text=True,timeout=30)
text=c.stdout+c.stderr;rc=None
if c.returncode==0:
 v=subprocess.run([str(b/'vvp.exe'),str(out/'test.vvp')],env=env,capture_output=True,text=True,timeout=30);text+=v.stdout+v.stderr;rc=v.returncode
(out/'test.log').write_text(text,encoding='utf8');passed=c.returncode==0 and rc==0 and 'PASS' in text
(out/'summary.json').write_text(json.dumps({'passed':passed,'source_sha256':{s.relative_to(r).as_posix():hashlib.sha256(s.read_bytes()).hexdigest() for s in src}},indent=2),encoding='utf8');print(text);print(out);raise SystemExit(0 if passed else 1)

