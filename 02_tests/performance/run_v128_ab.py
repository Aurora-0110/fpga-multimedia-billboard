from pathlib import Path
import os,subprocess,json,hashlib,datetime,concurrent.futures
root=Path(__file__).resolve().parents[2];test=Path(__file__).resolve().parent;out=root/'04_evidence'/('v128_address_ab_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();jobs=[]
for w,h in [(16,1),(32,3),(48,7),(640,480),(1280,720)]:
 for down in (0,1):jobs.append(('packer',dict(W=w,H=h,DOWN=down,DITHER=1,FAULT=0)))
for f in (1,2,3,4):jobs.append(('packer',dict(W=32,H=3,DOWN=f%2,DITHER=f%2,FAULT=f)))
for B,L,S,N in [(1,1,1,100000),(4,3,2,100000),(40,480,40,120000),(80,720,40,1200000)]:jobs.append(('reader',dict(B=B,L=L,S=S,CYCLES=N)))
def run(item):
 kind,par=item;label=kind+'_'+'_'.join(str(v)for v in par.values());top='tb_v122_'+kind
 src=[test/(top+'.sv'),test/('v119_'+('bmp_pixel_packer'if kind=='packer'else'idx_pair_reader')+'_reference.v'),root/('01_project/rtl/tf/bmp_pixel_packer.v'if kind=='packer'else'01_project/rtl/video/idx_pair_reader.v')]
 cmd=[str(b/'iverilog.exe'),'-g2012','-s',top,*['-P'+top+'.'+k+'='+str(v)for k,v in par.items()],'-o',str(out/(label+'.vvp')),*map(str,src)]
 c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=40);text=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  v=subprocess.run([str(b/'vvp.exe'),str(out/(label+'.vvp'))],env=env,capture_output=True,text=True,timeout=400);text+=v.stdout+v.stderr;rc=v.returncode
 (out/(label+'.log')).write_text(text,encoding='utf8');passed=c.returncode==0 and rc==0 and'PASS v122'in text and'FATAL'not in text
 print(label,passed,text[-380:],flush=True)
 return dict(case=label,parameters=par,passed=passed,compile_rc=c.returncode,sim_rc=rc,source_sha256={p.relative_to(root).as_posix():sha(p)for p in src+[Path(__file__)]})
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:rows=list(pool.map(run,jobs))
record=dict(passed=all(r['passed']for r in rows),complete=len(rows)==len(jobs),cases=rows,scope='Cycle-by-cycle V119 versus V122 reader/packer including all outputs, independent row/address checks, random ready/valid/backpressure/reset, top-down/bottom-up full720p and faults; abstract SDRAM only, no hardware')
(out/'summary.json').write_text(json.dumps(record,indent=2),encoding='utf8');print(out);raise SystemExit(0 if record['passed']else 1)