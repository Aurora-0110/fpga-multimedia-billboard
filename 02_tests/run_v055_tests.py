"""v055 regression. Run only in a WORKING COPY, never an archive snapshot."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--iverilog-bin',type=Path,required=True)
ap.add_argument('--td-sim-dir',type=Path,required=True)
ap.add_argument('--quick',action='store_true',help='Omit the long full-frame memory cases; not full acceptance')
a=ap.parse_args();t=Path(__file__).resolve().parent;root=t.parent
sources=[f for d in [root/'01_project',t] for f in d.rglob('*') if f.is_file() and f.suffix in {'.v','.vh','.sv','.adc','.sdc','.tcl','.py'} and not any(x in f.relative_to(root).parts for x in ['build','__pycache__'])]
def hashes():return {f.relative_to(root).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(sources)}
before=hashes();stamp=time.strftime('%Y%m%d_%H%M%S');rows=[]
cases=[('run_tmds_native.py',['--td-sim-dir',str(a.td_sim_dir)]),('run_tmds_dual_reset.py',['--td-sim-dir',str(a.td_sim_dir)]),('run_key_retry.py',[]),('run_timing_guard.py',[]),('run_retry_timing.py',[]),('run_top_reset.py',[])]
if not a.quick:cases.append(('run_idx_tests.py',['--tag','reproduce_'+stamp]))
for script,extra in cases:
 cmd=[sys.executable,str(t/script),'--iverilog-bin',str(a.iverilog_bin),*extra]
 start=time.monotonic();c=subprocess.run(cmd,timeout=3000)
 rows.append(dict(script=script,command=cmd,returncode=c.returncode,passed=c.returncode==0,elapsed_s=round(time.monotonic()-start,3)))
 if c.returncode:break
after=hashes();record=dict(quick_only=a.quick,cases=rows,source_sha256=before,source_unchanged=before==after,passed=all(r['passed'] for r in rows) and len(rows)==len(cases) and before==after)
out=t/('regression_'+stamp+'.json');out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('REGRESSION',out,'PASS' if record['passed'] else 'FAIL',flush=True)
raise SystemExit(0 if record['passed'] else 1)
