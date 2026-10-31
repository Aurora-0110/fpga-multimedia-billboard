from pathlib import Path
import subprocess,concurrent.futures,datetime,hashlib,json,os,sys,time
root=Path(__file__).resolve().parents[1]
out=root/'04_evidence'/('v123_extended_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
jobs=[('units','02_tests/wav/run_v123_units.py'),('three_wav','02_tests/wav/run_v123_three_wav.py'),('extra_spi','02_tests/wav/run_v123_extra_spi.py'),('ui','02_tests/ui/run_v123_ui.py'),('media','02_tests/media_controls/run_v123_media.py'),('native','02_tests/audio_visual/run_v123_native.py'),('pair_memory','02_tests/scale_pipeline/run_v123_pair_memory.py'),('multires_spi_memory','02_tests/multires/run_v123_spi_memory.py')]
source={f.relative_to(root).as_posix():hashlib.sha256(f.read_bytes()).hexdigest()for f in(root/'01_project').rglob('*')if f.is_file()}
def run(job):
 label,script=job;start=time.monotonic();rec=dict(case=label,script=script,script_sha256=hashlib.sha256((root/script).read_bytes()).hexdigest())
 try:
  c=subprocess.run([sys.executable,str(root/script)],cwd=root,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=1500);text=c.stdout+c.stderr;rec.update(returncode=c.returncode,passed=c.returncode==0)
 except subprocess.TimeoutExpired as ex:text='TIMEOUT\n'+str(ex);rec.update(timeout=True,passed=False)
 (out/(label+'.log')).write_text(text,encoding='utf8');rec.update(elapsed_seconds=round(time.monotonic()-start,3),summary_paths=[line.strip()+'/summary.json'for line in text.splitlines()if line.strip().startswith(str(root/'04_evidence'))and Path(line.strip()).is_dir()]);print(label,rec['passed'],text[-700:],flush=True);return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(run,jobs))
unchanged=all(hashlib.sha256((root/rel).read_bytes()).hexdigest()==h for rel,h in source.items())
summary=dict(passed=all(r['passed']for r in rows)and unchanged,cases=rows,source_sha256=source,sources_unchanged_during_run=unchanged,scope='Fresh units/threeWAV/SPI/UI/gestures/nativeODDR and scaled SPI+SDRAM integration, digital simulation only; not hardware/PVT/electrical acceptance')
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');print(out,flush=True);raise SystemExit(0 if summary['passed']else 1)
