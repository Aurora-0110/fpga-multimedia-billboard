from pathlib import Path
import concurrent.futures,subprocess,sys,datetime,json,os,hashlib
r=Path(__file__).resolve().parents[1];o=r/'04_evidence'/('v126_fifo_integrations_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));o.mkdir()
jobs=[('three_wav','02_tests/wav/run_v126_three_wav.py',[]),('spi_production','02_tests/wav/run_v126_extra_spi.py',['--production','--mode','1','--sdsc','0','--timeout','600'])]
def run(j):
 label,s,args=j;p=r/s;c=subprocess.run([sys.executable,str(p),*args],cwd=r,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=900);text=c.stdout+c.stderr;(o/(label+'.log')).write_text(text,encoding='utf8');print(label,c.returncode,text[-3000:],flush=True);return dict(case=label,passed=c.returncode==0,script_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as ex:rows=list(ex.map(run,jobs))
rec=dict(passed=all(x['passed']for x in rows),cases=rows,scope='Fresh production-depth FIFO three-WAV complete regression and one representative actual SPI pin audio+image case; not hardware or complete 720p SDRAM output test.')
(o/'summary.json').write_text(json.dumps(rec,indent=2),encoding='utf8');print(o);raise SystemExit(0 if rec['passed']else 1)
