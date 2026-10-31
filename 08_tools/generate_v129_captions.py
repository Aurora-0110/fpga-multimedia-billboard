"""V129: shared9bit text, 2x64-cue native ROM, 4+1 banked lossless12x12 fonts."""
from pathlib import Path
import json,hashlib,wave
from PIL import Image,ImageDraw,ImageFont
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[(1,'MUSIC','captions_music_user','MUSIC_用户提供完整歌词.txt','MUSIC_完整时间轴.json'),(3,'TURANDETUOLUO','captions_third_user','TURANDETUOLUO_用户提供完整歌词.txt','TURANDETUOLUO_完整时间轴.json')]
tracks=[];cues=[];sources=[]
for choice,name,folder,txt,js in inputs:
 src=r/'06_test_media'/folder;timeline=src/js;a=json.loads(timeline.read_text(encoding='utf-8'));source=json.loads((src/'SOURCE.json').read_text(encoding='utf-8'));wav=Path(source['audio_path'])
 assert a['full_user_text_covered']and sha(wav)==a['source_sha256']and sha(src/txt)==a['source_text_sha256']
 with wave.open(str(wav))as w:assert w.getparams()[:3]==(2,3,48000);frames=w.getnframes()
 assert 1<=len(a['rows'])<=64
 track=dict(choice=choice,name=name,cue_count=len(a['rows']),metadata_slot_base=0 if choice==1 else 64,global_cue_base=len(cues),source=str(wav),source_sha256=sha(wav),sample_frames=frames,duration_seconds=frames/48000,source_text_sha256=sha(src/txt),human_timing_verified=False,review=a['review'])
 for i,c in enumerate(a['rows']):
  assert 0<c['start_ms']<c['end_ms']and c['end_ms']*48<=frames and 0<len(c['text'])<=24
  if i:assert c['start_ms']>=a['rows'][i-1]['end_ms']
  cues.append(dict(**c,track_choice=choice,local_cue_index=i,metadata_slot=track['metadata_slot_base']+i))
 tracks.append(track);sources.extend([timeline,src/txt,src/'SOURCE.json'])
glyphs=list(dict.fromkeys(' '+''.join(c['text']for c in cues)));assert len(glyphs)<=320;ids={c:i for i,c in enumerate(glyphs)}
f=r/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf';assert sha(f)=='ca094f6b0001fb048ca39ddd797a0cdb0179e1e55c6561e111c49c3e6a61d7b7'
font=ImageFont.truetype(str(f),10);logical=[];packed=[]
for i in range(320):
 im=Image.new('L',(12,12));d=ImageDraw.Draw(im)
 if i<len(glyphs)and glyphs[i]!=' ':
  ch=glyphs[i];l,t,rr,bb=font.getbbox(ch);assert rr-l<=12 and bb-t<=12
  d.text(((12-rr+l)//2-l,(12-bb+t)//2-t),ch,font=font,fill=255)
 rows=[sum(1<<(11-x)for x in range(12)if im.getpixel((x,y))>=112)for y in range(12)];logical.extend(rows+[0]*4)
 payload=sum(v<<(12*y)for y,v in enumerate(rows));packed.extend((payload>>(18*k))&0x3ffff for k in range(8))
 for y in range(12):
  for x in range(12):
   bit=y*12+11-x;assert ((packed[i*8+bit//18]>>(bit%18))&1)==((rows[y]>>(11-x))&1)
text=[];meta=[0]*512
for c in cues:
 start=c['start_ms']*48;end=c['end_ms']*48;offset=len(text);length=len(c['text']);assert start<end<(1<<24)
 c.update(text_offset=offset,text_length=length)
 slot=c['metadata_slot']*4;meta[slot:slot+4]=[start&0x3ffff,end&0x3ffff,(offset<<5)|length,((start>>18)<<6)|(end>>18)]
 text.extend(ids[ch]for ch in c['text'])
used=len(text);assert used<=1024;text.extend([0]*(1024-used));rtl=r/'01_project/rtl/visual'
(rtl/'music_caption_config.vh').write_text('// V129 exact-user-text captions; automatically aligned, not human listening QA.\nlocalparam integer MUSIC_CUE_COUNT=53,THIRD_CUE_COUNT=16,MUSIC_GLYPH_AW=9,MUSIC_FONT_ROWS=2560;\n',encoding='utf-8')
assert [q['cue_count']for q in tracks]==[53,16]
for file,memory,values,bits in [('music_caption_meta_init.vh','metadata',meta,18),('music_caption_text_init.vh','text_memory',text,9)]:
 (rtl/file).write_text('// V129 generated, exact supplied lyrics; no runtime CPU/ASR.\n'+''.join(f'{memory}[{i}]={bits}\'h{v:0{(bits+3)//4}x};\n'for i,v in enumerate(values)),encoding='utf-8')
(rtl/'music_caption_font_init.vh').write_text('// V129 lossless144-bit glyphs: explicit2048+512 native18bit-word banks.\n'+''.join(f'{mem}[{i}]={18}\'h{v:05x};\n'for mem,values in [('font_memory_lo',packed[:2048]),('font_memory_hi',packed[2048:])]for i,v in enumerate(values)),encoding='utf-8')
spec=dict(version='V129',tracks=tracks,cues=cues,glyphs=glyphs,glyph_ids=ids,glyph_aw=9,font_slots=320,font_sha256=sha(f),font_size=10,font_rows=logical,font_packed_words=packed,font_bank_words=[2048,512],text_memory=text,metadata=meta,used_text_symbols=used,complete_lyrics=True,full_user_text_covered=True,human_timing_verified=False,layout=dict(cell=32,glyph_width=12,glyph_height=12,scale=2,text_y=672,panel=[64,662,1216,708]))
(r/'03_docs/v129_caption_spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
out=r/'04_evidence/v129_caption_generation';assert not out.exists();out.mkdir()
rec=dict(passed=True,complete=True,tracks=2,cues=len(cues),glyphs=len(glyphs),text_symbols=used,font_words=len(packed),logical_pixel_comparisons=320*144,expected_caption_brams=7,net_additional_brams=1,human_timing_verified=False,full_user_text_covered=True,source_sha256={p.relative_to(r).as_posix():sha(p)for p in [*sources,f,Path(__file__)]})
(out/'summary.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(rec,ensure_ascii=False,indent=2))
