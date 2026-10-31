"""Real TD synthesis/route/bit generation in fresh D: attempts. Never programs."""
from pathlib import Path
import argparse,os,json,hashlib,re,subprocess,time,sys,shutil
R=Path(__file__).resolve().parents[1];assert '01_versions'not in R.parts
TD=Path(r'D:\FPGA_Billboard\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def source_hashes():return {f.relative_to(R).as_posix():sha(f)for f in(R/'01_project').rglob('*')if f.is_file()and f.suffix in{'.v','.vh','.tcl','.adc','.sdc','.al','.prj'}}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['synthesis','physical']);p.add_argument('--attempt',type=int,default=1);p.add_argument('--synthesis-attempt',type=int,default=1);p.add_argument('--timeout',type=int,default=1800);a=p.parse_args()
 label='synth'if a.stage=='synthesis'else'physical';out=R/'05_td'/f'v132_audio_visual_{label}_attempt{a.attempt}'
 if out.exists():p.error('No overwrite; choose new attempt.')
 out.mkdir();tmp=R/'00_tmp';tmp.mkdir(exist_ok=True);env=dict(os.environ);env.update(ADB_ROOT=(R/'01_project').as_posix(),TEMP=str(tmp),TMP=str(tmp),TMPDIR=str(tmp),PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
 before=source_hashes();script=R/'01_project'/('build_audio_visual_synth.tcl'if a.stage=='synthesis'else'build_audio_visual_physical_check.tcl')
 if a.stage=='synthesis':env['ADB_OUT']=(out/'build').as_posix();pre=''
 else:
  syn=R/'05_td'/f'v132_audio_visual_synth_attempt{a.synthesis_attempt}'
  sj=json.loads((syn/'attempt.json').read_text('utf8'));assert sj['completed']and sj['source_sha256']==before,'Synthesis not matched to current source'
  gate=syn/'build/idx_video_Runs/syn_1';assert(gate/'idx_video_gate.db').is_file()
  env.update(ADB_GATE_DIR=gate.as_posix(),ADB_PHY_OUT=(out/'physical').as_posix());pre='set ::ADB_DIAGNOSTIC_BIT 1\n'
 invoke=out/'invoke.tcl';invoke.write_text(pre+'if {[catch {source {'+script.as_posix()+'}} msg opts]} {\n puts "@@@ TASK_ERROR: $msg"\n puts [dict get $opts -errorinfo]\n}\nexit\n',encoding='utf8')
 start=time.monotonic();rc=None;timedout=False
 with(out/'run.log').open('wb')as f:
  try:rc=subprocess.run([str(TD/'run.exe')],input=('source {'+invoke.as_posix()+'}\n').encode('utf8'),cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=a.timeout).returncode
  except subprocess.TimeoutExpired:timedout=True
 text=(out/'run.log').read_text(errors='replace');taskerr='@@@ TASK_ERROR:'in text;unchanged=before==source_hashes()
 rec=dict(scope='Actual same-source EG4S20NG88 TD build; no hardware/TF/Flash/network changes.',source_sha256=before,source_unchanged=unchanged,returncode=rc,timedout=timedout,elapsed_seconds=round(time.monotonic()-start,2),task_error=taskerr,completed=False)
 if a.stage=='synthesis':
  gate=out/'build/idx_video_Runs/syn_1';db=gate/'idx_video_gate.db';area=gate/'idx_video_gate.area';rec.update(gate_db_present=db.is_file(),area_present=area.is_file(),synth_marker_present='@@@ V119 RESOURCE-OPTIMIZED AUDIO VISUAL SYNTHESIS END'in text)
  if area.is_file():
   s=area.read_text();rec['resources']={k:int(re.search(r'^#'+k+r'\s+(\d+)',s,re.M).group(1))for k in['lut','reg','bram','bram32k','dsp','pll','gclk','pad']}
  rec['completed']=rc==0 and not timedout and not taskerr and unchanged and db.is_file()and area.is_file()and rec['synth_marker_present']
  if rec['completed']:
   pres=R/'04_evidence'/f'v132_synthesis_preserved_attempt{a.attempt}';pres.mkdir()
   for f in gate.iterdir():
    if f.is_file()and f.suffix in{'.db','.prj','.area','.cfg','.rpt'}:shutil.copy2(f,pres/f.name)
   rec['gate_db_sha256']=sha(db)
 else:
  report=out/'physical/sdram_phy.ts';s=report.read_text()if report.is_file()else'';slack={}
  for n in['SWNS','STNS','HWNS','HTNS']:
   m=re.search(r'\b'+n+r':\s*([-+]?\d+(?:\.\d+)?)',s)
   if m:slack[n]=float(m.group(1))
  area=out/'physical/sdram_phy.area'
  if area.is_file():
   at=area.read_text();rec['resources']={k:int(re.search(r'^#'+k+r'\s+(\d+)',at,re.M).group(1))for k in['lut','reg','bram','bram32k','dsp','pll','gclk','pad']}
  bit=out/'physical/v119_audio_pingpong_720p.bit';rec.update(slack_ns=slack,nonnegative_slack=len(slack)==4 and all(v>=0 for v in slack.values()),bit_present=bit.is_file()and bit.stat().st_size>0,gate_db_sha256=sha(gate/'idx_video_gate.db'),warning_lines=[x for x in text.splitlines()if 'WARNING:'in x])
  rec['completed']=rc==0 and not timedout and not taskerr and unchanged and rec['nonnegative_slack']and rec['bit_present']
 (out/'attempt.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in rec.items()if k!='source_sha256'},ensure_ascii=False,indent=2));print(out,flush=True);return 0 if rec['completed']else 2
if __name__=='__main__':raise SystemExit(main())
