"""Prepare user-audio transcripts and compact caption ROMs; no web lyric copying.
Only exact normalized cross-engine agreements are enabled; full ASR remains a draft.
"""
from pathlib import Path
import json,re,sys,math,hashlib
from PIL import Image,ImageDraw,ImageFont
r=Path(__file__).resolve().parents[1]
if '01_versions' in r.parts:raise SystemExit('Do not regenerate assets inside frozen archives')
sys.path.insert(0,r'D:\FPGA_Billboard\90_tools\media\asr\packages')
from opencc import OpenCC
cc=OpenCC('t2s');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a_path=r/'06_test_media/captions_music/recognition_draft.json';b_path=r/'06_test_media/captions_music_turbo/recognition_draft.json'
a=json.loads(a_path.read_text(encoding='utf-8'));b=json.loads(b_path.read_text(encoding='utf-8'))
assert a['complete'] and b['complete'] and a['source_sha256']==b['source_sha256']
clean=lambda s:re.sub(r'[^\u3400-\u9fffA-Za-z0-9]','',cc.convert(s))
out=r/'06_test_media/captions_music_prepared';out.mkdir(exist_ok=True)
full=[];enabled=[];review=[]
for x in b['segments']:
 text=cc.convert(x['text']).strip();norm=clean(text)
 # Instrumental lead-in/outro produced obvious ASR credits/repetition. Neither is imported.
 if x['start']<28 or x['start']>=216 or len(norm)>24 or not norm:
  review.append(dict(**x,reason='excluded_intro_outro_or_repetition'));continue
 row=dict(start_ms=round(x['start']*1000),end_ms=round(x['end']*1000),text=text)
 full.append(row)
 nearby=[y for y in a['segments']if y['end']>x['start']-0.8 and y['start']<x['end']+0.8]
 match=[y for y in nearby if len(norm)>=4 and norm in clean(y['text'])]
 if match:
  enabled.append(dict(**row,agreement_only_not_human_verified=True,second_engine_text=match[0]['text']))
 else:review.append(dict(**row,reason='two_engine_disagreement'))
assert 1<=len(enabled)<=64
# Preserve complete editable drafts for the user, not silently invented corrections.
def stamp(ms):return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
def srt(rows):return '\n\n'.join(f'{i+1}\n{stamp(c["start_ms"])} --> {stamp(c["end_ms"])}\n{c["text"]}'for i,c in enumerate(rows))+'\n'
(out/'MUSIC_双引擎待校对全稿.srt').write_text(srt(full),encoding='utf-8-sig')
(out/'MUSIC_当前启用候选.srt').write_text(srt(enabled),encoding='utf-8-sig')
(out/'MUSIC_逐句校对清单.json').write_text(json.dumps(dict(human_verified=False,complete_lyrics=False,unmatched_lines_disabled=True,source_sha256=a['source_sha256'],enabled=enabled,review=review),ensure_ascii=False,indent=2),encoding='utf-8')
# Compact12x12 glyphs,2x output scale,32px cells. Power-of-two glyph capacity.
glyphs=[' ']
for cue in enabled:
 assert 0<cue['start_ms']<cue['end_ms']<349000 and len(cue['text'])<=24
 for c in cue['text']:
  if c not in glyphs:glyphs.append(c)
aw=max(1,(len(glyphs)-1).bit_length());assert aw<=8
ids={c:i for i,c in enumerate(glyphs)}
font_path=r/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf';assert sha(font_path)=='ca094f6b0001fb048ca39ddd797a0cdb0179e1e55c6561e111c49c3e6a61d7b7'
font=ImageFont.truetype(str(font_path),10);rows=[]
for i in range(1<<aw):
 im=Image.new('L',(12,12));d=ImageDraw.Draw(im)
 if i<len(glyphs) and glyphs[i]!=' ':
  ch=glyphs[i];l,t,rr,bt=font.getbbox(ch);assert rr-l<=12 and bt-t<=12
  d.text(((12-rr+l)//2-l,(12-bt+t)//2-t),ch,font=font,fill=255)
 for y in range(16):rows.append(sum(1<<(11-x)for x in range(12)if y<12 and im.getpixel((x,y))>=112))
text=[];meta=[0]*256
for i,cue in enumerate(enabled):
 start=cue['start_ms']*48;end=cue['end_ms']*48;offset=len(text);length=len(cue['text']);assert length<32
 meta[i*4:(i+1)*4]=[start&0x3ffff,end&0x3ffff,(offset<<5)|length,((start>>18)<<6)|(end>>18)]
 text.extend(ids[c]for c in cue['text'])
assert len(text)<=1024;text+= [0]*(1024-len(text))
rtl=r/'01_project/rtl/visual'
(rtl/'music_caption_config.vh').write_text(f'// Prepared from local user WAV; agreement-only draft, NOT verified full lyrics.\nlocalparam integer MUSIC_CUE_COUNT={len(enabled)},MUSIC_GLYPH_AW={aw},MUSIC_FONT_ROWS={len(rows)};\n',encoding='utf-8')
for filename,memory,values,bits in [('music_caption_meta_init.vh','metadata',meta,18),('music_caption_text_init.vh','text_memory',text,8),('music_caption_font_init.vh','font_memory',rows,12)]:
 (rtl/filename).write_text('// Generated from local user-supplied music; no runtime CPU/ASR.\n'+''.join(f'{memory}[{i}]={bits}\'h{v:0{(bits+3)//4}x};\n'for i,v in enumerate(values)),encoding='utf-8')
spec=dict(version='V127',source=a['source'],source_sha256=a['source_sha256'],source_duration_seconds=a['duration'],source_pcm_format='48kHz24bit stereo',human_verified=False,complete_lyrics=False,enabled_policy='Exact simplified-CJK cross-engine agreement only. Unmatched lines are silent gaps, not fabricated text.',cues=enabled,glyphs=glyphs,glyph_ids=ids,font_sha256=sha(font_path),font_size=10,glyph_aw=aw,font_rows=rows,text_memory=text,metadata=meta,layout=dict(cell=32,glyph_width=12,glyph_height=12,scale=2,text_y=672,panel=[64,662,1216,708]))
(r/'03_docs/v127_caption_spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
record=dict(passed=True,human_verified=False,source_sha256={p.relative_to(r).as_posix():sha(p)for p in [a_path,b_path,font_path,Path(__file__)]},enabled_cues=len(enabled),draft_cues=len(full),glyphs=len(glyphs),glyph_capacity=1<<aw,font_bits=len(rows)*12,text_bits=len(text)*8,metadata_bits=len(meta)*18,scope='Offline local user-audio transcription preparation only, not verified lyrics/recognition on FPGA/hardware sync acceptance')
e=r/'04_evidence/v127_caption_generation';e.mkdir(exist_ok=True);(e/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(record,ensure_ascii=False,indent=2))
