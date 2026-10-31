"""Source-bound v119 targeted-regression / STA guard; no programming or Flash."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,time
root=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--check-reports-only',action='store_true');ap.add_argument('--attempt',type=int,default=1);ap.add_argument('--synth-attempt',type=int,default=1);ap.add_argument('--physical-attempt',type=int,default=1);args=ap.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def req(x,m):
 if not x:raise RuntimeError(m)
def local_source(rel):
 p=Path(rel)
 if not p.is_absolute():p=root/p
 req(p.is_relative_to(root),'source outside current project: '+rel)
 return p
def check_hashes(x):
 n=0
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ('source_sha256','sources') and isinstance(v,dict) and v and all(isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h)for h in v.values()):
    for rel,h in v.items():
     p=local_source(rel);req(p.is_file()and sha(p)==h,'source evidence mismatch: '+rel);n+=1
   elif isinstance(v,(dict,list)):n+=check_hashes(v)
 elif isinstance(x,list):
  for y in x:n+=check_hashes(y)
 return n
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
reg=use_latest('fresh_regression','v119_regression_complete_*')
req(len(reg['cases'])==11 and all(x['passed']for x in reg['cases']),'incomplete regression')
for row in reg['cases']:
 req(len(row['summary_paths'])==1,'missing result path '+row['case']);d=use_path(row['case'],Path(row['summary_paths'][0]));req(d.get('passed',d.get('pass')) is True,'failed detail')
units=use_latest('fresh_arbiter_and_snapshot_units','v119_units_*');req(len(units['cases'])==3,'incomplete units')
use_latest('three_wav_reader_and_switching','v119_three_wav_*')
use_latest('four_source_gestures_and_subtitles','v119_media_*')
use_latest('independent_ui_rasters','v119_ui_20*')
use_latest('fresh_native_hdmi_three_phases','v119_visual_native_*')
use_latest('additional_wav_actual_spi_model','v119_extra_spi_*')
rom=use_latest('routed_ui_caption_logo_init','v119_rom_init_*')
req(rom.get('physical_attempt')==args.physical_attempt and len(rom['mapped_roms'])==12,'ROM audit mismatch')
# Unmodified components: recorded source sets must match this work tree exactly.
for label,pattern in [('unchanged_wav_parser','v114_wav_decode_*'),('unchanged_prefetch36','v114_prefetch_*'),('unchanged_scaler720','v11[0124]_full_scaler_*'),('unchanged_dither','v11[0124]_dither_*')]:
 candidates=sorted((root/'04_evidence').glob(pattern+'/summary.json'))
 for path in reversed(candidates):
  try:use_path(label,path);reports[label]['inherited_not_rerun']=True;break
  except RuntimeError:continue
 else:raise RuntimeError('No source-matching inherited report '+label)
synth=root/f'05_td/v119_audio_visual_synth_attempt{args.synth_attempt}';syn=json.loads((synth/'attempt.json').read_text(encoding='utf8'));req(syn.get('completed') and syn.get('within_capacities'),'synthesis guard failed');req(check_hashes(syn)>0,'synthesis not source bound')
gate=synth/'build/idx_video_Runs/syn_1';req((gate/'idx_video_gate.db').is_file(),'gate DB missing')
phy=root/f'05_td/v119_audio_visual_physical_attempt{args.physical_attempt}';pr=json.loads((phy/'attempt.json').read_text(encoding='utf8'));physical=phy/'physical';req(pr.get('completed') and pr.get('nonnegative_slack'),'physical timing guard failed');req(not pr.get('diagnostic_bit_generated'),'physical stage unexpectedly generated bit');req(pr.get('synth_gate_sha256')==sha(gate/'idx_video_gate.db'),'gate DB changed');req(pr.get('physical_script_sha256')==sha(root/'01_project/build_audio_visual_physical_check.tcl'),'physical script changed');req(len(pr.get('slack_ns',{}))==4 and min(pr['slack_ns'].values())>=0,'invalid slack')
log=(phy/'run.log').read_text(encoding='utf8',errors='replace');req('TD PHYSICAL HOLD-FIX APPLIED' in log,'TD hold-fix marker missing');req('RUN-8102' not in log and 'PHY-8023 ERROR' not in log,'physical route error present')
check=physical/'sdram_check.rpt';req(check.is_file(),'check_timing report missing');txt=check.read_text(encoding='utf8',errors='replace');counts={m.group(1):int(m.group(2)) for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',txt,re.M)}
for k in ('no clock','clock definition','invalid constraint','pll/clock buffer clock constraints','combinational loops','no path constraints','shadowed/ignored timing exception constraints'):req(counts.get(k)==0,'check_timing failed '+k)
if args.check_reports_only:
 print(json.dumps(dict(reviewed_reports=reports,slack_ns=pr['slack_ns'],check_timing_counts=counts,synthesis_hashes_match=True),indent=2));raise SystemExit(0)
out=root/f'05_td/v119_audio_refill_bitgen_attempt{args.attempt}';req(not out.exists(),'bitgen evidence exists');bitname='v119_three_wav_720p.bit';target=root/'03_bitstreams'/bitname;req(not target.exists(),'published bit exists');out.mkdir(parents=True);db=physical/'sdram_pr.db';req(db.is_file(),'routed DB missing')
record={'scope':'v119 diagnostic SRAM candidate: preserves MUSIC/ADVOICE and discovers first additional regular WAV by FAT32 root SFN extension; four-source controls and Chinese UI V119. Reuses v116 bounded urgent-audio refill, same decoder and buffers. No cache-size/clock/format change. Does not establish real-card A3 closure.',
 'reviewed_reports':reports,'check_timing_counts':counts,'synthesis_attempt':str(synth.relative_to(root)),'physical_attempt':str(phy.relative_to(root)),
 'synthesis_attempt_sha256':sha(synth/'attempt.json'),'physical_attempt_sha256':sha(phy/'attempt.json'),'synth_gate_sha256':sha(gate/'idx_video_gate.db'),'routed_db_sha256':sha(db),'slack_ns':pr['slack_ns'],
 'formal_release_approved':False,'hardware_test':False,'flash_modified':False,
 'known_open_review':['Real TF-card service latency and v119 listening test remain unverified; no claim of hardware A3 closure',
 'Fresh regression budget tests accelerate service/consumer16x. New production4096FIFO reader tests use virtual sectors; pin protocol model uses short512FIFO. Not physical SD timing',
 'Additional-WAV pin integration and preserved-source existing tests are not full production-size long-duration real-card acceptance',
 'RGB332 frame cache; BMP source24bit, HDMI1280x720 and PCM24bit stereo48k; no FLAC/MP3 decode or gapless loop',
 'SDRAM macro relocation,33 abnormal input annotations,SiP/PVT and full-address actual-device BIST open',
 'No TF writes, Flash, programming, cold-start or electrical acceptance performed']}
tcl_lines=['if {[catch {','import_device eagle_s20.db -package EG4S20NG88','cd {GATE}','open_project idx_video.prj -noanalyze','import_db {DB}','cd {OUT}','update_timing -mode final','report_timing_status -file bit_source.ts','set f [open bit_source.ts r]','set ts [read $f]','close $f','puts $ts','foreach metric {SWNS STNS HWNS HTNS} {',' if {![regexp [format {%s: *(-?[0-9]+[.][0-9]+)ns} $metric] $ts ignored value]} {error "Missing metric $metric"}',' if {$value < 0} {error "Negative timing metric $metric"}','}','check_timing -file bit_source.check -verbose','commit_param -step bitgen','bitgen -bit BITNAME','export_bitgen_param -file diagnostic_bitgen_param.f','puts "@@@ V119_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE"','} msg opts]} {puts "@@@ TASK_ERROR: $msg"; puts [dict get $opts -errorinfo]}','exit']
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
record.update(elapsed_seconds=round(time.monotonic()-start,3),task_error='@@@ TASK_ERROR:' in log,marker_present='@@@ V119_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE' in log,nonempty_bit=bit.is_file() and bit.stat().st_size>0,reloaded_timing_check_matches=newcounts==counts)
record['completed']=bool(record.get('returncode')==0 and not record['task_error'] and record['marker_present'] and record['nonempty_bit'] and record['reloaded_timing_check_matches'] and record['reloaded_slack_matches'])
if record['completed']:
 req(sha(db)==record['routed_db_sha256'],'routed DB changed during bitgen');req(check_hashes(syn)>0,'synthesis source hashes changed');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(bit,target);record.update(bit_sha256=sha(target),bit_bytes=target.stat().st_size,published_path=str(target))
(out/'attempt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(record,ensure_ascii=False,indent=2),flush=True);print(out,flush=True);raise SystemExit(0 if record['completed'] else 1)

