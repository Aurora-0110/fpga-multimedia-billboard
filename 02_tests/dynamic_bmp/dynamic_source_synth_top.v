`timescale 1ns/1ps
module dynamic_source_synth_top(
 input wire clk,rst_n,miso,req_ack,
 input wire [7:0] file_letter,input wire [4:0] select,
 output wire cs_n,sck,mosi,req_valid,done,
 output reg [7:0] data_out
);
 wire pixel_valid,pixel_ready,source_done,source_ok;
 wire [23:0] pixel_rgb;
 wire [15:0] pixel_x,pixel_y,source_width,source_height;
 wire [7:0] source_error,error_code;
 wire [18:0] req_addr;
 wire [127:0] req_data;
 wire [31:0] row_stride,source_count,crc;
 wire sd_init,mounted,bmp_ok;
 tf_bmp_scaled_source source(
 .clk(clk),.rst_n(rst_n),.file_letter(file_letter),.miso(miso),.cs_n(cs_n),.sck(sck),.mosi(mosi),
 .pixel_valid(pixel_valid),.pixel_ready(pixel_ready),.pixel_rgb(pixel_rgb),.pixel_x(pixel_x),.pixel_y(pixel_y),
 .done(source_done),.ok(source_ok),.error_code(source_error),.sd_init(sd_init),.mounted(mounted),.bmp_ok(bmp_ok),
 .source_width(source_width),.source_height(source_height),.row_stride(row_stride),.source_pixel_count(source_count),.payload_crc32(crc));
 bmp_pixel_packer #(.WIDTH(1280),.HEIGHT(720)) packer(
 .clk(clk),.rst_n(rst_n),.enable(1'b1),.pixel_valid(pixel_valid),.pixel_ready(pixel_ready),
 .pixel_rgb(pixel_rgb),.pixel_x(pixel_x),.pixel_y(pixel_y),.source_done(source_done),.source_ok(source_ok),.source_error(source_error),
 .req_valid(req_valid),.req_addr(req_addr),.req_data(req_data),.req_ack(req_ack),.done(done),.error_code(error_code),.pixel_count(),.burst_count());
 always @*begin
  if(select<16)data_out=req_data[select*8+:8];
  else case(select)
   16:data_out=source_width[7:0];17:data_out=source_width[15:8];
   18:data_out=source_height[7:0];19:data_out=source_height[15:8];
   20:data_out=row_stride[7:0];21:data_out=row_stride[15:8];
   22:data_out=req_addr[7:0];23:data_out=req_addr[15:8];24:data_out={5'd0,req_addr[18:16]};
   25:data_out=error_code;26:data_out=source_count[7:0];27:data_out=crc[7:0];
   default:data_out={3'd0,bmp_ok,mounted,sd_init,source_ok,source_done};
  endcase
 end
endmodule
