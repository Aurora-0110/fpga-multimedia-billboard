`timescale 1ns/1ps
// RGB888 bilinear kernel, Q0.8 fractions, round-nearest once after BOTH axes.
// Four pipeline stages; one sample/cycle unless downstream stalls. Stalling
// freezes data AND valid bits globally. Convex interpolation never clips.
// Input four neighbours must ALREADY be edge-clamped by the coordinate unit.
module bilinear_rgb888 # (parameter TAG_BITS=32)(
 input wire clk,rst_n,in_valid,output wire in_ready,
 input wire [23:0] p00,p10,p01,p11,input wire [7:0] fx,fy,
 input wire [TAG_BITS-1:0] in_tag,
 output wire out_valid,input wire out_ready,
 output reg [23:0] out_rgb,output reg [TAG_BITS-1:0] out_tag);
 reg [3:0] v;
 wire advance=!v[3]||out_ready;
 assign in_ready=advance;assign out_valid=v[3];
 reg [7:0] fx1,fy1,fy2;
 reg [TAG_BITS-1:0] t1,t2,t3;
 reg signed [8:0] d0[0:2],d1[0:2];
 reg [7:0] b0[0:2],b1[0:2];
 reg [15:0] h0[0:2],h1[0:2];
 reg [23:0] acc[0:2];
 integer c;
 // Explicit operand widths prevent an unsigned pixel subtraction or a narrow
 // product from silently wrapping on descending colour gradients.
 function [15:0] horizontal;
  input [7:0] b;input signed [8:0] diff;input [7:0] f;
  reg signed [18:0] sum;
  begin sum=$signed({1'b0,b,8'b0})+diff*$signed({1'b0,f});horizontal=sum[15:0];end
 endfunction
 function [23:0] vertical;
  input [15:0] a,b;input [7:0] f;
  reg signed [16:0] diff;reg signed [25:0] sum;
  begin diff=$signed({1'b0,b})-$signed({1'b0,a});
   sum=$signed({1'b0,a,8'b0})+diff*$signed({1'b0,f});vertical=sum[23:0];end
 endfunction
 function [7:0] rounded;
  input [23:0] a;reg [24:0] z;
  begin z={1'b0,a}+25'd32768;rounded=z[23:16];end
 endfunction
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  v<=0;fx1<=0;fy1<=0;fy2<=0;t1<=0;t2<=0;t3<=0;out_tag<=0;out_rgb<=0;
  for(c=0;c<3;c=c+1)begin d0[c]<=0;d1[c]<=0;b0[c]<=0;b1[c]<=0;h0[c]<=0;h1[c]<=0;acc[c]<=0;end
 end else if(advance)begin
  v<={v[2:0],in_valid};fx1<=fx;fy1<=fy;fy2<=fy1;
  t1<=in_tag;t2<=t1;t3<=t2;out_tag<=t3;
  for(c=0;c<3;c=c+1)begin
   d0[c]<=$signed({1'b0,p10[c*8+:8]})-$signed({1'b0,p00[c*8+:8]});
   d1[c]<=$signed({1'b0,p11[c*8+:8]})-$signed({1'b0,p01[c*8+:8]});
   b0[c]<=p00[c*8+:8];b1[c]<=p01[c*8+:8];
   h0[c]<=horizontal(b0[c],d0[c],fx1);h1[c]<=horizontal(b1[c],d1[c],fx1);
   acc[c]<=vertical(h0[c],h1[c],fy2);out_rgb[c*8+:8]<=rounded(acc[c]);
  end
 end
endmodule
