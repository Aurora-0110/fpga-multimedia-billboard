`timescale 1ns/1ps
module bmp_scale_bridge #(
 parameter OUT_WIDTH=1280,OUT_HEIGHT=720,MAX_WIDTH=1280,MAX_HEIGHT=1024
)(
 input wire clk,rst_n,metadata_valid,
 input wire [15:0] source_width,source_height,input wire top_down,
 input wire source_valid,output wire source_ready,input wire [23:0] source_rgb,
 input wire source_done,source_ok,input wire [7:0] source_error,
 output wire pixel_valid,input wire pixel_ready,
 output wire [23:0] pixel_rgb,output wire [15:0] pixel_x,pixel_y,
 output reg done,ok,output reg [7:0] error_code
);
 reg started;
 wire scaler_done,scaler_error,scaler_valid,scaler_ready;
 wire [3:0] scaler_error_code;
 wire healthy=!done && error_code==0 && source_error==0 && !(source_done&&!source_ok);
 wire launch=metadata_valid && !started && healthy;
 bilinear_stream_scaler #(.OUT_WIDTH(OUT_WIDTH),.OUT_HEIGHT(OUT_HEIGHT),
 .MAX_WIDTH(MAX_WIDTH),.MAX_HEIGHT(MAX_HEIGHT)) scaler(
 .clk(clk),.rst_n(rst_n),.start(launch),.src_width(source_width),.src_height(source_height),.top_down(top_down),
 .busy(),.done(scaler_done),.error(scaler_error),.error_code(scaler_error_code),
 .in_valid(source_valid&&healthy),.in_ready(scaler_ready),.in_rgb(source_rgb),
 .out_valid(scaler_valid),.out_ready(pixel_ready&&healthy),.out_rgb(pixel_rgb),.out_x(pixel_x),.out_y(pixel_y));
 assign source_ready=scaler_ready&&healthy;
 assign pixel_valid=scaler_valid&&healthy;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin started<=0;done<=0;ok<=0;error_code<=0;end
 else if(!done)begin
  if(source_error!=0)begin error_code<=source_error;done<=1;ok<=0;end
  else if(source_done&&!source_ok)begin error_code<=8'h40;done<=1;ok<=0;end
  else if(scaler_error)begin error_code<={4'h4,scaler_error_code};done<=1;ok<=0;end
  else begin
   if(launch)started<=1;
   if(started&&source_done&&source_ok&&scaler_done)begin done<=1;ok<=1;end
  end
 end
endmodule
