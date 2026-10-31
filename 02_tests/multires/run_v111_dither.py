"""All 256 values at each Bayer phase; independent division oracle and registered ack."""
from pathlib import Path
import os,json,hashlib,subprocess,time
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent
tools=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
out=root/'04_evidence'/('v111_dither_'+time.strftime('%Y%m%d_%H%M%S'));out.mkdir()
build=here/'build'/out.name;build.mkdir(parents=True)
src=[here/'tb_v101_dither.sv',root/'01_project/rtl/tf/bmp_pixel_packer.v']
summary={'result':'IN_PROGRESS','scope':'RGB888-to-RGB332 ordered/truncated packer; exact /255 oracle; no hardware','source_sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src+[Path(__file__)]},'tests':[]}
try:
 for mode in (0,1):
  c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-Wall','-s','tb_v101_dither',f'-Ptb_v101_dither.DITHER={mode}','-o',str(build/f'{mode}.vvp'),*map(str,src)],env=env,capture_output=True,text=True,timeout=45)
  (out/f'compile{mode}.log').write_text(c.stdout+c.stderr,encoding='utf8');assert c.returncode==0,c.stderr
  for td in (0,1):
   c=subprocess.run([str(tools/'vvp.exe'),str(build/f'{mode}.vvp'),f'+TD={td}'],env=env,capture_output=True,text=True,timeout=60)
   text=c.stdout+c.stderr;(out/f'mode{mode}_td{td}.log').write_text(text,encoding='utf8')
   passed=c.returncode==0 and 'PASS dither' in text and not any(k in text for k in ('FATAL','ERROR'))
   row={'mode':mode,'top_down':bool(td),'passed':passed,'quantizer_comparisons':8192,'pixels':4096,'result_lines':[x for x in text.splitlines() if x.startswith(('PASS','FATAL','ERROR'))]}
   summary['tests'].append(row);print(row,flush=True);assert passed,text
 summary['result']='PASS'
except Exception as e:
 summary.update(result='FAIL',exception=repr(e));raise
finally:
 (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(out,flush=True)
