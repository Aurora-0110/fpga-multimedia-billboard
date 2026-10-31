`timescale 1ns/1ps
// Synthesis-only harness, not a functional board design or an input protocol.
// Narrow serial configuration/data and selected output bytes preserve all
// dynamic scaler paths while keeping the diagnostic top below pad capacity.
module scaler_synth_top(
 input wire clk,rst_n,start,cfg_shift_enable,pixel_shift_enable,in_valid,out_ready,
 input wire [7:0] data_in,input wire [3:0] select,
 output wire in_ready,out_valid,output reg [7:0] data_out
);
 reg [32:0] cfg;reg [23:0] rgb;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin cfg<=0;rgb<=0;end
 else begin
  if(cfg_shift_enable)cfg<={cfg[24:0],data_in};
  if(pixel_shift_enable)rgb<={rgb[15:0],data_in};
 end
 wire busy,done,error;wire [3:0] error_code;
 wire [23:0] out_rgb;wire [15:0] out_x,out_y;
 bilinear_stream_scaler dut(.clk(clk),.rst_n(rst_n),.start(start),
  .src_width(cfg[15:0]),.src_height(cfg[31:16]),.top_down(cfg[32]),
  .busy(busy),.done(done),.error(error),.error_code(error_code),
  .in_valid(in_valid),.in_ready(in_ready),.in_rgb(rgb),
  .out_valid(out_valid),.out_ready(out_ready),.out_rgb(out_rgb),.out_x(out_x),.out_y(out_y));
 always @*case(select)
  0:data_out=out_rgb[7:0];1:data_out=out_rgb[15:8];2:data_out=out_rgb[23:16];
  3:data_out=out_x[7:0];4:data_out=out_x[15:8];
  5:data_out=out_y[7:0];6:data_out=out_y[15:8];
  default:data_out={1'b0,error_code,error,done,busy};
 endcase
endmodule
