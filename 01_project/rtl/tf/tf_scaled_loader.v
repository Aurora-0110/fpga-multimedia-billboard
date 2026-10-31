`timescale 1ns/1ps
// Load-side integration only. done waits for source validation, scaler drain,
// and REGISTERED acceptance of the last coordinate-addressed SDRAM burst.
module tf_scaled_loader #(
 parameter RUNTIME_NAME=1,HALF_DIV=124,DATA_HALF_DIV=HALF_DIV,
 POWER_WAIT_CYCLES=4950000,INIT_GAP_CYCLES=49500,
 OUT_WIDTH=1280,OUT_HEIGHT=720,MAX_WIDTH=1280,MAX_HEIGHT=1024,DITHER_ENABLE=0
)(
 input wire [7:0] file_letter,input wire clk,rst_n,enable,miso,
 output wire cs_n,sck,mosi,
 output wire req_valid,output wire [18:0] req_addr,output wire [127:0] req_data,
 input wire req_ack,output wire done,output wire [7:0] error_code,
 output wire sd_init,mounted,bmp_ok
);
 wire pv,pr,sdone,sok;wire [23:0] rgb;wire [15:0] x,y;wire [7:0] err;
 tf_bmp_scaled_source #(.RUNTIME_NAME(RUNTIME_NAME),.HALF_DIV(HALF_DIV),.DATA_HALF_DIV(DATA_HALF_DIV),
 .POWER_WAIT_CYCLES(POWER_WAIT_CYCLES),.INIT_GAP_CYCLES(INIT_GAP_CYCLES),
 .OUT_WIDTH(OUT_WIDTH),.OUT_HEIGHT(OUT_HEIGHT),.MAX_WIDTH(MAX_WIDTH),.MAX_HEIGHT(MAX_HEIGHT)) source(
 .clk(clk),.rst_n(rst_n),.file_letter(file_letter),.miso(miso),.cs_n(cs_n),.sck(sck),.mosi(mosi),
 .pixel_valid(pv),.pixel_ready(pr),.pixel_rgb(rgb),.pixel_x(x),.pixel_y(y),
 .done(sdone),.ok(sok),.error_code(err),.sd_init(sd_init),.mounted(mounted),.bmp_ok(bmp_ok),
 .source_width(),.source_height(),.row_stride(),.source_pixel_count(),.payload_crc32());
 bmp_pixel_packer #(.WIDTH(OUT_WIDTH),.HEIGHT(OUT_HEIGHT),.DITHER_ENABLE(DITHER_ENABLE)) packer(
 .clk(clk),.rst_n(rst_n),.enable(enable),.pixel_valid(pv),.pixel_ready(pr),
 .pixel_rgb(rgb),.pixel_x(x),.pixel_y(y),.source_done(sdone),.source_ok(sok),.source_error(err),
 .req_valid(req_valid),.req_addr(req_addr),.req_data(req_data),.req_ack(req_ack),
 .done(done),.error_code(error_code),.pixel_count(),.burst_count());
endmodule
