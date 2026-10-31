from pathlib import Path
import os,sys,struct,time,json,hashlib,subprocess,datetime
root=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent
out=root/'04_evidence'/('v111_mount_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
rtl=root/'01_project/rtl/tf/media_bmp_probe.v';sources=[t/'tb_media_mount.sv',rtl,Path(__file__)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p.relative_to(root)):sha(p)for p in sources}
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
exe=out/'mount.vvp';c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-s','tb_media_mount','-o',str(exe),str(sources[0]),str(rtl)],capture_output=True,text=True,env=env);(out/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
cases=[dict(name='superfloppy')]+[dict(name=f'mbr_slot{x}',slot=x)for x in range(4)]
cases += [dict(name='mbr_first_match',slot=0,second=True),dict(name='mbr_first_bad_size',slot=0,second=True,empty=True,error=2),dict(name='mbr_no_fat32',slot=0,no_type=True,error=2),dict(name='mbr_zero_start',slot=0,zero=True,error=2),dict(name='mbr_wrap',slot=0,wrap=True,error=2),dict(name='mbr_small_partition',slot=0,small=True,error=4),dict(name='bad_signature',bad_sig=True,error=2),dict(name='bad_bps',bad_bps=True,error=2),dict(name='active_second_fat',active=True),dict(name='bad_active_fat',bad_active=True,error=3),dict(name='fragmented_root',fragment=True)]
for kind in ['boot','root','bmp']:
 for fault in [1,2]:cases.append(dict(name=f'{kind}_fault{fault}',fault=fault,where=kind,error=14))
rows=[]
for case in cases:
 d=out/case['name'];d.mkdir();part=2048 if 'slot'in case else 0
 boot=bytearray(512);boot[0]=0xeb;struct.pack_into('<H',boot,11,1024 if case.get('bad_bps')else 512);boot[13]=1;struct.pack_into('<H',boot,14,32);boot[16]=2;struct.pack_into('<I',boot,32,1056+65525);struct.pack_into('<I',boot,36,512);struct.pack_into('<H',boot,40,0x81 if case.get('active')else 0x82 if case.get('bad_active')else 0);struct.pack_into('<I',boot,44,2);boot[510:512]=b'\x55\xaa'if not case.get('bad_sig')else b'\0\0'
 rootsector=bytearray(512);rootsector[:11]=b'A       BMP';rootsector[11]=32;struct.pack_into('<H',rootsector,26,3);struct.pack_into('<I',rootsector,28,921654)
 bmp=bytearray(512);struct.pack_into('<2sIHHI',bmp,0,b'BM',921654,0,0,54);struct.pack_into('<IiiHHIIiiII',bmp,14,40,640,480,1,24,0,921600,0,0,0,0)
 sectors={part:boot,part+1056:rootsector,part+1057:bmp}
 if part:
  mbr=bytearray(512);mbr[510:512]=b'\x55\xaa';n=446+case['slot']*16;mbr[n+4]=0x83 if case.get('no_type')else 0x0c
  struct.pack_into('<I',mbr,n+8,0 if case.get('zero')else 0xfffffff0 if case.get('wrap')else part)
  struct.pack_into('<I',mbr,n+12,0 if case.get('empty')else 100 if case.get('small')else 100000)
  if case.get('second'):
   mbr[n+20]=0x0b;struct.pack_into('<II',mbr,n+24,4096,100000)
  sectors[0]=mbr
 if case.get('fragment'):
  sectors[part+1056]=bytearray(b'\xe5'+bytes(31))*16;sectors[part+1059]=rootsector
  fat=bytearray(512);struct.pack_into('<I',fat,8,5);sectors[part+32]=fat
 (d/'lbas.hex').write_text(''.join(f'{l:08x}\n'for l in sorted(sectors)));(d/'data.hex').write_text(''.join(f'{v:02x}\n'for l in sorted(sectors)for v in sectors[l]))
 fault_lba=part if case.get('where')=='boot'else part+1056 if case.get('where')=='root'else part+1057
 args=[f'+FIXTURE={d.as_posix()}',f'+BLOCKS={len(sectors)}',f'+ERROR={case.get("error",0)}',f'+BASE={part+1056}',f'+FAT={part+(544 if case.get("active")else 32)}',f'+FAULT={case.get("fault",0)}',f'+FAULT_LBA={fault_lba}']
 c=subprocess.run([str(b/'vvp.exe'),str(exe),*args],capture_output=True,text=True,env=env,timeout=25);text=c.stdout+c.stderr;(d/'run.log').write_text(text)
 row=dict(case,passed=c.returncode==0 and 'PASS mount' in text,result=text.strip());rows.append(row);print(case['name'],row['passed'],text.strip(),flush=True)
 if not row['passed']:break
rec=dict(passed=len(rows)==len(cases)and all(r['passed']for r in rows),cases=rows,source_sha256=before,sources_unchanged_during_run=all(sha(root/k)==v for k,v in before.items()))
rec['passed']=rec['passed']and rec['sources_unchanged_during_run'];(out/'summary.json').write_text(json.dumps(rec,indent=2));print(out);raise SystemExit(0 if rec['passed']else 1)
