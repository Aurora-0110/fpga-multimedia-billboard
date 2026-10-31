# HISTORICAL development replay only; not the final build/rebuild entry.
# Use run_acceptance.py and generate_v105_ui_font.py instead.
import os
if os.environ.get('REPLAY_HISTORICAL_V105_EXPERIMENT')!='1':
 raise SystemExit('Historical experiment intentionally disabled; use final RTL and run_acceptance.py.')
from pathlib import Path
import json
r=Path(r'D:\FPGA_Billboard\work\v105_center_glass_art_spectrum_20261026')
p=r/'01_project/rtl/visual/ui_help_overlay.v'
s=p.read_text(encoding='utf8').replace('// v104: Chinese two-column 720p function/status UI; same v102 timeout and gestures.','// v105: centered Chinese two-column rounded translucent 720p UI.\n// Lightweight glass tint/highlights only: no blur/refraction/framebuffer or new CPU.')
a=s.index(' function [23:0] tint;');b=s.index(' reg [3:0] row_now',a)
msgs=json.loads((r/'03_docs/v104_ui_font_spec.json').read_text(encoding='utf8'))['messages']
length=' function [3:0] message_length;input [5:0] msg;begin\n  case(msg)\n'+''.join(f"   6'd{i}:message_length=4'd{len(m)};\n" for i,m in enumerate(msgs))+'   default:message_length=0;\n  endcase\n end endfunction\n'
def corner(rad):
 vals=[]
 for y in range(rad):
  vals.append(next(x for x in range(rad) if (2*x+1-2*rad)**2+(2*y+1-2*rad)**2<=4*rad*rad))
 return f' function [4:0] corner{rad};input [4:0] v;begin\n  case(v)\n'+''.join(f"   5'd{y}:corner{rad}=5'd{x};\n" for y,x in enumerate(vals))+f'   default:corner{rad}=0;\n  endcase\n end endfunction\n'
s=s[:a]+''' // Fixed-radius pixel-center circle lookup; no per-pixel multiply/divide.
'''+length+corner(24)+corner(22)+''' function [23:0] tint;input [23:0] d,s;reg [9:0] a,b,c;begin
  a={2'b0,d[23:16]}+{2'b0,s[23:16]}+{1'b0,s[23:16],1'b0}+10'd2;
  b={2'b0,d[15:8]}+{2'b0,s[15:8]}+{1'b0,s[15:8],1'b0}+10'd2;
  c={2'b0,d[7:0]}+{2'b0,s[7:0]}+{1'b0,s[7:0],1'b0}+10'd2;
  tint={a[9:2],b[9:2],c[9:2]};
 end endfunction
 function [7:0] shadow_channel;input [7:0] d,s;reg [10:0] v;begin
  v={d,3'b0}-{3'b0,d}+{3'b0,s}+11'd4;shadow_channel=v[10:3];
 end endfunction
 function [23:0] drop_shadow;input [23:0] d;begin
  drop_shadow={shadow_channel(d[23:16],8'd128),shadow_channel(d[15:8],8'd152),shadow_channel(d[7:0],8'd172)};
 end endfunction
 wire [4:0] outer_inset=y<88?corner24(y-12'd64):(y>=632?corner24(12'd655-y):5'd0);
 wire [4:0] inner_inset=y<88?corner22(y-12'd66):(y>=632?corner22(12'd653-y):5'd0);
 wire [4:0] shadow_inset=y<96?corner24(y-12'd72):(y>=640?corner24(12'd663-y):5'd0);
 wire in_panel=y>=64&&y<656&&x>=(12'd288+outer_inset)&&x<(12'd992-outer_inset);
 wire in_inner=y>=66&&y<654&&x>=(12'd290+inner_inset)&&x<(12'd990-inner_inset);
 wire in_shadow=y>=72&&y<664&&x>=(12'd294+shadow_inset)&&x<(12'd998-shadow_inset);
'''+s[b:]
a=s.index(' wire [11:0] local_x=');b=s.index(' reg override_now',a)
s=s[:a]+''' wire [5:0] label_now=label_message(row_now),state_now=state_message(row_now);
 wire [3:0] label_len=message_length(label_now),state_len=message_length(state_now);
 wire [11:0] label_start=12'd448-{4'b0,label_len,4'b0};
 wire [11:0] state_start=12'd768-{4'b0,state_len,4'b0};
 wire label_hit=x>=label_start&&x<(label_start+{3'b0,label_len,5'b0});
 wire state_hit=x>=state_start&&x<(state_start+{3'b0,state_len,5'b0});
 wire [11:0] local_x=x-(state_hit?state_start:label_start);
 wire [4:0] value_col_now={1'b0,local_x[8:5]};
'''+s[b:]
s=s.replace('if(column_now>=7&&column_now<18)begin','if(state_hit)begin')
s=s.replace('reg [2:0] panel,border,glyph;','reg [2:0] panel,border,glyph,shadow;')
s=s.replace('panel<=0;border<=0;glyph<=0;','panel<=0;border<=0;glyph<=0;shadow<=0;')
a=s.index('  panel[0]<=');b=s.index('  font_y0<=',a)
s=s[:a]+'''  panel[0]<=ui_visible&&de&&in_panel;
  shadow[0]<=ui_visible&&de&&in_shadow;
  border[0]<=ui_visible&&de&&in_panel&&(!in_inner||
     (x>=576&&x<578&&y>=120&&y<640)||(y>=158&&y<160));
  panel[2:1]<=panel[1:0];border[2:1]<=border[1:0];glyph[2:1]<=glyph[1:0];shadow[2:1]<=shadow[1:0];
  glyph[0]<=ui_visible&&de&&glyph_y_now&&(label_hit||state_hit);
  message0<=label_hit?label_now:(state_hit?state_now:6'd0);
  text_col0<=local_x[8:5];
'''+s[b:]
a=s.index('  shade[0]<=');b=s.index('  x_out<=xx[2]',a)
s=s[:a]+'''  shade[0]<=((shown_field==1&&row_now==6)||(shown_field==2&&row_now==7))?24'hd5f4e8:
             ((row_now==10&&shown_keys!=0)?24'hfcebd5:(y<112?24'hf5fbff:(row_now==1?24'hedf6fc:24'heaf4fc)));
  ink[0]<=row_now<=1?24'h163046:((row_now==4&&shown_failed)?24'hba332c:
          ((row_now==9&&shown_audio)?24'h00796b:((row_now==10&&shown_keys!=0)?24'h885718:
          (label_hit?24'h42566c:24'h173b54))));
  rgb_out<=border[2]?24'hf9fdff:((glyph[2]&&bits2[15-font_x2])?ink[2]:
           (panel[2]?tint(base[2],shade[2]):(shadow[2]?drop_shadow(base[2]):base[2])));
'''+s[b:]
p.write_text(s,encoding='utf8')
g=r/'08_tools/generate_v105_ui_font.py';s=(r/'08_tools/generate_v104_ui_font.py').read_text(encoding='utf8').replace('v104','v105').replace('V104','V105')
s=s.replace("'panel':[48,64,656,648],'text_origin':[64,80]","'panel':[288,64,992,656],'radius':24,'column_centers':[448,768],'text_origin_y':80")
g.write_text(s,encoding='utf8')
# Independent Chinese oracle: same state matrix, variable-length centered text.
s=(r/'02_tests/ui/run_v104_ui.py').read_text(encoding='utf8').replace('v104','v105').replace('V104','V105')
(r/'02_tests/ui/run_v105_ui.py').write_text(s,encoding='utf8')
s=(r/'02_tests/ui/tb_v104_ui.sv').read_text(encoding='utf8').replace('v104','v105')
s=s.replace('integer ncases,ci,row,col,i,j,checks=0,chars=0,frame_pixels=0;','integer ncases,ci,row,col,i,j,checks=0,chars=0,frame_pixels=0,llen,slen,off;')
s=s.replace('''   @(negedge clk);x=64+col*32;y=80+row*40;de=1;cycles(3);
   got=d.override1?d.override_glyph1:d.text_glyph1;
   if(got!==text_memory[which*252+row*18+col])$fatal(1,"Chinese text case=%0d row=%0d col=%0d got=%0d expected=%0d",which,row,col,got,text_memory[which*252+row*18+col]);
   chars++;''','''   llen=7;while(llen>0&&text_memory[which*252+row*18+llen-1]==0)llen--;
   slen=11;while(slen>0&&text_memory[which*252+row*18+7+slen-1]==0)slen--;
   if((col<7&&col<llen)||(col>=7&&col<7+slen))begin
    @(negedge clk);x=col<7?448-llen*16+col*32:768-slen*16+(col-7)*32;y=80+row*40;de=1;cycles(3);
    got=d.override1?d.override_glyph1:d.text_glyph1;
    if(got!==text_memory[which*252+row*18+col])$fatal(1,"Chinese centered text case=%0d row=%0d col=%0d got=%0d expected=%0d",which,row,col,got,text_memory[which*252+row*18+col]);
    chars++;
   end''')
a=s.index(' function [23:0] blend_half;');b=s.index(' integer k,pipe_cycles',a)
s=s[:a]+''' // Mathematical rounded-rectangle oracle, NOT the RTL inset tables.
 function automatic bit rounded(input integer px,py,l,t,r,b,rad);
  integer dx,dy,cx,cy;begin
   rounded=0;
   if(px>=l&&px<r&&py>=t&&py<b)begin
    cx=px<l+rad?l+rad:(px>=r-rad?r-rad:2*px+1);
    cy=py<t+rad?t+rad:(py>=b-rad?b-rad:2*py+1);
    dx=(px<l+rad||px>=r-rad)?2*px+1-2*cx:0;
    dy=(py<t+rad||py>=b-rad)?2*py+1-2*cy:0;
    rounded=dx*dx+dy*dy<=4*rad*rad;
   end
  end
 endfunction
 function [23:0] glass;input [23:0] bg,t;integer k,v;begin
  for(k=0;k<3;k++)begin v=bg[k*8+:8]+3*t[k*8+:8]+2;glass[k*8+:8]=v/4;end
 end endfunction
 function [23:0] shadow_mix;input [23:0] bg;integer k,v,shade;begin
  for(k=0;k<3;k++)begin shade=k==2?128:(k==1?152:172);v=7*bg[k*8+:8]+shade+4;shadow_mix[k*8+:8]=v/8;end
 end endfunction
 integer left_length,right_length,startl,startr;bit lh,rh;
'''+s[b:]
a=s.index('  if(ref_visible&&de&&x>=48');b=s.index('  for(k=3;',a)
s=s[:a]+'''  if(ref_visible&&de)begin
   if(rounded(x,y,294,72,998,664,24))expect_rgb=shadow_mix(rgb);
   if(rounded(x,y,288,64,992,656,24))begin
    rr=(y>=80&&y<640)?(y-80)/40:15;
    shade=24'heaf4fc;
    if((ref_field==1&&rr==6)||(ref_field==2&&rr==7))shade=24'hd5f4e8;
    else if(rr==10&&ref_keys!=0)shade=24'hfcebd5;
    else if(y<112)shade=24'hf5fbff;
    else if(rr==1)shade=24'hedf6fc;
    expect_rgb=glass(rgb,shade);
    if(rr<14)begin
     left_length=7;while(left_length>0&&reference_text[rr*18+left_length-1]==0)left_length--;
     right_length=11;while(right_length>0&&reference_text[rr*18+7+right_length-1]==0)right_length--;
     startl=448-left_length*16;startr=768-right_length*16;
     lh=x>=startl&&x<startl+left_length*32;rh=x>=startr&&x<startr+right_length*32;
     ink=lh?24'h42566c:24'h173b54;
     if(rr<=1)ink=24'h163046;
     else if(rr==4&&ref_failed)ink=24'hba332c;
     else if(rr==9&&ref_audio)ink=24'h00796b;
     else if(rr==10&&ref_keys!=0)ink=24'h885718;
     if((lh||rh)&&(y-80)%40<32)begin
      lx=x-(rh?startr:startl);cc=(rh?7:0)+lx/32;fx=(lx%32)/2;fy=((y-80)%40)/2;
      bits=font_memory[reference_text[rr*18+cc]*16+fy];
      if(bits[15-fx])expect_rgb=ink;
     end
    end
    if(!rounded(x,y,290,66,990,654,22)||(x>=576&&x<578&&y>=120&&y<640)||(y>=158&&y<160))expect_rgb=24'hf9fdff;
   end
  end
'''+s[b:]
s=s.replace("rgb={i[7:0],j[7:0],8'h60};render_tag=(capture!=0);","rgb=capture==1?24'hffffff:{i[7:0],j[7:0],8'h60};render_tag=(capture!=0);")
s=s.replace('independent text cases / %0d cells','independent centered text cases / %0d actual glyph cells')
(r/'02_tests/ui/tb_v105_ui.sv').write_text(s,encoding='utf8')
print('UI v105 edits written; old source/test copies preserved in work and v104 archive.')
