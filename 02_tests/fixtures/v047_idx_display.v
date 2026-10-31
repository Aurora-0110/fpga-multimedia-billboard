`timescale 1ns/1ps
// Centered window only consumes SDRAM bytes; entire HDMI DE remains 1280x720.
// FIFO read data is registered, matched to one-cycle delayed coordinates.
module idx_display #(parameter PREFILL=3072)(
 input wire clk,rst_n,enable,frame_start,de,hs,vs,window,
 input wire empty,input wire [12:0] used,input wire [7:0] data,
 output wire pop,output wire [23:0] rgb,
 output reg de_d,hs_d,vs_d,output reg running,fault);
 wire start_now=frame_start&&enable&&!fault&&used>=PREFILL;
 wire active=enable&&!fault&&(running||start_now);
 reg valid_d;
 assign pop=rst_n&&active&&window&&!empty;
 assign rgb=valid_d?{data[7:5],data[7:5],data[7:6],data[4:2],data[4:2],data[4:3],data[1:0],data[1:0],data[1:0],data[1:0]}:24'h0;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin de_d<=0;hs_d<=1;vs_d<=1;running<=0;fault<=0;valid_d<=0;end
 else begin
 de_d<=de;hs_d<=hs;vs_d<=vs;valid_d<=pop;
 if(start_now)running<=1;
 if(active&&window&&empty)begin fault<=1;running<=0;end
 if(!enable)running<=0;
 end
endmodule
