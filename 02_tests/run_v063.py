"""Fresh v063 functional tests. Digital models only; never programs hardware."""
from pathlib import Path
import subprocess,os,json,datetime,hashlib,argparse,time
ap=argparse.ArgumentParser();ap.add_argument('--group',choices=['control','probe','spi','memory','all'],default='control');a=ap.parse_args()
r=Path(__file__).resolve().parents[1];t=r/'02_tests';p=r/'01_project/rtl';b=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'))
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out=t/'build'/('v063_'+a.group+'_'+stamp);out.mkdir(parents=True)
e=r/'04_evidence'/('sim_v063_'+a.group+'_'+stamp);e.mkdir()
cases=[]
if a.group in ['all','control']:cases.append(('playlist_control','tb_playlist_ctrl',[t/'tb_playlist_ctrl.sv',p/'tf/tf_playlist_ctrl.v'],[]))
if a.group in ['all','control']:
 for dwell in [0,1,8]:
  cases.append(('autoplay_'+str(dwell),'tb_autoplay_ctrl',[t/'tb_autoplay_ctrl.sv',p/'tf/tf_playlist_ctrl.v'],[]))
if a.group in ['all','probe']:
 legacy=t/'legacy_tf';f=legacy/'fixtures/superfloppy'
 data=[int(v,16) for v in (f/'data.hex').read_text().split()];lbas=[int(v,16) for v in (f/'lbas.hex').read_text().split()]
 entry=data[512:544];header=data[1024:1536];root=[0]*512
 for idx in range(3):
  ent=entry.copy();ent[0]=65+idx;ent[26]=4+idx;root[idx*32:idx*32+32]=ent
 data=data[:512]+root+header*3;lbas=lbas+[lbas[-1]+1,lbas[-1]+2]
 fields={'BLOCKS':'blocks','READS':'requests','ERROR':'error','MOUNT':'mounted','FOUND':'found','OK':'bmp_ok','TOPDOWN':'top_down','CLUSTER':'file_cluster','OFFSET':'offset','SIZE':'size','SDSC':'sdsc','CRC_READ':'crc_read','STALL':'stall','SD_INIT_ERROR':'sd_init_error'}
 base=json.loads((legacy/'fixtures/cases.json').read_text())[1]
 for idx in range(4):
  fixture=out/('fixture_'+str(idx));fixture.mkdir();x=dict(base);x['blocks']=5;x['file_cluster']=4+idx
  req=[0,lbas[1],lbas[2]+idx]
  if idx==3:x.update(requests=2,error=5,found=0,bmp_ok=0);req=req[:2]
  (fixture/'data.hex').write_text('\n'.join(f'{v:02x}' for v in data)+'\n');(fixture/'lbas.hex').write_text('\n'.join(f'{v:08x}' for v in lbas)+'\n');(fixture/'requests.hex').write_text('\n'.join(f'{v:08x}' for v in req)+'\n')
  args=['+FIXTURE='+fixture.as_posix(),f'+LETTER={65+idx if idx<3 else 90}','+MUTATE=1',*[f'+{k}={x[v]}' for k,v in fields.items()]]
  cases.append(('runtime_name_'+str(idx),'tb_playlist_probe',[t/'tb_playlist_probe.sv',p/'tf/fat32_bmp_probe.v'],args))
if a.group in ['all','spi']:
 for idx in range(3):cases.append(('partial_spi_'+str(idx),'tb_playlist_spi',[t/'tb_playlist_spi.sv',t/'sd_playlist_card_model.v',*(p/'tf').glob('*.v')],[f'+SELECT={idx}','+IMAGE='+(t/'fixtures/v056_A.hex').as_posix()]))
if a.group in ['all','memory']:
 src=[t/'tb_playlist_memory.sv',t/'vendor/IS42s32200.v',p/'tf/tf_playlist_ctrl.v',p/'tf/bmp_pixel_stream.v',p/'tf/bmp_pixel_packer.v']+[p/f for f in ['video/idx_writer.v','video/idx_reader.v','video/idx_display.v','video/idx_pipeline.v','video/fb_session_ctrl.v','video/video_timing.v','common/reset_release.v','mem/sdram_ctrl.v','mem/async_fifo.v']]
 cases.append(('autoplay_memory_A_B_C_A','tb_playlist_memory',src,['+IMAGE='+(t/'fixtures/v056_A.hex').as_posix()]))
rows=[]
for name,top,src,args in cases:
 start=time.monotonic();exe=out/(name+'.vvp');cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(t/'legacy_tf'),'-s',top,'-o',str(exe),*map(str,src)]
 if name in {'autoplay_0','autoplay_1','autoplay_8'}:cmd.insert(1,'-Ptb_autoplay_ctrl.DWELL='+name.split('_')[-1])
 cp=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=60);(e/(name+'_compile.log')).write_text(cp.stdout+cp.stderr,encoding='utf-8');row=dict(name=name,compile_rc=cp.returncode,passed=False,compile_command=cmd)
 if cp.returncode==0:
  cmd=[str(b/'vvp.exe'),str(exe),*args]
  try:
   with (e/(name+'.log')).open('w',encoding='utf-8') as log:cp=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1500)
   text=(e/(name+'.log')).read_text();row.update(sim_rc=cp.returncode,passed=cp.returncode==0 and 'PASS' in text and 'FATAL' not in text and 'error:' not in (e/(name+'_compile.log')).read_text().lower(),result_lines=[v for v in text.splitlines() if v.startswith(('PASS','FATAL','STAGE'))],command=cmd)
  except subprocess.TimeoutExpired:row['timeout']=True
 row['elapsed_s']=round(time.monotonic()-start,3);rows.append(row)
 result=dict(scope='v063 '+a.group+' functional models; partial SPI=80 bursts per name, memory test=full four epochs via sector server, NOT one all-SPI-to-HDMI simulation or real hardware signoff',passed=all(v['passed'] for v in rows),complete=len(rows)==len(cases),cases=rows,source_sha256={v.relative_to(r).as_posix():hashlib.sha256(v.read_bytes()).hexdigest() for v in set(f for c in cases for f in c[2])})
 (e/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(name,row,flush=True)
 if not row['passed']:break
raise SystemExit(not(result['passed'] and result['complete']))
