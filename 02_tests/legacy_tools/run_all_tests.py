"""Run four suites, or --collect existing current-source evidence without rerunning."""
from pathlib import Path
import hashlib,json,subprocess,sys,datetime
R=Path(__file__).resolve().parents[1]
for script in (() if '--collect' in sys.argv else ('run_tests.py','run_fat_tests.py','run_pixel_tests.py','run_full_spi_tests.py')):
 cp=subprocess.run([sys.executable,str(R/'tools'/script)])
 if cp.returncode:sys.exit(cp.returncode)
results=[json.loads((R/'04_evidence/sim'/name).read_text()) for name in ('latest_summary.json','fat_latest_summary.json','pixel_latest_summary.json','full_spi_latest_summary.json')]
actual={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.rglob('*.v'))}
assert all(x['source_sha256']==actual for x in results),'Stale simulation source hashes'
assert [(x['passed'],x['total']) for x in results]==[(21,21),(78,78),(30,30),(3,3)]
summary=dict(version='v022_bmp_pixel_stream_20261020',checked_at=datetime.datetime.now().astimezone().isoformat(),passed=132,total=132,source_sha256=actual,hardware_tested=False,scope='21 legacy + 78 header + 30 pixel stream + 3 complete SPI board synthetic tests; not physical proof')
(R/'04_evidence/sim/all_latest_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print('ALL_TESTS_PASS 132/132',flush=True)
