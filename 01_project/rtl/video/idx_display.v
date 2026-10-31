`timescale 1ns/1ps
// Centered window only consumes SDRAM bytes; entire HDMI DE remains 1280x720.
// FIFO read data is registered, matched to one-cycle delayed coordinates.
module idx_display #(parameter PREFILL=3072)(
 input wire clk,rst_n,timing_rst_n,enable,frame_start,de,hs,vs,window,
 input wire empty,input wire [12:0] used,input wire [7:0] data,
 output wire pop,output wire [23:0] rgb,
 output reg de_d,hs_d,vs_d,output reg running,fault,output reg picture_visible);
 wire start_now=frame_start&&enable&&!fault&&used>=PREFILL;
 wire active=enable&&!fault&&(running||start_now);
 reg valid_d;
 // Do not feed the falling-edge reset-release directly into FIFO address/
 // gray-pointer combinational logic. Local positive-edge validity preserves
 // reset-time blocking, but grants the data path a full pixel clock period.
 reg content_valid;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)content_valid<=0;else content_valid<=1;
 assign pop=content_valid&&active&&window&&!empty;
 assign rgb=valid_d?{data[7:5],data[7:5],data[7:6],data[4:2],data[4:2],data[4:3],data[1:0],data[1:0],data[1:0],data[1:0]}:24'h0;
 // KEY0/content epoch must NEVER reset the outgoing HDMI control cadence.
 always @(posedge clk or negedge timing_rst_n)
 if(!timing_rst_n)begin de_d<=0;hs_d<=1;vs_d<=1;end
 else begin de_d<=de;hs_d<=hs;vs_d<=vs;end
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin running<=0;fault<=0;valid_d<=0;picture_visible<=0;end
 else begin
 valid_d<=pop;
 // Same edge as the first registered FIFO pixel. Hold across scan blanking;
 // never infer visible content merely from TF load_done or frame_ready.
 if(pop)picture_visible<=1;
 if(!enable || fault || (active&&window&&empty))picture_visible<=0;
 if(start_now)running<=1;
 if(active&&window&&empty)begin fault<=1;running<=0;end
 if(!enable)running<=0;
 end
endmodule
