"""Guarded, source-bound v111 UI/pause/resource diagnostic SRAM bit generation; NO download/Flash.
Current media/storage/UI/scaler/prepared-TMDS/dither regressions are required.
Every recorded source hash must match; no stale evidence is reused.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,time
root=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--check-reports-only',action='store_true');ap.add_argument('--attempt',type=int,default=1);ap.add_argument('--synth-attempt',type=int,default=2);ap.add_argument('--physical-attempt',type=int,default=1);args=ap.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def req(x,m):
 if not x:raise RuntimeError(m)
def check_hashes(x):
 n=0
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ('source_sha256','sources') and isinstance(v,dict) and all(isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h) for h in v.values()):
    for rel,h in v.items():req((root/rel).is_file() and sha(root/rel)==h,'source evidence mismatch: '+rel);n+=1
   elif isinstance(v,(dict,list)):n+=check_hashes(v)
 elif isinstance(x,list):
  for y in x:n+=check_hashes(y)
 return n
reports={}
def use(name,pattern,selector,count=None):
 choices=[]
 for path in sorted((root/'04_evidence').glob(pattern+'/summary.json')):
  data=json.loads(path.read_text(encoding='utf-8'))
  if selector(data):choices.append((path,data))
 req(choices,'Missing qualifying evidence '+name)
 path,data=choices[-1];rows=data.get('tests',data.get('cases',[]))
 req(data.get('passed') is True or data.get('result')=='PASS','evidence failed '+str(path))
 req(all(row.get('passed') is True for row in rows),'failed row '+name)
 req(data.get('sources_unchanged_during_run',True),'source changed during run '+name)
 if count is not None:req(len(rows)==count,'incomplete '+name)
 bound=check_hashes(data);req(bound>0,'unbound evidence '+name)
 reports[name]=dict(path=path.relative_to(root).as_posix(),sha256=sha(path),source_hash_entries=bound,scope=data.get('scope',''),current_v111_execution=path.parent.name.startswith('v111_'))
 return data
use('media_controls','v11[01]_media_*',lambda d:d.get('complete') and {r['name'] for r in d.get('tests',[])}=={'controls','ui_pin','timeline_1','timeline_3','timeline_48','caption_pixels'},6)
use('hidden_ui','v11[01]_ui_*',lambda d:d.get('complete') and {r['name'] for r in d.get('tests',[])}=={'uptime','controls','ui'},3)
use('native_hdmi','v11[01]_visual_native_*',lambda d:len(d.get('tests',[]))==3,3)
use('wav_decode','v11[01]_wav_decode_*',lambda d:len(d.get('cases',[]))==20,20)
use('wav_playback','v11[01]_playback_*',lambda d:{r['mode'] for r in d.get('cases',[])}==set(range(8)),8)
use('mount_validation','v11[01]_mount_*',lambda d:len(d.get('cases',[]))==22,22)
for name,pat in [('bmp_chain1280','v11[01]_media_probe_*'),('bmp_chain2048','v11[01]_media_probe2048_*')]:
 use(name,pat,lambda d:d.get('requested_cases')==d.get('completed_cases') and d.get('completed_cases',0)>=70)
use('actual_spi_matrix','v11[01]_actual_spi_*',lambda d:d.get('short_fifo_pin_protocol_test') is True and {(r['mode'],r['sdsc'])for r in d.get('cases',[])}=={(0,0),(1,0),(1,1),(2,0),(3,1)},5)
use('actual_spi_default_fifo','v11[01]_actual_spi_*',lambda d:d.get('short_fifo_pin_protocol_test') is False and {(r['mode'],r['sdsc'])for r in d.get('cases',[])}=={(2,0)},1)
use('visual','v11[01]_visual_*',lambda d:d.get('complete') and {r['name'] for r in d.get('tests',[])}=={'activity','power_level','logo','dft','overlay','osd','top','audio_pcm','tmds'},9)
use('routed_ui_rom','v111_rom_init_*',lambda d:d.get('physical_attempt')==args.physical_attempt and len(d.get('mapped_roms',[]))==12 and sum(r.get('group')=='logo' for r in d.get('mapped_roms',[]))==2)
use('full720_scaler','v11[01]_full_scaler_*',lambda d:len(d.get('cases',[]))==2,2)
use('prepared_tmds','v11[01]_prepared_tmds_*',lambda d:d.get('complete') and len(d.get('tests',[]))==2,2)
for name,filename in [('scaler_units','quick_results.json'),('scaler_2048_boundary','address_boundary_results.json')]:
 path=root/'04_evidence/v110_scaler_units'/filename
 req(path.is_file(),'Missing '+name);data=json.loads(path.read_text(encoding='utf8'));req(data.get('result')=='PASS','failed '+name)
 req(data.get('sources_unchanged_during_run',True),'changed '+name);bound=check_hashes(data);req(bound>0,'unbound '+name)
 reports[name]=dict(path=path.relative_to(root).as_posix(),sha256=sha(path),source_hash_entries=bound,scope=data.get('scope',''),current_v111_execution=False)
use('dither','v11[01]_dither_*',lambda d:len(d.get('tests',[]))==4,4)
use('underrun_recovery','v111_underrun_*',lambda d:{r['mode'] for r in d.get('cases',[])}=={8},1)
if args.check_reports_only:
 print(json.dumps(reports,indent=2));raise SystemExit(0)
synth=root/f'05_td/v111_audio_visual_synth_attempt{args.synth_attempt}';syn=json.loads((synth/'attempt.json').read_text(encoding='utf8'));req(syn.get('completed') and syn.get('within_capacities'),'synthesis guard failed');req(check_hashes(syn)>0,'synthesis not source bound')
gate=synth/'build/idx_video_Runs/syn_1';req((gate/'idx_video_gate.db').is_file(),'gate DB missing')
phy=root/f'05_td/v111_audio_visual_physical_attempt{args.physical_attempt}';pr=json.loads((phy/'attempt.json').read_text(encoding='utf8'));physical=phy/'physical';req(pr.get('completed') and pr.get('nonnegative_slack'),'physical timing guard failed');req(not pr.get('diagnostic_bit_generated'),'physical stage unexpectedly generated bit');req(pr.get('synth_gate_sha256')==sha(gate/'idx_video_gate.db'),'gate DB changed');req(pr.get('physical_script_sha256')==sha(root/'01_project/build_audio_visual_physical_check.tcl'),'physical script changed');req(len(pr.get('slack_ns',{}))==4 and min(pr['slack_ns'].values())>=0,'invalid slack')
log=(phy/'run.log').read_text(encoding='utf8',errors='replace');req('TD PHYSICAL HOLD-FIX APPLIED' in log,'TD hold-fix marker missing');req('RUN-8102' not in log and 'PHY-8023 ERROR' not in log,'physical route error present')
check=physical/'sdram_check.rpt';req(check.is_file(),'check_timing report missing');txt=check.read_text(encoding='utf8',errors='replace');counts={m.group(1):int(m.group(2)) for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',txt,re.M)}
for k in ('no clock','clock definition','invalid constraint','pll/clock buffer clock constraints','combinational loops','no path constraints','shadowed/ignored timing exception constraints'):req(counts.get(k)==0,'check_timing failed '+k)
out=root/f'05_td/v111_audio_fault_ui_bitgen_attempt{args.attempt}';req(not out.exists(),'bitgen evidence exists');bitname='v111_audio_fault_ui_720p.bit';target=root/'03_bitstreams'/bitname;req(not target.exists(),'published bit exists');out.mkdir(parents=True);db=physical/'sdram_pr.db';req(db.is_file(),'routed DB missing')
record={'scope':'v111 split image/audio UI fault domains, independent audio error code, K0 action hints use actual pause/image state; PCM path unchanged from v110 (real-device A3 underrun remains open); source-bound unchanged v110 regressions explicitly retained; TF FAT32 MUSIC/ADVOICE PCM-WAV 48k16/24 mono/stereo playback, sector arbitration,2048-frame FIFO and source selection; independent Chinese UI plus real-PCM DFT/HDMI; source-bound simulations and physical checks, diagnostic SRAM candidate ONLY',
 'reviewed_reports':reports,'check_timing_counts':counts,'synthesis_attempt':str(synth.relative_to(root)),'physical_attempt':str(phy.relative_to(root)),
 'synthesis_attempt_sha256':sha(synth/'attempt.json'),'physical_attempt_sha256':sha(phy/'attempt.json'),'synth_gate_sha256':sha(gate/'idx_video_gate.db'),'routed_db_sha256':sha(db),'slack_ns':pr['slack_ns'],
 'formal_release_approved':False,'hardware_test':False,'flash_modified':False,
 'known_open_review':['SDRAM macro relocation, internal delay/abnormal input annotations,SiP/PVT and full-address real-device BIST remain open',
 'RGB332 frame cache; output1280x720, PCM24 internal stereo48k, not full24bit image cache',
 'WAV PCM48k only; no MP3/FLAC decoder, runtime file browser or gapless loop',
 'v110 real-device A3 underrun and erroneous K0 image retry hint were photographed; this version fixes UI categorization, NOT the root cause of underrun',
 'EOF drains then silence; change away/back to replay; no new speaker/cold-start/card-stall acceptance yet',
 'Real WAV mode disables fixed16s DEMO subtitles; no real lyrics/ad transcript or ASR claim',
 'SPI five-case matrix uses a512-frame test FIFO at nominal cadence including pause and paused switch; default2048 mode2 test accelerates consumption4x; neither proves electrical timing',
 'No Flash programming performed; SRAM candidate must be tested before Flash solidification']}
tcl_lines=['if {[catch {','import_device eagle_s20.db -package EG4S20NG88','cd {GATE}','open_project idx_video.prj -noanalyze','import_db {DB}','cd {OUT}','update_timing -mode final','report_timing_status -file bit_source.ts','set f [open bit_source.ts r]','set ts [read $f]','close $f','puts $ts','foreach metric {SWNS STNS HWNS HTNS} {',' if {![regexp [format {%s: *(-?[0-9]+[.][0-9]+)ns} $metric] $ts ignored value]} {error "Missing metric $metric"}',' if {$value < 0} {error "Negative timing metric $metric"}','}','check_timing -file bit_source.check -verbose','commit_param -step bitgen','bitgen -bit BITNAME','export_bitgen_param -file diagnostic_bitgen_param.f','puts "@@@ V111_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE"','} msg opts]} {puts "@@@ TASK_ERROR: $msg"; puts [dict get $opts -errorinfo]}','exit']
tcl='\n'.join(tcl_lines).replace('GATE',gate.as_posix()).replace('DB',db.as_posix()).replace('OUT',out.as_posix()).replace('BITNAME',bitname)+'\n';script=out/'invoke.tcl';script.write_text(tcl,encoding='utf8');record['invoke_tcl_sha256']=sha(script)
td=Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin');env=dict(os.environ);env['PATH']=str(td)+os.pathsep+env.get('PATH','');start=time.monotonic()
temp_dir=root/'00_tmp';temp_dir.mkdir(exist_ok=True)
env.update(TEMP=str(temp_dir),TMP=str(temp_dir),TMPDIR=str(temp_dir),PYTHONDONTWRITEBYTECODE='1')
with (out/'run.log').open('wb') as f:
 try:r=subprocess.run([str(td/'run.exe')],input=('source {'+script.as_posix()+'}\n').encode(),cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=240);record['returncode']=r.returncode
 except subprocess.TimeoutExpired:record['timeout']=True
log=(out/'run.log').read_text(encoding='utf8',errors='replace');bit=out/bitname;newcheck=out/'bit_source.check';newcounts={m.group(1):int(m.group(2)) for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',newcheck.read_text(encoding='utf8',errors='replace'),re.M)} if newcheck.is_file() else {}
record.update(elapsed_seconds=round(time.monotonic()-start,3),task_error='@@@ TASK_ERROR:' in log,marker_present='@@@ V111_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE' in log,nonempty_bit=bit.is_file() and bit.stat().st_size>0,reloaded_timing_check_matches=newcounts==counts)
record['completed']=bool(record.get('returncode')==0 and not record['task_error'] and record['marker_present'] and record['nonempty_bit'] and record['reloaded_timing_check_matches'])
if record['completed']:
 req(sha(db)==record['routed_db_sha256'],'routed DB changed during bitgen');req(check_hashes(syn)>0,'synthesis source hashes changed');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(bit,target);record.update(bit_sha256=sha(target),bit_bytes=target.stat().st_size,published_path=str(target))
(out/'attempt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(record,ensure_ascii=False,indent=2),flush=True);print(out,flush=True);raise SystemExit(0 if record['completed'] else 1)
