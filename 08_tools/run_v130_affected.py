"""Run six nonvisual affected groups and bind this run's independently passed UI/media."""
from pathlib import Path
import os,sys,json,subprocess,datetime,hashlib,concurrent.futures,time
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
out=r/'04_evidence'/('v130_affected_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();env=dict(os.environ);env.update(PYTHONIOENCODING='utf-8',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'),TMPDIR=str(r/'00_tmp'))
source={p.relative_to(r).as_posix():sha(p)for p in (r/'01_project').rglob('*')if p.is_file()}
jobs=[('numeric_frontend','02_tests/volume/run_v126_volume.py',[]),('volume_hdmi','02_tests/volume/run_v126_packets.py',[]),('top_spectrum','02_tests/audio_visual/run_v130_tests.py',['--only','top','overlay','audio_pcm']),('native','02_tests/audio_visual/run_v126_volume_native.py',[]),('ui_audio','02_tests/wav/run_v128_ui_audio.py',['--only','1']),('visual_core','02_tests/audio_visual/run_v130_tests.py',['--only','activity','power_level','logo','dft','osd','tmds'])]
def run(j):
 label,script,args=j;start=time.monotonic();p=r/script
 try:
  c=subprocess.run([sys.executable,str(p),*args],cwd=r,env=env,capture_output=True,text=True,timeout=900);text=c.stdout+c.stderr;rc=c.returncode
 except subprocess.TimeoutExpired as ex:text=str(ex);rc=-1
 (out/(label+'.log')).write_text(text,encoding='utf-8');print(label,rc,text[-1800:],flush=True)
 return dict(case=label,passed=rc==0,returncode=rc,seconds=round(time.monotonic()-start,2),script_sha256=sha(p),summary_paths=[line.strip()+'/summary.json'for line in text.splitlines()if line.strip().startswith(str(r/'04_evidence'))and Path(line.strip()).is_dir()])
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:rows=list(pool.map(run,jobs))
for label,pattern,script in [('media','v130_media_[0-9]*','02_tests/media_controls/run_v130_media.py'),('ui','v130_ui_[0-9]*','02_tests/ui/run_v130_ui.py')]:
 dirs=sorted((r/'04_evidence').glob(pattern));p=dirs[-1]/'summary.json';j=json.loads(p.read_text(encoding='utf-8'));assert j['passed']and j['complete'],str(p)
 for row in j['tests']:
  for rel,h in row['source_sha256'].items():assert sha(r/rel)==h,rel
 rows.append(dict(case=label,passed=True,same_version_completed_earlier_this_turn=True,not_inherited_baseline=True,script_sha256=sha(r/script),summary_paths=[str(p)]))
unchanged=all(sha(r/p)==h for p,h in source.items());summary=dict(passed=len(rows)==8 and all(x['passed']for x in rows)and unchanged,cases=rows,source_sha256=source,sources_unchanged_during_run=unchanged,scope='Fresh V130 groups including this-turn16-row UI and4-state controls. Byte-identical TF/SPI/SDRAM core evidence explicitly inherited separately, not falsely rerun/hardware accepted.')
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(out,flush=True);raise SystemExit(0 if summary['passed']else 1)
