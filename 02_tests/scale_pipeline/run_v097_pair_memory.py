from pathlib import Path
import hashlib,json,os,subprocess,time
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
tools=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
out=root/'04_evidence'/('v097_pair_memory_'+time.strftime('%Y%m%d_%H%M%S'));out.mkdir()
src=[here/'tb_pair_memory.sv',root/'02_tests/vendor/IS42s32200.v',*[rtl/s for s in ['common/reset_release.v','mem/sdram_ctrl.v','mem/async_fifo.v','video/idx_pair_reader.v','video/idx_pair_display.v','video/idx_pair_pipeline.v','video/video_timing.v']]]
summary={'result':'IN_PROGRESS','scope':'Real controller/physical SDRAM bus model/paired FIFO/display with synthetic burst writer; full width720p plus concurrent writer; NOT TF or hardware',
         'source_sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src},'tests':[]}
try:
 for h,step in [(8,40),(720,2)]:
  name=f'h{h}_step{step}';exe=out/(name+'.vvp');log=out/(name+'.log')
  cmd=[str(tools/'iverilog.exe'),'-g2012','-Wall','-s','tb_pair_memory',f'-Ptb_pair_memory.HEIGHT={h}',f'-Ptb_pair_memory.STOP_STEP={step}','-o',str(exe),*map(str,src)]
  c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=45);log.write_text(c.stdout+c.stderr,encoding='utf-8')
  row={'name':name,'compile_rc':c.returncode,'passed':False};start=time.monotonic()
  if c.returncode==0:
   with log.open('a',encoding='utf-8') as f:
    try:c=subprocess.run([str(tools/'vvp.exe'),str(exe)],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=600);row['returncode']=c.returncode
    except subprocess.TimeoutExpired:row['timeout']=True
   text=log.read_text(encoding='utf-8');row['passed']=row.get('returncode')==0 and 'PASS pair_memory' in text and not any(s in text.upper() for s in ['FATAL','ERROR','VIOLATION'])
   row['result_lines']=[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR'))]
  row['elapsed_seconds']=round(time.monotonic()-start,3);summary['tests'].append(row);print(name,row,flush=True);assert row['passed'],log.read_text(encoding='utf-8')[-6000:]
 summary['result']='PASS'
finally:
 (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(out,flush=True)
