"""Independent font/text/cue oracle and production sample-event regressions.
Offline transcription correctness is NOT inferred from RTL tests.
"""
from pathlib import Path
import os,json,hashlib,datetime,subprocess,time,concurrent.futures
from PIL import Image,ImageDraw,ImageFont
r=Path(__file__).resolve().parents[2];t=Path(__file__).parent;rtl=r/'01_project/rtl'
out=r/'04_evidence'/('v127_captions_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
specpath=r/'03_docs/v127_caption_spec.json';spec=json.loads(specpath.read_text(encoding='utf8'))
fontpath=r/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf';assert sha(fontpath)==spec['font_sha256']
font=ImageFont.truetype(str(fontpath),10);fontrows=[]
for i in range(1<<spec['glyph_aw']):
 im=Image.new('L',(12,12));ch=spec['glyphs'][i]if i<len(spec['glyphs'])else' '
 if ch!=' ':
  l,top,right,bottom=font.getbbox(ch);assert right-l<=12 and bottom-top<=12
  ImageDraw.Draw(im).text(((12-(right-l))//2-l,(12-(bottom-top))//2-top),ch,font=font,fill=255)
 for y in range(16):fontrows.append(sum(1<<(11-x)for x in range(12)if y<12 and im.getpixel((x,y))>=112))
text=[];cues=[];meta=[]
for cue in spec['cues']:
 start=cue['start_ms']*48;end=cue['end_ms']*48;offset=len(text);length=len(cue['text']);assert start<end and length<=24
 assert not cues or start>=(cues[-1]>>32)&0xffffffff
 cues.append((start<<64)|(end<<32)|(offset<<21)|(length<<16));text.extend(spec['glyph_ids'][ch]for ch in cue['text'])
 meta.extend([start&0x3ffff,end&0x3ffff,(offset<<5)|length,((start>>18)<<6)|(end>>18)])
text +=[0]*(1024-len(text));meta +=[0]*(256-len(meta))
assert fontrows==spec['font_rows'] and text==spec['text_memory'] and meta==spec['metadata']
(out/'font.hex').write_text(''.join(f'{x:03x}\n'for x in fontrows));(out/'text.hex').write_text(''.join(f'{x:02x}\n'for x in text));(out/'cues.hex').write_text(''.join(f'{x:024x}\n'for x in cues));(out/'metadata.hex').write_text(''.join(f'{x:05x}\n'for x in meta))
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'),TMPDIR=str(r/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
jobs=[('player','tb_v127_caption_player',[t/'tb_v127_caption_player.sv',rtl/'visual/pcm_caption_player.v'],[f'+CUES={out}/cues.hex',f'+COUNT={len(cues)}']),
 ('pixels','tb_v127_caption_pixels',[t/'tb_v127_caption_pixels.sv',rtl/'visual/subtitle_overlay.v'],[f'+CUES={out}/cues.hex',f'+COUNT={len(cues)}',f'+FONT={out}/font.hex',f'+TEXT={out}/text.hex',f'+PREVIEW={out}/caption.ppm']),
 ('alignment','tb_v127_caption_alignment',[t/'tb_v127_caption_alignment.sv',rtl/'visual/pcm_caption_player.v',rtl/'visual/audio_pcm_frontend.v',rtl/'audio/i2s_test_tone.v'],[])]
common=[*sorted((rtl/'visual').glob('music_caption*.vh')),rtl/'visual/dft_cos_q10.vh',specpath,fontpath,Path(__file__)]
def run(job):
 name,top,src,plus=job;start=time.monotonic();exe=out/(name+'.vvp');bound={p.relative_to(r).as_posix():sha(p)for p in src+common}
 c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s',top,'-o',str(exe),*map(str,src)],capture_output=True,text=True,env=env,timeout=40);log=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  try:v=subprocess.run([str(b/'vvp.exe'),str(exe),*plus],capture_output=True,text=True,env=env,timeout=400);log+=v.stdout+v.stderr;rc=v.returncode
  except subprocess.TimeoutExpired:log+='\nTIMEOUT\n'
 (out/(name+'.log')).write_text(log,encoding='utf8');unchanged=all(sha(r/k)==v for k,v in bound.items())
 row=dict(name=name,passed=c.returncode==0 and rc==0 and 'PASS v127' in log and 'FATAL'not in log and 'ERROR'not in log and unchanged,compile_rc=c.returncode,sim_rc=rc,elapsed_seconds=round(time.monotonic()-start,3),source_sha256=bound,sources_unchanged=unchanged,results=[l for l in log.splitlines()if l.startswith(('PASS','FATAL','ERROR'))]);print(name,row['passed'],row['results'],flush=True)
 if not row['passed']:print(log[-3000:],flush=True)
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(run,jobs))
summary=dict(passed=all(row['passed']for row in rows),complete=len(rows)==len(jobs),tests=rows,enabled_cues=len(cues),independent_font_text_metadata_oracle=True,transcription_human_verified=False,complete_lyrics=False,scope='Real sample counter/pause/mute/source reset plus accelerated injected cue endpoints, full720p independent pixels/4cycle controls and 2stage gain alignment. NOT transcript accuracy, HDMI sink latency or hardware acceptance.')
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
for p in out.glob('*.ppm'):
 try:Image.open(p).save(p.with_suffix('.png'))
 except Exception as ex:print('Preview error',ex)
print(out,flush=True);raise SystemExit(0 if summary['passed']else 1)
