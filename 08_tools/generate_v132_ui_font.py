"""Reproduce/check lossless V132 compact UI ROM from pinned Noto font. Default read-only."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import argparse,hashlib,json,re
R=Path(__file__).resolve().parents[1]
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--write',action='store_true');x=a.parse_args()
 if x.write and '01_versions'in R.parts:a.error('Frozen archive: --write forbidden.')
 s=json.loads((R/'03_docs/v130_ui_font_spec.json').read_text('utf8'));p=R/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf';assert hashlib.sha256(p.read_bytes()).hexdigest()==s['font_sha256'];font=ImageFont.truetype(str(p),14)
 rows=[]
 for g in range(128):
  im=Image.new('L',(16,16));ch=s['glyphs'][g]if g<len(s['glyphs'])else' '
  if ch!=' ':
   l,t,r,b=font.getbbox(ch);assert r-l<=16 and b-t<=16
   ImageDraw.Draw(im).text(((16-r+l)//2-l,(16-b+t)//2-t),ch,font=font,fill=255)
  rows.extend(sum(1<<(15-x)for x in range(16)if im.getpixel((x,y))>=112)for y in range(16))
 original={int(a):int(b,16)for a,b in re.findall(r"font_memory\[(\d+)\]=16'h([0-9a-fA-F]+);",(R/'01_project/rtl/visual/media_ui_zh_font_init.vh').read_text('utf8'))}
 assert [original[i]for i in range(2048)]==rows,'Original font differs from pinned raster'
 banks=[[0]*512 for _ in range(3)]
 for g in range(128):
  for y in range(16):
   v=rows[g*16+y];assert v&0x8001==0 and(y!=15 or v==0),'Font changed: compaction precondition fails; do not crop'
  payload=sum(((rows[g*16+y]>>1)&0x3fff)<<(14*y)for y in range(15))
  for w in range(12):banks[w//4][g*4+w%4]=(payload>>(18*w))&0x3ffff
 target=R/'01_project/rtl/visual/media_ui_font_packed_v132.vh'
 if x.write:
  text='// V132 lossless 128x(14x15) UI payload in three512x18 native9K ROMs.\n// Original16x16 edge zeros proven by prepare_v132_ui_compact.py; OFL unchanged.\n'
  text+=''.join(f"ui_font_rom{bank}[{i}]=18'h{v:05x};\n"for bank in range(3)for i,v in enumerate(banks[bank]));target.write_text(text,encoding='utf8')
 actual={(int(b),int(i)):int(v,16)for b,i,v in re.findall(r"ui_font_rom([012])\[(\d+)\]=18'h([0-9a-fA-F]+);",target.read_text('utf8'))}
 assert len(actual)==1536
 for b in range(3):
  for i in range(512):assert actual[b,i]==banks[b][i],(b,i)
 print('PASS V132 font regeneration: pinned font -> original2048rows -> all1536 packed18bit words; pixel shapes unchanged; write=',x.write)
if __name__=='__main__':main()
