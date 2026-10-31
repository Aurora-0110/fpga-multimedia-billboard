"""Run the native TD synthesis commands without the absent GUI run-manager helper.
Commands are reproduced from the preserved successful v116 TD synthesis log.
No installation/driver files, clocks, constraints or permissions are changed.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,time
root=Path(__file__).resolve().parents[2];project=root/'01_project'
ap=argparse.ArgumentParser();ap.add_argument('--attempt',type=int,default=2);args=ap.parse_args()
out=root/f'05_td/v119_audio_visual_synth_attempt{args.attempt}';assert not out.exists();out.mkdir(parents=True)
gate=out/'build/idx_video_Runs/syn_1';gate.mkdir(parents=True)
seed=root/'05_td/v119_audio_visual_synth_attempt1/build/idx_video_Runs/syn_1/idx_video.prj'
shutil.copy2(seed,gate/'idx_video.prj')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reference=root/'04_evidence/v116_final_synthesis_preserved/idx_video_Runs/syn_1/run.log'
text=reference.read_text(encoding='utf8',errors='replace')
for cmd in ('elaborate -top idx_audio_visual_top','optimize_rtl','optimize_gate -packarea idx_video_gate.area','export_db idx_video_gate.db'):
 assert f'start command "{cmd}"' in text
script=out/'invoke.tcl'
commands=[f'cd {{{gate.as_posix()}}}','import_device eagle_s20.db -package EG4S20NG88','open_project idx_video.prj',
 'commit_param -step design','elaborate -top idx_audio_visual_top',
 f'read_adc {{{(project/"boards/idx_video.adc").as_posix()}}}',f'read_sdc {{{(project/"boards/idx_video.sdc").as_posix()}}}',
 'export_db idx_video_elaborate.db','commit_param -step rtl','set_param rtl min_control_set 2','insert_debugger','optimize_rtl',
 'report_area -file idx_video_rtl.area','export_db idx_video_rtl.db','commit_param -step gate',
 'set_param gate pack_effort high','set_param gate pack_seq_in_io off','optimize_gate -packarea idx_video_gate.area',
 'update_pll_param -module idx_audio_visual_top','report_qor -step gate -file gate.qor','start_timer',
 'report_area -file idx_video_gate.area','legalize_phy_inst','update_timing','start_timer',
 'report_timing_status -file idx_video_gate.ts','report_timing_summary -file idx_video_gate.timing','flow_status -file flow.status',
 'export_db idx_video_gate.db','export_flow_status -s read_design -e opt_gate','flow_status',
 'puts "@@@ V119 NATIVE SYNTHESIS COMPLETE"']
script.write_text('if {[catch {\n'+'\n'.join(commands)+'\n} msg opts]} {puts "@@@ TASK_ERROR: $msg"; puts [dict get $opts -errorinfo]}\nexit\n',encoding='utf8')
record=dict(scope='Actual TD native full-system synthesis using preserved successful command sequence; no place/route/bit/hardware',
 reason='GUI launch_runs crashed; installed run_commands_prompt.exe and doc/scripts/DefaultFlow.tcl are absent. Direct native TD commands require neither helper.',
 reference_v116_log_sha256=sha(reference),generated_project_sha256=sha(gate/'idx_video.prj'),
 source_sha256={p.relative_to(root).as_posix():sha(p)for p in project.rglob('*')if p.is_file() and p.suffix in {'.v','.vh','.tcl','.adc','.sdc'}and 'build'not in p.relative_to(project).parts})
td=Path(r'D:\FPGA_Billboard\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin');env=dict(os.environ);env['PATH']=str(td)+os.pathsep+env.get('PATH','');env.update(TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),TMPDIR=str(root/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
start=time.monotonic()
with (out/'run.log').open('wb')as log:
 try:
  p=subprocess.run([str(td/'run.exe')],input=('source {'+script.as_posix()+'}\n').encode(),cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600);record['returncode']=p.returncode
 except subprocess.TimeoutExpired:record['timeout']=True
text=(out/'run.log').read_text(encoding='utf8',errors='replace');area=gate/'idx_video_gate.area'
record.update(elapsed_seconds=round(time.monotonic()-start,3),task_error='@@@ TASK_ERROR:'in text,
 synth_marker_present='@@@ V119 NATIVE SYNTHESIS COMPLETE'in text,gate_db_present=(gate/'idx_video_gate.db').is_file(),area_present=area.is_file(),
 sources_unchanged=all(sha(root/p)==h for p,h in record['source_sha256'].items()))
if area.is_file():
 s=area.read_text(encoding='utf8',errors='replace');record['resources']={k:int(re.search(r'^#'+k+r'\s+(\d+)',s,re.M).group(1))for k in ['lut','reg','bram','bram32k','dsp','pll','gclk','pad']}
 record['within_capacities']=all(record['resources'][k]<=n for k,n in {'lut':19600,'reg':19600,'bram':64,'bram32k':16,'dsp':29,'pll':4,'gclk':16,'pad':66}.items())
record['completed']=bool(record.get('returncode')==0 and not record['task_error']and record['synth_marker_present']and record['gate_db_present']and record.get('within_capacities')and record['sources_unchanged'])
(out/'attempt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in record.items()if k!='source_sha256'},ensure_ascii=False,indent=2),flush=True);print(out,flush=True);raise SystemExit(0 if record['completed']else 1)
