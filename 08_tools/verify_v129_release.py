"""Read-only V129 release integrity verification; never tests/programs frozen hardware."""
from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parents[1];m=json.loads((r/'V129_RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
for rel,row in m['files'].items():
 p=r/rel;assert p.is_file(),rel;assert p.stat().st_size==row['bytes']and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],rel
s=json.loads((r/'VERSION_STATUS.json').read_text(encoding='utf-8'))
assert s['version']==m['version']=='v129_third_track_captions_20261030'
assert s['full_user_text_covered']and s['enabled_cues']==69 and s['caption_tracks']==[1,3]
assert not s['human_timing_verified']and not s['hardware_accepted']and not s['flash_modified']and not s['tf_modified']
assert hashlib.sha256((r/m['recommended_bit']).read_bytes()).hexdigest()==s['bit_sha256']==m['bit_sha256']
assert s['network_settings_changed']==False
print('PASS V129 release manifest',len(m['files']),'files; two independent subtitle tracks. Human timing/hardware acceptance pending.')
