from pathlib import Path
import os,subprocess,datetime,json,hashlib
r=Path(__file__).resolve().parents[1];rtl=r/'01_project/rtl';t=r/'02_tests'
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
out=r/'04_evidence'/('v078_memory_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
src=[t/'tb_v078_memory.sv',t/'vendor/IS42s32200.v',*[rtl/x for x in ['common/reset_release.v','mem/sdram_ctrl.v','mem/async_fifo.v','video/idx_slide_reader.v','video/idx_dual_pipeline.v','video/idx_display.v','video/video_timing.v']]]
rows=[]
for height,step in [(8,40),(480,2)]:
 name=f'h{height}_step{step}';exe=out/(name+'.vvp');log=out/(name+'.log')
 cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-s','tb_v078_memory',f'-Ptb_v078_memory.HEIGHT={height}',f'-Ptb_v078_memory.STOP_STEP={step}','-o',str(exe),*map(str,src)]
 c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=30);log.write_text(c.stdout+c.stderr,encoding='utf8');row={'case':name,'compile_rc':c.returncode,'passed':False}
 if not c.returncode:
  with log.open('a',encoding='utf8') as f:
   try:v=subprocess.run([str(b/'vvp.exe'),str(exe)],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=600);row['sim_rc']=v.returncode
   except subprocess.TimeoutExpired:row['timeout']=True
  text=log.read_text();row['passed']=row.get('sim_rc')==0 and 'PASS memory' in text and 'ERROR' not in text and 'VIOLATION' not in text.upper()
 row['result_lines']=[s for s in log.read_text().splitlines() if s.startswith(('PASS','FATAL','ERROR'))];rows.append(row)
 print(name,row,flush=True)
 (out/'summary.json').write_text(json.dumps({'passed':all(x['passed'] for x in rows),'scope':'Real SDRAM bus model/controller/arbiter/FIFO/display, synthetic burst loader, not TF nor hardware; full 40-step reduced-height plus full-resolution first 2 steps','tests':rows,'sha256':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in src}},indent=2))
 if not row['passed']:break
print(out,flush=True)
raise SystemExit(0 if len(rows)==2 and all(x['passed'] for x in rows) else 1)
