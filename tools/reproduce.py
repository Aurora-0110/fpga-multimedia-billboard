"""Configurable V132 reproduction entry. Never programs or writes TF/Flash."""
from pathlib import Path
import argparse,subprocess,os,sys,json,hashlib,datetime,re,shutil
ROOT=Path(__file__).resolve().parents[1]

def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('action',choices=['verify','test','synthesis','implementation'])
 p.add_argument('--case',choices=['font','controls','ui','captions','logo'],default='font')
 p.add_argument('--iverilog-bin',default=os.environ.get('FPGA_IVERILOG_BIN'))
 p.add_argument('--td-bin',default=os.environ.get('FPGA_TD_BIN'))
 p.add_argument('--timeout',type=int,default=1800)
 a=p.parse_args();env=dict(os.environ);tmp=ROOT/'00_tmp';tmp.mkdir(exist_ok=True)
 env.update(TEMP=str(tmp),TMP=str(tmp),TMPDIR=str(tmp),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
 if a.action=='verify':return subprocess.call([sys.executable,'-B',str(ROOT/'tools/verify_public.py')],env=env)
 if a.action=='test':
  iv=Path(a.iverilog_bin)if a.iverilog_bin else Path(shutil.which('iverilog')or'').parent
  names=['iverilog.exe','vvp.exe']if os.name=='nt'else['iverilog','vvp']
  if not all((iv/x).is_file()for x in names):p.error('Set --iverilog-bin to the directory containing iverilog and vvp.')
  env['FPGA_IVERILOG_BIN']=str(iv.resolve());env['PATH']=str(iv.resolve())+os.pathsep+env.get('PATH','')
  return subprocess.call([sys.executable,'-B',str(ROOT/'tools/portable_v132'/('run_'+a.case+'.py'))],cwd=ROOT,env=env)
 if not a.td_bin:p.error('Set --td-bin to the TD6.2.1 bin directory.')
 td=Path(a.td_bin);run=td/('run.exe'if os.name=='nt'else'run');
 if not run.is_file():p.error('TD run executable missing: '+str(run))
 out=ROOT/'runs'/('build_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir(parents=True)
 source={f.relative_to(ROOT).as_posix():sha(f)for f in(ROOT/'01_project').rglob('*')if f.is_file()}
 env['ADB_ROOT']=(ROOT/'01_project').as_posix();env['ADB_OUT']=(out/'synthesis').as_posix()
 def invoke(stage,script,extra=''):
  task=out/(stage+'.tcl');task.write_text(extra+'if {[catch {source {'+script.as_posix()+'}} msg opts]} {puts "@@@ REPRO_ERROR: $msg";puts [dict get $opts -errorinfo]}\nexit\n',encoding='utf8')
  log=out/(stage+'.log')
  with log.open('wb')as f:
   rc=subprocess.run([str(run)],input=('source {'+task.as_posix()+'}\n').encode(),cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=a.timeout).returncode
  text=log.read_text(errors='replace');return rc==0 and '@@@ REPRO_ERROR:'not in text
 ok=invoke('synthesis',ROOT/'01_project/build_audio_visual_synth.tcl')
 gate=out/'synthesis/idx_video_Runs/syn_1';ok=ok and(gate/'idx_video_gate.db').is_file()
 if ok and a.action=='implementation':
  env['ADB_GATE_DIR']=gate.as_posix();env['ADB_PHY_OUT']=(out/'physical').as_posix()
  ok=invoke('physical',ROOT/'01_project/build_audio_visual_physical_check.tcl','set ::ADB_DIAGNOSTIC_BIT 1\n')
  timing=out/'physical/sdram_phy.ts';slack={}
  if timing.is_file():
   text=timing.read_text()
   for name in ['SWNS','STNS','HWNS','HTNS']:
    m=re.search(r'\b'+name+r':\s*([-+]?\d+(?:\.\d+)?)',text)
    if m:slack[name]=float(m.group(1))
  ok=ok and len(slack)==4 and all(v>=0 for v in slack.values())and(out/'physical/v119_audio_pingpong_720p.bit').is_file()
 else:slack=None
 unchanged=all(sha(ROOT/f)==h for f,h in source.items());ok=ok and unchanged
 rec=dict(passed=ok,action=a.action,source_unchanged=unchanged,source_sha256=source,slack_ns=slack,hardware_programmed=False,formal_release_approved=False,notes='Fresh output only; reports and retained device/timing boundaries must be reviewed, not exit code alone.')
 (out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in rec.items()if k!='source_sha256'},indent=2));print(out)
 return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
