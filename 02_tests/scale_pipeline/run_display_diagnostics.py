from pathlib import Path
import datetime,hashlib,json,os,subprocess
r=Path(__file__).resolve().parents[2];h=Path(__file__).resolve().parent;p=r/'01_project/rtl'
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
out=r/'04_evidence'/('v088_display_diagnostics_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
src=[h/'tb_display_diagnostics.sv',p/'video/display_diagnostics.v'];sha_src=src+[p/'video/osd_font.vh']
cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(p),'-s','tb_display_diagnostics','-o',str(out/'test.vvp'),*map(str,src)]
c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=30);text=c.stdout+c.stderr;rc=None
if c.returncode==0:
 c2=subprocess.run([str(b/'vvp.exe'),str(out/'test.vvp')],capture_output=True,text=True,env=env,timeout=40);text+=c2.stdout+c2.stderr;rc=c2.returncode
(out/'run.log').write_text(text,encoding='utf-8')
summary={'scope':'Independent banner RGB/font/control/audio-gate, six live/history/reset scenarios; NOT board or long-running full system','passed':c.returncode==0 and rc==0 and 'PASS display_diagnostics' in text and 'FATAL' not in text,'compile_returncode':c.returncode,'run_returncode':rc,'source_sha256':{s.relative_to(r).as_posix():hashlib.sha256(s.read_bytes()).hexdigest() for s in sha_src},'results':[s for s in text.splitlines() if s.startswith(('PASS','FATAL'))]}
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2));print(out);raise SystemExit(0 if summary['passed'] else 1)
