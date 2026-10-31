from pathlib import Path
import subprocess,concurrent.futures,datetime,os,json,hashlib,sys
root=Path(__file__).resolve().parents[1];out=root/'04_evidence'/('v123_regression_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
env=dict(os.environ);env.update(PYTHONIOENCODING='utf-8',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),TMPDIR=str(root/'00_tmp'))
jobs=[
 ('playback8','02_tests/wav/run_v114_playback_tests.py',[]),
 ('audio_diag_raster','02_tests/audio_visual/run_v114_audio_diag.py',[]),
 ('old_no_bmp','02_tests/wav/run_v116_refill_budget.py',['--baseline','--bmp','0','--under','0']),
 ('new_spc1_pause','02_tests/wav/run_v116_refill_budget.py',['--mode','1','--under','0']),
 ('buffers5','02_tests/wav/run_v114_buffers2.py',[]),
 ('old_spc64','02_tests/wav/run_v116_refill_budget.py',['--baseline','--spc','64','--wait','1600','--under','1']),
 ('new_spc64','02_tests/wav/run_v116_refill_budget.py',['--spc','64','--wait','1600','--under','0']),
 ('ui_audio_controls','02_tests/wav/run_v114_ui_audio.py',['--only','1']),
 ('underrun_recovery','02_tests/wav/run_v114_underrun_recovery.py',[]),
 ('top720p','02_tests/audio_visual/run_v114_tests.py',['--only','top']),
 ('actual_spi_switch','02_tests/wav/run_v116_actual_spi_tests.py',['--short','--mode','3','--sdsc','1','--timeout','600'])]
prod={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in (root/'01_project').rglob('*')if p.is_file()}
def run(job):
 label,script,args=job;start=datetime.datetime.now().astimezone().isoformat();p=root/script;rec={'case':label,'script':script,'script_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'args':args,'started':start}
 try:
  c=subprocess.run([sys.executable,str(p),*args],cwd=root,env=env,capture_output=True,text=True,timeout=1000);text=c.stdout+c.stderr;rec.update(returncode=c.returncode,passed=c.returncode==0)
 except subprocess.TimeoutExpired as e:text='TIMEOUT\n'+str(e);rec.update(timeout=True,passed=False)
 (out/(label+'.log')).write_text(text,encoding='utf-8');rec['finished']=datetime.datetime.now().astimezone().isoformat();rec['summary_paths']=[line.strip()+'/summary.json'for line in text.splitlines()if line.strip().startswith(str(root/'04_evidence'))and Path(line.strip()).is_dir()]
 print(label,'PASS'if rec['passed']else 'FAIL',text[-750:],flush=True);return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:rows=list(pool.map(run,jobs))
unchanged=all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in prod.items())
rec={'passed':all(row['passed']for row in rows)and unchanged,'cases':rows,'source_sha256':prod,'sources_unchanged_during_run':unchanged,'scope':'Fresh targeted regression on v123 address-optimized production RTL. Deterministic budget tests are16x accelerated, pin integration uses short512FIFO SD behavior card, top720p injects memory. NOT actual board/TF/PVT acceptance.'}
(out/'summary.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf8');print(out,flush=True);raise SystemExit(0 if rec['passed']else 1)
