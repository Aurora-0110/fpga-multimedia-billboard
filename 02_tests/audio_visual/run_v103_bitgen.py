"""Guarded v103 diagnostic SRAM bit generation; never downloads or writes Flash."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,time
root=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--attempt',type=int,default=1);ap.add_argument('--synth-attempt',type=int,default=1);ap.add_argument('--physical-attempt',type=int,default=1);args=ap.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def req(x,m):
 if not x: raise RuntimeError(m)
def check_hashes(x):
 n=0
 if isinstance(x,dict):
  for k,v in x.items():
   if k=='source_sha256':
    for rel,h in v.items():req((root/rel).is_file() and sha(root/rel)==h,'source evidence mismatch: '+rel);n+=1
   elif isinstance(v,(dict,list)):n+=check_hashes(v)
 elif isinstance(x,list):
  for y in x:n+=check_hashes(y)
 return n
reports={}
patterns={'hidden_ui':'v102_ui_*','robustness':'v103_acceptance_*','native_hdmi':'v103_visual_native_*','actual_spi':'v097_actual_spi_*','scaled_spi_memory':'v097_scaled_spi_memory_*','legacy_units':'v103_units_*','paired_units':'v097_pair_units_*','paired_memory':'v097_pair_memory_*','multires_chain':'v101_multires_chain_*','multires_scaler':'v101_multires_scaler_*','multires_spi_memory':'v101_multires_spi_memory_*','dither':'v101_dither_*'}
required_counts={'native_hdmi':3,'legacy_units':5,'robustness':3,'hidden_ui':3,'multires_chain':28,'multires_scaler':8,'multires_spi_memory':4,'dither':4}
for name,pat in patterns.items():
 paths=sorted((root/'04_evidence').glob(pat+'/summary.json'));req(paths,'missing evidence '+pat);path=paths[-1];data=json.loads(path.read_text(encoding='utf8'))
 req(data.get('passed') is True or data.get('result')=='PASS','evidence not PASS '+str(path));cases=data.get('tests',data.get('cases',[]));req(all(x.get('passed') is True for x in cases),'failed case '+name);bound=check_hashes(data);req(bound>0,'unbound evidence '+name)
 if name in required_counts:req(len(cases)==required_counts[name],'incomplete v103 suite '+name)
 if name=='robustness':
  req(data.get('complete') and {x['name'] for x in cases}=={'playlist','diagnostics','audio_long'},'incomplete fresh TF/fault/audio acceptance suite')
 if name=='hidden_ui':
  req(data.get('complete') and {x['name'] for x in cases}=={'uptime','controls','ui'},'incomplete current UI/gesture/uptime suite')
 if name=='multires_chain':
  expected={'header_'+x for x in ('maximum','maximum_top','minimum','reject_width2049','reject_height2049','reject_negative_height2049','reject_widthzero','reject_negative_width','reject_heightzero','reject_height_intmin')}
  expected|={'stage'+str(stage)+'_'+x for stage in (1,2) for x in ('max_width_bottom','odd_width_top','max_height_bottom','max_height_top','offset511_top','single_pixel_drain','late_crc','bad_index','timeout')}
  req({x['case']['name'] for x in cases}==expected,'wrong multires chain coverage')
  req(data.get('requested_cases')==28 and data.get('completed_cases')==28,'incomplete multires chain')
 if name=='multires_scaler':
  expected={(1,1,32,18,True),(2048,1,32,18,False),(1,2048,32,18,True),(2048,2048,32,18,False),(2047,1537,32,18,True),(720,1280,64,36,True),(320,240,1280,720,True),(2048,2048,1280,720,False)}
  req({(*x['source'],*x['output'],x['top_down']) for x in cases}==expected,'wrong multires scaler coverage')
  req(all(x['output_pixels']==x['output'][0]*x['output'][1] for x in cases),'invalid scaler pixel count')
 if name=='multires_spi_memory':req({x['case']['name'] for x in cases}=={'max_width_bottom_retry','odd_width_top','max_height_padding_top','late_crc_no_publish'},'wrong real SPI multires coverage')
 if name=='dither':
  req({(x['mode'],x['top_down']) for x in cases}=={(m,t) for m in (0,1) for t in (False,True)},'wrong dither coverage')
  req(all(x['pixels']==4096 and x['quantizer_comparisons']==8192 for x in cases),'incomplete dither comparisons')
 reports[name]={'path':path.relative_to(root).as_posix(),'sha256':sha(path),'source_hash_entries':bound,'scope':data.get('scope',''),'current_v103_execution':path.parent.name.startswith('v103_')}
visuals=[p for p in sorted((root/'04_evidence').glob('v103_visual_*/summary.json')) if '_native_' not in p.parent.name]
req(visuals,'missing active visual regression');path=visuals[-1];data=json.loads(path.read_text(encoding='utf8'))
req(data.get('passed') is True and all(x.get('passed') is True for x in data.get('tests',[])),'active visual regression failed')
req(data.get('complete') is True and {x['name'] for x in data.get('tests',[])}=={'activity','power_level','logo','dft','overlay','osd','top','audio_pcm','tmds'},'v103 FULL visual suite required; --only is not a release gate')
bound=check_hashes(data);req(bound>0,'visual evidence is not source bound')
reports['visual']={'path':path.relative_to(root).as_posix(),'sha256':sha(path),'source_hash_entries':bound,'scope':data.get('scope',''),'current_v103_execution':path.parent.name.startswith('v103_')}
synth=root/f'05_td/v103_audio_visual_synth_attempt{args.synth_attempt}';syn=json.loads((synth/'attempt.json').read_text(encoding='utf8'));req(syn.get('completed') and syn.get('within_capacities'),'synthesis guard failed');req(check_hashes(syn)>0,'synthesis not source bound')
gate=synth/'build/idx_video_Runs/syn_1';req((gate/'idx_video_gate.db').is_file(),'gate DB missing')
phy=root/f'05_td/v103_audio_visual_physical_attempt{args.physical_attempt}';pr=json.loads((phy/'attempt.json').read_text(encoding='utf8'));physical=phy/'physical';req(pr.get('completed') and pr.get('nonnegative_slack'),'physical timing guard failed');req(not pr.get('diagnostic_bit_generated'),'physical stage unexpectedly generated bit');req(pr.get('synth_gate_sha256')==sha(gate/'idx_video_gate.db'),'gate DB changed');req(pr.get('physical_script_sha256')==sha(root/'01_project/build_audio_visual_physical_check.tcl'),'physical script changed');req(len(pr.get('slack_ns',{}))==4 and min(pr['slack_ns'].values())>=0,'invalid slack')
log=(phy/'run.log').read_text(encoding='utf8',errors='replace');req('TD PHYSICAL HOLD-FIX APPLIED' in log,'TD hold-fix marker missing');req('RUN-8102' not in log and 'PHY-8023 ERROR' not in log,'physical route error present')
check=physical/'sdram_check.rpt';req(check.is_file(),'check_timing report missing');txt=check.read_text(encoding='utf8',errors='replace');counts={m.group(1):int(m.group(2)) for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',txt,re.M)}
for k in ('no clock','clock definition','invalid constraint','pll/clock buffer clock constraints','combinational loops','no path constraints','shadowed/ignored timing exception constraints'):req(counts.get(k)==0,'check_timing failed '+k)
out=root/f'05_td/v103_audio_spectrum_bitgen_attempt{args.attempt}';req(not out.exists(),'bitgen evidence exists');bitname='v103_acceptance_robustness_720p.bit';target=root/'03_bitstreams'/bitname;req(not target.exists(),'published bit exists');out.mkdir(parents=True);db=physical/'sdram_pr.db';req(db.is_file(),'routed DB missing')
record={'scope':'v103 bounded framebuffer-progress watchdog/transport retry and non-hideable current+historical fault banner; fresh robustness/legacy/system/native regressions, source-hash-verified unchanged v102 UI and v101/v097 storage/scaler evidence; diagnostic SRAM candidate, NOT hardware signoff','reviewed_reports':reports,'check_timing_counts':counts,'synthesis_attempt':str(synth.relative_to(root)),'physical_attempt':str(phy.relative_to(root)),'synthesis_attempt_sha256':sha(synth/'attempt.json'),'physical_attempt_sha256':sha(phy/'attempt.json'),'synth_gate_sha256':sha(gate/'idx_video_gate.db'),'routed_db_sha256':sha(db),'slack_ns':pr['slack_ns'],'formal_release_approved':False,'hardware_test':False,'flash_modified':False,'known_open_review':['SDRAM hard macro relocation/SiP/PVT/internal delay and full-address real-device BIST remain open','RGB332 frame buffer remains the implementation boundary','audio source is I2S demo tone; TF WAV/MP3 playback is not implemented','bit is SRAM diagnostic candidate only; do not write Flash without separate user instruction']}
tcl_lines=['if {[catch {','import_device eagle_s20.db -package EG4S20NG88','cd {GATE}','open_project idx_video.prj -noanalyze','import_db {DB}','cd {OUT}','update_timing -mode final','report_timing_status -file bit_source.ts','set f [open bit_source.ts r]','set ts [read $f]','close $f','puts $ts','foreach metric {SWNS STNS HWNS HTNS} {',' if {![regexp [format {%s: *(-?[0-9]+[.][0-9]+)ns} $metric] $ts ignored value]} {error "Missing metric $metric"}',' if {$value < 0} {error "Negative timing metric $metric"}','}','check_timing -file bit_source.check -verbose','commit_param -step bitgen','bitgen -bit BITNAME','export_bitgen_param -file diagnostic_bitgen_param.f','puts "@@@ V103_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE"','} msg opts]} {puts "@@@ TASK_ERROR: $msg"; puts [dict get $opts -errorinfo]}','exit']
tcl='\n'.join(tcl_lines).replace('GATE',gate.as_posix()).replace('DB',db.as_posix()).replace('OUT',out.as_posix()).replace('BITNAME',bitname)+'\n';script=out/'invoke.tcl';script.write_text(tcl,encoding='utf8');record['invoke_tcl_sha256']=sha(script)
td=Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin');env=dict(os.environ);env['PATH']=str(td)+os.pathsep+env.get('PATH','');start=time.monotonic()
temp_dir=root/'00_tmp';temp_dir.mkdir(exist_ok=True)
env.update(TEMP=str(temp_dir),TMP=str(temp_dir),TMPDIR=str(temp_dir),PYTHONDONTWRITEBYTECODE='1')
with (out/'run.log').open('wb') as f:
 try:r=subprocess.run([str(td/'run.exe')],input=('source {'+script.as_posix()+'}\n').encode(),cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=240);record['returncode']=r.returncode
 except subprocess.TimeoutExpired:record['timeout']=True
log=(out/'run.log').read_text(encoding='utf8',errors='replace');bit=out/bitname;newcheck=out/'bit_source.check';newcounts={m.group(1):int(m.group(2)) for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',newcheck.read_text(encoding='utf8',errors='replace'),re.M)} if newcheck.is_file() else {}
record.update(elapsed_seconds=round(time.monotonic()-start,3),task_error='@@@ TASK_ERROR:' in log,marker_present='@@@ V103_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE' in log,nonempty_bit=bit.is_file() and bit.stat().st_size>0,reloaded_timing_check_matches=newcounts==counts)
record['completed']=bool(record.get('returncode')==0 and not record['task_error'] and record['marker_present'] and record['nonempty_bit'] and record['reloaded_timing_check_matches'])
if record['completed']:
 req(sha(db)==record['routed_db_sha256'],'routed DB changed during bitgen');req(check_hashes(syn)>0,'synthesis source hashes changed');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(bit,target);record.update(bit_sha256=sha(target),bit_bytes=target.stat().st_size,published_path=str(target))
(out/'attempt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(record,ensure_ascii=False,indent=2),flush=True);print(out,flush=True);raise SystemExit(0 if record['completed'] else 1)
