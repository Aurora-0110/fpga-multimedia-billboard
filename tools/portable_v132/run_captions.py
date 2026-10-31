# Portable harness copy; production RTL and original harness remain untouched.
"""Independent two-track public-text/font oracle and production caption regressions."""
from pathlib import Path
import os,json,hashlib,datetime,subprocess,time,concurrent.futures,re
from PIL import Image,ImageDraw,ImageFont
r=Path(__file__).resolve().parents[2];assert '01_versions'not in r.parts
t=r/'02_tests/captions';rtl=r/'01_project/rtl';out=r/'04_evidence'/('v130_captions_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
specpath=r/'03_docs/v130_caption_spec.json';spec=json.loads(specpath.read_text(encoding='utf-8'))
fontpath=r/spec['font_path'];assert sha(fontpath)==spec['font_sha256'];font=ImageFont.truetype(str(fontpath),11);fontrows=[]
for i in range(320):
 im=Image.new('L',(12,12));ch=spec['glyphs'][i]if i<len(spec['glyphs'])else' '
 if ch!=' ':
  l,top,right,bottom=font.getbbox(ch);assert right-l<=12 and bottom-top<=12
  ImageDraw.Draw(im).text(((12-(right-l))//2-l,(12-(bottom-top))//2-top),ch,font=font,fill=255)
 for y in range(16):fontrows.append(sum(1<<(11-x)for x in range(12)if y<12 and im.getpixel((x,y))>=112))
text=[];cues=[];meta=[0]*512
for track in spec['tracks']:
 tc=[c for c in spec['cues']if c['track_choice']==track['choice']];assert len(tc)==track['cue_count']
 for i,c in enumerate(tc):
  start=c['start_ms']*48;end=c['end_ms']*48;offset=len(text);length=len(c['text']);assert start<end and length<=24
  if i:assert start>=tc[i-1]['end_ms']*48
  cues.append((start<<64)|(end<<32)|(offset<<21)|(length<<16));text.extend(spec['glyph_ids'][ch]for ch in c['text'])
  addr=((track['choice']==3)*64+i)*4
  meta[addr:addr+4]=[start&0x3ffff,end&0x3ffff,(offset<<5)|length,((start>>18)<<6)|(end>>18)]
 assert all(v==0 for v in meta[track['metadata_slot_base']*4+len(tc)*4:(track['metadata_slot_base']+64)*4])
text.extend([0]*(1024-len(text)));assert fontrows==spec['font_rows']and text==spec['text_memory']and meta==spec['metadata']
packed=[]
for gid in range(320):
 payload=sum(fontrows[gid*16+y]<<(12*y)for y in range(12));packed.extend((payload>>(18*k))&0x3ffff for k in range(8))
assert packed==spec['font_packed_words']
raw=(rtl/'visual/music_caption_font_init.vh').read_text(encoding='utf-8')
for mem,words in [('font_memory_lo',packed[:2048]),('font_memory_hi',packed[2048:])]:
 actual={int(i):int(v,16)for i,v in re.findall(mem+r"\[(\d+)\]=18'h([0-9a-fA-F]+);",raw)};assert [actual[i]for i in range(len(words))]==words
userpaths=[]
for choice,folder,file in [(1,'public_captions','music.txt'),(3,'public_captions','extra.txt')]:
 p=r/'06_test_media'/folder/file;userpaths.append(p)
 for line,original in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
  joined=''.join(q['text']for q in spec['cues']if q['track_choice']==choice and q['source_line']==line)
  assert re.sub(r'\s','',joined)==re.sub(r'\s','',original),(choice,line,joined,original)
# Independently verify both ROM banks against the self-authored source timeline.
source=json.loads((r/'06_test_media/public_captions/captions.json').read_text('utf-8'))
for track in source['tracks']:
 actual=[c for c in spec['cues']if c['track_choice']==track['choice']]
 assert len(actual)==len(track['cues'])
 for old,new in zip(track['cues'],actual):
  for key in ['text','start_ms','end_ms']:assert old[key]==new[key]
for name,values,digits in [('font',fontrows,3),('font_packed',packed,5),('text',text,3),('cues',cues,24),('metadata',meta,5)]:
 (out/(name+'.hex')).write_text(''.join(f'{v:0{digits}x}\n'for v in values),encoding='ascii')
b=Path(os.environ['FPGA_IVERILOG_BIN']);env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'),TMPDIR=str(r/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
jobs=[('player','tb_v130_caption_player',[t/'tb_v130_caption_player.sv',rtl/'visual/pcm_caption_player.v'],[f'+CUES={out}/cues.hex',f'+COUNT={len(cues)}','+MUSIC_COUNT=53','+THIRD_COUNT=16']),('pixels','tb_v130_caption_pixels',[t/'tb_v130_caption_pixels.sv',rtl/'visual/subtitle_overlay.v'],[f'+CUES={out}/cues.hex',f'+COUNT={len(cues)}',f'+FONT={out}/font.hex',f'+TEXT={out}/text.hex',f'+PREVIEW={out}/caption.ppm']),('alignment','tb_v130_caption_alignment',[t/'tb_v130_caption_alignment.sv',rtl/'visual/pcm_caption_player.v',rtl/'visual/audio_pcm_frontend.v',rtl/'audio/i2s_test_tone.v'],[])]
common=[*sorted((rtl/'visual').glob('music_caption*.vh')),rtl/'visual/dft_cos_q10.vh',specpath,fontpath,Path(__file__),*userpaths]
def run(job):
 name,top,src,plus=job;start=time.monotonic();exe=out/(name+'.vvp');bound={p.relative_to(r).as_posix():sha(p)for p in src+common}
 c=subprocess.run([str(b/('iverilog.exe' if os.name=='nt' else 'iverilog')),'-g2012','-Wall','-I',str(rtl),'-s',top,'-o',str(exe),*map(str,src)],capture_output=True,text=True,env=env,timeout=40);log=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  try:v=subprocess.run([str(b/('vvp.exe' if os.name=='nt' else 'vvp')),str(exe),*plus],capture_output=True,text=True,env=env,timeout=400);log+=v.stdout+v.stderr;rc=v.returncode
  except subprocess.TimeoutExpired:log+='\nTIMEOUT\n'
 (out/(name+'.log')).write_text(log,encoding='utf-8');unchanged=all(sha(r/k)==v for k,v in bound.items())
 row=dict(name=name,passed=c.returncode==0 and rc==0 and 'PASS v130'in log and 'FATAL'not in log and 'ERROR'not in log and unchanged,compile_rc=c.returncode,sim_rc=rc,elapsed_seconds=round(time.monotonic()-start,3),source_sha256=bound,sources_unchanged=unchanged,results=[l for l in log.splitlines()if l.startswith(('PASS','FATAL','ERROR'))]);print(name,row['passed'],row['results'],flush=True)
 if not row['passed']:print(log[-3000:],flush=True)
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(run,jobs))
summary=dict(passed=all(row['passed']for row in rows),complete=len(rows)==len(jobs),tests=rows,enabled_cues=len(cues),tracks=[1,3],glyphs=len(spec['glyphs']),independent_font_text_metadata_oracle=True,public_source_timeline_verified=True,full_public_test_text_covered=True,original_lyrics_included=False,lossless_packed_glyphs_checked=True,scope='Public test text, both banks real sample counters/pauses/mute/restart/AD clearing and accelerated cue endpoints. Independent720p glyph pixels with4cycle latency, full bank1 characters. Not audio listening or hardware acceptance.')
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
for p in out.glob('*.ppm'):
 try:Image.open(p).save(p.with_suffix('.png'))
 except Exception as ex:print('Preview error',ex)
print(out,flush=True);raise SystemExit(0 if summary['passed']else 1)
