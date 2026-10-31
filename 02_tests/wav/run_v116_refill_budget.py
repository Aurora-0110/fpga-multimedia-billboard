from pathlib import Path
import os,subprocess,json,struct,datetime,hashlib,argparse
ap=argparse.ArgumentParser();ap.add_argument('--baseline',action='store_true');ap.add_argument('--spc',type=int,default=1);ap.add_argument('--wait',type=int,default=250);ap.add_argument('--bmp',type=int,default=1);ap.add_argument('--under',type=int,default=0);ap.add_argument('--mode',type=int,default=0);a=ap.parse_args()
root=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
out=root/'04_evidence'/('v116_refill_'+('old_'if a.baseline else 'new_')+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));out.mkdir()
nm=24001;rows=[(((i*197+12345)%0x7ffffe)+1,-(((i*163+31415)%0x7ffffe)+1))for i in range(nm)]
pcm=b''.join((v&0xffffff).to_bytes(3,'little')for row in rows for v in row)
data=b'RIFF'+struct.pack('<I',len(pcm)+36)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,2,48000,288000,6,24)+b'data'+struct.pack('<I',len(pcm))+pcm
(out/'music.hex').write_text(''.join(f'{l&0xffffff:06x}{r&0xffffff:06x}\n'for l,r in rows))
fat={2:0xfffffff};sectors={};rootdir=bytearray(512);rootdir[:11]=b'MUSIC   WAV';rootdir[11]=32;rootdir[26:28]=struct.pack('<H',10);rootdir[28:32]=struct.pack('<I',len(data));sectors[600]=rootdir
num=(len(data)+a.spc*512-1)//(a.spc*512);chain=[10+3*i for i in range(num)]
for j,cl in enumerate(chain):
 fat[cl]=chain[j+1]if j+1<len(chain)else 0xfffffff
 for s in range(a.spc):
  start=(j*a.spc+s)*512
  if start<len(data):sectors[600+(cl-2)*a.spc+s]=data[start:start+512].ljust(512,b'\0')
for cl,val in fat.items():
 lba=32+cl//128;q=bytearray(sectors.get(lba,bytes(512)));q[(cl%128)*4:(cl%128)*4+4]=struct.pack('<I',val);sectors[lba]=q
keys=sorted(sectors);flat=b''.join(sectors[k]for k in keys);(out/'sectors.hex').write_text(''.join(f'{v:02x}\n'for v in flat))
fixture='reg[7:0] disk[0:'+str(len(flat)-1)+'];\ninitial $readmemh("'+(out/'sectors.hex').as_posix()+'",disk);\nfunction[7:0]sector_byte;input[31:0]lba;input integer idx;begin case(lba)\n'
fixture+=''.join(f"32'd{k}:sector_byte=disk[{j*512}+idx];\n"for j,k in enumerate(keys));fixture+="default:sector_byte=0;endcase end endfunction\n";(out/'wav_fixture.vh').write_text(fixture)
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),TMPDIR=str(root/'00_tmp'))
sources=[t/'tb_v116_refill_budget.sv',t/'v116_budget_host.sv',(t/'v114_media_sd_arbiter_reference.v'if a.baseline else rtl/'tf/media_sd_arbiter.v')]+[rtl/x for x in ['tf/fat32_audio_prefetch.v','audio/wav_pcm_decode.v','audio/tf_wav_reader.v','audio/tf_wav_playback.v','audio/audio_choice_cdc.v','mem/async_fifo.v','common/reset_release.v']]
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources+[Path(__file__)]}
exe=out/'test.vvp';c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(out),*(['-DBASELINE']if a.baseline else []),'-s','tb_v116_refill_budget','-o',str(exe)]+list(map(str,sources)),capture_output=True,text=True,env=env);(out/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
c=subprocess.run([str(b/'vvp.exe'),str(exe),f'+MUSIC={(out/"music.hex").as_posix()}',f'+NM={nm}',f'+SPC={a.spc}',f'+SHIFT={a.spc.bit_length()-1}',f'+BLOCK_WAIT={a.wait}',f'+BMP={a.bmp}',f'+UNDER={a.under}',f'+MODE={a.mode}'],capture_output=True,text=True,env=env,timeout=240)
(out/'run.log').write_text(c.stdout+c.stderr);print(c.stdout,flush=True)
rec={'pass':c.returncode==0 and 'PASS refill-budget'in c.stdout,'args':vars(a),'scope':'Deterministic service-budget transport model with16x accelerated service/consumer, NOT real card timing nor hardware root-cause proof','source_sha256':hashes,'unchanged':all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in hashes.items())};rec['pass'] &=rec['unchanged'];(out/'summary.json').write_text(json.dumps(rec,indent=2));print(out,flush=True);raise SystemExit(0 if rec['pass']else 1)
