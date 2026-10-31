from pathlib import Path
import os,subprocess,time,json,hashlib
r=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
o=r/'04_evidence'/('v111_prepared_tmds_'+time.strftime('%Y%m%d_%H%M%S'));o.mkdir();env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
for name in ['exhaustive','pipeline']:
 top='tb_v111_prepared_'+name;src=[t/(top+'.sv'),r/'01_project/rtl/video/tmds_encoder.v'];before={p.relative_to(r).as_posix():sha(p) for p in src+[Path(__file__)]};st=time.monotonic();exe=o/(name+'.vvp')
 c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-Wall','-s',top,'-o',str(exe),*map(str,src)],capture_output=True,text=True,env=env,timeout=45);txt=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  v=subprocess.run([str(b/'vvp.exe'),str(exe)],capture_output=True,text=True,env=env,timeout=180);txt+=v.stdout+v.stderr;rc=v.returncode
 (o/(name+'.log')).write_text(txt,encoding='utf8');row=dict(name=name,passed=c.returncode==0 and rc==0 and 'PASS' in txt and not any(x in txt for x in ['FATAL','ERROR']),source_sha256=before,sources_unchanged_during_run=all(sha(r/k)==v for k,v in before.items()),elapsed_seconds=round(time.monotonic()-st,3),results=[x for x in txt.splitlines() if x.startswith(('PASS','FATAL','ERROR'))]);row['passed']&=row['sources_unchanged_during_run'];rows.append(row);print(row,flush=True)
s=dict(passed=all(x['passed'] for x in rows),complete=len(rows)==2,scope='New prepared-input exhaustive check and actual two-edge three-lane retiming vs independent iterative DVI reference; no physical/electrical claim',tests=rows);(o/'summary.json').write_text(json.dumps(s,indent=2),encoding='utf8');print(o);raise SystemExit(0 if s['passed'] else 1)
