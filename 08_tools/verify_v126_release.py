"""Read-only release file/source/STA integrity check, also works inside frozen archive."""
from pathlib import Path
import json,hashlib,re
r=Path(__file__).resolve().parents[1]
if not (r/'V126_RELEASE_MANIFEST.json').is_file():raise SystemExit('V126 has no released candidate manifest; inspect VERSION_STATUS.json. No test bit was generated.')
m=json.loads((r/'V126_RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
assert m['version']=='v126_fifo_prefix_20261030'
for name,entry in m['files'].items():
 p=r/name
 assert p.resolve().is_relative_to(r.resolve()),name
 assert p.is_file() and p.stat().st_size==entry['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],name
status=json.loads((r/'VERSION_STATUS.json').read_text(encoding='utf-8'))
assert status['simulation_passed'] and status['bit_generated'] and not status['hardware_test'] and not status['flash_modified']
assert len(m['slack_ns'])==4 and min(m['slack_ns'].values())>=0
assert status['slack_ns']==m['slack_ns']
for k in ('no clock','clock definition','invalid constraint','pll/clock buffer clock constraints','combinational loops','no path constraints','shadowed/ignored timing exception constraints'):
 assert m['check_timing_counts'][k]==0,k
assert status['subtitle_asr_implemented'] is False
assert m['fifo_equivalence_cases']==21
print('PASS V126 release: source/evidence/bit hashes, 21-case FIFO equivalence and nonnegative reported STA; NOT hardware/Flash/ASR acceptance.')
print('Candidate:',r/m['recommended_bit'])
print('STA ns:',m['slack_ns'])
print('Checked files:',len(m['files']))
