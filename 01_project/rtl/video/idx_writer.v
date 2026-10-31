`timescale 1ns/1ps
// Diagnostic RGB332, 16 consecutive pixels per native 128-bit burst.
// req_ready is registered ACCEPTANCE acknowledgement, not ready/valid.
module idx_writer #(parameter W=640,H=480)(
 input wire clk,rst_n,enable,req_ready,
 output wire req_valid,output wire [18:0] addr,
 output reg [127:0] data,output reg done);
 reg [18:0] ba; reg [9:0] xb,y; integer i;
 function [7:0] pattern;
 input integer x,yy;
 begin
 if(x==0 || x==W-1 || yy==0 || yy==H-1 || (x%64)==0 || (yy%64)==0) pattern=8'hff;
 else case(x/(W/8))
 0:pattern=8'hff;1:pattern=8'hfc;2:pattern=8'h1f;3:pattern=8'h1c;
 4:pattern=8'he3;5:pattern=8'he0;6:pattern=8'h03;default:pattern=0;
 endcase
 end endfunction
 assign req_valid=enable&&!done;
 assign addr=ba;
 always @* begin
 data=0;
 for(i=0;i<16;i=i+1) data[i*8+:8]=pattern(xb*16+i,y);
 end
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin ba<=0;xb<=0;y<=0;done<=0;end
 else if(req_ready&&!done)begin
  if(ba==W*H/16-1)done<=1;
  else begin ba<=ba+1'b1;
   if(xb==W/16-1)begin xb<=0;y<=y+1'b1;end else xb<=xb+1'b1;
  end
 end
endmodule
