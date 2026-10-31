"""Generate V128 exact-user-text caption ROMs; lossless144bit glyph packing."""
from pathlib import Path
import json,hashlib,math,wave,re
from PIL import Image,ImageDraw,ImageFont
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=r/'06_test_media/captions_music_user';p=src/'MUSIC_完整时间轴.json';a=json.loads(p.read_text(encoding='utf-8'));cues=a['rows']
source=json.loads((src/'SOURCE.json').read_text(encoding='utf-8'));wav=Path(source['audio_path']);assert sha(wav)==a['source_sha256']
assert sha(src/'MUSIC_用户提供完整歌词.txt')==a['source_text_sha256']
with wave.open(str(wav))as w:assert w.getparams()[:3]==(2,3,48000);sample_frames=w.getnframes()
assert a['full_user_text_covered']and 1<=len(cues)<=64
for i,c in enumerate(cues):
 assert 0<c['start_ms']<c['end_ms'] and c['end_ms']*48<=sample_frames and len(c['text'])<=24
 if i:assert c['start_ms']>=cues[i-1]['end_ms']
glyphs=list(dict.fromkeys(' '+''.join(c['text']for c in cues)));assert len(glyphs)<=256;ids={c:i for i,c in enumerate(glyphs)}
f=r/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf';assert sha(f)=='ca094f6b0001fb048ca39ddd797a0cdb0179e1e55c6561e111c49c3e6a61d7b7'
font=ImageFont.truetype(str(f),10);logical=[];packed=[]
for i in range(256):
 im=Image.new('L',(12,12));d=ImageDraw.Draw(im)
 if i<len(glyphs)and glyphs[i]!=' ':
  ch=glyphs[i];l,t,rr,bb=font.getbbox(ch);assert rr-l<=12 and bb-t<=12
  d.text(((12-rr+l)//2-l,(12-bb+t)//2-t),ch,font=font,fill=255)
 rows=[sum(1<<(11-x)for x in range(12)if im.getpixel((x,y))>=112)for y in range(12)]
 logical.extend(rows+[0]*4)
 payload=sum(v<<(12*y)for y,v in enumerate(rows));packed.extend((payload>>(18*k))&0x3ffff for k in range(8))
 # Exhaustive independent arithmetic bit-address check, no crop or resize.
 for y in range(12):
  for x in range(12):
   bit=y*12+11-x
   assert ((packed[i*8+bit//18]>>(bit%18))&1)==((rows[y]>>(11-x))&1)
text=[];meta=[0]*256
for i,c in enumerate(cues):
 start=c['start_ms']*48;end=c['end_ms']*48;offset=len(text);length=len(c['text']);assert start<end<(1<<24)
 meta[4*i:4*i+4]=[start&0x3ffff,end&0x3ffff,(offset<<5)|length,((start>>18)<<6)|(end>>18)]
 text.extend(ids[ch]for ch in c['text'])
assert len(text)<=1024;used=len(text);text +=[0]*(1024-len(text))
rtl=r/'01_project/rtl/visual'
(rtl/'music_caption_config.vh').write_text(f'// Full52 user-supplied lyric lines, automatically aligned to original WAV.\n// Human listening/HDMI hardware latency verification still required.\nlocalparam integer MUSIC_CUE_COUNT={len(cues)},MUSIC_GLYPH_AW=8,MUSIC_FONT_ROWS=2048;\n',encoding='utf-8')
for filename,memory,values,bits in [('music_caption_meta_init.vh','metadata',meta,18),('music_caption_text_init.vh','text_memory',text,8),('music_caption_font_init.vh','font_memory',packed,18)]:
 (rtl/filename).write_text('// V128 generated from exact user-provided lyrics + preserved WAV; no runtime CPU/ASR.\n'+''.join(f'{memory}[{i}]={bits}\'h{v:0{(bits+3)//4}x};\n'for i,v in enumerate(values)),encoding='utf-8')
spec=dict(version='V128',source=str(wav),source_sha256=sha(wav),source_duration_seconds=sample_frames/48000,source_sample_frames=sample_frames,source_pcm_format='48kHz24bit stereo',user_text_sha256=a['source_text_sha256'],human_verified=False,human_timing_verified=False,complete_lyrics=True,full_user_text_covered=True,cues=cues,glyphs=glyphs,glyph_ids=ids,font_sha256=sha(f),font_size=10,glyph_aw=8,font_rows=logical,font_packed_words=packed,font_storage='256 glyphs x8words x18bits; each glyph12rows x12bits; no lost pixels',text_memory=text,metadata=meta,used_text_symbols=used,layout=dict(cell=32,glyph_width=12,glyph_height=12,scale=2,text_y=672,panel=[64,662,1216,708]),timing_review=a['review'])
(r/'03_docs/v128_caption_spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
out=r/'04_evidence/v128_caption_generation';assert not out.exists();out.mkdir()
rec=dict(passed=True,complete=True,full_user_text_covered=True,source_lines=52,cues=len(cues),glyphs=len(glyphs),text_symbols=used,logical_pixel_comparisons=256*144,font_packed_bits=len(packed)*18,font_naive_padded_bits=4096*12,human_timing_verified=False,source_sha256={q.relative_to(r).as_posix():sha(q)for q in [p,src/'MUSIC_用户提供完整歌词.txt',f,Path(__file__)]})
(out/'summary.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(rec,ensure_ascii=False,indent=2))
