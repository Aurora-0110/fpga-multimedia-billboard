from pathlib import Path
import subprocess,os,datetime,json,hashlib
r=Path(__file__).resolve().parents[1]; rtl=r/'01_project/rtl';b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
out=r/'04_evidence'/('v076_audio_sync_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
sources=[r/'02_tests/tb_v076_audio_sync.sv',rtl/'ip/hdmi_tx_wrap.v',rtl/'video/video_timing.v',rtl/'video/tmds_encoder.v',rtl/'common/reset_release.v',*sorted((rtl/'audio').glob('*.v'))]
cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-s','tb_v076_audio_sync','-o',str(out/'test.vvp'),*map(str,sources)]
c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30);(out/'compile.log').write_text(c.stdout+c.stderr,encoding='utf8');print(c.stdout+c.stderr,flush=True)
record={'compile_rc':c.returncode,'passed':False,'source_sha256':{p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
if c.returncode==0:
 v=subprocess.run([str(b/'vvp.exe'),str(out/'test.vvp'),'+OUT='+out.as_posix()],env=env,capture_output=True,text=True,timeout=650)
 (out/'sim.log').write_text(v.stdout+v.stderr,encoding='utf8');print(v.stdout+v.stderr,flush=True);record.update(sim_rc=v.returncode,passed=v.returncode==0 and 'PASS' in v.stdout)
if record['passed']:
 d=subprocess.run([os.sys.executable,str(r/'02_tests/check_v076_audio_sync.py'),str(out)],capture_output=True,text=True,timeout=30)
 (out/'decode.log').write_text(d.stdout+d.stderr,encoding='utf8');print(d.stdout+d.stderr,flush=True)
 record['independent_decode_rc']=d.returncode;record['passed']=d.returncode==0
(out/'simulation.json').write_text(json.dumps(record,indent=2),encoding='utf8');print(out,flush=True)
raise SystemExit(0 if record['passed'] else 1)
