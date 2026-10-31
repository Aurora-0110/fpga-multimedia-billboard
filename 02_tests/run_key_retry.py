from pathlib import Path
import subprocess,os,json,argparse
R=Path(__file__).resolve().parents[1];t=R/'02_tests';ap=argparse.ArgumentParser();ap.add_argument('--iverilog-bin',type=Path,default=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'));a=ap.parse_args();b=a.iverilog_bin.resolve();e=dict(os.environ);e['PATH']=str(b)+os.pathsep+e.get('PATH','')
f=t/'build/key_retry.vvp';cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-s','tb_key_retry','-o',str(f),str(t/'tb_key_retry.sv'),str(R/'01_project/rtl/common/key_debounce.v')]
c=subprocess.run(cmd,env=e,capture_output=True,text=True);assert c.returncode==0,c.stderr
v=subprocess.run([str(b/'vvp.exe'),str(f)],env=e,capture_output=True,text=True,timeout=30);text=c.stdout+c.stderr+v.stdout+v.stderr
(t/'logs/v054/key_retry.log').write_text(text,encoding='utf8');row=dict(passed=v.returncode==0 and 'PASS key_retry' in text,compile_command=cmd,returncode=v.returncode,output=text)
(t/'key_retry_results.json').write_text(json.dumps(row,indent=2),encoding='utf8');print(text);raise SystemExit(0 if row['passed'] else 1)
