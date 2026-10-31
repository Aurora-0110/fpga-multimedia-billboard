"""Use a process-local Icarus runtime; never change Windows/system PATH."""
from pathlib import Path
import datetime,json,os,subprocess,sys
R=Path(__file__).resolve().parents[1]
if sys.version_info < (3,9):
 print('ERROR: Python 3.9+ required.');sys.exit(2)
binpath=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')).resolve()
lib=binpath.parent/'lib/ivl'
required=[binpath/x for x in ('iverilog.exe','vvp.exe','libgcc_s_seh-1.dll','libstdc++-6.dll','libwinpthread-1.dll')]+[lib/x for x in ('ivl.exe','ivlpp.exe')]
env=dict(os.environ);env['PATH']=str(binpath)+os.pathsep+env.get('PATH','');env['IVERILOG_BIN']=str(binpath)
# Suppress OS loader popup in children, so failures become actionable log errors.
if os.name=='nt':
 import ctypes
 ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x8000)
report={'bundle_version':R.name,'checked_at':datetime.datetime.now().astimezone().isoformat(),
 'iverilog_bin':str(binpath),'environment_scope':'this process and child processes only',
 'missing_files':[str(p) for p in required if not p.is_file()], 'tool_checks':[],
 'rtl_suite_started':False,'rtl_suite_exit_code':None,'hardware_tested':False}
def save():
 d=R/'04_evidence/launcher';d.mkdir(parents=True,exist_ok=True)
 stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
 (d/(stamp+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if report['missing_files']:
 print('ERROR: Incomplete Icarus runtime. Set IVERILOG_BIN to the full ucrt64/bin directory.\n'+'\n'.join(report['missing_files']),flush=True)
 save();sys.exit(2)
for exe in ('iverilog.exe','vvp.exe'):
 cmd=[str(binpath/exe)]+(['-B',str(lib)] if exe=='iverilog.exe' else ['-M',str(lib)])+['-V']
 try:
  cp=subprocess.run(cmd,capture_output=True,text=True,errors='replace',env=env,timeout=20)
  report['tool_checks'].append({'command':cmd,'returncode':cp.returncode,'output':cp.stdout+cp.stderr})
 except (OSError,subprocess.TimeoutExpired) as exc:
  report['tool_checks'].append({'command':cmd,'error':str(exc)})
  print('ERROR: Icarus startup failed: '+str(exc),flush=True);save();sys.exit(2)
 if cp.returncode:
  print('ERROR: Icarus startup failed: '+cp.stdout+cp.stderr,flush=True);save();sys.exit(2)
print('Icarus runtime startup OK (local PATH). Running all 99 tests...',flush=True)
report['rtl_suite_started']=True
try:cp=subprocess.run([sys.executable,str(R/'tools/run_all_tests.py')],env=env);rc=cp.returncode
except OSError as exc:
 report['suite_error']=str(exc);rc=2
report['rtl_suite_exit_code']=rc;save();sys.exit(rc)
