from pathlib import Path
import os,subprocess,json,hashlib,datetime,concurrent.futures
root=Path(__file__).resolve().parents[2];test=Path(__file__).resolve().parent;out=root/'04_evidence'/('v122_address_long_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();jobs=[]
for B,L,S,N in [(80,720,2,6000000),(80,1,40,200000)]:jobs.append(('reader',dict(B=B,L=L,S=S,CYCLES=N)))
def run(item):
 kind,par=item;label=kind+'_'+'_'.join(str(v)for v in par.values());top='tb_v122_reader_long'
 src=[test/(top+'.sv'),test/('v119_'+('bmp_pixel_packer'if kind=='packer'else'idx_pair_reader')+'_reference.v'),root/('01_project/rtl/tf/bmp_pixel_packer.v'if kind=='packer'else'01_project/rtl/video/idx_pair_reader.v')]
 cmd=[str(b/'iverilog.exe'),'-g2012','-s',top,*['-P'+top+'.'+k+'='+str(v)for k,v in par.items()],'-o',str(out/(label+'.vvp')),*map(str,src)]
 c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=40);text=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  v=subprocess.run([str(b/'vvp.exe'),str(out/(label+'.vvp'))],env=env,capture_output=True,text=True,timeout=600);text+=v.stdout+v.stderr;rc=v.returncode
 (out/(label+'.log')).write_text(text,encoding='utf8');passed=c.returncode==0 and rc==0 and'PASS v122'in text and'FATAL'not in text
 print(label,passed,text[-380:],flush=True)
 return dict(case=label,parameters=par,passed=passed,compile_rc=c.returncode,sim_rc=rc,source_sha256={p.relative_to(root).as_posix():sha(p)for p in src+[Path(__file__)]})
with concurrent.futures.ThreadPoolExecutor(max_workers=1)as pool:rows=list(pool.map(run,jobs))
record=dict(passed=all(r['passed']for r in rows),complete=len(rows)==len(jobs),cases=rows,scope='Cycle-by-cycle V119 versus V122 reader/packer including all outputs, independent row/address checks, random ready/valid/backpressure/reset, full720p bank wrap plus40-step transition, >=2 completed transitions per case, abstract SDRAM only, no hardware')
(out/'summary.json').write_text(json.dumps(record,indent=2),encoding='utf8');print(out);raise SystemExit(0 if record['passed']else 1)