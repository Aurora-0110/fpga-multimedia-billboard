`timescale 1ns/1ps
module tf_bmp_scaled_source #(
 parameter RUNTIME_NAME=1,HALF_DIV=124,DATA_HALF_DIV=HALF_DIV,
 POWER_WAIT_CYCLES=4950000,INIT_GAP_CYCLES=49500,
 OUT_WIDTH=1280,OUT_HEIGHT=720,MAX_WIDTH=1280,MAX_HEIGHT=1024
)(
 input wire clk,rst_n,input wire [7:0] file_letter,input wire miso,
 output wire cs_n,sck,mosi,
 output wire pixel_valid,input wire pixel_ready,
 output wire [23:0] pixel_rgb,output wire [15:0] pixel_x,pixel_y,
 output wire done,ok,output wire [7:0] error_code,
 output wire sd_init,mounted,bmp_ok,
 output wire [15:0] source_width,source_height,output wire [31:0] row_stride,
 output wire [31:0] source_pixel_count,payload_crc32
);
 wire raw_valid,raw_ready,raw_done,raw_ok,top_down;
 wire [23:0] raw_rgb;
 wire [7:0] raw_error;
 tf_bmp_source #(.RUNTIME_NAME(RUNTIME_NAME),.HALF_DIV(HALF_DIV),.DATA_HALF_DIV(DATA_HALF_DIV),
 .POWER_WAIT_CYCLES(POWER_WAIT_CYCLES),.INIT_GAP_CYCLES(INIT_GAP_CYCLES),
 .DYNAMIC_SIZE(1),.MAX_WIDTH(MAX_WIDTH),.MAX_HEIGHT(MAX_HEIGHT)) source(
 .clk(clk),.rst_n(rst_n),.file_letter(file_letter),.miso(miso),.cs_n(cs_n),.sck(sck),.mosi(mosi),
 .pixel_valid(raw_valid),.pixel_ready(raw_ready),.pixel_rgb(raw_rgb),.pixel_x(),.pixel_y(),
 .done(raw_done),.ok(raw_ok),.error_code(raw_error),.sd_init(sd_init),.mounted(mounted),.bmp_ok(bmp_ok),
 .pixel_count(source_pixel_count),.payload_crc32(payload_crc32),
 .source_width(source_width),.source_height(source_height),.row_stride(row_stride),.source_top_down(top_down));
 bmp_scale_bridge #(.OUT_WIDTH(OUT_WIDTH),.OUT_HEIGHT(OUT_HEIGHT),.MAX_WIDTH(MAX_WIDTH),.MAX_HEIGHT(MAX_HEIGHT)) bridge(
 .clk(clk),.rst_n(rst_n),.metadata_valid(bmp_ok),.source_width(source_width),.source_height(source_height),.top_down(top_down),
 .source_valid(raw_valid),.source_ready(raw_ready),.source_rgb(raw_rgb),.source_done(raw_done),.source_ok(raw_ok),.source_error(raw_error),
 .pixel_valid(pixel_valid),.pixel_ready(pixel_ready),.pixel_rgb(pixel_rgb),.pixel_x(pixel_x),.pixel_y(pixel_y),
 .done(done),.ok(ok),.error_code(error_code));
endmodule
