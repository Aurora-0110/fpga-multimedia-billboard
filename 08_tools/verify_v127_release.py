"""Verify V127 local release bytes only. Does not execute tools or program hardware."""
from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parents[1];p=r/'V127_RELEASE_MANIFEST.json';j=json.loads(p.read_text(encoding='utf8'))
assert j['version']=='v127_sample_captions_20261030'and j['hardware_accepted']is False and j['complete_lyrics']is False
assert len(j['slack_ns'])==4 and min(j['slack_ns'].values())>=0
for rel,entry in j['files'].items():
 q=Path(rel);assert not q.is_absolute()and '..'not in q.parts
 q=r/q;assert q.is_file()and q.stat().st_size==entry['bytes']and hashlib.sha256(q.read_bytes()).hexdigest()==entry['sha256'],rel
bit=r/j['recommended_bit'];assert bit.is_file()and bit.stat().st_size>0
print('PASS V127 release byte verification',len(j['files']),'files; bit SHA256',hashlib.sha256(bit.read_bytes()).hexdigest())
print('Not hardware acceptance, full lyrics correctness, Flash approval or PVT signoff.')
