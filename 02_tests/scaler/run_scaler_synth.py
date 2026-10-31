from pathlib import Path
import os,subprocess,json,hashlib,time
R=Path(__file__).resolve().parents[2];OUT=R/'05_td/v085_scaler_synth_attempt1';TD=Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin')
if OUT.exists():raise FileExistsError('Use a fresh attempt; no overwrite')
OUT.mkdir(parents=True);ROOT=R/'01_project';HERE=Path(__file__).resolve().parent
files=[ROOT/'rtl/scale/bilinear_rgb888.v',ROOT/'rtl/scale/bilinear_stream_scaler.v',HERE/'scaler_synth_top.v']
tcl=OUT/'invoke.tcl'
body='create_project scaler_unit {'+OUT.as_posix()+'} -family eg4 -device EG4S20NG88 -speed 1\n'
body+=''.join('add_files {'+f.as_posix()+'}\n' for f in files)
body+='top_module scaler_synth_top\nset_param -run syn_1 gate pack_seq_in_io off\nlaunch_runs syn_1\nwait_run syn_1 600\n'
body+='if {![file exists {'+(OUT/'scaler_unit_Runs/syn_1/scaler_unit_gate.db').as_posix()+'}]} {error "SYNTHESIS_INCOMPLETE"}\nputs "@@@ SCALER_UNIT_SYNTH_COMPLETE_NOT_SYSTEM_SIGNOFF"\n'
tcl.write_text('if {[catch {\n'+body+'} msg opts]} {\n puts "@@@ TASK_ERROR: $msg"\n puts [dict get $opts -errorinfo]\n}\nexit\n',encoding='utf-8')
env=dict(os.environ);env['PATH']=str(TD)+os.pathsep+env.get('PATH','')
record={'scope':'Independent scaler-only synthesis harness; NOT production integration, place/route, timing, bit or hardware acceptance','source_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
t=time.monotonic()
with (OUT/'run.log').open('wb') as log:
 try:
  p=subprocess.run([str(TD/'run.exe')],input=('source {'+tcl.as_posix()+'}\n').encode(),cwd=OUT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=660)
  record['returncode']=p.returncode
 except subprocess.TimeoutExpired:record['timeout']=True
text=(OUT/'run.log').read_text(errors='replace')
record.update(elapsed_seconds=round(time.monotonic()-t,2),synth_marker_present='@@@ SCALER_UNIT_SYNTH_COMPLETE_NOT_SYSTEM_SIGNOFF' in text,task_error='@@@ TASK_ERROR:' in text)
record['gate_db_present']=(OUT/'scaler_unit_Runs/syn_1/scaler_unit_gate.db').is_file()
(OUT/'attempt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(record,indent=2))
if not record['synth_marker_present'] or record['task_error'] or not record['gate_db_present']:raise SystemExit(2)
