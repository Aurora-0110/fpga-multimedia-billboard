"""Read-only verification of v115 saved audit, unchanged v114 RTL and bitstream."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
status=load(root/'VERSION_STATUS.json')
manifest=load(root/'04_evidence/v115_record_manifest.json')
for rel,h in manifest['files_sha256'].items():
 p=root/rel
 assert p.is_file()and sha(p)==h,rel
for rel,h in status['production_files_sha256'].items():assert sha(root/rel)==h,rel
report=load(root/status['audio_audit_report'])
assert report['passed']and len(report['files'])==2
for rel,h in report['source_sha256'].items():assert sha(root/rel)==h,rel
for entry in report['files']:
 assert entry['pass_all']and entry['byte_for_byte_equal']and entry['stable_during_read']
 assert entry['sha256']==entry['expected_sha256']==entry['sha256_after_checks']
 assert entry['full_decode']['pass']and entry['full_decode']['stderr_empty']
 assert entry['full_decode']['returncode']==0
 golden=root/'06_test_media/audio'/Path(entry['path']).name
 assert sha(golden)==entry['sha256'],str(golden)
 log=(root/status['audio_audit_report']).parent/Path(entry['full_decode']['stderr_log']).name
 assert log.is_file()and not log.read_text(encoding='utf8').strip(),str(log)
bit=root/status['bitstream_relative']
assert sha(bit)==status['bitstream_sha256']
assert not any(status[k]for k in ('new_rtl','new_simulation','new_td_build','new_bitstream','hardware_download','hardware_acceptance','flash_modified','input_files_modified','handoff_zip_generated','a3_root_cause_closed'))
print(json.dumps(dict(passed=True,version=status['version'],checked_artifacts=len(manifest['files_sha256']),unchanged_production_files=len(status['production_files_sha256']),supplied_files_matched=2,bitstream_version='v114',bitstream_unchanged=True,scope='Saved evidence consistency only; does not re-read E or accept hardware'),ensure_ascii=False,indent=2))
