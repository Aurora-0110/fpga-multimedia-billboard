`timescale 1ns/1ps
// Reuses v026 read-only SD/FAT/BMP protocol. No reference-image CRC gate:
// any supported image is accepted, each sector must pass SD CRC16.
module tf_bus_bmp_source #(
 parameter RUNTIME_NAME=0, HALF_DIV=124, DATA_HALF_DIV=HALF_DIV, POWER_WAIT_CYCLES=4950000, INIT_GAP_CYCLES=49500,
 DYNAMIC_SIZE=0,MAX_WIDTH=1280,MAX_HEIGHT=1024
)(input wire [7:0] file_letter, input wire clk,rst_n,
 input wire ready,read_done,dv, input wire [3:0] se,input wire [8:0] di,input wire [7:0] db,
 output wire read_req,output wire [31:0] read_lba,
 output wire [31:0] mount_base,mount_fat,mount_max,mount_root, output wire [7:0] mount_spc,output wire [3:0] mount_shift,
 output wire pixel_valid,input wire pixel_ready,
 output wire [23:0] pixel_rgb,output wire [15:0] pixel_x,pixel_y,
 output wire done,ok,output wire [7:0] error_code,
 output wire mounted,bmp_ok,
 output wire [31:0] pixel_count,payload_crc32,
 output wire [15:0] source_width,source_height,output wire [31:0] row_stride,output wire source_top_down);
 wire [3:0] pe,xe;
 wire pd,xd,xok,pr,xr,top;wire [31:0] pl,xl,fs,off,cl,base,fat,mx;
 wire [7:0] spc;wire [3:0] sh;
 wire use_pixels=pd&&bmp_ok;
 assign read_req=use_pixels?xr:pr;assign read_lba=use_pixels?xl:pl;
 assign mount_base=base;assign mount_fat=fat;assign mount_max=mx;assign mount_spc=spc;assign mount_shift=sh;
 media_bmp_probe #(.RUNTIME_NAME(RUNTIME_NAME),.DYNAMIC_SIZE(DYNAMIC_SIZE),.MAX_WIDTH(MAX_WIDTH),.MAX_HEIGHT(MAX_HEIGHT)) probe(.file_letter(file_letter),.clk(clk),.rst_n(rst_n),.sd_ready(ready),.sd_read_done(read_done),
 .sd_error(se),.data_valid(dv),.data_index(di),.data_byte(db),
 .read_req(pr),.read_lba(pl),.mounted(mounted),.file_found(),.bmp_ok(bmp_ok),
 .done(pd),.top_down(top),.error_code(pe),.file_size(fs),.pixel_offset(off),.file_cluster(cl),.sectors_scanned(),
 .data_base(base),.fat_base(fat),.cluster_max(mx),.mounted_root(mount_root),.mounted_spc(spc),.mounted_shift(sh),
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
