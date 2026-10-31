from pathlib import Path
import subprocess,os,hashlib,json,datetime
r=Path(__file__).resolve().parents[1];t=r/'02_tests';b=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'))
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');e=r/'04_evidence'/('sim_geometry_'+stamp);e.mkdir();out=t/'build'/('geometry_'+stamp);out.mkdir(parents=True)
src=[t/'tb_geometry_equivalence.sv',t/'fixtures/fat32_bmp_probe_v056.v',r/'01_project/rtl/tf/fat32_bmp_probe.v'];exe=out/'geometry.vvp'
cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-s','tb_geometry_equivalence','-o',str(exe),*map(str,src)]
c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=60);(e/'compile.log').write_text(c.stdout+c.stderr,encoding='utf-8')
assert c.returncode==0,c.stderr
p=subprocess.run([str(b/'vvp.exe'),str(exe)],env=env,capture_output=True,text=True,timeout=60);text=p.stdout+p.stderr;(e/'simulation.log').write_text(text,encoding='utf-8')
ok=p.returncode==0 and 'PASS geometry differential cases=2048 accepted=320 rejected=1728' in text and 'FATAL' not in text
(e/'summary.json').write_text(json.dumps(dict(passed=ok,complete=True,scope='2048 deterministic BPB geometry differential cases versus v056; not exhaustive/formal proof',source_sha256={f.relative_to(r).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in src}),indent=2),encoding='utf-8')
print(text);raise SystemExit(not ok)
