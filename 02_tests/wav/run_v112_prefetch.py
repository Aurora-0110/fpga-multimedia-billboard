from pathlib import Path
import os,subprocess,json,struct,datetime,hashlib,random
root=Path(__file__).resolve().parents[2];t=Path(__file__).parent;rtl=root/'01_project/rtl'
out=root/'04_evidence'/('v112_prefetch_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
cases=[dict(name=f'file_{spc}_{n}',spc=spc,n=n) for spc in [1,2,8,128] for n in [1,511,512,513,1031,5003]]
cases += [dict(name='directory_early',spc=2,n=1024,directory=True),dict(name='directory_limit',spc=8,n=66048,directory=True,expect=6,maxn=65536),dict(name='premature_eoc',spc=1,n=1700,short=True,expect=7,maxn=512),dict(name='bad_final_eoc',spc=1,n=1031,bad_final=True,expect=8),dict(name='bad_cluster_zero',spc=1,n=1700,bad_zero=True,expect=8,maxn=512),dict(name='address_overflow',spc=128,n=512,base=0xffffff00,expect=4,maxn=0)]
for where in ['data_first','data_second','fat']:
 for kind in [1,2]:cases.append(dict(name=f'{where}_fault{kind}',spc=1,n=1700,bad_where=where,bad_kind=kind,expect=1 if kind==1 else 3,maxn=0 if where=='data_first'else 512))
rows=[];sources=[t/'tb_v112_prefetch.sv',t/'wav_block_stall_model.sv',rtl/'tf/fat32_audio_prefetch.v',Path(__file__)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={str(p.relative_to(root)):sha(p)for p in sources}
for case in cases:
 d=out/case['name'];d.mkdir();n=case['n'];spc=case['spc'];base=case.get('base',600);directory=case.get('directory',False);fs=65536 if directory else n
 rng=random.Random(n*47+spc);data=bytes(rng.randrange(256)for _ in range(n));(d/'gold.hex').write_text(''.join(f'{x:02x}\n'for x in data))
 nblocks=(n+511)//512;nclusters=(nblocks+spc-1)//spc;chain=[127,300,129]+list(range(401,401+max(nclusters-3,0)));chain=chain[:nclusters]
 sectors={};fat={}
 for j,cl in enumerate(chain):
  fat[cl]=chain[j+1]if j+1<len(chain)else 0xfffffff
  for k in range(spc):
   off=(j*spc+k)*512
   if off>=n:break
   sectors[base+(cl-2)*spc+k]=data[off:off+512].ljust(512,b'\0')
 if case.get('short'):fat[chain[0]]=0xfffffff
 if case.get('bad_final'):fat[chain[-1]]=500
 if case.get('bad_zero'):fat[chain[0]]=0
 for cl,val in fat.items():
  lba=32+cl//128;q=bytearray(sectors.get(lba,bytes(512)));q[(cl%128)*4:(cl%128)*4+4]=struct.pack('<I',val);sectors[lba]=q
 keys=sorted(sectors);flat=b''.join(sectors[k]for k in keys)
 (d/'sectors.hex').write_text(''.join(f'{v:02x}\n'for v in flat))
 fixture='reg [7:0] disk[0:'+str(len(flat)-1)+'];\ninitial $readmemh("sectors.hex",disk);\nfunction [7:0] sector_byte;input [31:0] lba;input integer idx;begin\ncase(lba)\n'
 fixture+=''.join(f"32'd{k}:sector_byte=disk[{i*512}+idx];\n"for i,k in enumerate(keys));fixture+="default:sector_byte=0;\nendcase\nend endfunction\n";(d/'wav_fixture.vh').write_text(fixture)
 bad=0xffffffff
 if 'bad_where'in case:bad={'data_first':base+(chain[0]-2)*spc,'data_second':base+(chain[1]-2)*spc,'fat':32+chain[0]//128}[case['bad_where']]
 vals={'GOLDN':n,'FS':fs,'DIR':int(directory),'CL':127,'BASE':base,'SPC':spc,'SHIFT':spc.bit_length()-1,'BADLBA':bad,'BADKIND':case.get('bad_kind',0),'EXPECT':case.get('expect',0),'MAXN':case.get('maxn',n)}
 (d/'prefetch_meta.vh').write_text(''.join(f"localparam [31:0] {k}=32'd{v};\n"for k,v in vals.items()))
 exe=d/'test.vvp';c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(d),'-s','tb_v112_prefetch','-o',str(exe),*map(str,sources[:3])],cwd=d,env=env,capture_output=True,text=True);(d/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
 c=subprocess.run([str(b/'vvp.exe'),str(exe)],cwd=d,env=env,capture_output=True,text=True,timeout=60);(d/'run.log').write_text(c.stdout+c.stderr)
 passed=c.returncode==0 and 'PASS'in c.stdout;rows.append(dict(case=case,passed=passed,result=c.stdout.strip()));print(case['name'],passed,c.stdout.strip(),flush=True)
 if not passed:break
rec=dict(passed=len(rows)==len(cases)and all(x['passed']for x in rows),cases=rows,source_sha256=before,sources_unchanged=all(sha(root/k)==v for k,v in before.items()),scope='Independent sparse FAT32 bytes, 2-bank ownership/backpressure/CRC quarantine, 1/2/8/128 sectors per cluster, tail/EOC/overflow/error matrix; virtual transport only')
rec['passed'] &=rec['sources_unchanged'];(out/'summary.json').write_text(json.dumps(rec,indent=2));print(out);raise SystemExit(0 if rec['passed']else 1)