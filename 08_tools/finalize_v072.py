from pathlib import Path
import hashlib,json,shutil,datetime,re
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent/'v070_four_image_playlist_20261024'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(rel,d):
 p=ROOT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def copy(p,q):
 q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():assert sha(q)==sha(p),str(q)
 else:shutil.copy2(p,q)
def main():
 out=ROOT/'05_td/v072_attempt1_normal_user';audit=read(out/'audit.json');attempt=read(out/'attempt.json')
 assert audit['numerical_checkpoint_pass'] and audit['diagnostic_bit_generated'] and not audit['failures']
 assert audit['slack_ns']['SWNS']>=0 and audit['slack_ns']['HWNS']>=0
 assert attempt['returncode']==0 and attempt['pack_seq_in_io_off_confirmed']
 for rel,h in attempt['source_sha256'].items():assert sha(ROOT/'01_project'/rel)==h,rel
 bit=out/'reports/v072_four_image_audio_720p.bit'
 assert sha(bit)==attempt['bit_sha256'] and bit.stat().st_size==attempt['bit_bytes']
 dest=ROOT/'03_bitstreams/v072_four_image_audio_720p.bit';copy(bit,dest)
 retained={};results=[]
 def verify_sources(mapping):
  for rel,h in mapping.items():
   p=ROOT/rel;assert p.is_file() and sha(p)==h,rel
   if 'build' in Path(rel).parts:
    q=ROOT/'04_evidence/retained_test_sources'/rel.replace('/build/','/model_sources/');copy(p,q)
    retained[rel]={'retained':q.relative_to(ROOT).as_posix(),'sha256':h}
 summaries=['v072_modes_20261024_014822/summary.json','v072_modes_20261024_014823/summary.json','sim_v070_probe_20261024_014911/summary.json','sim_v070_spi_20261024_014912/summary.json']
 for s in summaries:
  p=ROOT/'04_evidence'/s;d=read(p);assert d['passed'] and d['complete']
  rows=d.get('tests',d.get('cases'));assert rows and all(x['passed'] for x in rows)
  verify_sources(d.get('source_sha256',{}))
  for row in rows:verify_sources(row.get('source_sha256',{}))
  results.append({'summary':p.relative_to(ROOT).as_posix(),'fresh_jobs_passed':len(rows),'scope':d['scope']})
 audio=ROOT/'04_evidence/audio_20261024_014525';sim=read(audio/'simulation.json');dec=read(audio/'independent_decode.json')
 assert sim['passed'] and sim['compile_rc']==sim['sim_rc']==sim['independent_decode_rc']==0 and dec['passed']
 verify_sources(sim['source_sha256'])
 for rel,h in dec['trace_sha256'].items():assert sha(audio/rel)==h
 assert dec['symbols_checked']==46872 and dec['hdmi_pcm_frames']==[800,0]
 results.append({'summary':(audio/'simulation.json').relative_to(ROOT).as_posix(),'fresh_jobs_passed':1,'scope':'929384 active TMDS comparisons, actual I2S serial receive, signed gain, independent HDMI packet decoder; reset flush; not electrical/sink acceptance'})
 native=read(ROOT/'02_tests/tmds_v072_audio_native_results.json');assert native['passed'] and len(native['cases'])==3
 native_sources={}
 for row in native['cases']:
  assert row['passed'] and row['compile_returncode']==row['sim_returncode']==0
  for s in row['compile_command']:
   p=Path(s)
   if p.suffix in {'.v','.sv'} and p.is_file():
    rel=p.relative_to(ROOT).as_posix();native_sources[rel]=sha(p)
 verify_sources(native_sources)
 write('04_evidence/v072_native_sources.json',native_sources)
 results.append({'summary':'02_tests/tmds_v072_audio_native_results.json','fresh_jobs_passed':3,'scope':'Enabled-audio native TD ODDR serializer bit scoreboards, three clock offsets and two lock/retry epochs each; no real pins or sink'})
 # The expensive full-frame memory test is inherited only after every input is byte-identical.
 oldsummary=BASE/'04_evidence/sim_v070_memory_20261024_003713/summary.json';old=read(oldsummary)
 assert old['passed'] and old['complete'];verify_sources(old['source_sha256'])
 inherited=ROOT/'04_evidence/inherited_v070_memory'
 for p in oldsummary.parent.iterdir():
  if p.is_file() and p.suffix in {'.json','.log'}:copy(p,inherited/p.name)
 write('04_evidence/v072_memory_inheritance.json',{'inherited_from':str(oldsummary),'rerun_in_v072':False,'all_recorded_input_hashes_match_v072':True,'source_sha256':old['source_sha256'],'scope':old['scope'],'results':old['cases'][0]['result_lines'],'reason':'Memory, BMP, FIFO and display RTL unchanged. Audio/output stage is separately simulated. This is NOT a new complete all-SPI-to-HDMI or physical SDRAM test.'})
 for p in (out/'build').rglob('*'):
  if p.is_file() and p.suffix.lower() in {'.log','.logw','.rpt','.srr','.qor','.sdc','.adc','.prj','.tcl','.timing','.ts','.area','.txt'}:
   copy(p,ROOT/'04_evidence/v072_td_synthesis'/p.relative_to(out/'build'))
 changed=[];unchanged=[]
 for p in sorted((ROOT/'01_project').rglob('*')):
  if not p.is_file() or any(x in {'build','__pycache__'} for x in p.relative_to(ROOT).parts):continue
  rel=p.relative_to(ROOT).as_posix();oldp=BASE/rel
  if not oldp.exists() or sha(oldp)!=sha(p):changed.append({'file':rel,'baseline_sha256':sha(oldp) if oldp.exists() else None,'sha256':sha(p)})
  else:unchanged.append({'file':rel,'sha256':sha(p)})
 expected={'01_project/boards/idx_video_top.v','01_project/build_idx_physical_check.tcl','01_project/build_idx_synth.tcl','01_project/rtl/audio/hdmi_audio_packets.v','01_project/rtl/audio/i2s_test_tone.v','01_project/rtl/ip/hdmi_tx_wrap.v','01_project/tools/run_idx_bitstream.py'}
 assert {x['file'] for x in changed}==expected,changed
 protected=['boards/idx_video.adc','boards/idx_video.sdc','rtl/ip/pll_video720.v','rtl/ip/pll_sdram.v','rtl/video/tmds_serializer.v']
 for rel in protected:assert sha(ROOT/'01_project'/rel)==sha(BASE/'01_project'/rel),rel
 write('04_evidence/v072_project_delta.json',{'baseline':BASE.name,'changed':changed,'unchanged':unchanged,'protected_unchanged':protected,'note':'TF/FAT32/BMP/SDRAM, video clocks, NG88 ADC/SDC and native serializer unchanged. Top aligns coordinates/enables audio; complete symbols gain one pixel before fast serializer. Physical placement is newly routed.'})
 publication=dict(audit);publication.update(source_matches_build=True,bit_sha256=sha(dest),bit_bytes=dest.stat().st_size,published_bit=dest.relative_to(ROOT).as_posix(),programmed=False,hardware_accepted=False,release_type='Numerically passing engineering hardware-test candidate; not full signoff')
 write('04_evidence/v072_td_publication.json',publication)
 write('04_evidence/v072_test_matrix.json',{'all_fresh_listed_tests_passed':True,'fresh_test_jobs_passed':sum(x['fresh_jobs_passed'] for x in results),'results':results,'inherited_full_memory_test':'04_evidence/v072_memory_inheritance.json','full_all_spi_to_hdmi_test_rerun':False,'audio_decoder':'04_evidence/audio_20261024_014525/independent_decode.json','retained_build_sources':retained,'native_sources':'04_evidence/v072_native_sources.json','auxiliary_checker_sha256':{rel:sha(ROOT/rel) for rel in ['02_tests/check_v072_audio.py','02_tests/run_v072_audio.py','02_tests/run_v072_audio_native.py']},'hardware_tested':False})
 write('VERSION_STATUS.json',{'version':ROOT.name,'archive_id':'v072_hdmi_audio_pipeline_20261024','date':'2026-10-24','target':'VF-E20NG88 / EG4S20NG88 / 24 MHz','baseline':BASE.name,'v070_user_confirmed_hardware_pass':True,'scope':'TF FAT32 A/B/C/D 24bit BMP -> RGB332 SDRAM -> 720p HDMI; generated stereo I2S -> actual serial receive -> signed attenuation -> HDMI audio islands/ACR/infoframes','playlist_images':4,'visible_dwell_seconds':5,'source_resolution':[640,480],'source_bpp':24,'framebuffer_format':'RGB332','output_resolution':[1280,720],'audio':{'sample_rate_hz':48000,'sample_bits':24,'channels':2,'tone_hz':1000,'gain':'signed divide by 4','final_peak':262144,'audio_files_required':False,'new_external_i2s_wires_required':False},'bitstream':dest.relative_to(ROOT).as_posix(),'bit_bytes':dest.stat().st_size,'bit_sha256':sha(dest),'fresh_test_jobs_passed':sum(x['fresh_jobs_passed'] for x in results),'test_matrix':'04_evidence/v072_test_matrix.json','td_publication':'04_evidence/v072_td_publication.json','td_slack_ns':audit['slack_ns'],'td_coverage_percent':audit['coverage_percent'],'warning_flags':audit['warning_flags'],'constraints_changed':False,'clocks_changed':False,'hardware_programmed':False,'hardware_acceptance':False,'audible_playback_verified':False,'formal_release_approved':False,'nonvolatile_boot_implemented':False,'open_items':audit['open_review']+['First real audio/video sink acceptance pending; fixed720p/48k LPCM, no EDID/DDC capability negotiation.','RGB332 framebuffer does not preserve full 24bit source color precision.','No TF audio-file playback, audio-video content sync, or nonvolatile boot release.'],'created_at':datetime.datetime.now().astimezone().isoformat()})
 print('PASS finalize v072; bit='+sha(dest)+'; fresh_jobs='+str(sum(x['fresh_jobs_passed'] for x in results)))
if __name__=='__main__':main()
