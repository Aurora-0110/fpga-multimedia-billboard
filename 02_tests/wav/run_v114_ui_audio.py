from pathlib import Path
import os,subprocess,json,struct,datetime,hashlib,random,argparse
ap=argparse.ArgumentParser();ap.add_argument('--only',nargs='*',type=int);a=ap.parse_args()
root=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
out=root/'04_evidence'/('v114_ui_audio_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
rng=random.Random(63129)
def wav(frames):
 pcm=b''.join((v&0xffffff).to_bytes(3,'little')for row in frames for v in row)
 return b'RIFF'+struct.pack('<I',len(pcm)+36)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,2,48000,288000,6,24)+b'data'+struct.pack('<I',len(pcm))+pcm
music=[(rng.randrange(1,1<<23),-rng.randrange(1,1<<23))for _ in range(2501)];ad=[(-rng.randrange(1,1<<23),rng.randrange(1,1<<23))for _ in range(1537)]
for name,rows in [('music',music),('ad',ad)]:(out/(name+'.hex')).write_text(''.join(f'{l&0xffffff:06x}{rr&0xffffff:06x}\n'for l,rr in rows))
# Sparse FAT32: root2->8. First directory sector contains only deleted entries,
# audio files are fragmented and each cluster is exactly one sector.
fat={2:8,8:0xfffffff};sectors={}
root0=bytearray(b'\xe5'+b'\0'*31)*16;sectors[600]=root0
root1=bytearray(512)
def entry(name,cl,size,attr=32):
 q=bytearray(32);q[:11]=name;q[11]=attr;q[20:22]=struct.pack('<H',cl>>16);q[26:28]=struct.pack('<H',cl&65535);q[28:32]=struct.pack('<I',size);return q
for i,(rows,chain,name) in enumerate([(music,[5]+list(range(20,120,3)),b'MUSIC   WAV'),(ad,[12]+list(range(22,120,3)),b'ADVOICE WAV')]):
 data=wav(rows);chain=chain[:(len(data)+511)//512]
 for j,cl in enumerate(chain):
  sectors[600+cl-2]=data[j*512:(j+1)*512].ljust(512,b'\0');fat[cl]=chain[j+1]if j<len(chain)-1 else 0xfffffff
 root1[i*32:(i+1)*32]=entry(name,chain[0],len(data))
sectors[606]=root1
for cl,val in fat.items():
 lba=32+cl//128;q=bytearray(sectors.get(lba,bytes(512)));q[(cl%128)*4:(cl%128)*4+4]=struct.pack('<I',val);sectors[lba]=q
sector_keys=sorted(sectors)
flat=b''.join(sectors[k]for k in sector_keys);(out/'sectors.hex').write_text(''.join(f'{v:02x}\n'for v in flat))
fixture='reg [7:0] disk[0:'+str(len(flat)-1)+'];\ninitial $readmemh("'+(out/'sectors.hex').as_posix()+'",disk);\nfunction [7:0] sector_byte;input [31:0] lba;input integer idx;begin\ncase(lba)\n'
fixture+=''.join(f"32'd{k}:sector_byte=disk[{i*512}+idx];\n"for i,k in enumerate(sector_keys))
fixture+="32'd999999:sector_byte=idx[7:0];default:sector_byte=8'd0;\nendcase\nend endfunction\n";(out/'wav_fixture.vh').write_text(fixture)
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'))
sources=[t/'tb_v114_ui_audio.sv',t/'wav_block_model.sv']+[rtl/x for x in ['tf/media_sd_arbiter.v','tf/fat32_byte_stream.v','tf/fat32_audio_prefetch.v','audio/wav_pcm_decode.v','audio/tf_wav_reader.v','audio/tf_wav_playback.v','audio/audio_choice_cdc.v','mem/async_fifo.v','common/reset_release.v','common/media_controls.v']]
exe=out/'play.vvp';c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(out),'-s','tb_v114_ui_audio','-o',str(exe)]+list(map(str,sources)),capture_output=True,text=True,env=env);(out/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
results=[]
for mode in a.only if a.only else [1]:
 c=subprocess.run([str(b/'vvp.exe'),str(exe),f'+MODE={mode}',f'+MUSIC={(out/"music.hex").as_posix()}',f'+AD={(out/"ad.hex").as_posix()}',f'+NM={len(music)}',f'+NA={len(ad)}'],capture_output=True,text=True,env=env,timeout=100)
 (out/f'mode{mode}.log').write_text(c.stdout+c.stderr);passed=c.returncode==0 and 'PASS' in c.stdout;results.append(dict(mode=mode,passed=passed));print(mode,passed,c.stdout.strip()[-900:],flush=True)
 if not passed:break
rec={'passed':all(x['passed']for x in results),'cases':results,'scope':'Actual UI gesture integration: independent UI toggles while playing/paused, enter/exit audio controls, pause filling and exact ordered resume/source switch; sector transport model; legacy eight cases including midstream/FIFO-full, first sample, switch-while-paused and near-EOF pause; virtual sector transport + shared arbiter + fragmented FAT root/files + PCM decode + asynchronous FIFO + selection; NOT real SPI pins/hardware','sources':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources}}
(out/'summary.json').write_text(json.dumps(rec,indent=2));print(out);raise SystemExit(0 if rec['passed']else 1)
