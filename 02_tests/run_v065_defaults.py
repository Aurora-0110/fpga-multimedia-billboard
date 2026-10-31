from pathlib import Path
import subprocess,os,json,hashlib
r=Path(__file__).resolve().parents[1];b=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'))
e=r/'04_evidence';o=r/'02_tests/build/v065_defaults';o.mkdir(parents=True,exist_ok=True)
src=[r/'02_tests/tb_v065_production_defaults.sv',r/'01_project/boards/idx_video_top.v',*[p for p in sorted((r/'01_project/rtl').rglob('*.v')) if not p.name.startswith('pll_')]]
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
cmd=[str(b/'iverilog.exe'),'-g2012','-I',str(r/'01_project/rtl'),'-Wall','-i','-s','tb_v065_production_defaults','-o',str(o/'test.vvp'),*map(str,src)]
x=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=60);text=x.stdout+x.stderr
row=dict(scope='ELABORATION ONLY: -i intentionally omits PLL source files and ignores absent vendor primitives. No PLL/PHY/runtime signoff.',compile_rc=x.returncode,command=cmd,passed=False)
if x.returncode==0:
 y=subprocess.run([str(b/'vvp.exe'),str(o/'test.vvp')],capture_output=True,text=True,env=env,timeout=30);text+=y.stdout+y.stderr;row.update(sim_rc=y.returncode,passed=y.returncode==0 and 'PASS production parameter' in text)
row['source_sha256']={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}
(e/'production_defaults.log').write_text(text,encoding='utf-8');(e/'production_defaults.json').write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8');print(text)
raise SystemExit(0 if row['passed'] else 1)
