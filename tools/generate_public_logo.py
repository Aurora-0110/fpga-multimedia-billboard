"""Generate public demo logo ROMs, or import a locally authorized --image.
Default: self-authored FPGA wordmark, not official Anlogic/TF artwork.
Interfaces, palette, 112x56 rows and synchronous one-cycle latency are retained.
"""
from pathlib import Path
import argparse
from PIL import Image,ImageDraw,ImageFont

def main():
 r=Path(__file__).resolve().parents[1]
 if '01_versions'in r.parts:raise SystemExit('Do not modify frozen archives')
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--image',type=Path);a=p.parse_args()
 canvas=Image.new('RGB',(112,56),'white')
 if a.image:
  image=Image.open(a.image).convert('RGB');image.thumbnail((112,56),Image.Resampling.LANCZOS);canvas.paste(image,((112-image.width)//2,(56-image.height)//2))
 else:
  d=ImageDraw.Draw(canvas);d.rounded_rectangle((3,4,108,51),radius=9,outline=(24,56,88),width=3)
  font=ImageFont.truetype(str(r/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf'),24)
  d.text((22,6),'FPGA',font=font,fill=(24,56,88));d.rectangle((23,42,88,44),fill=(207,24,48))
 values=[];rows=[]
 for y in range(64):
  row=[]
  for x in range(128):
   v=0
   if y<56 and x<112:
    rr,g,b=canvas.getpixel((x,y));v=0 if min(rr,g,b)>185 else(2 if rr>g*1.25 and rr>b*1.15 else 1)
   row.append(v)
  values.extend(row)
  if y<56:rows.append(sum(v<<(2*x)for x,v in enumerate(row[:112])))
 head="`timescale 1ns/1ps\n// PUBLIC self-authored FPGA demo artwork; original TF image is not included.\n"
 text=head+'''module official_logo(input wire[6:0]x,input wire[5:0]y,output wire[1:0]pixel);
 reg[223:0]rowbits;
 always @* begin case(y)
'''+''.join(f"6'd{y}:rowbits=224'h{v:056x};\n"for y,v in enumerate(rows))+'''default:rowbits=0;endcase end
 assign pixel=x<112?((rowbits>>(x*2))&2'b11):2'b00;
endmodule
'''
 sync=text[text.index('module official_logo('):].replace('module official_logo(','module official_logo_sync(input wire clk,',1).replace(' always @* begin case(y)',' reg[6:0]xpos;\n always @(posedge clk)begin xpos<=x;case(y)').replace('rowbits=','rowbits<=').replace('assign pixel=x<112?((rowbits>>(x*2))','assign pixel=xpos<112?((rowbits>>(xpos*2))')
 (r/'01_project/rtl/video/official_logo.v').write_text(text+'\n'+sync,encoding='utf-8')
 (r/'01_project/rtl/visual/official_logo_compact_sync.v').write_text(head+'''module official_logo_compact_sync(input wire clk,input wire[6:0]x,input wire[5:0]y,output reg[1:0]pixel);
 (* ram_style="bram" *)reg[1:0]memory[0:8191];
 wire[12:0]address={y,x};
 initial begin
'''+''.join(f"memory[{i}]=2'd{v};\n"for i,v in enumerate(values))+'''end
 always @(posedge clk)pixel<=memory[address];
endmodule
''',encoding='utf-8')
 print('Public logo ROMs generated: 112x56, 2-bit palette, padded 128x64 memory')
if __name__=='__main__':main()
