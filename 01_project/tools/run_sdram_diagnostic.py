"""Fresh TD synthesis + place/route checkpoint. No bitgen, no download.
Exit 0 means numerical checkpoint only; release remains blocked.
"""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys, time
from audit_td_reports import audit

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--td-bin',type=Path,required=True,help='TD bin directory (contains run.exe)')
    ap.add_argument('--out',type=Path,required=True,help='NEW writable output directory')
    ap.add_argument('--timeout',type=int,default=300)
    a=ap.parse_args()
    project=Path(__file__).resolve().parents[1];out=a.out.resolve();td=a.td_bin.resolve()
    if not (td/'run.exe').is_file():ap.error('run.exe missing')
    if out.exists():ap.error('Output exists: choose a NEW path; old results are never overwritten')
    out.mkdir(parents=True)
    env=dict(os.environ);env['PATH']=str(td)+os.pathsep+env.get('PATH','')
    env['ADB_ROOT']=project.as_posix();env['ADB_OUT']=(out/'build').as_posix()
    env['ADB_PHY_OUT']=(out/'reports').as_posix();env.pop('ADB_GATE_DIR',None)
    # An inner Tcl error can still leave TD process exit code 0. Preserve marker.
    wrapper=out/'invoke.tcl'
    script=(project/'build_sdram_video.tcl').as_posix()
    wrapper.write_text('if {[catch {source {'+script+'}} msg opts]} {\n puts "@@@ TASK_ERROR: $msg"\n puts [dict get $opts -errorinfo]\n}\nexit\n',encoding='utf-8')
    record={'target':'EG4S20NG88','scope':'Numerical diagnostic only; NO bitgen or hardware acceptance',
            'source_sha256':{p.relative_to(project).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(project.rglob('*')) if p.is_file() and p.suffix in {'.v','.vh','.tcl','.adc','.sdc'} and 'build' not in p.relative_to(project).parts}}
    start=time.monotonic();rc=None
    with (out/'run.log').open('wb') as f:
        try:
            r=subprocess.run([str(td/'run.exe')],input=('source {'+wrapper.as_posix()+'}\n').encode(),
                stdout=f,stderr=subprocess.STDOUT,env=env,cwd=out,timeout=a.timeout)
            rc=r.returncode
        except subprocess.TimeoutExpired:record['timeout']=True
    record.update(returncode=rc,elapsed_s=round(time.monotonic()-start,3))
    result=audit(out/'reports',out/'run.log')
    synlog=out/'build/sdram_video_Runs/syn_1/run.log'
    import re
    text=synlog.read_text(errors='replace') if synlog.is_file() else ''
    parameter_ok=bool(re.search(r'pack_seq_in_io\s*\|\s*off\s*\|',text))
    if not parameter_ok:result['failures'].append('mandatory pack_seq_in_io=off not confirmed')
    if rc != 0:result['failures'].append('TD process failed or timed out')
    result['numerical_checkpoint_pass']=not result['failures']
    record['pack_seq_in_io_off_confirmed']=parameter_ok
    (out/'attempt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['numerical_checkpoint_pass'] else 2
if __name__=='__main__':sys.exit(main())
