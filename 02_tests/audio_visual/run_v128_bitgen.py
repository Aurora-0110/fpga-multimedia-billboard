"""Fresh V128 source-bound test/ROM/STA guard. Never programs SRAM or Flash."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,time
root=Path(__file__).resolve().parents[2];a=argparse.ArgumentParser();a.add_argument('--check-reports-only',action='store_true');a.add_argument('--attempt',type=int,default=1);args=a.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def req(x,m):
 if not x:raise RuntimeError(m)
def check_hashes(x):
 n=0
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ('source_sha256','sources')and isinstance(v,dict)and v and all(isinstance(h,str)and re.fullmatch('[0-9a-f]{64}',h)for h in v.values()):
    for rel,h in v.items():
     p=Path(rel);req(not p.is_absolute()and '..'not in p.parts,'not a current relative source: '+rel);p=root/p
     req(p.is_file()and sha(p)==h,'evidence hash mismatch '+rel);n+=1
   elif isinstance(v,(dict,list)):n+=check_hashes(v)
 elif isinstance(x,list):
  for v in x:n+=check_hashes(v)
 return n
reports={}
def use_path(name,path):
 j=json.loads(path.read_text(encoding='utf-8-sig'));req(j.get('passed',j.get('pass'))is True or j.get('result')=='PASS','failed report '+str(path))
 for key in ('tests','cases'):
  if isinstance(j.get(key),list):req(j[key]and all(x.get('passed',x.get('pass'))is True for x in j[key]),'failed/incomplete cases '+str(path))
 n=check_hashes(j);req(n>0,'no source hashes '+str(path));reports[name]=dict(path=path.relative_to(root).as_posix(),sha256=sha(path),source_checks=n)
 return j
def latest(name,pattern):
 dirs=sorted((root/'04_evidence').glob(pattern));req(bool(dirs),'no evidence '+pattern)
 return use_path(name,dirs[-1]/'summary.json')
req('01_versions'not in root.parts,'Never generate bit in frozen archives')
af=latest('fresh_affected','v128_affected_[0-9]*');req(len(af['cases'])==8,'affected cases')
# The orchestrator binds the current production tree; also verify every child report independently.
for row in af['cases']:
 for path in row['summary_paths']:use_path('affected_'+row['case'],Path(path))
use_path('caption_generation_provenance',root/'04_evidence/v128_caption_generation/summary.json')
ca=latest('captions','v128_captions_[0-9]*');req(ca.get('complete')and len(ca['tests'])==3 and ca['enabled_cues']==53,'caption coverage')
latest('actual_top_captions','v128_caption_top_[0-9]*')
three=latest('fresh_three_wav','v128_three_wav_[0-9]*');req(three.get('complete')and len(three['cases'])==11,'three WAV coverage')
# SPI source is byte-identical. Fresh600s attempt status retained separately, not called PASS.
latest('arbiter_diagnostics','v128_units_[0-9]*')
core=use_path('unchanged_core_and_SPI_baseline_reports',root/'04_evidence/v128_unchanged_core_with_spi/summary.json');req(core.get('complete')and len(core['inherited_reports'])==10,'inherited core coverage')
for entry in core['inherited_reports']:
 req(entry['inherited_not_rerun']and sha(Path(entry['baseline_report']))==entry['baseline_report_sha256'],'baseline report changed')
rom=latest('routed_rom_init','v128_rom_init_[0-9]*');req(rom.get('physical_attempt')==1 and len(rom['mapped_roms'])==13,'ROM source/attempt coverage')
use_path('resource_review',root/'04_evidence/v128_resource_review/summary.json')
syn_dir=root/'05_td/v128_audio_visual_synth_attempt1';syn=json.loads((syn_dir/'attempt.json').read_text());req(syn['completed']and syn['within_capacities']and check_hashes(syn)>0,'synthesis/source guard')
gate=syn_dir/'build/idx_video_Runs/syn_1';phy_dir=root/'05_td/v128_audio_visual_physical_attempt1';phy=json.loads((phy_dir/'attempt.json').read_text());physical=phy_dir/'physical'
req(phy['completed']and phy['nonnegative_slack']and not phy['diagnostic_bit_generated'],'physical guard')
req(phy['synth_gate_sha256']==sha(gate/'idx_video_gate.db'),'synthesis DB changed')
req(phy['physical_script_sha256']==sha(root/phy['physical_script']),'physical flow changed')
req(len(phy['slack_ns'])==4 and min(phy['slack_ns'].values())>=0,'negative/missing slack')
counts={m.group(1):int(m.group(2))for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',(physical/'sdram_check.rpt').read_text(),re.M)}
for k in ('no clock','clock definition','invalid constraint','pll/clock buffer clock constraints','combinational loops','no path constraints','shadowed/ignored timing exception constraints'):req(counts.get(k)==0,'timing constraint failure '+k)
# Existing intentional diagnostic/CDC exclusions remain exactly unchanged, not silently expanded.
base=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v126_fifo_prefix_20261030\01_project')
for rel in ['01_project/boards/idx_video.adc','01_project/boards/idx_video.sdc','01_project/rtl/ip/pll_video720.v','01_project/rtl/ip/pll_sdram.v']:req(sha(root/rel)==sha(base/rel),'pin/clock/constraint change '+rel)
record=dict(scope='V128 full52user lyric lines/53cues, dual offline forced alignment, actual WAV sample events and lossless glyph packing. Fresh tests and routed ROM/STA. Human timing/HDMI sink/hardware/PVT signoff remain open.',reviewed_reports=reports,synthesis_attempt_sha256=sha(syn_dir/'attempt.json'),physical_attempt_sha256=sha(phy_dir/'attempt.json'),synth_gate_sha256=sha(gate/'idx_video_gate.db'),routed_db_sha256=sha(physical/'sdram_pr.db'),slack_ns=phy['slack_ns'],check_timing_counts=counts,transcript_human_verified=False,complete_lyrics=True,full_user_text_covered=True,human_timing_verified=False,hardware_test=False,flash_modified=False,formal_release_approved=False)
if args.check_reports_only:print(json.dumps(record,ensure_ascii=False,indent=2));raise SystemExit(0)
out=root/f'05_td/v128_sample_caption_bitgen_attempt{args.attempt}';req(not out.exists(),'never overwrite bitgen evidence');out.mkdir();name='v128_sample_captions_720p.bit';target=root/'03_bitstreams'/name;req(not target.exists(),'published bit exists')
db=physical/'sdram_pr.db';script=out/'invoke.tcl'
lines=['if {[catch {','cd {GATE}','import_device eagle_s20.db -package EG4S20NG88','open_project idx_video.prj -noanalyze','import_db {DB}','cd {OUT}','update_timing -mode final','report_timing_status -file bit_source.ts','set f [open bit_source.ts r]','set t [read $f]','close $f','foreach m {SWNS STNS HWNS HTNS} {',r' set pattern [format {%s:\s*(-?[0-9.]+)ns} $m]',' if {![regexp $pattern $t ignored v] || $v < 0} {error "TIMING_METRIC_FAILED $m"}','}','check_timing -file bit_source.check -verbose','commit_param -step bitgen','bitgen -bit BITNAME','export_bitgen_param -file diagnostic_bitgen_param.f','puts "@@@ V128_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE"','} msg opts]} {puts "@@@ TASK_ERROR: $msg"; puts [dict get $opts -errorinfo]}','exit']
script.write_text('\n'.join(lines).replace('GATE',gate.as_posix()).replace('DB',db.as_posix()).replace('OUT',out.as_posix()).replace('BITNAME',name)+'\n',encoding='utf8');record['invoke_tcl_sha256']=sha(script)
td=Path(r'D:\FPGA_Billboard\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin');env=dict(os.environ);env.update(PATH=str(td)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),TMPDIR=str(root/'00_tmp'),PYTHONDONTWRITEBYTECODE='1');start=time.monotonic()
with (out/'run.log').open('wb')as log:
 try:c=subprocess.run([str(td/'run.exe')],input=('source {'+script.as_posix()+'}\n').encode(),cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240);record['returncode']=c.returncode
 except subprocess.TimeoutExpired:record['timeout']=True
log=(out/'run.log').read_text(encoding='utf8',errors='replace');bit=out/name
reloaded={k:float(v)for k,v in re.findall(r'(SWNS|STNS|HWNS|HTNS):\s*(-?\d+\.\d+)ns',(out/'bit_source.ts').read_text())}if(out/'bit_source.ts').is_file()else{}
newcounts={m.group(1):int(m.group(2))for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',(out/'bit_source.check').read_text(),re.M)}if(out/'bit_source.check').is_file()else{}
record.update(elapsed_seconds=round(time.monotonic()-start,3),reloaded_slack_ns=reloaded,reloaded_slack_matches=reloaded==phy['slack_ns'],reloaded_timing_check_matches=newcounts==counts,task_error='@@@ TASK_ERROR:'in log,marker_present='@@@ V128_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE'in log,nonempty_bit=bit.is_file()and bit.stat().st_size>0)
record['completed']=bool(record.get('returncode')==0 and not record['task_error']and record['marker_present']and record['nonempty_bit']and record['reloaded_slack_matches']and record['reloaded_timing_check_matches'])
if record['completed']:
 req(check_hashes(syn)>0 and sha(db)==record['routed_db_sha256'],'bit source changed during generation');target.parent.mkdir(exist_ok=True);shutil.copy2(bit,target);record.update(bit_sha256=sha(target),bit_bytes=target.stat().st_size,published_path=str(target))
(out/'attempt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(record,ensure_ascii=False,indent=2),flush=True);print(out,flush=True);raise SystemExit(0 if record['completed']else 1)
