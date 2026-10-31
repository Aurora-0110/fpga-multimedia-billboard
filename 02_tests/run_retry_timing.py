from pathlib import Path
import subprocess,os,json,argparse
R=Path(__file__).resolve().parents[1];t=R/'02_tests';ap=argparse.ArgumentParser();ap.add_argument('--iverilog-bin',type=Path,default=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'));a=ap.parse_args();b=a.iverilog_bin.resolve();e=dict(os.environ);e['PATH']=str(b)+os.pathsep+e.get('PATH','')
build=t/'build/retry';build.mkdir(parents=True,exist_ok=True);log=t/'logs/v054';log.mkdir(parents=True,exist_ok=True);rows=[]
for name,old in [('v047_reproduce',True),('v052_fixed',False)]:
 display_source=t/'fixtures/v047_idx_display.v' if old else R/'01_project/rtl/video/idx_display.v'
 cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-s','tb_retry_timing',*(['-DOLD_DISPLAY'] if old else []),'-o',str(build/(name+'.vvp')),str(t/'tb_retry_timing.sv'),str(R/'01_project/rtl/video/video_timing.v'),str(display_source)]
 c=subprocess.run(cmd,env=e,capture_output=True,text=True);assert c.returncode==0,c.stderr
 v=subprocess.run([str(b/'vvp.exe'),str(build/(name+'.vvp'))],env=e,capture_output=True,text=True,timeout=20)
 text=c.stdout+c.stderr+v.stdout+v.stderr;(log/(name+'.log')).write_text(text,encoding='utf8');ok=(v.returncode!=0 and 'RETRY_TIMING_GLITCH' in text) if old else (v.returncode==0 and 'PASS retry_timing' in text)
 rows.append(dict(name=name,passed=ok,expected_failure=old,compile_command=cmd,returncode=v.returncode,output=text));print(name,ok,text)
(t/'retry_timing_results.json').write_text(json.dumps(dict(passed=all(x['passed'] for x in rows),scope='Expected-failing old reset vs fixed timing, not proof of physical monitor root cause',cases=rows),indent=2),encoding='utf8')
raise SystemExit(0 if all(x['passed'] for x in rows) else 1)
