"""Compile self-authored timed captions into the existing V132 sample-count ROMs.
No speech recognition, original lyrics, original media, or runtime CPU is required.
Input: JSON array of tracks with choice (1 or 3) and nonoverlapping cues in ms.
Default input is CC0 self-authored public test text. Run in a working copy only.
"""
from pathlib import Path
import json,hashlib,argparse
from PIL import Image,ImageDraw,ImageFont

def main():
 r=Path(__file__).resolve().parents[1]
 if '01_versions' in r.parts:raise SystemExit('Do not modify frozen archives')
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--input',type=Path,default=r/'06_test_media/public_captions/captions.json')
 a=p.parse_args();source=json.loads(a.input.read_text(encoding='utf-8'))
 sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
 tracks=[];cues=[]
 assert [t['choice']for t in source['tracks']]==[1,3]
 for t in source['tracks']:
  rows=t['cues'];assert 1<=len(rows)<=64
  base=0 if t['choice']==1 else 64
  tracks.append(dict(choice=t['choice'],name=t['name'],cue_count=len(rows),metadata_slot_base=base,global_cue_base=len(cues),caption_source='public self-authored test text'))
  for i,c in enumerate(rows):
   assert 0<c['start_ms']<c['end_ms'] and c['end_ms']*48 < 1<<24
   assert 0<len(c['text'])<=24
   if i:assert c['start_ms']>=rows[i-1]['end_ms']
   cues.append(dict(**c,track_choice=t['choice'],local_cue_index=i,metadata_slot=base+i,source_line=i+1))
 glyphs=list(dict.fromkeys(' '+''.join(c['text']for c in cues)));assert len(glyphs)<=320
 ids={c:i for i,c in enumerate(glyphs)}
 f=r/'07_reference/fonts/chill_round/ChillRoundM.otf'
 assert sha(f)=='2c8da065414e3cab951744f15c25b17a9ab4ae93e48def22004bc917550d1219'
 font=ImageFont.truetype(str(f),11);logical=[];packed=[]
 for i in range(320):
  im=Image.new('L',(12,12));d=ImageDraw.Draw(im)
  if i<len(glyphs)and glyphs[i]!=' ':
   ch=glyphs[i];l,t,rr,bb=font.getbbox(ch);assert rr-l<=12 and bb-t<=12
   d.text(((12-rr+l)//2-l,(12-bb+t)//2-t),ch,font=font,fill=255)
  rows=[sum(1<<(11-x)for x in range(12)if im.getpixel((x,y))>=112)for y in range(12)]
  logical.extend(rows+[0]*4);payload=sum(v<<(12*y)for y,v in enumerate(rows))
  packed.extend((payload>>(18*k))&0x3ffff for k in range(8))
 text=[];meta=[0]*512
 for c in cues:
  start=c['start_ms']*48;end=c['end_ms']*48;offset=len(text);length=len(c['text'])
  c.update(text_offset=offset,text_length=length)
  slot=c['metadata_slot']*4
  meta[slot:slot+4]=[start&0x3ffff,end&0x3ffff,(offset<<5)|length,((start>>18)<<6)|(end>>18)]
  text.extend(ids[ch]for ch in c['text'])
 used=len(text);assert used<=1024;text.extend([0]*(1024-used));rtl=r/'01_project/rtl/visual'
 (rtl/'music_caption_config.vh').write_text('// Generated PUBLIC TEST DATA; original private lyrics are not distributed.\nlocalparam integer MUSIC_CUE_COUNT=%d,THIRD_CUE_COUNT=%d,MUSIC_GLYPH_AW=9,MUSIC_FONT_ROWS=2560;\n'%tuple(t['cue_count']for t in tracks),encoding='utf-8')
 for file,memory,values,bits in [('music_caption_meta_init.vh','metadata',meta,18),('music_caption_text_init.vh','text_memory',text,9)]:
  (rtl/file).write_text('// Public self-authored test captions; no original lyrics.\n'+''.join(f"{memory}[{i}]={bits}'h{v:0{(bits+3)//4}x};\n"for i,v in enumerate(values)),encoding='utf-8')
 (rtl/'music_caption_font_init.vh').write_text('// ChillRoundM (OFL-1.1), public test glyphs, two native 18-bit banks.\n'+''.join(f"{mem}[{i}]=18'h{v:05x};\n"for mem,values in [('font_memory_lo',packed[:2048]),('font_memory_hi',packed[2048:])]for i,v in enumerate(values)),encoding='utf-8')
 spec=dict(version='V132-public',tracks=tracks,cues=cues,glyphs=glyphs,glyph_ids=ids,glyph_aw=9,font_slots=320,font_sha256=sha(f),font_size=11,font_rows=logical,font_packed_words=packed,font_bank_words=[2048,512],text_memory=text,metadata=meta,used_text_symbols=used,caption_license='CC0-1.0',private_media_included=False,font_path=f.relative_to(r).as_posix(),layout=dict(cell=48,glyph_width=12,glyph_height=12,scale=3,text_y=658,panel=[64,648,1216,704]))
 (r/'03_docs/v130_caption_spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(tracks=len(tracks),cues=len(cues),glyphs=len(glyphs),text_symbols=used,original_media_included=False)))
if __name__=='__main__':main()
