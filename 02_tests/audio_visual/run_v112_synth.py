"""Compile the actual separate full720p board candidate, synthesis only."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,time

root=Path(__file__).resolve().parents[2];project=root/'01_project'
parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,default=1);args=parser.parse_args()
out=root/f'05_td/v112_audio_visual_synth_attempt{args.attempt}'
assert not out.exists(),'Never overwrite synthesis evidence'
out.mkdir(parents=True)
td=Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin')
env=dict(os.environ);env['PATH']=str(td)+os.pathsep+env.get('PATH','')
temp_dir=root/'00_tmp';temp_dir.mkdir(exist_ok=True)
env.update(TEMP=str(temp_dir),TMP=str(temp_dir),TMPDIR=str(temp_dir),PYTHONDONTWRITEBYTECODE='1')
env['ADB_ROOT']=project.as_posix();env['ADB_OUT']=(out/'build').as_posix()
record={'scope':'Actual idx_audio_visual_top system candidate, synthesis ONLY; no place/route/timing/bit/hardware',
        'source_sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in project.rglob('*') if p.is_file() and p.suffix in {'.v','.vh','.tcl','.adc','.sdc'} and 'build' not in p.relative_to(project).parts}}
script=project/'build_audio_visual_synth.tcl';wrapper=out/'invoke.tcl'
wrapper.write_text('if {[catch {source {'+script.as_posix()+'}} msg opts]} {\n puts "@@@ TASK_ERROR: $msg"\n puts [dict get $opts -errorinfo]\n}\nexit\n',encoding='utf-8')
start=time.monotonic()
with (out/'run.log').open('wb') as f:
 try:
  c=subprocess.run([str(td/'run.exe')],input=('source {'+wrapper.as_posix()+'}\n').encode(),cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=420)
  record['returncode']=c.returncode
 except subprocess.TimeoutExpired:record['timeout']=True
text=(out/'run.log').read_text(encoding='utf-8',errors='replace')
gate=out/'build/idx_video_Runs/syn_1/idx_video_gate.db';area=gate.with_suffix('.area')
record.update(elapsed_seconds=round(time.monotonic()-start,3),task_error='@@@ TASK_ERROR:' in text,
              synth_marker_present='@@@ V112 RESOURCE-OPTIMIZED AUDIO VISUAL SYNTHESIS END' in text,gate_db_present=gate.is_file(),area_present=area.is_file())
if area.is_file():
 s=area.read_text(encoding='utf-8',errors='replace')
 record['resources']={k:int(re.search(r'^#'+k+r'\s+(\d+)',s,re.M).group(1)) for k in ['lut','reg','bram','bram32k','dsp','pll','gclk','pad']}
 record['within_capacities']=all(record['resources'][k]<=n for k,n in {'lut':19600,'reg':19600,'bram':64,'bram32k':16,'dsp':29,'pll':4,'gclk':16,'pad':66}.items())
record['completed']=record.get('returncode')==0 and not record['task_error'] and record['synth_marker_present'] and record['gate_db_present'] and record.get('within_capacities',False)
(out/'attempt.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='source_sha256'},indent=2),flush=True);print(out,flush=True)
raise SystemExit(0 if record['completed'] else 1)
