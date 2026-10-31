from pathlib import Path
import argparse,subprocess,os,json,time,hashlib
ap=argparse.ArgumentParser();ap.add_argument('--iverilog-bin',type=Path,required=True);ap.add_argument('--timeout',type=int,default=900);ap.add_argument('--tag',default='v055');a=ap.parse_args()
assert a.tag.replace('_','').isalnum(),'ASCII tag required'
t=Path(__file__).resolve().parent;p=t.parent/'01_project';b=a.iverilog_bin.resolve();env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
(t/'build').mkdir(exist_ok=True);logs=t/'logs'/a.tag;logs.mkdir(parents=True,exist_ok=True)
files=['video/idx_writer.v','video/idx_reader.v','video/idx_display.v','video/idx_pipeline.v','video/fb_session_ctrl.v','video/video_timing.v','common/reset_release.v','mem/sdram_ctrl.v','mem/async_fifo.v']
source_sha256={str(f.relative_to(t.parent)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in [t/'tb_idx_chain.sv',t/'vendor/IS42s32200.v',*[p/'rtl'/f for f in files]]}
rows=[]
for name,options in [('real_bus_720p',[]),('slow_memory_44MHz',['-Ptb_idx_chain.SD_HALF=11.363636']),('underflow_and_retry',['-Ptb_idx_chain.NEGATIVE=1'])]:
 out=t/'build'/f'{a.tag}_{name}.vvp';cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-s','tb_idx_chain',*options,'-o',str(out),str(t/'tb_idx_chain.sv'),str(t/'vendor/IS42s32200.v'),*[str(p/'rtl'/f) for f in files]]
 start=time.monotonic();r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=60)
 (logs/f'{name}_compile.log').write_text(r.stdout+r.stderr,encoding='utf-8');row={'name':name,'compile_command':cmd,'compile_returncode':r.returncode,'passed':False}
 if r.returncode==0:
  try:
   with (logs/f'{name}.log').open('w',encoding='utf-8') as log:
    sim=subprocess.run([str(b/'vvp.exe'),str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,text=True,timeout=a.timeout)
   text=(logs/f'{name}.log').read_text(encoding='utf-8')
   row.update(sim_returncode=sim.returncode,passed=sim.returncode==0 and 'PASS idx_chain' in text,result_lines=[l for l in text.splitlines() if l.startswith(('PASS','FATAL','ERROR'))])
  except subprocess.TimeoutExpired:row['timeout']=True
 row['elapsed_s']=round(time.monotonic()-start,3);rows.append(row)
 (t/('idx_results.json' if a.tag=='v052' else 'idx_results_'+a.tag+'.json')).write_text(json.dumps({'scope':'Fresh v055 full-frame real controller + ISSI bus model + asynchronous FIFO + 720p timing. No PHY/TMDS electrical or hardware acceptance.','source_sha256':source_sha256,'cases':rows,'passed':all(x['passed'] for x in rows)},indent=2),encoding='utf-8')
 print(name,row['passed'],row.get('result_lines',[]),flush=True)
 if not row['passed']:break
raise SystemExit(0 if len(rows)==3 and all(x['passed'] for x in rows) else 1)
