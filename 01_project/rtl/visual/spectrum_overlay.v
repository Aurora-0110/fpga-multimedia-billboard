`timescale 1ns/1ps
// v105: 64 rainbow display bars interpolated from 16 REAL DFT bands.
// The 64 bars are not 64 independent measured frequencies.
// Frame-blank preprocessing + synchronous 64x16 BRAM, not a pixel multiplier.
// ONLY rounded thin bar/peak pixels are blended;
// no panel, text, axis or baseline. Gaps/hidden/zero-level pixels pass BIT EXACT.
// sound_active comes from actual HDMI-bound post-gain PCM, not DFT random data.
// Keep the v098 three-register RGB/coordinate/sync/visibility latency contract.
module spectrum_overlay #(
 parameter TRACK_RELEASE_FRAMES=8, ALPHA_MAX=12
)(input wire clk,rst_n,input wire[11:0]x,y,input wire[23:0]rgb,
 input wire de,hs,vs,picture_visible,enable,
 input wire[127:0]levels,input wire levels_valid,track_change,sound_active,
 output reg[11:0]x_out,y_out,output reg[23:0]rgb_out,
 output reg de_out,hs_out,vs_out,picture_visible_out);
 localparam FW=TRACK_RELEASE_FRAMES>1?$clog2(TRACK_RELEASE_FRAMES+1):1;
 reg[127:0]target,frame_target;reg source_ready,epoch_pending;
 reg[3:0]opacity;reg[FW-1:0]holdoff;
 reg[7:0]height[0:15],peak[0:15];integer i;
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
 end
 wire tick=de&&x==0&&y==0;
 // V124: preserve same-edge frame/epoch/opacity snapshots below, but start
 // the off-screen preprocessing engine through a registered one-cycle pulse.
 // This cuts the measured XY decode -> seven LUTs -> build_index CE path.
 // Video RGB/XY/sync stays THREE cycles. 257-clock rebuild is far before y464.
 reg tick_q;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)tick_q<=0;else tick_q<=tick;
 reg updating,frame_quiet,frame_track;reg[1:0]update_phase;reg[3:0]update_band;
 reg[7:0]h_q,p_q,goal_q,h_next_q,p_next_q;
 wire[7:0]up_delta=goal_q-h_q,down_delta=h_q-goal_q;
 wire[7:0]release_step=frame_track?8'd18:8'd6;
 wire[7:0]next_height=frame_quiet?(opacity==0?8'd0:(h_q>release_step?h_q-release_step:8'd0)):
  h_q<goal_q?(up_delta>24?h_q+8'd24:goal_q):
  h_q>goal_q?(down_delta>4?h_q-8'd4:goal_q):h_q;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  target<=0;frame_target<=0;source_ready<=0;epoch_pending<=0;opacity<=0;holdoff<=0;
  updating<=0;update_band<=0;update_phase<=0;frame_quiet<=1;frame_track<=0;
  h_q<=0;p_q<=0;goal_q<=0;h_next_q<=0;p_next_q<=0;
  preparing<=0;draw_ready<=0;build_phase<=0;build_index<=0;
  ha<=0;hb<=0;pa<=0;pb<=0;build_word<=0;
  for(i=0;i<16;i=i+1)begin height[i]<=0;peak[i]<=0;end
 end else begin
  if(track_change)epoch_pending<=1;
  if(track_change||!picture_visible||!sound_active)begin target<=0;source_ready<=0;end
  else if(levels_valid)begin target<=levels;source_ready<=1;end
  if(!picture_visible||!enable)begin opacity<=0;holdoff<=0;end
  if(tick)begin
   epoch_pending<=0;
   frame_target<=target;
   frame_track<=track_change||epoch_pending||holdoff!=0;
   frame_quiet<=!picture_visible||!enable||!sound_active||!source_ready||
    track_change||epoch_pending||holdoff!=0;
   if(!picture_visible||!enable)begin opacity<=0;holdoff<=0;end
   else if(track_change||epoch_pending)begin
    holdoff<=TRACK_RELEASE_FRAMES;opacity<=opacity>2?opacity-4'd2:4'd0;
   end else if(holdoff!=0)begin
    holdoff<=holdoff-1'b1;opacity<=opacity>2?opacity-4'd2:4'd0;
   end else if(sound_active&&source_ready)begin
    if(opacity<ALPHA_MAX)opacity<=opacity+1'b1;
   end else if(opacity!=0)opacity<=opacity-1'b1;
  end
  if(tick_q)begin
   updating<=1;update_band<=0;update_phase<=0;preparing<=0;draw_ready<=0;
  end else if(updating)begin
   // Four short stages: read, height/peak-decay, peak-compare, write.
   // One arithmetic lane, 64 clocks/frame; no video pixel latency change.
   // Breaks the measured h_q -> height arithmetic -> peak compare -> array
   // write path rather than waiving timing or adding multicycle exceptions.
   case(update_phase)
    0:begin
     h_q<=height[update_band];p_q<=peak[update_band];
     goal_q<=frame_target[update_band*8+:8]>144?8'd144:frame_target[update_band*8+:8];
     update_phase<=1;
    end
    1:begin
     h_next_q<=next_height;
     if(frame_quiet&&opacity==0)p_next_q<=0;
     else if(frame_quiet)p_next_q<=p_q>release_step?p_q-release_step:8'd0;
     else p_next_q<=p_q!=0?p_q-1'b1:8'd0;
     update_phase<=2;
    end
    2:begin
     if(!frame_quiet&&h_next_q>=p_q)p_next_q<=h_next_q;
     update_phase<=3;
    end
    3:begin
     height[update_band]<=h_next_q;peak[update_band]<=p_next_q;
     if(update_band==15)begin updating<=0;preparing<=1;build_index<=0;build_phase<=0;end
     else begin update_band<=update_band+1'b1;update_phase<=0;end
    end
   endcase
  end else if(preparing)begin
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
 // Independent fixed rainbow palette, no upstream RTL/assets copied.
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
 // Exact algebraic reduction: bg*(16-a)+fg*a = bg*16+(fg-bg)*a.
 // Signed 9x5 product lets TD use spare DSP lanes, instead of six LUT
 // shift/add products. Same Q4 floor rounding and THREE-clock pixel latency.
 function[7:0]blend;input[7:0]bg,fg;input[3:0]a;
  reg signed[8:0]diff;reg signed[13:0]product,sum;
  begin
   diff=$signed({1'b0,fg})-$signed({1'b0,bg});
   product=diff*$signed({1'b0,a});
   sum=$signed({2'b0,bg,4'b0})+product;blend=sum[11:4];
  end
 endfunction
 // Stage0: synchronous RAM read + source pixel/control/hue. Stage1: geometry
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
