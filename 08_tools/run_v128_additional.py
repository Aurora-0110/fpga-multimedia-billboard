from pathlib import Path
import concurrent.futures,subprocess,sys,json,datetime,hashlib,os,time
r=Path(__file__).resolve().parents[1];out=r/'04_evidence'/('v128_additional_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
jobs=[('actual_top','02_tests/captions/run_v128_caption_top.py',[]),('three_wav','02_tests/wav/run_v128_three_wav.py',[]),('spi_production','02_tests/wav/run_v128_extra_spi.py',['--production','--mode','1','--sdsc','0','--timeout','600']),('arbiter_units','02_tests/wav/run_v128_units.py',[])]
def run(row):
 name,rel,args=row;start=time.monotonic()
 try:
  c=subprocess.run([sys.executable,str(r/rel),*args],cwd=r,capture_output=True,text=True,timeout=900);text=c.stdout+c.stderr;rc=c.returncode
 except subprocess.TimeoutExpired as ex:text=str(ex);rc=-1
 (out/(name+'.log')).write_text(text,encoding='utf-8');print(name,rc,text[-2100:],flush=True)
 return dict(name=name,passed=rc==0,returncode=rc,seconds=round(time.monotonic()-start,3),script_sha256=hashlib.sha256((r/rel).read_bytes()).hexdigest())
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(run,jobs))
(out/'summary.json').write_text(json.dumps(dict(passed=all(x['passed']for x in results),cases=results,scope='Fresh caption top wiring,3WAV consumer/FIFO,actual SPI production pins and arbiter diagnostics; no programming.'),indent=2),encoding='utf-8')
print(out);raise SystemExit(0 if all(x['passed']for x in results)else 1)
