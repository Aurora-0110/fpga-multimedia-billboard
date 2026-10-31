"""Read-only check of release hashes and matching test/build provenance."""
from pathlib import Path,PurePosixPath
import hashlib,json,sys
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check_provenance():
 sim=json.loads((R/'04_evidence/sim/all_latest_summary.json').read_text(encoding='utf-8'))
 td=json.loads((R/'04_evidence/td/build_result.json').read_text(encoding='utf-8'))
 assert sim['version']=='v022_bmp_pixel_stream_20261020' and td['version']==sim['version']
 assert (sim['passed'],sim['total'])==(132,132)
 actual={p.relative_to(R).as_posix():sha(p) for p in sorted(R.rglob('*.v'))}
 assert actual==sim['source_sha256'],'Simulation source mismatch'
 for k,v in td['source_sha256'].items():
  assert sha(R/'01_project'/k)==v,'TD source mismatch: '+k
  if k.endswith('.v'):assert sim['source_sha256']['01_project/'+k]==v
 assert td['exit_code']==0 and td['bit_generated'] and td['timing_passed'] and td['release_ready_for_hardware_test']
 assert not td['critical_messages']
 assert sha(R/td['bit_file'])==td['bit_sha256'],'Bit mismatch'
 hw=json.loads((R/'04_evidence/hardware/v026_bmp_pixel_acceptance/user_acceptance.json').read_text(encoding='utf-8'))
 assert hw['version']=='v026_bmp_pixel_hw_pass_20261020' and hw['user_text']=='灯完全符合'
 assert hw['evidence_type']=='user_report' and hw['complete_pixel_crc_acceptance_passed']
 assert sha(R/hw['bit_file'])==hw['bit_sha256']==td['bit_sha256']
 assert not hw['new_download'] and not hw['sdram_tested'] and not hw['hdmi_real_image_tested']
 info=json.loads((R/'VERSION.json').read_text(encoding='utf-8'))
 assert info['version']==hw['version'] and info['hardware']['complete_pixel_crc_acceptance_passed']
 return sim,td
if __name__=='__main__':
 manifest=json.loads((R/'RELEASE_MANIFEST_SHA256.json').read_text(encoding='utf-8'))
 for name,digest in manifest['files'].items():
  rel=PurePosixPath(name)
  assert not rel.is_absolute() and '..' not in rel.parts
  assert sha(R.joinpath(*rel.parts))==digest,'File changed: '+name
 check_provenance()
 print('RELEASE_VERIFY_PASS: v026 user-reported full BMP pixel/CRC hardware acceptance; inherited 132/132 simulation, TD/STA and v023 SRAM download; hashes consistent; no SDRAM/HDMI image acceptance')
