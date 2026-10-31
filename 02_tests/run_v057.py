from pathlib import Path
import subprocess,os,json,datetime,time,hashlib,argparse
ap=argparse.ArgumentParser();ap.add_argument('--iverilog-bin',type=Path,default=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')));ap.add_argument('--group',choices=['quick','spi','chain','legacy'],default='quick');a=ap.parse_args()
r=Path(__file__).resolve().parents[1];t=r/'02_tests';p=r/'01_project/rtl';b=a.iverilog_bin;env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out=t/'build'/('v057_'+a.group+'_'+stamp);out.mkdir(parents=True);logs=r/'04_evidence'/('sim_'+a.group+'_'+stamp);logs.mkdir()
tf=list((p/'tf').glob('*.v'))
if a.group=='quick':
 cases=[('packer_bottom','tb_bmp_packer',[t/'tb_bmp_packer.sv',p/'tf/bmp_pixel_packer.v'],[],[]),('packer_top','tb_bmp_packer',[t/'tb_bmp_packer.sv',p/'tf/bmp_pixel_packer.v'],[],['+TOP=1'])]+[(f'packer_error_{i}','tb_bmp_packer',[t/'tb_bmp_packer.sv',p/'tf/bmp_pixel_packer.v'],[],[f'+MODE={i}']) for i in range(1,4)]
elif a.group=='spi':
 src=[t/'tb_tf_loader.sv',t/'legacy_tf/sd_bmp_card_model.v',*tf]
 cases=[('crc_reject','tb_tf_loader',src,[],['+CRC_READ=7','+ERROR=26']),('full_new_image','tb_tf_loader',src,[],[]),('full_top_down','tb_tf_loader',src,[],['+TOP=1'])]
 # TOP is both a test/model argument: use corresponding true top-down image file.
elif a.group=='chain':
 src=[t/'tb_bmp_memory_chain.sv',t/'vendor/IS42s32200.v',p/'tf/bmp_pixel_stream.v',p/'tf/bmp_pixel_packer.v']+[p/f for f in ['video/idx_writer.v','video/idx_reader.v','video/idx_display.v','video/idx_pipeline.v','video/fb_session_ctrl.v','video/video_timing.v','common/reset_release.v','mem/sdram_ctrl.v','mem/async_fifo.v']]
 cases=[('bmp_memory_720p','tb_bmp_memory_chain',src,[],[]),('bmp_memory_top_down','tb_bmp_memory_chain',src,[],['+TOP=1'])]
else:
 src=[t/'legacy_tf/tb_bmp_pixel_stream.v',p/'tf/bmp_pixel_stream.v']
 import zlib
 crc=zlib.crc32(bytes((i*17+11)&255 for i in range(36)))
 modes=[(0,0),(5,6),(6,6),(7,6),(8,7),(9,3),(10,3),(11,3),(12,1),(13,5),(14,5),(15,5),(16,2),(17,4),(18,2),(19,2),(20,2),(21,7),(23,1),(24,6),(25,6)]
 cases=[(f'legacy_pixels_{i}','tb_bmp_pixel_stream',src,[],[f'+MODE={i}',f'+ERROR={err}',f'+CRC={crc:08x}','+OFFSET=500']) for i,err in modes]
rows=[]
for name,top,src,opts,args in cases:
 start=time.monotonic();exe=out/(name+'.vvp');cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-s',top,*opts,'-o',str(exe),*map(str,src)]
 cp=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=90);(logs/(name+'_compile.log')).write_text(cp.stdout+cp.stderr,encoding='utf-8');row=dict(name=name,compile_rc=cp.returncode,passed=False)
 if cp.returncode==0:
  if a.group in ['spi','chain']:
   args=[f'+IMAGE={(t/"fixtures"/("v056_top.hex" if "+TOP=1" in args else "v056_A.hex")).as_posix()}',*args]
  try:
   cmd=[str(b/'vvp.exe'),str(exe),*args]
   with (logs/(name+'.log')).open('w',encoding='utf-8') as f:cp=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1000)
   text=(logs/(name+'.log')).read_text(encoding='utf-8');row.update(sim_rc=cp.returncode,passed=cp.returncode==0 and 'PASS' in text and 'FATAL' not in text,result_lines=[l for l in text.splitlines() if l.startswith(('PASS','FATAL','ERROR'))],command=cmd)
  except subprocess.TimeoutExpired:row['timeout']=True
 row['elapsed_s']=round(time.monotonic()-start,3);rows.append(row)
 result=dict(scope='v057 '+a.group+' fresh simulation, NO hardware/electrical acceptance',passed=all(x['passed'] for x in rows),complete=len(rows)==len(cases),cases=rows,source_sha256={f.relative_to(r).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in src})
 (logs/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(name,row,flush=True)
 if not row['passed']:break
raise SystemExit(0 if result['passed'] and result['complete'] else 1)
