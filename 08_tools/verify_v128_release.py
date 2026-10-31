from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parents[1];m=json.loads((r/'V128_RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
for rel,row in m['files'].items():
 p=r/rel;assert p.is_file(),rel;assert p.stat().st_size==row['bytes']and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],rel
s=json.loads((r/'VERSION_STATUS.json').read_text(encoding='utf-8'))
assert s['version']==m['version']=='v128_lyrics_alignment_20261030'
assert s['full_user_text_covered']and s['enabled_cues']==53 and not s['human_timing_verified']and not s['hardware_accepted']
assert hashlib.sha256((r/m['recommended_bit']).read_bytes()).hexdigest()==s['bit_sha256']==m['bit_sha256']
print('PASS V128 release manifest',len(m['files']),'files; full user text, timing/hardware acceptance still pending')