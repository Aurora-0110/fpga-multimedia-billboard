"""v065 dual-speed SD SPI tests. Digital protocol models, not electrical/PVT signoff."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,subprocess,time,zlib
ap=argparse.ArgumentParser();ap.add_argument('--group',choices=['quick','timing','full','all'],default='quick');a=ap.parse_args()
r=Path(__file__).resolve().parents[1];t=r/'02_tests';p=r/'01_project/rtl';b=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'))
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out=t/'build'/('v065_speed_'+a.group+'_'+stamp);out.mkdir(parents=True)
e=r/'04_evidence'/('sim_speed_'+a.group+'_'+stamp);e.mkdir();cases=[]
unit=[t/'tb_spi_speed.sv',p/'tf/spi_byte.v'];loader=[t/'tb_spi_loader_speed.sv',t/'sd_playlist_card_model.v',*sorted((p/'tf').glob('*.v'))]
if a.group in ['quick','all']:
 for init,data in [(124,12),(124,25),(1,1)]:cases.append((f'byte_{init}_{data}','tb_spi_speed',unit,dict(INIT_DIV=init,DATA_DIV=data),[]))
 cases.append(('legacy_byte','tb_spi_byte',[t/'legacy_tf/tb_spi_byte.v',p/'tf/spi_byte.v'],{},[]))
 for name,args in [('sdhc',[]),('sdsc',['+SDSC=1']),('crc_boot',['+CRC_READ=1','+ERROR=26']),('crc_payload',['+CRC_READ=7','+ERROR=26']),('reset_retry',['+RETRY=1'])]:cases.append((name,'tb_spi_loader_speed',loader,dict(INIT_DIV=124,DATA_DIV=12),args))
if a.group in ['timing','all']:
 for name,init,data,delay in [('old_990k',124,25,0),('new_2062k',124,12,0),('new_2062k_miso40ns',124,12,40)]:cases.append((name,'tb_spi_loader_speed',loader,dict(INIT_DIV=init,DATA_DIV=data,MISO_DELAY_NS=delay),[]))
if a.group == 'full':
 for idx in range(3):cases.append((f'full_SPI_{chr(65+idx)}','tb_spi_loader_speed',loader,dict(INIT_DIV=6,DATA_DIV=1),[f'+SELECT={idx}','+BURSTS=19200']))
 cases.append(('full_SPI_top_down','tb_spi_loader_speed',loader,dict(INIT_DIV=6,DATA_DIV=1),['+TOP=1','+BURSTS=19200']))

if a.group in ['timing','all']:
 for idx in [1,2]:cases.append((f'real_divider_{chr(65+idx)}','tb_spi_loader_speed',loader,dict(INIT_DIV=124,DATA_DIV=12),[f'+SELECT={idx}']))
rows=[]
for name,top,src,params,args in cases:
 start=time.monotonic();exe=out/(name+'.vvp');cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-s',top,*[f'-P{top}.{k}={v}' for k,v in params.items()],'-o',str(exe),*map(str,src)]
 cp=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=90);ct=cp.stdout+cp.stderr;(e/(name+'_compile.log')).write_text(ct,encoding='utf-8');row=dict(name=name,params=params,compile_rc=cp.returncode,passed=False,compile_command=cmd)
 if cp.returncode==0:
  if top=='tb_spi_loader_speed':
   image=t/'fixtures/v056_A.hex';payload=bytes(int(v,16) for v in image.read_text().split())[54:];idx=int(next((x.split('=')[1] for x in args if x.startswith('+SELECT=')),'0'));mask=[0,0xe0,0xc0][idx]
   crc=zlib.crc32(bytes(v^mask for v in payload));args=[*args,'+IMAGE='+image.as_posix(),f'+CRC={crc:08x}']
  cmd=[str(b/'vvp.exe'),str(exe),*args];row['command']=cmd
  try:
   with (e/(name+'.log')).open('w',encoding='utf-8') as log:cp=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
   text=(e/(name+'.log')).read_text();metrics=next((v for v in text.splitlines() if v.startswith('METRICS ')),'')
   row.update(sim_rc=cp.returncode,passed=cp.returncode==0 and 'PASS' in text and 'FATAL' not in text and 'error:' not in ct.lower(),result_lines=[v for v in text.splitlines() if v.startswith(('PASS','FATAL','METRICS'))],metrics=dict(re.findall(r'(\w+)=([\w-]+)',metrics)))
  except subprocess.TimeoutExpired:row['timeout']=True
 row['elapsed_s']=round(time.monotonic()-start,3);rows.append(row)
 result=dict(scope='v065 SPI protocol and divider testing; real divider values for partial speed comparison; full images use accelerated simulation clocks/dividers, not electrical validation, not full SPI-SDRAM-HDMI integration',passed=all(v['passed'] for v in rows),complete=len(rows)==len(cases),cases=rows,source_sha256={v.relative_to(r).as_posix():hashlib.sha256(v.read_bytes()).hexdigest() for v in set(f for c in cases for f in c[2])})
 if len([v for v in rows if v['name'] in ['old_990k','new_2062k']])==2:
  old=next(v for v in rows if v['name']=='old_990k')['metrics'];new=next(v for v in rows if v['name']=='new_2062k')['metrics']
  equal=all(old[k]==new[k] for k in ['bursts','reads','hash','error']);ratio=int(old['total_cycles'])/int(new['total_cycles']);result['speed_comparison']=dict(equal_data_hash_and_counts=equal,partial_total_cycle_speedup=ratio,old_cycles=old['total_cycles'],new_cycles=new['total_cycles'],hardware_measured=False)
  result['passed'] &= equal and ratio>1.5
 (e/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(name,row,flush=True)
 if not row['passed']:break
print('REPORT',e/'summary.json',flush=True)
raise SystemExit(0 if result['passed'] and result['complete'] else 1)
