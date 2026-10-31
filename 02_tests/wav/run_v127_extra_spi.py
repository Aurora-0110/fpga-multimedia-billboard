from pathlib import Path
import argparse,time,os,subprocess,sys,json,struct,datetime,hashlib,random
root=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
sys.path.insert(0,str(root/'02_tests/dynamic_bmp'));from run_dynamic_tests import color,interpolate
sys.path.insert(0,str(root/'02_tests/multires'));from multires_reference import indexed
out=root/'04_evidence'/('v127_extra_spi_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
parser=argparse.ArgumentParser();parser.add_argument('--mode',type=int,choices=[0,1,2,3]);parser.add_argument('--sdsc',type=int,choices=[0,1,2,3],default=0);parser.add_argument('--short',action='store_true');parser.add_argument('--production',action='store_true');parser.add_argument('--timeout',type=int,default=600);args=parser.parse_args()
assert not(args.short and args.production),'production mode must use full4096 FIFO'
rng=random.Random(93543)
def wav(rows):
 pcm=b''.join((x&0xffffff).to_bytes(3,'little')for row in rows for x in row)
 return b'RIFF'+struct.pack('<I',len(pcm)+36)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,2,48000,288000,6,24)+b'data'+struct.pack('<I',len(pcm))+pcm
music=[(rng.randrange(1,1<<23),-rng.randrange(1,1<<23))for _ in range(501 if args.short else 1501)];ad=[(-rng.randrange(1,1<<23),rng.randrange(1,1<<23))for _ in range(401 if args.short else 1201)]
legacy_ad=list(ad);ad=[(l//2,r//2)for l,r in ad]
for name,rows in [('music',music),('ad',ad)]:(out/(name+'.hex')).write_text(''.join(f'{l&0xffffff:06x}{r&0xffffff:06x}\n'for l,r in rows))
fat={2:8,8:0xfffffff};sectors={};root0=bytearray(b'\xe5'+b'\0'*31)*16;sectors[600]=root0;root1=bytearray(512)
def entry(name,cl,size):
 q=bytearray(32);q[:11]=name;q[11]=32;q[26:28]=struct.pack('<H',cl);q[28:32]=struct.pack('<I',size);return q
files=[(b'MUSIC   WAV',wav(music),list(range(20,120,3))),(b'ADVOICE WAV',wav(legacy_ad),list(range(22,120,3))),(b'TURAND~1WAV',wav(ad),list(range(21,120,3)))]
for name,width,height,top,first in [('a',13,20,True,100),('b',23,15,False,101)]:
 stride=(width*3+3)&~3;size=54+stride*height
 data=bytearray(struct.pack('<2sIHHI',b'BM',size,0,0,54)+struct.pack('<IiiHHIIiiII',40,width,-height if top else height,1,24,0,stride*height,0,0,0,0))
 for row in range(height):
  for x in range(width):red,g,bl=color(x,row if top else height-1-row);data.extend([bl,g,red])
  data.extend(bytes(stride-width*3))
 files.append((name.upper().encode()+b'       BMP',data,list(range(first,120,3))))
 gold=[0]*576
 for i,p in enumerate(interpolate(width,height,top)):
  row,x=divmod(i,32);y=row if top else 17-row;gold[y*32+x]=indexed(p,x,y)
 (out/f'indexed_{name}.hex').write_text(''.join(f'{x:02x}\n'for x in gold))
for i,(name,data,chain) in enumerate(files):
 chain=chain[:(len(data)+511)//512]
 for j,cl in enumerate(chain):
  sectors[600+cl-2]=data[j*512:(j+1)*512].ljust(512,b'\0');fat[cl]=chain[j+1]if j<len(chain)-1 else 0xfffffff
 root1[i*32:(i+1)*32]=entry(name,chain[0],len(data))
sectors[606]=root1
boot=bytearray(512);boot[0]=0xeb;struct.pack_into('<H',boot,11,512);boot[13]=1;struct.pack_into('<H',boot,14,32);boot[16]=1;struct.pack_into('<I',boot,32,70600);struct.pack_into('<I',boot,36,568);struct.pack_into('<I',boot,44,2);boot[510:512]=b'\x55\xaa';sectors[0]=boot
for cl,val in fat.items():
 lba=32+cl//128;q=bytearray(sectors.get(lba,bytes(512)));q[(cl%128)*4:(cl%128)*4+4]=struct.pack('<I',val);sectors[lba]=q
(out/'lbas.hex').write_text(''.join(f'{k:08x}\n'for k in sorted(sectors)));(out/'data.hex').write_text(''.join(f'{v:02x}\n'for k in sorted(sectors)for v in sectors[k]))
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
sources=[t/'tb_v119_extra_spi.sv',root/'02_tests/multires/sd_fat_card_model_large.v']+[rtl/x for x in ['tf/spi_byte.v','tf/sd_spi_reader.v','tf/media_sd_arbiter.v','tf/media_bmp_probe.v','tf/bmp_pixel_stream.v','tf/bmp_pixel_packer.v','tf/tf_bus_bmp_source.v','tf/tf_bus_bmp_scaled_source.v','tf/tf_bus_scaled_loader.v','scale/bmp_scale_bridge.v','scale/bilinear_stream_scaler.v','scale/bilinear_rgb888.v','tf/fat32_byte_stream.v','tf/fat32_audio_prefetch.v','audio/wav_pcm_decode.v','audio/tf_wav_reader.v','audio/audio_choice_cdc.v','audio/tf_wav_playback.v','mem/async_fifo.v','common/reset_release.v']]
before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[Path(__file__)]}
(out/'source_before_compile.json').write_text(json.dumps(before,indent=2))
exe=out/'spi.vvp';c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(rtl),'-s','tb_wav_actual_spi',*(['-DSHORT_SPI'] if args.short else []),*(['-DPRODUCTION_SPI'] if args.production else []),'-o',str(exe)]+list(map(str,sources)),capture_output=True,text=True,env=env);(out/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
results=[]
cases=[(args.mode,args.sdsc)] if args.mode is not None else [(0,0),(1,0),(1,1),(2,0),(3,1)]
for mode,sdsc in cases:
 log=out/f'mode{mode}_sdsc{sdsc}.log'
 print(f'START mode={mode} sdsc={sdsc} log={log}',flush=True);start=time.monotonic();timed_out=False
 with log.open('w') as f:
  try:
   c=subprocess.run([str(b/'vvp.exe'),'-i','-v',str(exe),f'+FIXTURE={out.as_posix()}',f'+BLOCKS={len(sectors)}',f'+NM={len(music)}',f'+NA={len(ad)}',f'+MODE={mode}',f'+SDSC={sdsc}'],stdout=f,stderr=subprocess.STDOUT,text=True,env=env,timeout=args.timeout)
   rc=c.returncode
  except subprocess.TimeoutExpired:timed_out=True;rc=None
 text=log.read_text();passed=rc==0 and 'PASS actual SPI' in text
 results.append(dict(mode=mode,sdsc=sdsc,passed=passed,timeout=timed_out,elapsed_seconds=round(time.monotonic()-start,2)))
 print(mode,sdsc,passed,text.strip()[-1600:],flush=True)
 if not passed:break
rec={'passed':len(results)==len(cases) and all(x['passed']for x in results),'cases':results,'production_parameters':args.production,'short_fifo_pin_protocol_test':args.short,'scope':'Third-slot SFN-alias WAV has distinct payload from preserved ADVOICE. Actual new single sd_spi_reader pins+behavioral card, both new bus BMP/scaler/packer and WAV/CDC/FIFO,32x18 test raster. Not full720p SDRAM/HDMI integration or electrical hardware.','source_sha256':before,'sources_unchanged_during_run':all(hashlib.sha256((root/k).read_bytes()).hexdigest()==v for k,v in before.items())}
rec['passed']=rec['passed'] and rec['sources_unchanged_during_run']
(out/'summary.json').write_text(json.dumps(rec,indent=2));print(out);raise SystemExit(0 if rec['passed']else 1)
