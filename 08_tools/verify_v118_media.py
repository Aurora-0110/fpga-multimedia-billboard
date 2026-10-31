"""Read-only integrity check for v118 media and its unchanged v117/v116 design."""
from pathlib import Path
import hashlib,json,struct
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
manifest=load(ROOT/'04_evidence/v117_release_manifest.json')
meta={name:'BASELINE_v117_'+name for name in ('VERSION_STATUS.json','README_先看这里.md','README_归档位置.md')}
for rel,expected in manifest['files_sha256'].items():
 p=ROOT/meta.get(rel,rel)
 assert p.is_file() and sha(p)==expected,rel
status=load(ROOT/'VERSION_STATUS.json')
assert status['release_version']=='v118' and status['design_version']=='v116'
assert all(status[k] is False for k in ('new_rtl','new_simulation','new_td_build','new_bitstream','tf_files_modified','flash_modified','hardware_acceptance','hardware_download','program_flash_executed','verify_flash_executed','cold_boot_tested','formal_release_approved','actual_long_track_a3_root_cause_closed','handoff_zip_generated'))
assert sha(ROOT/status['bitstream_relative'])==status['bit_sha256']=='540faced66d96a83d6ab6e54caca5e614c54ae6be8822774f35febe1ee6cfdb6'
media=ROOT/status['media_snapshot_relative']
media_manifest=load(media/'MANIFEST_SHA256.json')
for rel,expected in media_manifest['files_sha256'].items():assert sha(media/rel)==expected,rel
report=load(media/'04_records/conversion_report.json')
assert not report['tf_card_read_or_written'] and not report['board_tested']
for entry in report['outputs']:
 p=media/entry['output_relative'];b=p.read_bytes()
 assert b[:2]==b'BM' and len(b)==921654
 assert struct.unpack_from('<I',b,2)[0]==len(b) and struct.unpack_from('<I',b,10)[0]==54
 assert struct.unpack_from('<IiiHHI',b,14)==(40,640,480,1,24,0)
 assert sha(p)==entry['sha256'] and sha(media/entry['original_relative'])==entry['source_sha256']
 with Image.open(p) as bmp,Image.open(media/'02_preview'/(entry['letter']+'.png')) as preview:
  bmp.load();preview.load()
  assert bmp.size==(640,480) and bmp.mode=='RGB' and bmp.tobytes()==preview.tobytes()
assert sorted(p.name for p in (media/'01_TF_ROOT').iterdir())==['B.BMP','C.BMP']
print(json.dumps(dict(passed=True,version=status['version'],design_version='v116',
 unchanged_v117_artifacts_checked=len(manifest['files_sha256']),
 media_manifest_entries=len(media_manifest['files_sha256']),bmp_files=report['outputs'],
 visual_review_recorded=status['media_visual_review_passed'],new_rtl=False,new_bitstream=False,
 tf_written=False,flash_modified=False,actual_board_display_tested=False),ensure_ascii=False,indent=2))
