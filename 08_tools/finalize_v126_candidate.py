"""Bounded, source/test/STA-guarded finalization. Does not program FPGA/Flash."""
from pathlib import Path
import time,json,subprocess,sys,os,datetime,argparse
r=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--physical-attempt',type=int,default=1);args=a.parse_args()
path=r/f'05_td/v126_audio_visual_physical_attempt{args.physical_attempt}/attempt.json';deadline=time.monotonic()+960
print('Bounded wait for selected implementation and production FIFO integration tests; no programming/Flash.',flush=True)
while not path.exists():
 if time.monotonic()>deadline:raise TimeoutError('Physical report not ready within bounded wait')
 time.sleep(1)
physical=json.loads(path.read_text(encoding='utf8'))
if not physical['completed']:raise RuntimeError('Physical STA not closed; bit generation remains blocked: '+str(physical.get('slack_ns',physical.get('warning_lines'))))
while not sorted((r/'04_evidence').glob('v126_fifo_integrations_*/summary.json')):
 if time.monotonic()>deadline:raise TimeoutError('FIFO integration summary not ready')
 time.sleep(1)
integ=json.loads(sorted((r/'04_evidence').glob('v126_fifo_integrations_*/summary.json'))[-1].read_text(encoding='utf8'));assert integ['passed']
steps=[('resources','08_tools/review_v126_resources.py'),('rom','02_tests/ui/check_v126_rom_init.py'),('guarded_bit','02_tests/audio_visual/run_v126_bitgen.py')]
out=r/'04_evidence'/('v126_finalize_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir();rows=[]
for label,script in steps:
 p=subprocess.run([sys.executable,str(r/script),'--physical-attempt',str(args.physical_attempt)],cwd=r,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=360)
 text=p.stdout+p.stderr;(out/(label+'.log')).write_text(text,encoding='utf8');print(label,p.returncode,text[-2400:],flush=True);rows.append(dict(case=label,passed=p.returncode==0))
 (out/'summary.json').write_text(json.dumps(dict(passed=len(rows)==3 and all(x['passed']for x in rows),selected_physical_attempt=args.physical_attempt,steps=rows),indent=2),encoding='utf8')
 if p.returncode:raise SystemExit(p.returncode)
print('Candidate bit generated; no hardware acceptance is implied.',out,flush=True)
