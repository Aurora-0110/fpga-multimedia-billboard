from pathlib import Path
import hashlib,json,os,subprocess,time

root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent
tools=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
out=root/'04_evidence'/('v087_full_scaler_'+time.strftime('%Y%m%d_%H%M%S'));out.mkdir()
env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
src=[here/'tb_full_scaler.sv',root/'01_project/rtl/scale/bilinear_stream_scaler.v',root/'01_project/rtl/scale/bilinear_rgb888.v']
summary={'result':'IN_PROGRESS','scope':'Full1280x720 bilinear RTL output vs independent integer per-pixel oracle; NOT SDRAM/video or hardware',
         'source_sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src},'cases':[]}
try:
 cmd=[str(tools/'iverilog.exe'),'-g2012','-Wall','-s','tb_full_scaler','-o',str(out/'full.vvp'),*map(str,src)]
 c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=45)
 (out/'compile.log').write_text(c.stdout+c.stderr,encoding='utf-8');assert c.returncode==0,c.stderr
 for w,h,td in [(640,480,1),(17,11,0)]:
  name=f'{w}x{h}_top{td}';log=out/(name+'.log');start=time.monotonic()
  row={'source':[w,h],'top_down':bool(td),'passed':False}
  with log.open('w',encoding='utf-8') as f:
   try:
    c=subprocess.run([str(tools/'vvp.exe'),str(out/'full.vvp'),f'+W={w}',f'+H={h}',f'+TD={td}'],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=900)
    row['returncode']=c.returncode
   except subprocess.TimeoutExpired:row['timeout']=True
  text=log.read_text(encoding='utf-8');row['elapsed_seconds']=round(time.monotonic()-start,3)
  row['passed']=row.get('returncode')==0 and 'PASS full_scaler' in text and not any(s in text for s in ['FATAL','ERROR'])
  row['result_lines']=[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR','PROGRESS'))]
  summary['cases'].append(row);print(name,row,flush=True)
  assert row['passed'],text
 summary['result']='PASS'
finally:
 (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(out,flush=True)
