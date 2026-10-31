`timescale 1ns/1ps
// Registered-output async FIFO -> local 2-pair queue -> one pixel each pixel
// clock. Pair metadata is latched with the SAME emitted pixel, including lane1.
module idx_pair_display #(parameter PREFILL=3072)(
 input wire clk,rst_n,timing_rst_n,enable,frame_start,de,hs,vs,window,
 input wire empty,input wire [12:0] used,input wire [23:0] data,
 output wire pop,output wire [23:0] rgb,
 output reg [1:0] displayed_index,output reg [5:0] displayed_step,
 output reg de_d,hs_d,vs_d,output reg running,fault,picture_visible
);
 reg content_valid,pending,lane,valid_d;reg [1:0] count;
 reg [23:0] pair0,pair1;reg [7:0] color_d;
 wire start_now=frame_start&&enable&&!fault&&used>=PREFILL&&count!=0;
 wire active=enable&&!fault&&(running||start_now);
 wire consume=content_valid&&active&&window&&(count!=0);
 wire retire=consume&&lane;
 wire arrive=pending;
 // One pending registered FIFO read counts as a reserved local slot.
 assign pop=content_valid&&enable&&!fault&&!empty&&({1'b0,count}+pending<3'd2);
 assign rgb=valid_d?{color_d[7:5],color_d[7:5],color_d[7:6],color_d[4:2],color_d[4:2],color_d[4:3],color_d[1:0],color_d[1:0],color_d[1:0],color_d[1:0]}:24'd0;
 always @(posedge clk or negedge timing_rst_n)
 if(!timing_rst_n)begin de_d<=0;hs_d<=1;vs_d<=1;end
 else begin de_d<=de;hs_d<=hs;vs_d<=vs;end
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  content_valid<=0;pending<=0;lane<=0;valid_d<=0;count<=0;pair0<=0;pair1<=0;color_d<=0;
  displayed_index<=0;displayed_step<=0;running<=0;fault<=0;picture_visible<=0;
 end else begin
  content_valid<=1;pending<=pop;valid_d<=consume;
  case({arrive,retire})
   2'b10:begin
    if(count==0)pair0<=data;else pair1<=data;
    count<=count+1'b1;
   end
   2'b01:begin pair0<=pair1;count<=count-1'b1;end
   2'b11:begin
    if(count==1)pair0<=data;else begin pair0<=pair1;pair1<=data;end
   end
   default:begin end
  endcase
  if(consume)begin
   color_d<=lane?pair0[15:8]:pair0[7:0];lane<=~lane;
   displayed_index<=pair0[23:22];displayed_step<=pair0[21:16];picture_visible<=1;
  end
  if(start_now)running<=1;
  if(!enable||fault||(active&&window&&count==0))picture_visible<=0;
  if(active&&window&&count==0)begin fault<=1;running<=0;end
  if(!enable)running<=0;
 end
endmodule
