"""Independent integer TMDS oracle, including actual emitted 10-bit disparity.
The legacy source is compiled separately, never mixed with production modules.
No PHY/monitor simulation. Expected legacy failure is regression evidence only.
"""
from pathlib import Path
import random, subprocess, os, json, hashlib, argparse, datetime
p=argparse.ArgumentParser();p.add_argument('--legacy',action='store_true');a=p.parse_args()
r=Path(__file__).resolve().parents[1];t=r/'02_tests';e=r/'04_evidence'/(('legacy_tmds_' if a.legacy else 'fixed_tmds_')+datetime.datetime.now().strftime('%H%M%S'));e.mkdir(exist_ok=False)
b=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'));env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
seq=[]
def add(d=0,de=1,c=0,rst=1):seq.append((d,de,c,rst))
for c in range(4):add(de=0,c=c)
# All 256 values, both isolated and long constant runs.
for d in range(256):
 add(de=0)
 for k in range(64):add(d)
# Actual RGB332-expanded backgrounds and screen background, plus white-border transitions.
for d in [219,182,255,0,8,24,48]:
 add(de=0)
 for line in range(12):
  for x in range(1280):add(d if 320<=x<960 else 24)
  for x in range(370):add(de=0,c=line%4)
rng=random.Random(66023)
for k in range(16000):add(rng.randrange(256),de=(k%1650<1280),c=rng.randrange(4),rst=(k%4093!=0))
rd=0;vec=[];rdmin=0;rdmax=0
for d,de,c,rst in seq:
 if not rst:q=0b1101010100;rd=0
 elif not de:q=[0b1101010100,0b0010101011,0b0101010100,0b1010101011][c];rd=0
 else:
  n=d.bit_count();xnor=n>4 or (n==4 and not d&1);qm=d&1;last=d&1
  for i in range(1,8):
   last=last^((d>>i)&1)^int(xnor);qm|=last<<i
  m8=int(not xnor);n1=qm.bit_count();balance=2*n1-8
  if rd==0 or balance==0:inv=1-m8
  else:inv=int((rd>0 and balance>0) or (rd<0 and balance<0))
  q=(inv<<9)|(m8<<8)|(qm^(255 if inv else 0))
  rd+=2*q.bit_count()-10
 rdmin=min(rdmin,rd);rdmax=max(rdmax,rd)
 vec.append(d|(c<<8)|(de<<10)|(q<<11)|((rd&63)<<21)|(rst<<27))
(e/'vectors.hex').write_text(''.join(f'{v:08x}\n' for v in vec),encoding='ascii')
src=t/'tmds_encoder_v065_reference.v' if a.legacy else r/'01_project/rtl/video/tmds_encoder.v'
exe=e/'test.vvp';cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-s','tb_v066_tmds','-o',str(exe),str(t/'tb_v066_tmds.sv'),str(src)]
c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30);(e/'compile.log').write_text(c.stdout+c.stderr)
row={'legacy':a.legacy,'vectors':len(vec),'reference_RD':[rdmin,rdmax],'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'compile_rc':c.returncode}
if c.returncode==0:
 v=subprocess.run([str(b/'vvp.exe'),str(exe),'+VECTORS='+(e/'vectors.hex').as_posix(),f'+COUNT={len(vec)}'],env=env,capture_output=True,text=True,timeout=90)
 text=v.stdout+v.stderr;(e/'simulation.log').write_text(text);print(text);row.update(sim_rc=v.returncode,passed=v.returncode==0 and 'PASS' in text)
(e/'summary.json').write_text(json.dumps(row,indent=2)+'\n');raise SystemExit(0 if row.get('passed') or (a.legacy and row.get('sim_rc')==1 and 'TMDS invariant failed' in text and 'ERROR' not in text and 'xxxxxxxx' not in text) else 1)
