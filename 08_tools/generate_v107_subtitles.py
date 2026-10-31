"""Compile plain SRT into small embedded FPGA cue/text/font ROMs. No ASR/TF SRT parser.
Use a WORK copy only. At most 8 non-overlapping one-line cues, 24 glyphs per cue.
The default file is explicitly DEMO_ONLY, not a transcript of collected media.
"""
from pathlib import Path
import re,json,hashlib,argparse
from PIL import Image,ImageDraw,ImageFont
r=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--srt',type=Path,default=r/'06_test_media/subtitles/DEMO_ONLY.srt');p.add_argument('--confirmed-transcript',action='store_true');a=p.parse_args()
if '01_versions' in r.parts:raise SystemExit('Do not edit frozen archives')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ms(s):
 h,m,s,f=map(int,re.split('[:,]',s));assert m<60 and s<60 and f<1000
 return ((h*60+m)*60+s)*1000+f
text=a.srt.read_text(encoding='utf-8-sig').strip();cues=[]
for block in re.split(r'\n\s*\n',text):
 lines=block.strip().splitlines();assert len(lines)==3,'Exactly one plain text line required per cue'
 m=re.fullmatch(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})',lines[1]);assert m,'Invalid SRT timestamp'
 begin,end=map(ms,m.groups());line=lines[2].strip()
 assert 0<=begin<end<2**32 and len(line)<=24 and line and '<' not in line,'Invalid range/text'
 assert not cues or begin>=cues[-1]['end_ms'],'Overlapping/unsorted cue'
 cues.append(dict(start_ms=begin,end_ms=end,text=line))
assert 1<=len(cues)<=8
assert cues[-1]['end_ms']<=16000, "This prototype axis is 16 seconds; extend/verify RTL axis before importing a longer SRT"
fontpath=r/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf';font=ImageFont.truetype(str(fontpath),14)
glyphs=list(' 0123456789:')
for c in cues:
 for x in c['text']:
  if x not in glyphs:glyphs.append(x)
assert len(glyphs)<=128
ids={c:i for i,c in enumerate(glyphs)};rows=[]
for n in range(128):
 im=Image.new('L',(16,16));d=ImageDraw.Draw(im)
 if n<len(glyphs) and glyphs[n]!=' ':
  ch=glyphs[n];l,t,rr,b=font.getbbox(ch);assert rr-l<=16 and b-t<=16
  d.text(((16-(rr-l))//2-l,(16-(b-t))//2-t),ch,font=font,fill=255)
 rows.extend(sum(1<<(15-x) for x in range(16) if im.getpixel((x,y))>=112) for y in range(16))
rtl=r/'01_project/rtl/visual'
(rtl/'subtitle_font_init.vh').write_text('// Generated from pinned OFL Noto CJK; no runtime font access.\n'+''.join(f"font_memory[{i}]=16'h{v:04x};\n" for i,v in enumerate(rows)),encoding='utf8')
cells=[]
for n in range(8):cells.extend(ids[x] for x in (cues[n]['text'] if n<len(cues) else '').ljust(32))
(rtl/'subtitle_text_init.vh').write_text('// 8 cues x 32 glyphs, unused cells blank.\n'+''.join(f"text_memory[{i}]=7'd{v};\n" for i,v in enumerate(cells)),encoding='utf8')
f=['// Generated SRT metadata. Endpoint is exclusive; overlaps rejected.','localparam integer CUE_COUNT='+str(len(cues))+';']
for name,key,bits in [('cue_start','start_ms',32),('cue_end','end_ms',32),('cue_length','length',5)]:
 f += [f'function [{bits-1}:0] {name};input [2:0] id;begin case(id)']
 for i,c in enumerate(cues):f += [f"3'd{i}:{name}={bits}'d{len(c['text']) if key=='length' else c[key]};"]
 f += [f"default:{name}={bits}'d{0xffffffff if bits==32 else 0};endcase end endfunction"]
f += [f"localparam [6:0] SUB_DIGIT_ZERO=7'd{ids['0']},SUB_COLON=7'd{ids[':']};"]
(rtl/'subtitle_cues.vh').write_text('\n'.join(f)+'\n',encoding='utf8')
# Extend new UI text lengths while preserving old UI compatibility assets.
ui=rtl/'media_ui_overlay.v';u=ui.read_text(encoding='utf8');spec=json.loads((r/'03_docs/v107_ui_font_spec.json').read_text(encoding='utf8'))
u=re.sub(r"^   6'd(?:4[6-9]|5[0-9]|6[0-3]):message_length=.*?;\n",'',u,flags=re.M)
u=re.sub(r"(6'd45:message_length=4'd4;)",r"\1\n"+'\n'.join(f"   6'd{i}:message_length=4'd{len(s)};" for i,s in enumerate(spec['messages']) if i>=46),u)
ui.write_text(u,encoding='utf8')
meta=dict(srt=str(a.srt),srt_sha256=sha(a.srt),confirmed_transcript=a.confirmed_transcript,demo_only=not a.confirmed_transcript,cues=cues,glyphs=glyphs,glyph_ids=ids,font_sha256=sha(fontpath),font_size=14,threshold=112,limits={'cues':8,'line_glyphs':24,'runtime_srt':False},note='Static precompiled subtitles, NOT speech recognition. Actual WAV playback is not implemented in this version.')
(r/'03_docs/v107_subtitle_spec.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
out=r/'04_evidence/v107_caption_assets';out.mkdir(exist_ok=True)
(out/'font.hex').write_text(''.join(f'{v:04x}\n' for v in rows));(out/'text.hex').write_text(''.join(f'{v:02x}\n' for v in cells))
print('Compiled',len(cues),'DEMO cues;',len(glyphs),'glyphs. No claimed ad transcript/audio sync.')
