`timescale 1ns/1ps
// Four registered stages; one pixel per clock. Q2 contrast=2..6 (50..150%).
// Per-channel result = clamp(floor((input-128)*gain/4)+128+brightness).
// Only selected framebuffer pixels are changed; border/background are bypassed.
// Pixel coordinates, syncs, image tag and visibility have the SAME four clocks.
module picture_adjust(
 input wire clk,rst_n,input wire [23:0] rgb,
 input wire [11:0] x,y,input wire de,hs,vs,picture_visible,apply_pixel,
 input wire [1:0] image_index,input wire signed [7:0] brightness,input wire [2:0] contrast_q2,
 output reg [23:0] rgb_out,output reg [11:0] x_out,y_out,
 output reg de_out,hs_out,vs_out,picture_visible_out,output reg [1:0] image_index_out);
 reg signed [8:0] r0,g0,b0;
 reg signed [12:0] r1,g1,b1;
 reg signed [12:0] r2,g2,b2;
 reg signed [7:0] bright0,bright1;
 reg [2:0] gain0;
 reg [23:0] raw[0:2];reg [11:0] xx[0:2],yy[0:2];
 reg [3:0] ctl[0:2];reg [1:0] tag[0:2];reg apply[0:2];integer i;
 function [7:0] clip;input signed [12:0] v;begin
 if(v<0)clip=0;else if(v>255)clip=255;else clip=v[7:0];end endfunction
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  r0<=0;g0<=0;b0<=0;r1<=0;g1<=0;b1<=0;r2<=0;g2<=0;b2<=0;
  bright0<=0;bright1<=0;gain0<=4;
  for(i=0;i<3;i=i+1)begin raw[i]<=0;xx[i]<=0;yy[i]<=0;ctl[i]<=4'b0110;tag[i]<=0;apply[i]<=0;end
  rgb_out<=0;x_out<=0;y_out<=0;de_out<=0;hs_out<=1;vs_out<=1;picture_visible_out<=0;image_index_out<=0;
 end else begin
  r0<=$signed({1'b0,rgb[23:16]})-9'sd128;
  g0<=$signed({1'b0,rgb[15:8]})-9'sd128;
  b0<=$signed({1'b0,rgb[7:0]})-9'sd128;
  gain0<=contrast_q2;bright0<=brightness;
  r1<=r0*$signed({1'b0,gain0});g1<=g0*$signed({1'b0,gain0});b1<=b0*$signed({1'b0,gain0});bright1<=bright0;
  r2<=(r1>>>2)+13'sd128+bright1;g2<=(g1>>>2)+13'sd128+bright1;b2<=(b1>>>2)+13'sd128+bright1;
  raw[0]<=rgb;xx[0]<=x;yy[0]<=y;ctl[0]<={de,hs,vs,picture_visible};tag[0]<=image_index;apply[0]<=apply_pixel;
  for(i=1;i<3;i=i+1)begin raw[i]<=raw[i-1];xx[i]<=xx[i-1];yy[i]<=yy[i-1];ctl[i]<=ctl[i-1];tag[i]<=tag[i-1];apply[i]<=apply[i-1];end
  rgb_out<=apply[2]?{clip(r2),clip(g2),clip(b2)}:raw[2];
  x_out<=xx[2];y_out<=yy[2];{de_out,hs_out,vs_out,picture_visible_out}<=ctl[2];image_index_out<=tag[2];
 end
endmodule
