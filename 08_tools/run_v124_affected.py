from pathlib import Path
import os,sys,json,subprocess,datetime,hashlib,concurrent.futures,time
r=Path(__file__).resolve().parents[1];out=r/'04_evidence'/('v124_affected_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
env=dict(os.environ);env.update(PYTHONIOENCODING='utf-8',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'),TMPDIR=str(r/'00_tmp'))
source={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in (r/'01_project').rglob('*')if p.is_file()}
jobs=[('media','02_tests/media_controls/run_v124_media.py',[]),('ui','02_tests/ui/run_v124_ui.py',[]),('native','02_tests/audio_visual/run_v124_volume_native.py',[]),('ui_audio','02_tests/wav/run_v124_ui_audio.py',['--only','1']),('visual_core','02_tests/audio_visual/run_v124_tests.py',['--only','activity','power_level','logo','dft','osd','tmds'])]
def run(j):
 label,script,args=j;start=time.monotonic();p=r/script
 try:
  c=subprocess.run([sys.executable,str(p),*args],cwd=r,env=env,capture_output=True,text=True,timeout=1800);text=c.stdout+c.stderr;rc=c.returncode
 except subprocess.TimeoutExpired as ex:text=str(ex);rc=-1
 (out/(label+'.log')).write_text(text,encoding='utf8');print(label,rc,text[-1800:],flush=True)
 return dict(case=label,passed=rc==0,returncode=rc,seconds=round(time.monotonic()-start,2),script_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),summary_paths=[line.strip()+'/summary.json'for line in text.splitlines()if line.strip().startswith(str(r/'04_evidence'))and Path(line.strip()).is_dir()])
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as p:rows=list(p.map(run,jobs))
unchanged=all(hashlib.sha256((r/p).read_bytes()).hexdigest()==h for p,h in source.items());summary=dict(passed=all(x['passed']for x in rows)and unchanged,cases=rows,source_sha256=source,sources_unchanged_during_run=unchanged,scope='Fresh V124 control/UI/spectrum/native regressions; exact-source-identical V123 reader/FIFO/SPI regressions inherited separately. No ASR/hardware claim')
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(out,flush=True);raise SystemExit(0 if summary['passed']else 1)
