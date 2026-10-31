from pathlib import Path
import os,sys,json,hashlib,subprocess,time
from multires_reference import color
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
tools=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
stamp=time.strftime('%Y%m%d_%H%M%S');out=root/'04_evidence'/('v101_multires_scaler_'+stamp);out.mkdir();build=here/'build'/out.name;build.mkdir(parents=True)
sources=[here/'tb_v101_full_scaler.sv',rtl/'scale/bilinear_stream_scaler.v',rtl/'scale/bilinear_rgb888.v']
summary={'result':'IN_PROGRESS','scope':'Independent integer four-corner oracle; streaming large source, full720p scaler output; NOT full720p SPI/physicalSDRAM/HDMI end-to-end','source_sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[Path(__file__),here/'multires_reference.py',root/'02_tests/dynamic_bmp/run_dynamic_tests.py']},'tests':[]}
cases=[(1,1,32,18,1),(2048,1,32,18,0),(1,2048,32,18,1),(2048,2048,32,18,0),(2047,1537,32,18,1),(720,1280,64,36,1),(320,240,1280,720,1),(2048,2048,1280,720,0)]
def reference(w,h,ow,oh,td):
 for y in range(oh):
  sy,ry=divmod(y*(h-1),oh-1);fy=ry*256//(oh-1)
  for x in range(ow):
   sx,rx=divmod(x*(w-1),ow-1);fx=rx*256//(ow-1)
   corners=[color(xx,yy if td else h-1-yy) for yy in (sy,min(sy+1,h-1)) for xx in (sx,min(sx+1,w-1))]
   weights=((256-fx)*(256-fy),fx*(256-fy),(256-fx)*fy,fx*fy)
   c=[(sum(p[ch]*a for p,a in zip(corners,weights))+32768)//65536 for ch in range(3)]
   yield c[0]<<16|c[1]<<8|c[2]
try:
 for ow,oh in sorted({(v[2],v[3]) for v in cases}):
  cmd=[str(tools/'iverilog.exe'),'-g2012','-Wall','-s','tb_v101_full_scaler',f'-Ptb_v101_full_scaler.OW={ow}',f'-Ptb_v101_full_scaler.OH={oh}','-o',str(build/f'{ow}_{oh}.vvp'),*map(str,sources)]
  c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=45);(out/f'compile_{ow}_{oh}.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
 for w,h,ow,oh,td in cases:
  name=f'{w}x{h}_to_{ow}x{oh}_td{td}';folder=build/name;folder.mkdir();start=time.monotonic()
  with (folder/'expected.hex').open('w') as f:
   for p in reference(w,h,ow,oh,td):f.write(f'{p:06x}\n')
  c=subprocess.run([str(tools/'vvp.exe'),str(build/f'{ow}_{oh}.vvp'),f'+W={w}',f'+H={h}',f'+TD={td}'],cwd=folder,env=env,capture_output=True,text=True,timeout=1200)
  text=c.stdout+c.stderr;(out/(name+'.log')).write_text(text);passed=c.returncode==0 and 'PASS scaler' in text and not any(x in text for x in ('FATAL','ERROR'))
  row={'name':name,'source':[w,h],'output':[ow,oh],'top_down':bool(td),'output_pixels':ow*oh,'expected_sha256':hashlib.sha256((folder/'expected.hex').read_bytes()).hexdigest(),'passed':passed,'elapsed_seconds':round(time.monotonic()-start,3),'result_lines':[x for x in text.splitlines() if x.startswith(('PASS','FATAL','ERROR'))]};summary['tests'].append(row);print(name,passed,row['result_lines'],flush=True);assert passed,text[-4000:]
 summary['result']='PASS'
finally:
 (out/'summary.json').write_text(json.dumps(summary,indent=2));print(out,flush=True)
