# HISTORICAL development replay only; not the final build/rebuild entry.
# Use run_acceptance.py and generate_v105_ui_font.py instead.
import os
if os.environ.get('REPLAY_HISTORICAL_V105_EXPERIMENT')!='1':
 raise SystemExit('Historical experiment intentionally disabled; use final RTL and run_acceptance.py.')
from pathlib import Path
r=Path(r'D:\FPGA_Billboard\work\v105_center_glass_art_spectrum_20261026')
p=r/'01_project/rtl/visual/spectrum_overlay.v';s=p.read_text(encoding='utf8')
s=s.replace('// v099: 16-band transparent 720p spectrum. ONLY bar/peak pixels are blended;','// v105: 64 rainbow display bars interpolated from 16 REAL DFT bands.\n// The 64 bars are not 64 independent measured frequencies.\n// Frame-blank preprocessing + synchronous 64x16 BRAM, not a pixel multiplier.\n// ONLY rounded thin bar/peak pixels are blended;')
s=s.replace(' reg[7:0]height[0:15],peak[0:15];integer i;',''' reg[7:0]height[0:15],peak[0:15];integer i;
 // Built before the first visible bar (y>=464). No asynchronous RAM reset.
 // draw_ready masks uninitialized startup reads; first valid frame rebuilds all64.
 (* ram_style="block" *)reg[15:0]display_memory[0:63];
 reg[15:0]pixel_hp,build_word;
 reg preparing,draw_ready;reg[1:0]build_phase;reg[5:0]build_index;
 reg[7:0]ha,hb,pa,pb;
 function[7:0]lerp4;input[7:0]a,b;input[1:0]f;reg[9:0]v;begin
  case(f)
   0:v={a,2'b0};
   1:v={2'b0,a}+{1'b0,a,1'b0}+{2'b0,b}+10'd2;
   2:v={1'b0,a,1'b0}+{1'b0,b,1'b0}+10'd2;
   3:v={2'b0,a}+{2'b0,b}+{1'b0,b,1'b0}+10'd2;
  endcase
  lerp4=v[9:2];
 end endfunction
 wire[11:0]bx=x-12'd128;
 always @(posedge clk)begin
  if(preparing&&build_phase==2)display_memory[build_index]<=build_word;
  pixel_hp<=display_memory[bx[9:4]];
 end''')
s=s.replace('h_q<=0;p_q<=0;goal_q<=0;h_next_q<=0;p_next_q<=0;','''h_q<=0;p_q<=0;goal_q<=0;h_next_q<=0;p_next_q<=0;
  preparing<=0;draw_ready<=0;build_phase<=0;build_index<=0;
  ha<=0;hb<=0;pa<=0;pb<=0;build_word<=0;''')
s=s.replace('frame_target<=target;updating<=1;update_band<=0;update_phase<=0;','frame_target<=target;updating<=1;update_band<=0;update_phase<=0;preparing<=0;draw_ready<=0;')
s=s.replace('if(update_band==15)updating<=0;','if(update_band==15)begin updating<=0;preparing<=1;build_index<=0;build_phase<=0;end')
a=s.index('  end\n end\n function[23:0]gradient;')
s=s[:a]+'''  end else if(preparing)begin
   case(build_phase)
    0:begin
     ha<=height[build_index[5:2]];pa<=peak[build_index[5:2]];
     hb<=height[build_index[5:2]==15?4'd15:build_index[5:2]+4'd1];
     pb<=peak[build_index[5:2]==15?4'd15:build_index[5:2]+4'd1];
     build_phase<=1;
    end
    1:begin
     build_word<={lerp4(pa,pb,build_index[1:0]),lerp4(ha,hb,build_index[1:0])};build_phase<=2;
    end
    2:begin
     if(build_index==63)begin preparing<=0;draw_ready<=1;end
     else begin build_index<=build_index+1'b1;build_phase<=0;end
    end
   endcase
  end
 end
'''+s[a+len('  end\n end\n'):]
a=s.index(' function[23:0]gradient;');b=s.index(' // Explicit shift/add',a)
s=s[:a]+''' // Independent fixed rainbow palette, no upstream RTL/assets copied.
 function[23:0]rainbow;input[3:0]band;begin case(band)
  0:rainbow=24'hf15d6e;1:rainbow=24'hf77b54;2:rainbow=24'hf39f36;
  3:rainbow=24'hd5b32b;4:rainbow=24'h99bf3c;5:rainbow=24'h56bf65;
  6:rainbow=24'h2dbb91;7:rainbow=24'h25b6b8;8:rainbow=24'h27a7d8;
  9:rainbow=24'h438de8;10:rainbow=24'h6374ed;11:rainbow=24'h8b65e6;
  12:rainbow=24'ha661d8;13:rainbow=24'hbf62c8;14:rainbow=24'hd763ad;
  15:rainbow=24'he36891;
 endcase end endfunction
 function[7:0]light_channel;input[7:0]v;reg[9:0]a;begin
  a={2'b0,v}+{1'b0,v,1'b0}+10'd255;light_channel=a[9:2];
 end endfunction
 function[23:0]highlight;input[23:0]v;begin
  highlight={light_channel(v[23:16]),light_channel(v[15:8]),light_channel(v[7:0])};
 end endfunction
'''+s[b:]
a=s.index(' wire[11:0]bx=x-12\'d128,from_bottom=');s=s[:a]+''' // Stage0: synchronous RAM read + source pixel/control/hue. Stage1: geometry
 // and foreground/alpha. Stage2: RGB blend + aligned output. Still THREE clocks.
 reg[11:0]xx[0:1],yy[0:1];reg[3:0]control[0:1];
 reg[23:0]base0,base1,hue0,color1;reg[3:0]alpha1;
 reg[3:0]slot0;reg cell0,permit0;reg[3:0]opacity0;integer q;
 wire[11:0]bar_top=12'd608-{4'b0,pixel_hp[7:0]};
 wire bar_on=cell0&&pixel_hp[7:0]!=0&&yy[0]<608&&yy[0]>=bar_top&&
     ((slot0!=4&&slot0!=11)||(yy[0]>bar_top&&yy[0]<607));
 wire peak_on=cell0&&slot0>=5&&slot0<11&&pixel_hp[15:8]!=0&&
     yy[0]>=12'd606-{4'b0,pixel_hp[15:8]}&&yy[0]<12'd608-{4'b0,pixel_hp[15:8]};
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  for(q=0;q<2;q=q+1)begin xx[q]<=0;yy[q]<=0;control[q]<=4'b0110;end
  base0<=0;base1<=0;hue0<=0;color1<=0;alpha1<=0;
  cell0<=0;permit0<=0;slot0<=0;opacity0<=0;
  x_out<=0;y_out<=0;rgb_out<=0;de_out<=0;hs_out<=1;vs_out<=1;picture_visible_out<=0;
 end else begin
  xx[0]<=x;yy[0]<=y;control[0]<={de,hs,vs,picture_visible};
  xx[1]<=xx[0];yy[1]<=yy[0];control[1]<=control[0];base0<=rgb;base1<=base0;
  hue0<=rainbow(bx[9:6]);slot0<=bx[3:0];
  cell0<=x>=128&&x<1152&&bx[3:0]>=4&&bx[3:0]<12;
  permit0<=enable&&picture_visible&&de&&draw_ready;opacity0<=opacity;
  color1<=(peak_on||yy[0]<536)?highlight(hue0):hue0;
  alpha1<=permit0&&(bar_on||peak_on)?opacity0:4'd0;
  rgb_out<={blend(base1[23:16],color1[23:16],alpha1),
    blend(base1[15:8],color1[15:8],alpha1),blend(base1[7:0],color1[7:0],alpha1)};
  x_out<=xx[1];y_out<=yy[1];{de_out,hs_out,vs_out,picture_visible_out}<=control[1];
 end
endmodule
'''
p.write_text(s,encoding='utf8')
# Preserve old TB; v105 checks geometry + all64 derived RAM entries independently.
p=r/'02_tests/audio_visual/tb_v105_overlay.sv';s=(r/'02_tests/audio_visual/tb_v099_overlay.sv').read_text(encoding='utf8').replace('v099','v105')
s=s.replace('reg[23:0]color_table[0:17];','reg[23:0]color_table[0:15];')
s=s.replace('integer a,b,i,qi,n=0,checks=0,paint=0,untouched=0,band,step,alpha,fd=0,captured=0;','integer a,b,i,qi,n=0,checks=0,paint=0,untouched=0,band,step,alpha,fd=0,captured=0,h,p,frac,nb,slot,memchecks=0;')
a=s.index('  if(en&&pv&&de&&x>=128');b=s.index('  if(e!=rgb)',a)
s=s[:a]+'''  if(en&&pv&&de&&d.draw_ready&&x>=128&&x<1152&&(x-128)%16>=4&&(x-128)%16<12)begin
   band=(x-128)/64;frac=((x-128)/16)%4;nb=band<15?band+1:15;slot=(x-128)%16;
   h=((4-frac)*d.height[band]+frac*d.height[nb]+2)/4;
   p=((4-frac)*d.peak[band]+frac*d.peak[nb]+2)/4;
   bar=h!=0&&y<608&&y>=608-h&&((slot!=4&&slot!=11)||(y>608-h&&y<607));
   pk=slot>=5&&slot<11&&p!=0&&y>=606-p&&y<608-p;
   if(bar||pk)begin
    fg=color_table[band];
    if(pk||y<536)fg={8'((3*fg[23:16]+255)/4),8'((3*fg[15:8]+255)/4),8'((3*fg[7:0]+255)/4)};
    alpha=d.opacity;e=gold_blend(rgb,fg,alpha);
   end
  end
'''+s[b:]
s=s.replace('task frame;begin x=0;y=0;de=1;tick(1);x=1;tick(66);end endtask','''task verify_display;integer z,bb,nn,ff,hh,pp;begin
 for(z=0;z<64;z++)begin
  bb=z/4;nn=bb<15?bb+1:15;ff=z%4;
  hh=((4-ff)*d.height[bb]+ff*d.height[nn]+2)/4;
  pp=((4-ff)*d.peak[bb]+ff*d.peak[nn]+2)/4;
  if(d.display_memory[z]!=={8'(pp),8'(hh)})$fatal(1,"interpolation RAM cell%0d got%h h%0d p%0d",z,d.display_memory[z],hh,pp);
  memchecks++;
 end
 if(!d.draw_ready||d.updating||d.preparing)$fatal(1,"display preprocessing deadline");
end endtask
 task frame;begin x=0;y=0;de=1;tick(1);x=1;tick(258);verify_display;end endtask''')
a=s.index("  color_table[0]=");b=s.index('  tick(3);',a)
colors=['f15d6e','f77b54','f39f36','d5b32b','99bf3c','56bf65','2dbb91','25b6b8','27a7d8','438de8','6374ed','8b65e6','a661d8','bf62c8','d763ad','e36891']
s=s[:a]+''.join(f"  color_table[{i}]=24'h{v};\n" for i,v in enumerate(colors))+s[b:]
s=s.replace("rgb={8'(a*255/1279),8'((a/80+b/45)%2?40:64),8'(b*160/719+60)};","rgb=24'hffffff;")
s=s.replace('tick(66);if(d.opacity','tick(258);verify_display;if(d.opacity')
s=s.replace('alpha/16 oracle/3cycle-sync/all16channels','alpha/64 interpolated display bars/3cycle-sync/all16 measured channels')
s=s.replace('$finish;\n end','''$display("PASS v105 all64 interpolation RAM checks=%0d / fixed256-clock preprocessing deadline / no new spectral bands claimed",memchecks);$finish;
 end''')
p.write_text(s,encoding='utf8')
# Fresh versioned runners; deliberately retain actual tb_v103_top.sv entry.
for name in ['tests','native','synth','physical','bitgen']:
 p=r/f'02_tests/audio_visual/run_v105_{name}.py';s=(r/f'02_tests/audio_visual/run_v104_{name}.py').read_text(encoding='utf8').replace('v104','v105').replace('V104','V105')
 s=s.replace('v105_chinese_two_column_ui_720p','v105_center_glass_art_spectrum_720p')
 s=s.replace("('overlay','tb_v099_overlay',[t/'tb_v099_overlay.sv'","('overlay','tb_v105_overlay',[t/'tb_v105_overlay.sv'")
 s=s.replace('fresh Chinese two-column UI/font/pixel/gesture tests','fresh centered rounded translucent Chinese UI/font/pixel/gesture and64-interpolated-rainbow spectrum tests')
 p.write_text(s,encoding='utf8')
for rel in ['02_tests/ui/check_v104_rom_init.py','08_tools/run_acceptance.py','01_project/build_audio_visual_synth.tcl','01_project/build_audio_visual_physical_check.tcl']:
 p=r/rel;s=p.read_text(encoding='utf8').replace('v104','v105').replace('V104','V105').replace('v105_chinese_two_column_ui_720p','v105_center_glass_art_spectrum_720p')
 target=r/rel.replace('check_v104','check_v105');target.write_text(s,encoding='utf8')
p=r/'01_project/boards/idx_audio_visual_top.v';s=p.read_text(encoding='utf8').replace('v104','v105').replace('V104','V105');p.write_text(s,encoding='utf8')
print('v105 spectrum/verification/build entries written; ROM checked as before; top TB intentionally retained tb_v103_top.sv')
