"""Source-bound v126 address-equivalence / full-regression / STA guard; no programming or Flash."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,time
root=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--check-reports-only',action='store_true');ap.add_argument('--attempt',type=int,default=1);ap.add_argument('--synth-attempt',type=int,default=1);ap.add_argument('--physical-attempt',type=int,default=1);args=ap.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def req(x,m):
 if not x:raise RuntimeError(m)
def local_source(rel):
 p=Path(rel)
 if p.is_absolute():
  # Immutable report may name its original work root. Map ONLY explicitly
  # approved baseline roots, then hash the CURRENT file, not the old file.
  for prefix in [root,Path(r'D:\FPGA_Billboard\work\v125_pcm_pipeline_20261030'),Path(r'D:\FPGA_Billboard\work\v124_volume_timing_20261030'),Path(r'D:\FPGA_Billboard\work\v123_volume_20261029'),Path(r'D:\FPGA_Billboard\work\v122_address_pipeline_20261029')]:
   try:p=p.relative_to(prefix);break
   except ValueError:continue
  else:raise RuntimeError('Unapproved evidence source root: '+rel)
 req('..' not in p.parts,'source traversal: '+rel)
 p=root/p
 req(p.resolve().is_relative_to(root.resolve()),'source outside current project: '+rel)
 return p
fifo_equivalence=None
equivalent_fifo_entries=[]
def check_hashes(x):
 n=0
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ('source_sha256','sources') and isinstance(v,dict) and v and all(isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h)for h in v.values()):
    for rel,h in v.items():
     p=local_source(rel)
     if p.is_file() and sha(p)==h:n+=1
     elif p==root/'01_project/rtl/mem/async_fifo.v' and fifo_equivalence and h==fifo_equivalence['old_production_sha256'] and sha(p)==fifo_equivalence['new_production_sha256']:
      equivalent_fifo_entries.append(dict(source=rel,original_sha256=h,current_sha256=sha(p),basis='v126_fifo_equivalence exhaustive oracle + same-cycle A/B; not a hash match'));n+=1
     else:raise RuntimeError('source evidence mismatch: '+rel)
   elif isinstance(v,(dict,list)):n+=check_hashes(v)
 elif isinstance(x,list):
  for y in x:n+=check_hashes(y)
 return n
if not args.check_reports_only:
 req('01_versions' not in root.parts,'Frozen archive: copy to a new work directory before bit generation')
reports={}
def use_path(name,path):
 data=json.loads(path.read_text(encoding='utf-8-sig'))
 req(data.get('passed',data.get('pass')) is True or data.get('result')=='PASS','failed '+str(path))
 for key in ('tests','cases'):
  if key in data and isinstance(data[key],list):
   req(bool(data[key]) and all(isinstance(row,dict) and (row.get('passed',row.get('pass')) is True or row.get('result')=='PASS') for row in data[key]),'failed child '+key+' '+str(path))
 n=check_hashes(data);req(n>0,'unbound '+str(path));reports[name]=dict(path=path.relative_to(root).as_posix(),sha256=sha(path),source_hash_entries=n,scope=data.get('scope',''));return data
def use_latest(name,pattern):
 paths=sorted((root/'04_evidence').glob(pattern+'/summary.json'));req(paths,'Missing '+name);return use_path(name,paths[-1])
fifo_equivalence=use_latest('production_fifo_semantic_equivalence','v126_fifo_equivalence_*')
req(fifo_equivalence.get('outside_function_byte_identical') is True and len(fifo_equivalence['cases'])==21,'incomplete FIFO equivalence')
req(fifo_equivalence['exhaustive_widths']==[2,4,8,9,10,11,12] and fifo_equivalence['phase_ps']==[137,1375,6157],'FIFO equivalence coverage')
affected=use_latest('fresh_affected_batch','v126_affected_*');req(len(affected['cases'])==8,'incomplete changed-block regression')
use_latest('gestures_original_demo_timeline','v126_media_*')
use_latest('fresh_independent_ui_rasters','v126_ui_20*')
use_latest('active_volume_native_oddr','v126_volume_native_*')
use_latest('audio_ui_integration','v126_ui_audio_*')
use_latest('fresh_two_stage_volume','v126_volume_20*')
use_latest('fresh_volume_hdmi_payload','v126_volume_packets_*')
# Two focused visual reports: one actual top/three-cycle spectrum A-B/PCM,
# one unchanged math/DFT/TMDS/OSD rerun against current integration dependencies.
for label,required in [('top_spectrum_ab_pcm',{'top','overlay','audio_pcm'}),('numeric_dft_activity_tmds',{'activity','power_level','logo','dft','osd','tmds'})]:
 for path in reversed(sorted((root/'04_evidence').glob('v126_visual_*/summary.json'))):
  data=json.loads(path.read_text(encoding='utf8'))
  if required=={x.get('name')for x in data.get('tests',[])}:
   use_path(label,path);break
 else:raise RuntimeError('Missing focused visual report '+label)
use_latest('unchanged_address_equivalence','v124_address_ab_*');reports['unchanged_address_equivalence']['inherited_not_rerun']=True
# Complete individual V123 children only. The V123 aggregate had a failed top
# and is NOT inherited as passed. Its OSD failure is fixed and re-tested above.
baseline=json.loads((root/'04_evidence/v123_regression_20261029_234537/summary.json').read_text(encoding='utf8'))
for row in baseline['cases']:
 if row['case']in {'top720p','ui_audio_controls'}:continue
 req(row['passed'],'failed baseline child '+row['case'])
 req(len(row['summary_paths'])==1,'ambiguous baseline child')
 use_path('unchanged_v123_'+row['case'],local_source(row['summary_paths'][0]));reports['unchanged_v123_'+row['case']]['inherited_not_rerun']=True
for label,pattern in [('arbiter_snapshot_units','v123_units_*'),('three_wav_switch','v123_three_wav_*'),('extra_wav_spi','v123_extra_spi_*'),('paired_sdram720','v123_pair_memory_*'),('scaled_spi_bus_memory','v123_multires_spi_memory_*'),('wav_parser','v114_wav_decode_*'),('prefetch36','v114_prefetch_*'),('full_scaler720','v11[0124]_full_scaler_*'),('long_address','v122_address_long_*'),('dither','v122_dither_*')]:
 candidates=sorted((root/'04_evidence').glob(pattern+'/summary.json'))
 for path in reversed(candidates):
  try:use_path(label,path);reports[label]['inherited_not_rerun']=True;break
  except RuntimeError:continue
 else:raise RuntimeError('No current-source or explicitly certified FIFO-equivalent inherited report '+label)
three=use_latest('fresh_production_three_wav','v126_three_wav_*')
req(three.get('complete') is True and len(three['cases'])==11,'incomplete fresh three-WAV regression')
spi=use_latest('fresh_production_spi_audio_image','v126_extra_spi_*')
req(spi.get('production_parameters') is True and len(spi['cases'])==1 and spi['cases'][0]['mode']==1 and spi['cases'][0]['sdsc']==0,'fresh representative production SPI regression missing')
rom=use_latest('routed_ui_caption_logo_init','v126_rom_init_*')
req(rom.get('physical_attempt')==args.physical_attempt and len(rom['mapped_roms'])==12,'ROM audit mismatch')
use_latest('routed_resource_review','v126_resource_review')
synth=root/f'05_td/v126_audio_visual_synth_attempt{args.synth_attempt}';syn=json.loads((synth/'attempt.json').read_text(encoding='utf8'));req(syn.get('completed') and syn.get('within_capacities'),'synthesis guard failed');req(check_hashes(syn)>0,'synthesis not source bound')
gate=synth/'build/idx_video_Runs/syn_1';req((gate/'idx_video_gate.db').is_file(),'gate DB missing')
phy=root/f'05_td/v126_audio_visual_physical_attempt{args.physical_attempt}';pr=json.loads((phy/'attempt.json').read_text(encoding='utf8'));physical=phy/'physical';req(pr.get('completed') and pr.get('nonnegative_slack'),'physical timing guard failed');req(not pr.get('diagnostic_bit_generated'),'physical stage unexpectedly generated bit');req(pr.get('synth_gate_sha256')==sha(gate/'idx_video_gate.db'),'gate DB changed');req(pr.get('physical_script_sha256')==sha(root/pr.get('physical_script','01_project/build_audio_visual_physical_check.tcl')),'physical script changed');req(len(pr.get('slack_ns',{}))==4 and min(pr['slack_ns'].values())>=0,'invalid slack')
log=(phy/'run.log').read_text(encoding='utf8',errors='replace');req('TD PHYSICAL HOLD-FIX APPLIED' in log,'TD hold-fix marker missing');req('RUN-8102' not in log and 'PHY-8023 ERROR' not in log,'physical route error present')
check=physical/'sdram_check.rpt';req(check.is_file(),'check_timing report missing');txt=check.read_text(encoding='utf8',errors='replace');counts={m.group(1):int(m.group(2)) for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',txt,re.M)}
for k in ('no clock','clock definition','invalid constraint','pll/clock buffer clock constraints','combinational loops','no path constraints','shadowed/ignored timing exception constraints'):req(counts.get(k)==0,'check_timing failed '+k)
if args.check_reports_only:
 print(json.dumps(dict(reviewed_reports=reports,slack_ns=pr['slack_ns'],check_timing_counts=counts,synthesis_hashes_match=True),indent=2));raise SystemExit(0)
out=root/f'05_td/v126_volume_bitgen_attempt{args.attempt}';req(not out.exists(),'bitgen evidence exists');bitname='v126_volume_720p.bit';target=root/'03_bitstreams'/bitname;req(not target.exists(),'published bit exists');out.mkdir(parents=True);db=physical/'sdram_pr.db';req(db.is_file(),'routed DB missing')
record={'scope':'V126 SRAM candidate: 11-step ramped PCM volume, aligned two-stage stereo/epoch pipeline, valid-qualified DFT optimization, parallel-prefix FIFO conversion (same cycles/flags). UI V126. No clock/cache/precision/pin/SDC change. Fresh affected tests plus explicitly certified converter-only inheritance; no ASR, hardware signoff or TF throughput claim.',
 'reviewed_reports':reports,'explicit_semantic_fifo_inheritance':equivalent_fifo_entries,'check_timing_counts':counts,'synthesis_attempt':str(synth.relative_to(root)),'physical_attempt':str(phy.relative_to(root)),
 'physical_script':pr.get('physical_script','01_project/build_audio_visual_physical_check.tcl'),'physical_script_sha256':pr['physical_script_sha256'],
 'synthesis_attempt_sha256':sha(synth/'attempt.json'),'physical_attempt_sha256':sha(phy/'attempt.json'),'synth_gate_sha256':sha(gate/'idx_video_gate.db'),'routed_db_sha256':sha(db),'slack_ns':pr['slack_ns'],
 'formal_release_approved':False,'hardware_test':False,'flash_modified':False,
 'known_open_review':['V126 has NO new hardware/listening test; former-version user feedback is not inherited as V126 acceptance. Subtitles are still the fixed DEMO timeline, not ASR',
 'Fresh regression budget tests accelerate service/consumer16x. New production4096FIFO reader tests use virtual sectors; pin protocol model uses short512FIFO. Not physical SD timing',
 'Additional-WAV pin integration and preserved-source existing tests are not full production-size long-duration real-card acceptance',
 'RGB332 frame cache; BMP source24bit, HDMI1280x720 and PCM24bit stereo48k; no FLAC/MP3 decode or gapless loop',
 'SDRAM macro relocation,33 abnormal input annotations,SiP/PVT and full-address actual-device BIST open',
 'No TF writes, Flash, programming, cold-start or electrical acceptance performed']}
tcl_lines=['if {[catch {','import_device eagle_s20.db -package EG4S20NG88','cd {GATE}','open_project idx_video.prj -noanalyze','import_db {DB}','cd {OUT}','update_timing -mode final','report_timing_status -file bit_source.ts','set f [open bit_source.ts r]','set ts [read $f]','close $f','puts $ts','foreach metric {SWNS STNS HWNS HTNS} {',' if {![regexp [format {%s: *(-?[0-9]+[.][0-9]+)ns} $metric] $ts ignored value]} {error "Missing metric $metric"}',' if {$value < 0} {error "Negative timing metric $metric"}','}','check_timing -file bit_source.check -verbose','commit_param -step bitgen','bitgen -bit BITNAME','export_bitgen_param -file diagnostic_bitgen_param.f','puts "@@@ V126_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE"','} msg opts]} {puts "@@@ TASK_ERROR: $msg"; puts [dict get $opts -errorinfo]}','exit']
tcl='\n'.join(tcl_lines).replace('GATE',gate.as_posix()).replace('DB',db.as_posix()).replace('OUT',out.as_posix()).replace('BITNAME',bitname)+'\n';script=out/'invoke.tcl';script.write_text(tcl,encoding='utf8');record['invoke_tcl_sha256']=sha(script)
td=Path(os.environ.get('ADB_TD_BIN',r'D:\FPGA_Billboard\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin'));env=dict(os.environ);env['PATH']=str(td)+os.pathsep+env.get('PATH','');start=time.monotonic()
temp_dir=root/'00_tmp';temp_dir.mkdir(exist_ok=True)
env.update(TEMP=str(temp_dir),TMP=str(temp_dir),TMPDIR=str(temp_dir),PYTHONDONTWRITEBYTECODE='1')
with (out/'run.log').open('wb') as f:
 try:r=subprocess.run([str(td/'run.exe')],input=('source {'+script.as_posix()+'}\n').encode(),cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=240);record['returncode']=r.returncode
 except subprocess.TimeoutExpired:record['timeout']=True
log=(out/'run.log').read_text(encoding='utf8',errors='replace');bit=out/bitname;newcheck=out/'bit_source.check';newcounts={m.group(1):int(m.group(2)) for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',newcheck.read_text(encoding='utf8',errors='replace'),re.M)} if newcheck.is_file() else {}
reloaded_slack={k:float(v) for k,v in re.findall(r'(SWNS|STNS|HWNS|HTNS):\s*(-?\d+\.\d+)ns',(out/'bit_source.ts').read_text(encoding='utf8',errors='replace'))} if (out/'bit_source.ts').is_file() else {}
record.update(reloaded_slack_ns=reloaded_slack,reloaded_slack_matches=reloaded_slack==pr['slack_ns'])
record.update(elapsed_seconds=round(time.monotonic()-start,3),task_error='@@@ TASK_ERROR:' in log,marker_present='@@@ V126_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE' in log,nonempty_bit=bit.is_file() and bit.stat().st_size>0,reloaded_timing_check_matches=newcounts==counts)
record['completed']=bool(record.get('returncode')==0 and not record['task_error'] and record['marker_present'] and record['nonempty_bit'] and record['reloaded_timing_check_matches'] and record['reloaded_slack_matches'])
if record['completed']:
 req(sha(db)==record['routed_db_sha256'],'routed DB changed during bitgen');req(check_hashes(syn)>0,'synthesis source hashes changed');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(bit,target);record.update(bit_sha256=sha(target),bit_bytes=target.stat().st_size,published_path=str(target))
(out/'attempt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(record,ensure_ascii=False,indent=2),flush=True);print(out,flush=True);raise SystemExit(0 if record['completed'] else 1)

