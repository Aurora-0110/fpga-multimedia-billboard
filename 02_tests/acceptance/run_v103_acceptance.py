"""Bounded TF recovery, non-hideable fault evidence, nominal 48k LPCM and flood/reset tests. No hardware writes."""
from pathlib import Path
import os,sys,subprocess,hashlib,json,datetime,time,concurrent.futures,argparse
r=Path(__file__).resolve().parents[2];rtl=r/'01_project/rtl';t=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--only',nargs='*');a=ap.parse_args()
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
e=dict(os.environ);tmp=r/'00_tmp';tmp.mkdir(exist_ok=True);e.update(PATH=str(b)+os.pathsep+e.get('PATH',''),TEMP=str(tmp),TMP=str(tmp),TMPDIR=str(tmp),PYTHONDONTWRITEBYTECODE='1')
o=r/'04_evidence'/('v103_acceptance_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));o.mkdir()
jobs=[('playlist','tb_v103_playlist',[t/'tb_v103_playlist.sv',rtl/'tf/tf_double_playlist.v']),('diagnostics','tb_v103_diagnostics',[t/'tb_v103_diagnostics.sv',rtl/'video/display_diagnostics_osd.v']),('audio_long','tb_v103_audio_long',[t/'tb_v103_audio_long.sv',rtl/'audio/hdmi_audio_packets.v',rtl/'video/video_timing.v'])]
if a.only:jobs=[x for x in jobs if x[0] in a.only]
assert jobs,'No selected tests'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(job):
 name,top,src=job;bind=src+([rtl/'video/osd_font.vh'] if name=='diagnostics' else [])
 hashes={p.relative_to(r).as_posix():sha(p) for p in bind};start=time.monotonic();exe=o/(name+'.vvp');rc=None
 c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s',top,'-o',str(exe),*map(str,src)],env=e,capture_output=True,text=True,timeout=45);text=c.stdout+c.stderr
 if not c.returncode:
  try:
   v=subprocess.run([str(b/'vvp.exe'),str(exe)],env=e,capture_output=True,text=True,timeout=420);rc=v.returncode;text+=v.stdout+v.stderr
  except subprocess.TimeoutExpired:text+='\nTIMEOUT\n'
 stable=all(sha(r/k)==v for k,v in hashes.items())
 row={'name':name,'compile_rc':c.returncode,'sim_rc':rc,'source_sha256':hashes,'sources_unchanged_during_run':stable,'elapsed_seconds':round(time.monotonic()-start,3),'passed':not c.returncode and rc==0 and 'PASS v103_' in text and 'FATAL' not in text and 'ERROR' not in text and stable,'results':[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR'))]}
 (o/(name+'.log')).write_text(text,encoding='utf8');print(name,row['passed'],row['results'],flush=True)
 if not row['passed']:print(text[-3000:],flush=True)
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(run,jobs))
s={'passed':all(x['passed'] for x in rows),'complete':{x['name'] for x in rows}=={'playlist','diagnostics','audio_long'},'tests':rows,'scope':'v103 fresh module tests: exact TF inactivity with actual-progress input and initial+2 auto retry; old front retained; hidden+historical faults; 8192 stereo24 LPCM samples at nominal48k/74.25M plus queue flood/reset. No actual TF/SDRAM/speaker/cold-start/stress hardware verification.'}
(o/'summary.json').write_text(json.dumps(s,indent=2),encoding='utf8');print(o,flush=True);sys.exit(0 if s['passed'] else 1)
