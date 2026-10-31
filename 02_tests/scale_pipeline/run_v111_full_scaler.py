"""Two complete 720p streams, independent per-pixel oracle, parallel finite runs.
The historical900s attempt was a wall timeout, not a passing result.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,os,subprocess,time
r=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent
out=r/'04_evidence'/('v111_full_scaler_'+time.strftime('%Y%m%d_%H%M%S'));out.mkdir()
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[t/'tb_full_scaler.sv',r/'01_project/rtl/scale/bilinear_stream_scaler.v',r/'01_project/rtl/scale/bilinear_rgb888.v',Path(__file__)]
before={p.relative_to(r).as_posix():sha(p) for p in sources}
summary=dict(passed=False,scope='Real bilinear scaler RTL: two COMPLETE1280x720 outputs vs independent per-pixel integer oracle, not SDRAM/video/physical hardware',source_sha256=before,cases=[])
exe=out/'full.vvp';c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-Wall','-s','tb_full_scaler','-o',str(exe),*map(str,sources[:-1])],capture_output=True,text=True,env=env,timeout=45)
(out/'compile.log').write_text(c.stdout+c.stderr,encoding='utf8');assert c.returncode==0,c.stderr
start=time.monotonic()
def run(case):
 w,h,td=case;name=f'{w}x{h}_td{td}';row=dict(source=[w,h],top_down=bool(td),passed=False,wall_timeout_seconds=2400);st=time.monotonic()
 with (out/(name+'.log')).open('w',encoding='utf8') as f:
  try:v=subprocess.run([str(b/'vvp.exe'),str(exe),f'+W={w}',f'+H={h}',f'+TD={td}'],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=2400);row['returncode']=v.returncode
  except subprocess.TimeoutExpired:row['timeout']=True
 text=(out/(name+'.log')).read_text(encoding='utf8');row.update(passed=row.get('returncode')==0 and 'PASS full_scaler' in text and not any(x in text for x in ['FATAL','ERROR']),elapsed_seconds=round(time.monotonic()-st,3),results=[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR','PROGRESS'))]);print(name,row,flush=True);return row
with ThreadPoolExecutor(max_workers=2) as pool:summary['cases']=list(pool.map(run,[(640,480,1),(17,11,0)]))
summary.update(elapsed_seconds=round(time.monotonic()-start,3),sources_unchanged_during_run=all(sha(r/k)==v for k,v in before.items()))
summary['passed']=all(x['passed'] for x in summary['cases']) and summary['sources_unchanged_during_run'];summary['result']='PASS' if summary['passed'] else 'FAIL'
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(out,flush=True);raise SystemExit(0 if summary['passed'] else 1)
