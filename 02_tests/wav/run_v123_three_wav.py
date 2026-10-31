"""v119 additional WAV discovery through FAT32 SFN aliases; no hardware/card IO."""
from pathlib import Path
import argparse,concurrent.futures,datetime,hashlib,json,os,random,struct,subprocess
parser=argparse.ArgumentParser();parser.add_argument('--only',type=int,nargs='*');args=parser.parse_args()
root=Path(__file__).resolve().parents[2];t=Path(__file__).parent;rtl=root/'01_project/rtl'
out=root/'04_evidence'/('v123_three_wav_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
bin=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
env=dict(os.environ);env.update(PATH=str(bin)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),TMPDIR=str(root/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rng=random.Random(1192026)
tracks={name:[(rng.randrange(1,1<<23),-rng.randrange(1,1<<23)) for _ in range(n)] for name,n in [('music',2501),('ad',1537),('extra',6001)]}
for name,rows in tracks.items():(out/(name+'.hex')).write_text(''.join(f'{l&0xffffff:06x}{r&0xffffff:06x}\n'for l,r in rows))
def wav(rows,bad=False):
 data=b''.join((v&0xffffff).to_bytes(3,'little')for row in rows for v in row)
 return b'RIFF'+struct.pack('<I',len(data)+36)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,3 if bad else 1,2,48000,288000,6,24)+b'data'+struct.pack('<I',len(data))+data

def entry(name,cl,size,attr=32):
 assert len(name)==11
 q=bytearray(32);q[:11]=name;q[11]=attr;q[20:22]=struct.pack('<H',cl>>16);q[26:28]=struct.pack('<H',cl&65535);q[28:32]=struct.pack('<I',size);return q

def lfn_entries(name,alias):
 # Real two-entry VFAT name, followed by the authoritative standard 8.3 alias.
 checksum=0
 for c in alias:checksum=(((checksum&1)<<7)+(checksum>>1)+c)&255
 units=list(struct.unpack('<'+'H'*len(name),name.encode('utf-16le')))+[0]
 units += [0xffff]*((-len(units))%13)
 result=[]
 for order in range(len(units)//13,0,-1):
  q=bytearray(32);q[0]=order|(0x40 if order==len(units)//13 else 0);q[11]=15;q[13]=checksum
  for at,value in zip([1,3,5,7,9,14,16,18,20,22,24,28,30],units[(order-1)*13:order*13]):struct.pack_into('<H',q,at,value)
  result.append(q)
 return result

sources=[t/'tb_v119_three_wav.sv',t/'wav_block_model.sv']+[rtl/x for x in ['tf/media_sd_arbiter.v','tf/fat32_byte_stream.v','tf/fat32_audio_prefetch.v','audio/wav_pcm_decode.v','audio/tf_wav_reader.v','audio/tf_wav_playback.v','audio/audio_choice_cdc.v','mem/async_fifo.v','common/reset_release.v']]
source_sha={p.relative_to(root).as_posix():sha(p)for p in sources}

def fixture(mode,d):
 fat={2:8,8:14,14:0xfffffff};sectors={600:(b'\xe5'+b'\0'*31)*16}
 blobs={}
 for i,(name,rows) in enumerate(tracks.items()):
  blob=wav(rows,bad=mode==3 and name=='extra');blobs[name]=blob
  chain=[100+i+j*3 for j in range((len(blob)+511)//512)]
  for j,cl in enumerate(chain):sectors[600+cl-2]=blob[j*512:(j+1)*512].ljust(512,b'\0');fat[cl]=chain[j+1]if j+1<len(chain)else 0xfffffff
 alias=b'MUSIC2  WAV'if mode==1 else b'TURAND~1WAV'
 rows=[entry(b'MUSIC   WAV',100,len(blobs['music'])),entry(b'ADVOICE WAV',101,len(blobs['ad'])),
       entry(b'NOTWAVE TXT',9999,64),entry(b'FOLDER  WAV',9998,0,16),entry(b'VOLUME  WAV',9997,0,8),
       entry(b'\xe5ELETED WAV',9996,128),entry(b'WRONG   WAX',9995,128),entry(b'MUSIC   MP3',9994,128)]
 if mode not in (2,10):rows+=lfn_entries('TURANDETUOLUO.WAV',alias)+[entry(alias,102,len(blobs['extra']))]
 if mode==9:rows += [entry(b'OTHER   WAV',101,len(blobs['ad']))] # Choose first extra, not last.
 if mode==6:
  root8=bytearray((b'\xe5'+b'\0'*31)*16)
  for i,q in enumerate(rows[:8]):root8[32*i:32*(i+1)]=q
  sectors[606]=root8
  final=bytearray(512)
  for i,q in enumerate(rows[8:]):final[32*i:32*(i+1)]=q
  sectors[612]=final
 else:
  final=bytearray(512)
  for i,q in enumerate(rows):final[32*i:32*(i+1)]=q
  sectors[606]=final;sectors[612]=bytes(512)
 for cl,value in fat.items():
  lba=32+cl//128;q=bytearray(sectors.get(lba,bytes(512)));struct.pack_into('<I',q,(cl%128)*4,value);sectors[lba]=q
 keys=sorted(sectors);flat=b''.join(sectors[k]for k in keys)
 (d/'sectors.hex').write_text(''.join(f'{v:02x}\n'for v in flat))
 code=f'reg [7:0] disk[0:{len(flat)-1}];\ninitial $readmemh("{(d/"sectors.hex").as_posix()}",disk);\nfunction [7:0] sector_byte;input [31:0] lba;input integer idx;begin\ncase(lba)\n'
 code+=''.join(f"32'd{k}:sector_byte=disk[{i*512}+idx];\n"for i,k in enumerate(keys))
 code+="32'd999999:sector_byte=idx[7:0];default:sector_byte=8'd0;\nendcase\nend endfunction\n"
 (d/'wav_fixture.vh').write_text(code)
 (d/'fixture_description.json').write_text(json.dumps(dict(mode=mode,root_chain=[2,8,14],alias=alias.decode(),long_name='TURANDETUOLUO.WAV',missing_extra=mode in (2,10),invalid_format=mode==3,extra_directory_entry_after_root_FAT_boundary=mode==6,extra_frames=len(tracks['extra'])),indent=2))

labels=['long_filename_alias','short_filename','missing_third_no_fallback','bad_third_format_no_fallback','canonical_music_unchanged','canonical_ad_unchanged','root_directory_FAT_boundary','pause_full4096_then_extra_music_extra','rapid_three_zero_two_three','first_extra_directory_order','missing_third_then_music_recovery']
def run(mode):
 d=out/f'case{mode}';d.mkdir();fixture(mode,d);exe=d/'sim.vvp'
 c=subprocess.run([str(bin/'iverilog.exe'),'-g2012','-Wall','-I',str(d),'-s','tb_v119_three_wav','-o',str(exe),*map(str,sources)],env=env,capture_output=True,text=True,timeout=60)
 log=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  try:
   plus=[f'+MODE={mode}']
   for name,arg in [('music','MUSIC'),('ad','AD'),('extra','EXTRA')]:plus += [f'+{arg}={(out/(name+".hex")).as_posix()}']
   plus += [f'+NM={len(tracks["music"])}',f'+NA={len(tracks["ad"])}',f'+NX={len(tracks["extra"])}']
   v=subprocess.run([str(bin/'vvp.exe'),str(exe),*plus],env=env,capture_output=True,text=True,timeout=180);log+=v.stdout+v.stderr;rc=v.returncode
  except subprocess.TimeoutExpired:log+='\nTIMEOUT\n'
 (d/'run.log').write_text(log,encoding='utf8')
 passed=c.returncode==0 and rc==0 and 'PASS v119' in log and 'FATAL' not in log and 'ERROR:' not in log
 rec=dict(mode=mode,label=labels[mode],passed=passed,compile_rc=c.returncode,sim_rc=rc,results=[x for x in log.splitlines()if x.startswith(('PASS','FATAL'))])
 print(json.dumps(rec,ensure_ascii=False),flush=True)
 if not passed:print(log[-2500:],flush=True)
 return rec
modes=args.only if args.only is not None else list(range(len(labels)))
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:records=list(pool.map(run,modes))
unchanged=all(sha(root/p)==h for p,h in source_sha.items())
summary=dict(passed=all(x['passed']for x in records)and unchanged,complete=modes==list(range(len(labels))),cases=records,source_sha256=source_sha,sources_unchanged_during_run=unchanged,scope='4096-frame production FIFO, exact PCM sequence/epoch, shared v116 arbiter and fragmented FAT32 sectors. Virtual transport, not SPI pins/actual card timing or hardware acceptance. Extra WAV selected through SFN alias; no long-name UI decoding.')
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');print(out,flush=True)
raise SystemExit(0 if summary['passed']else 1)
