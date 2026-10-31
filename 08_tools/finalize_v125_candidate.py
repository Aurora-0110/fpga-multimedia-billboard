from pathlib import Path
import time,json,subprocess,sys,os,datetime
r=Path(__file__).resolve().parents[1]
path=r/'05_td/v125_audio_visual_physical_attempt1/attempt.json';deadline=time.monotonic()+600
print('Waiting with600-second limit for the active physical implementation; no programming/Flash.',flush=True)
while not path.exists():
 if time.monotonic()>deadline:raise TimeoutError('Physical report not ready within bounded wait')
 time.sleep(1)
physical=json.loads(path.read_text(encoding='utf8'))
if not physical['completed']:raise RuntimeError('Physical STA not closed; bit generation remains blocked: '+str(physical.get('slack_ns')))
steps=[('resources','08_tools/review_v125_resources.py'),('rom','02_tests/ui/check_v125_rom_init.py'),('guarded_bit','02_tests/audio_visual/run_v125_bitgen.py')]
out=r/'04_evidence'/('v125_finalize_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir();rows=[]
for label,script in steps:
 p=subprocess.run([sys.executable,str(r/script)],cwd=r,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=360)
 text=p.stdout+p.stderr;(out/(label+'.log')).write_text(text,encoding='utf8');print(label,p.returncode,text[-1600:],flush=True);rows.append(dict(case=label,passed=p.returncode==0))
 (out/'summary.json').write_text(json.dumps(dict(passed=len(rows)==3 and all(x['passed']for x in rows),steps=rows),indent=2),encoding='utf8')
 if p.returncode:raise SystemExit(p.returncode)
print('Candidate bit generated; no hardware acceptance is implied.',out,flush=True)
