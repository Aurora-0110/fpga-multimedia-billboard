from pathlib import Path
import os,sys,subprocess,json,datetime,hashlib
R=Path(__file__).resolve().parents[1];B=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'));L=B.parent/'lib/ivl'
env=dict(os.environ);env['PATH']=str(B)+os.pathsep+env.get('PATH','')
if not all((B/x).exists() for x in ['iverilog.exe','vvp.exe']):sys.exit('Set IVERILOG_BIN to directory containing iverilog.exe and vvp.exe')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f');O=R/'02_tests/build'/('fat_'+stamp);O.mkdir(parents=True);E=R/'04_evidence/sim'/('fat_'+stamp);E.mkdir(parents=True)
rtl=[R/'01_project/rtl'/x for x in ['spi_byte.v','sd_spi_reader.v','fat32_bmp_probe.v','led_595.v']]
results=[];executables={}
for label,top,extras,prod in [('controller','tb_fat32_bmp_probe',[],False),('spi','tb_fat_spi_integration',['sd_fat_card_model.v'],False),('spi_prod','tb_fat_spi_integration',['sd_fat_card_model.v'],True),('board','tb_fat_board',['sd_fat_card_model.v'],False)]:
 if not (R/'02_tests'/(top+'.v')).exists():continue
 exe=O/(label+'.vvp');src=rtl+[R/'02_tests'/x for x in extras]+[R/'02_tests'/(top+'.v')]
 if label=='board':src += [R/'01_project/boards/tf_probe_top.v']
 cmd=[str(B/'iverilog.exe'),'-B',str(L),'-g2012','-Wall','-I',str(R/'02_tests'),'-s',top,'-o',str(exe)]+(['-DPROD_DIV'] if prod else [])+list(map(str,src))
 cp=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=45);text=subprocess.list2cmdline(cmd)+'\n'+cp.stdout+cp.stderr;(E/('compile_'+label+'.log')).write_text(text,encoding='utf-8')
 if cp.returncode:print(text);sys.exit(1)
 executables[label]=exe
cases=json.loads((R/'02_tests/fixtures/cases.json').read_text())
select={'mbr_ok','superfloppy','sdsc','partition_slot2','root_second_sector','root_fat_chain','active_fat1','root_high_cluster','spc128','top_down','filters','no_file','root_bad','root_cycle','crc_boot','crc_root','crc_bmp','bmp_width'}
for label in executables:
 for c in cases:
  if label=='spi' and c['name'] not in select:continue
  if label in ('spi_prod','board') and c['name']!='mbr_ok':continue
  if label=='controller' and os.environ.get('FAT_SMOKE')=='1' and c['name']!='mbr_ok':continue
  name=label+'_'+c['name']
  args=[f'+FIXTURE={R/"02_tests/fixtures"/c["name"]}']
  fields={'BLOCKS':'blocks','READS':'requests','ERROR':'error','MOUNT':'mounted','FOUND':'found','OK':'bmp_ok','TOPDOWN':'top_down','CLUSTER':'file_cluster','OFFSET':'offset','SIZE':'size','SDSC':'sdsc','CRC_READ':'crc_read','STALL':'stall','SD_INIT_ERROR':'sd_init_error'}
  args += [f'+{a}={c[b]}' for a,b in fields.items()]
  if label in ('spi','board') and c['name']=='mbr_ok':args+=['+RESTART']
  cmd=[str(B/'vvp.exe'),'-M',str(L),str(executables[label])]+args
  try:
   cp=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=120);text=cp.stdout+cp.stderr;ok=cp.returncode==0 and 'PASS' in text and 'FATAL' not in text
  except subprocess.TimeoutExpired as e:text='TIMEOUT '+str(e);ok=False
  (E/(name+'.log')).write_text(subprocess.list2cmdline(cmd)+'\n'+text,encoding='utf-8');results.append(dict(name=name,passed=ok,log=(E/(name+'.log')).relative_to(R).as_posix()))
  print(('PASS ' if ok else 'FAIL ')+name+' '+text[-300:].strip(),flush=True)
summary=dict(version=R.name,passed=sum(t['passed'] for t in results),total=len(results),tests=results,scope='Synthetic sparse FAT32 sectors only. No physical card, BMP payload stream or display acceptance.',hardware_tested=False,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.rglob('*.v'))})
(E/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');(R/'04_evidence/sim/fat_latest_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
sys.exit(0 if all(t['passed'] for t in results) else 1)
