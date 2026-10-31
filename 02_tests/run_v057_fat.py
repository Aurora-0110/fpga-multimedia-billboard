from pathlib import Path
import subprocess,os,json,datetime,hashlib
r=Path(__file__).resolve().parents[1];t=r/'02_tests';legacy=t/'legacy_tf';b=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'))
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');o=t/'build'/('fat_v057_'+stamp);o.mkdir(parents=True);e=r/'04_evidence'/('sim_fat_'+stamp);e.mkdir()
rtl=r/'01_project/rtl/tf/fat32_bmp_probe.v';tb=legacy/'tb_fat32_bmp_probe.v';exe=o/'fat.vvp'
cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(legacy),'-s','tb_fat32_bmp_probe','-o',str(exe),str(tb),str(rtl)]
c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=90);(e/'compile.log').write_text(c.stdout+c.stderr,encoding='utf-8');assert c.returncode==0,c.stderr
cases=json.loads((legacy/'fixtures/cases.json').read_text(encoding='utf-8'));rows=[]
fields={'BLOCKS':'blocks','READS':'requests','ERROR':'error','MOUNT':'mounted','FOUND':'found','OK':'bmp_ok','TOPDOWN':'top_down','CLUSTER':'file_cluster','OFFSET':'offset','SIZE':'size','SDSC':'sdsc','CRC_READ':'crc_read','STALL':'stall','SD_INIT_ERROR':'sd_init_error'}
for x in cases:
 cmd=[str(b/'vvp.exe'),str(exe),'+FIXTURE='+str((legacy/'fixtures'/x['name']).as_posix()),*[f'+{k}={x[v]}' for k,v in fields.items()]]
 cp=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30);text=cp.stdout+cp.stderr;ok=cp.returncode==0 and 'PASS' in text and 'FATAL' not in text
 (e/(x['name']+'.log')).write_text(subprocess.list2cmdline(cmd)+'\n'+text,encoding='utf-8');rows.append(dict(name=x['name'],passed=ok));print(x['name'],ok,flush=True)
 if not ok:break
result=dict(scope='v057 pipelined BPB geometry and legacy FAT/BMP/CRC negative cases; digital only',passed=all(x['passed'] for x in rows),complete=len(rows)==len(cases),cases=rows,source_sha256={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [rtl,tb,legacy/'fixture_setup.vh']})
(e/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');raise SystemExit(not(result['passed'] and result['complete']))
