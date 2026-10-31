from pathlib import Path
import subprocess,os,struct,json,hashlib,datetime,random
root=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
out=root/'04_evidence'/('v112_wav_decode_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'))
exe=out/'decode.vvp'
c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-s','tb_wav_decode','-o',str(exe),str(t/'tb_wav_decode.sv'),str(rtl/'audio/wav_pcm_decode.v')],capture_output=True,text=True,env=env);(out/'compile.log').write_text(c.stdout+c.stderr)
assert c.returncode==0,c.stderr
rng=random.Random(4329);results=[]
def chunk(name,p):return name+struct.pack('<I',len(p))+p+(b'\0' if len(p)&1 else b'')
def wav(bits=24,ch=2,n=521,junk=False):
 frames=[[-(1<<(bits-1)),(1<<(bits-1))-1],[-1,0],[0,-1],[1,1]]
 frames += [[rng.randrange(-(1<<(bits-1)),1<<(bits-1)) for _ in range(2)] for _ in range(n-4)]
 if ch==1:frames=[[x[0],x[0]] for x in frames]
 pcm=b''.join((v&((1<<bits)-1)).to_bytes(bits//8,'little') for row in frames for v in row[:ch])
 fmt=struct.pack('<HHIIHH',1,ch,48000,48000*ch*bits//8,ch*bits//8,bits)
 if junk:fmt+=b'Z'
 body=b'WAVE'+(chunk(b'JUNK',b'12345') if junk else b'')+chunk(b'fmt ',fmt)+(chunk(b'LIST',b'abc') if junk else b'')+chunk(b'data',pcm)
 return b'RIFF'+struct.pack('<I',len(body))+body,[tuple((v<<(24-bits))&0xffffff for v in row)for row in frames]
cases=[]
for bits in [16,24]:
 for ch in [1,2]:
  for junk in [False,True]:
   d,e=wav(bits,ch,junk=junk);cases.append((f'pcm{bits}_{ch}ch_chunks{int(junk)}',d,e,False))
d,e=wav()
for name,off,val in [('not_riff',0,b'RIFX'),('compressed',20,struct.pack('<H',3)),('rate44100',24,struct.pack('<I',44100)),('bad_byterate',28,struct.pack('<I',12)),('align',32,struct.pack('<H',2)),('bits8',34,struct.pack('<H',8)),('channels3',22,struct.pack('<H',3)),('riff_bound',4,struct.pack('<I',len(d)+100)),('chunk_bound',40,struct.pack('<I',len(d)+12))]:
 q=bytearray(d);q[off:off+len(val)]=val;cases.append((name,bytes(q),[],True))
# malformed non-frame data length, even bytes so container valid; decoder must reject
q=bytearray(d[:-2]);q[4:8]=struct.pack('<I',len(q)-8);q[40:44]=struct.pack('<I',len(q)-44);cases.append(('incomplete_frame',bytes(q),[],True))
# The exact two prepared user files: inspect REAL headers, hash, compare first1024 frames with wave module.
import wave
media=[]
for path in [Path(r'D:\FPGA_Billboard\media\music_natianxiayule_20261026\02_audio\MUSIC.WAV'),Path(r'D:\FPGA_Billboard\media\ad_audio_BV15N4y1Z7hi_20261026\02_audio\ADVOICE.WAV')]:
 with wave.open(str(path),'rb') as w:
  media.append(dict(path=str(path),channels=w.getnchannels(),bits=w.getsampwidth()*8,rate=w.getframerate(),frames=w.getnframes(),seconds=w.getnframes()/w.getframerate(),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
  raw=w.readframes(1024)
  fmt=struct.pack('<HHIIHH',1,2,48000,288000,6,24)
  body=b'WAVE'+chunk(b'fmt ',fmt)+chunk(b'data',raw)
  e=[tuple(int.from_bytes(raw[i+j:i+j+3],'little') for j in (0,3)) for i in range(0,len(raw),6)]
  cases.append((path.stem+'_real_first1024',b'RIFF'+struct.pack('<I',len(body))+body,e,False))
for name,d,e,fail in cases:
 p=out/(name+'.hex');p.write_text(''.join(f'{v:02x}\n'for v in d));q=out/(name+'_pcm.hex');q.write_text(''.join(f'{l:06x}{r:06x}\n'for l,r in e))
 c=subprocess.run([str(b/'vvp.exe'),str(exe),f'+BYTES={p.as_posix()}',f'+PCM={q.as_posix()}',f'+NB={len(d)}',f'+NP={len(e)}',f'+ERR={int(fail)}'],capture_output=True,text=True,env=env,timeout=30)
 (out/(name+'.log')).write_text(c.stdout+c.stderr);passed=c.returncode==0 and 'PASS wav' in c.stdout;results.append(dict(name=name,passed=passed,expected_rejection=fail,frames=len(e)))
 print(name,passed,c.stdout.strip()[:150],flush=True)
 if not passed:break
rec={'passed':len(results)==len(cases) and all(x['passed']for x in results),'cases':results,'real_media':media,'sources':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [t/'tb_wav_decode.sv',rtl/'audio/wav_pcm_decode.v']}}
(out/'summary.json').write_text(json.dumps(rec,indent=2));print(out);raise SystemExit(0 if rec['passed']else 1)
