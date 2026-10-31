`timescale 1ns/1ps
// Reuses v026 read-only SD/FAT/BMP protocol. No reference-image CRC gate:
// any supported image is accepted, each sector must pass SD CRC16.
module tf_bmp_source #(
 parameter RUNTIME_NAME=0, HALF_DIV=124, DATA_HALF_DIV=HALF_DIV, POWER_WAIT_CYCLES=4950000, INIT_GAP_CYCLES=49500,
 DYNAMIC_SIZE=0,MAX_WIDTH=1280,MAX_HEIGHT=1024
)(input wire [7:0] file_letter, input wire clk,rst_n,miso,output wire cs_n,sck,mosi,
 output wire pixel_valid,input wire pixel_ready,
 output wire [23:0] pixel_rgb,output wire [15:0] pixel_x,pixel_y,
 output wire done,ok,output wire [7:0] error_code,
 output wire sd_init,mounted,bmp_ok,
 output wire [31:0] pixel_count,payload_crc32,
 output wire [15:0] source_width,source_height,output wire [31:0] row_stride,output wire source_top_down);
 wire ready,read_done,dv;wire [3:0] se,pe,xe;
 wire [8:0] di;wire [7:0] db;
 wire pd,xd,xok,pr,xr,top;wire [31:0] pl,xl,fs,off,cl,base,fat,mx;
 wire [7:0] spc;wire [3:0] sh;
 wire use_pixels=pd&&bmp_ok;
 sd_spi_reader #(.HALF_DIV(HALF_DIV),.DATA_HALF_DIV(DATA_HALF_DIV),.POWER_WAIT_CYCLES(POWER_WAIT_CYCLES),
 .INIT_GAP_CYCLES(INIT_GAP_CYCLES)) reader(
 .clk(clk),.rst_n(rst_n),.miso(miso),.sck(sck),.mosi(mosi),.cs_n(cs_n),
 .read_req(use_pixels?xr:pr),.read_lba(use_pixels?xl:pl),.ready(ready),
 .init_done(sd_init),.read_done(read_done),.signature_ok(),.error_code(se),
 .high_capacity(),.data_crc(),.received_crc(),.data_sum(),.last_r1(),.last_cmd(),
 .data_valid(dv),.data_index(di),.data_byte(db));
 fat32_bmp_probe #(.RUNTIME_NAME(RUNTIME_NAME),.DYNAMIC_SIZE(DYNAMIC_SIZE),.MAX_WIDTH(MAX_WIDTH),.MAX_HEIGHT(MAX_HEIGHT)) probe(.file_letter(file_letter),.clk(clk),.rst_n(rst_n),.sd_ready(ready),.sd_read_done(read_done),
 .sd_error(se),.data_valid(dv),.data_index(di),.data_byte(db),
 .read_req(pr),.read_lba(pl),.mounted(mounted),.file_found(),.bmp_ok(bmp_ok),
 .done(pd),.top_down(top),.error_code(pe),.file_size(fs),.pixel_offset(off),.file_cluster(cl),.sectors_scanned(),
 .data_base(base),.fat_base(fat),.cluster_max(mx),.mounted_spc(spc),.mounted_shift(sh),
 .source_width(source_width),.source_height(source_height),.row_stride(row_stride));
 bmp_pixel_stream #(.DYNAMIC_SIZE(DYNAMIC_SIZE),.MAX_WIDTH(MAX_WIDTH),.MAX_HEIGHT(MAX_HEIGHT)) pixels(.clk(clk),.rst_n(rst_n),.start(use_pixels),
 .file_size(fs),.pixel_offset(off),.file_cluster(cl),.data_base(base),.fat_base(fat),.cluster_max(mx),
 .mounted_spc(spc),.mounted_shift(sh),.top_down(top),.source_width(source_width),.source_height(source_height),
 .sd_ready(ready),.sd_read_done(read_done),.sd_error(se),.data_valid(dv),.data_index(di),.data_byte(db),
 .read_req(xr),.read_lba(xl),.pixel_valid(pixel_valid),.pixel_ready(pixel_ready),
 .pixel_rgb(pixel_rgb),.pixel_x(pixel_x),.pixel_y(pixel_y),
 .busy(),.done(xd),.ok(xok),.error_code(xe),.pixel_count(pixel_count),.payload_crc32(payload_crc32));
 assign error_code=se!=0?{4'h1,se}:pe!=0?{4'h2,pe}:xe!=0?{4'h3,xe}:8'h00;
 assign done=(error_code!=0)||xd;
 assign ok=xd&&xok&&(error_code==0);
 assign source_top_down=top;
endmodule
