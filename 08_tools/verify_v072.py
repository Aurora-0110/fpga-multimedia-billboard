"""Read-only offline delivery verifier. No programming, device access or card writes."""
from pathlib import Path
import hashlib,json,struct
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def validate():
 status=read(ROOT/'VERSION_STATUS.json')
 assert status['version']==status['archive_id']=='v072_hdmi_audio_pipeline_20261024'
 assert status['playlist_images']==4 and status['framebuffer_format']=='RGB332'
 for key in ['hardware_programmed','hardware_acceptance','audible_playback_verified','formal_release_approved','nonvolatile_boot_implemented','constraints_changed','clocks_changed']:assert status[key] is False,key
 assert status['audio']['sample_rate_hz']==48000 and status['audio']['sample_bits']==24 and status['audio']['channels']==2
 media=read(ROOT/'06_test_media/four_image_playlist/MEDIA_MANIFEST.json')
 assert [x['filename'] for x in media['order']]==[x+'.BMP' for x in 'ABCD']
 for item in media['order']:
  p=ROOT/'06_test_media/four_image_playlist/TF_ROOT'/item['filename'];d=p.read_bytes()
  assert len(d)==item['bytes']==921654 and sha(p)==item['sha256']
  assert d==(ROOT/'07_reference/official_original_bmp'/item['official_original']).read_bytes()
  assert d[:2]==b'BM' and struct.unpack_from('<I',d,2)[0]==len(d) and struct.unpack_from('<I',d,10)[0]==54
  assert struct.unpack_from('<iiHHI',d,18)==(640,480,1,24,0)
 matrix=read(ROOT/status['test_matrix'])
 assert matrix['all_fresh_listed_tests_passed'] and matrix['fresh_test_jobs_passed']==status['fresh_test_jobs_passed']==21
 assert not matrix['hardware_tested'] and not matrix['full_all_spi_to_hdmi_test_rerun']
 checked={}
 def sources(mapping):
  for rel,h in mapping.items():
   p=ROOT/rel
   if not p.exists():p=ROOT/matrix['retained_build_sources'][rel]['retained']
   assert sha(p)==h,rel
   checked[rel]=h
 total=0
 for entry in matrix['results']:
  d=read(ROOT/entry['summary']);assert d['passed'],entry['summary']
  if 'complete' in d:assert d['complete']
  rows=d.get('tests',d.get('cases'))
  n=len(rows) if rows is not None else 1
  assert n==entry['fresh_jobs_passed'],entry['summary']
  total+=n;sources(d.get('source_sha256',{}))
  for row in rows or []:
   assert row['passed'];sources(row.get('source_sha256',{}))
 assert total==21
 sources(matrix['auxiliary_checker_sha256']);sources(read(ROOT/matrix['native_sources']))
 decoderpath=ROOT/matrix['audio_decoder'];decoder=read(decoderpath);assert decoder['passed'] and decoder['symbols_checked']>46000
 assert decoder['packets']['2']==200
 for name,h in decoder['trace_sha256'].items():assert sha(decoderpath.parent/name)==h,name
 mem=read(ROOT/matrix['inherited_full_memory_test'])
 assert not mem['rerun_in_v072'] and mem['all_recorded_input_hashes_match_v072']
 sources(mem['source_sha256'])
 inherited=read(ROOT/'04_evidence/inherited_v070_memory/summary.json')
 assert inherited['passed'] and inherited['complete']
 sources(inherited.get('source_sha256',{}))
 for row in inherited.get('tests',[]):assert row['passed'];sources(row.get('source_sha256',{}))
 td=read(ROOT/status['td_publication']);attempt=read(ROOT/'05_td/v072_attempt1_normal_user/attempt.json')
 assert td['numerical_checkpoint_pass'] and td['diagnostic_bit_generated'] and td['source_matches_build'] and not td['failures']
 assert not td['programmed'] and not td['hardware_accepted'] and not td['formal_release_approved']
 assert td['slack_ns']==status['td_slack_ns'] and td['slack_ns']['SWNS']>=0 and td['slack_ns']['HWNS']>=0
 assert not td['warning_flags']['USR-6135'] and td['warning_flags']['PHY-7002']
 assert attempt['returncode']==0
 sources({'01_project/'+k:v for k,v in attempt['source_sha256'].items()})
 bit=ROOT/status['bitstream']
 assert sha(bit)==status['bit_sha256']==td['bit_sha256']==attempt['bit_sha256']
 assert bit.stat().st_size==status['bit_bytes']==td['bit_bytes']==attempt['bit_bytes']
 delta=read(ROOT/'04_evidence/v072_project_delta.json')
 assert len(delta['changed'])==7
 sources({x['file']:x['sha256'] for x in delta['changed']+delta['unchanged']})
 unchanged={x['file'] for x in delta['unchanged']}
 for rel in delta['protected_unchanged']:assert '01_project/'+rel in unchanged,rel
 assert (ROOT/'07_reference/hdl_util_hdmi/LICENSE-MIT').is_file()
 return {'version':status['version'],'passed':True,'four_official_images_verified':True,'fresh_test_jobs_passed':total,'source_hashes_checked':len(checked),'inherited_full_memory_hashes_checked':len(mem['source_sha256']),'full_memory_rerun':False,'td_slack_ns':td['slack_ns'],'bit_bytes':bit.stat().st_size,'bit_sha256':sha(bit),'hardware_acceptance':False,'audible_playback_verified':False,'formal_release_approved':False}
if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False,indent=2))
