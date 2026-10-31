`timescale 1ns/1ps
// RGB888 -> RGB332, little-endian 16-byte native SDRAM bursts.
// req_ack is a REGISTERED ACCEPTANCE indication, NOT combinational ready.
// Hold request/address/data until ack, including the final burst.
module v119_bmp_pixel_packer_reference #(parameter WIDTH=640,HEIGHT=480,DITHER_ENABLE=0)(
 input wire clk,rst_n,enable,pixel_valid,output wire pixel_ready,
 input wire [23:0] pixel_rgb,input wire [15:0] pixel_x,pixel_y,
 input wire source_done,source_ok,input wire [7:0] source_error,
 output reg req_valid,output reg [18:0] req_addr,output reg [127:0] req_data,
 input wire req_ack,output reg done,output reg [7:0] error_code,
 output reg [31:0] pixel_count,burst_count);
 localparam PIXELS=WIDTH*HEIGHT,BURSTS=PIXELS/16;
 reg [127:0] assemble;
 reg [3:0] lane;
 reg [15:0] expect_x,expect_y;
 reg direction_down,started;
 // Optional spatial (never frame-varying) 4x4 ordered quantization. The
 // Bayer phase uses LOGICAL output coordinates, so top/down BMP ordering and
 // stalls cannot move the pattern. Only the loader write side changes; the
 // SDRAM framebuffer and HDMI reconstruction remain RGB332.
 wire [3:0] bayer={pixel_x[0]^pixel_y[0],pixel_y[0],
                   pixel_x[1]^pixel_y[1],pixel_y[1]};
 wire [7:0] threshold={bayer,4'b1000};
 function [2:0] quant3;
  input [7:0] value,th;
  reg [10:0] n,q;
  begin
   // value*7 + midpoint threshold; no multiplier/DSP or variable divider.
   n=({3'b0,value}<<3)-{3'b0,value}+{3'b0,th};
   // Exact floor(n/255) for 0<=n<=2033 (exhaustively checked by TB).
   q=n+11'd1+(n>>8);quant3=q[10:8];
  end
 endfunction
 function [1:0] quant2;
  input [7:0] value,th;
  reg [9:0] n,q;
  begin
   n=({2'b0,value}<<1)+{2'b0,value}+{2'b0,th};
   q=n+10'd1+(n>>8);quant2=q[9:8];
  end
 endfunction
 // Separate function nets avoid an Icarus 13 expression-synthesis assertion
 // for concatenated function calls inside a constant conditional expression.
 // This is combinationally identical and preserves the registered ack path.
 wire [2:0] qr=quant3(pixel_rgb[23:16],threshold);
 wire [2:0] qg=quant3(pixel_rgb[15:8],threshold);
 wire [1:0] qb=quant2(pixel_rgb[7:0],threshold);
 wire [7:0] indexed;
 generate if(DITHER_ENABLE)begin: ordered_quantization
  assign indexed={qr,qg,qb};
 end else begin: truncate_quantization
  assign indexed={pixel_rgb[23:21],pixel_rgb[15:13],pixel_rgb[7:6]};
 end endgenerate
 assign pixel_ready=enable&&!req_valid&&!done&&error_code==0&&pixel_count<PIXELS;
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin
  req_valid<=0;req_addr<=0;req_data<=0;done<=0;error_code<=0;
  pixel_count<=0;burst_count<=0;assemble<=0;lane<=0;
  expect_x<=0;expect_y<=0;direction_down<=0;started<=0;
 end else begin
  if(req_valid&&req_ack)begin req_valid<=0;burst_count<=burst_count+1'b1;end
  if(!done&&error_code==0)begin
   if(source_error!=0)begin error_code<=source_error;req_valid<=0;end
   else if(source_done&&!source_ok)begin error_code<=8'h41;req_valid<=0;end
   else if(source_done&&pixel_count!=PIXELS)begin error_code<=8'h42;req_valid<=0;end
   else if(pixel_valid&&pixel_ready)begin
    if(pixel_x>=WIDTH||pixel_y>=HEIGHT||pixel_x!=expect_x||
       (!started&&pixel_y!=0&&pixel_y!=HEIGHT-1)||
       (started&&pixel_y!=expect_y))begin error_code<=8'h43;req_valid<=0;end
    else begin
     started<=1;
     if(!started)direction_down<=pixel_y==0;
     if(pixel_x==WIDTH-1)begin
      expect_x<=0;expect_y<=direction_down?pixel_y+1'b1:pixel_y-1'b1;
     end else begin expect_x<=pixel_x+1'b1;expect_y<=pixel_y;end
     assemble<={indexed,assemble[127:8]};pixel_count<=pixel_count+1'b1;
     if(lane==15)begin
      req_valid<=1;req_addr<=pixel_y*(WIDTH/16)+(pixel_x>>4);
      req_data<={indexed,assemble[127:8]};lane<=0;
     end else lane<=lane+1'b1;
    end
   end
   if(source_done&&source_ok&&source_error==0&&pixel_count==PIXELS&&
      burst_count==BURSTS&&!req_valid&&lane==0)done<=1;
  end
 end end
endmodule
