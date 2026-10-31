from pathlib import Path
import argparse,subprocess,os,json,hashlib
ap=argparse.ArgumentParser();ap.add_argument('--iverilog-bin',type=Path,required=True);a=ap.parse_args()
t=Path(__file__).resolve().parent;b=a.iverilog_bin.resolve();e=dict(os.environ);e['PATH']=str(b)+os.pathsep+e.get('PATH','');o=t/'build/timing_guard';o.mkdir(parents=True,exist_ok=True);l=t/'logs/v054';l.mkdir(parents=True,exist_ok=True)
files=[t/'tb_timing_guard.sv',t.parent/'01_project/rtl/video/video_timing.v']
c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-s','tb_timing_guard','-o',str(o/'test.vvp'),*[str(f) for f in files]],env=e,capture_output=True,text=True,timeout=30);text=c.stdout+c.stderr
row={'compile_returncode':c.returncode,'passed':False,'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
if c.returncode==0:
 v=subprocess.run([str(b/'vvp.exe'),str(o/'test.vvp')],env=e,capture_output=True,text=True,timeout=60);text+=v.stdout+v.stderr;row.update(sim_returncode=v.returncode,passed=v.returncode==0 and text.count('PASS timing_guard')==2)
row['output']=text;(l/'timing_guard.log').write_text(text,encoding='utf-8');(t/'timing_guard_results.json').write_text(json.dumps(row,indent=2),encoding='utf-8');print(text);raise SystemExit(0 if row['passed'] else 1)
