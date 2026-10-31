`timescale 1ns/1ps
module tb_dynamic_bmp_spi;
 reg clk=0,rst_n=0;
 always #5 clk=~clk;
 wire miso,mosi,sck,cs_n,pixel_valid,pixel_ready,source_done,source_ok;
 wire [23:0] pixel_rgb;
 wire [15:0] pixel_x,pixel_y,source_width,source_height;
 wire [7:0] source_error,packed_error;
 wire [31:0] row_stride,source_pixel_count,payload_crc32,packed_count,burst_count;
 wire sd_init,mounted,bmp_ok,req_valid,packed_done;
 wire [18:0] req_addr;
 wire [127:0] req_data;
 reg req_ack=0;
 tf_bmp_scaled_source #(.OUT_WIDTH(32),.OUT_HEIGHT(18),.HALF_DIV(2),.DATA_HALF_DIV(1),
 .POWER_WAIT_CYCLES(16),.INIT_GAP_CYCLES(4)) source(
 .clk(clk),.rst_n(rst_n),.file_letter(8'h41),.miso(miso),.cs_n(cs_n),.sck(sck),.mosi(mosi),
 .pixel_valid(pixel_valid),.pixel_ready(pixel_ready),.pixel_rgb(pixel_rgb),.pixel_x(pixel_x),.pixel_y(pixel_y),
 .done(source_done),.ok(source_ok),.error_code(source_error),.sd_init(sd_init),.mounted(mounted),.bmp_ok(bmp_ok),
 .source_width(source_width),.source_height(source_height),.row_stride(row_stride),
 .source_pixel_count(source_pixel_count),.payload_crc32(payload_crc32));
 bmp_pixel_packer #(.WIDTH(32),.HEIGHT(18)) packer(
 .clk(clk),.rst_n(rst_n),.enable(1'b1),.pixel_valid(pixel_valid),.pixel_ready(pixel_ready),
 .pixel_rgb(pixel_rgb),.pixel_x(pixel_x),.pixel_y(pixel_y),
 .source_done(source_done),.source_ok(source_ok),.source_error(source_error),
 .req_valid(req_valid),.req_addr(req_addr),.req_data(req_data),.req_ack(req_ack),.done(packed_done),.error_code(packed_error),
 .pixel_count(packed_count),.burst_count(burst_count));
 sd_fat_card_model card(.rst_n(rst_n),.cs_n(cs_n),.sck(sck),.mosi(mosi),.miso(miso));
 reg [23:0] expected_scaled[0:575];
 reg [7:0] expected_indexed[0:575];
 reg written[0:35];
 integer expected_error,expected_width,expected_height,expected_stride,expected_top,expected_crc;
 integer retry=0,seen=0,writes=0,pending=0,delay_ack=0,lane,saved_commands;
 string fixture;
 always @(posedge clk)begin
  if(!rst_n)begin
   req_ack<=0;seen=0;writes=0;pending=0;
   for(lane=0;lane<36;lane=lane+1)written[lane]=0;
  end else begin
   if(pixel_valid&&pixel_ready)begin
    if(seen>=576||pixel_rgb!==expected_scaled[seen]||pixel_x!==seen%32||pixel_y!==(expected_top?seen/32:17-seen/32))$fatal(1,"SPI scaled pixel mismatch %0d",seen);
    seen=seen+1;
   end
   if(req_ack)begin req_ack<=0;pending=0;end
   else if(pending)begin if(delay_ack==0)req_ack<=1;else delay_ack=delay_ack-1;end
   else if(req_valid)begin
    if(req_addr>=36||written[req_addr])$fatal(1,"SPI invalid burst %0d",req_addr);
    for(lane=0;lane<16;lane=lane+1)if(req_data[lane*8+:8]!==expected_indexed[req_addr*16+lane])$fatal(1,"SPI burst content mismatch");
    written[req_addr]=1;writes=writes+1;pending=1;delay_ack=writes%9;
   end
  end
 end
 task run_once;
  begin
   rst_n=0;repeat(6)@(negedge clk);rst_n=1;
   wait(packed_done||packed_error!=0);repeat(25)@(negedge clk);
   if(packed_error!=expected_error||source_error!=expected_error)$fatal(1,"SPI error %02h expected %02h",packed_error,expected_error);
   if(expected_error==0)begin
    if(!packed_done||!source_ok||!source_done||!sd_init||!mounted||!bmp_ok||seen!=576||writes!=36||burst_count!=36||packed_count!=576)$fatal(1,"SPI incomplete result");
    if(source_width!=expected_width||source_height!=expected_height||row_stride!=expected_stride||source_pixel_count!=expected_width*expected_height||payload_crc32!==expected_crc)$fatal(1,"SPI metadata/count/CRC mismatch");
    if(!cs_n||sck||!mosi)$fatal(1,"SPI not idle after success");
   end else if(packed_done)$fatal(1,"SPI corrupted frame published");
   saved_commands=card.command_count;
   repeat(300)@(negedge clk);
   if(card.command_count!=saved_commands)$fatal(1,"SPI traffic after terminal result");
   $display("PASS dynamic actual_SPI src=%0dx%0d top=%0d err=%02h pixels=%0d bursts=%0d CMD17=%0d",expected_width,expected_height,expected_top,packed_error,seen,writes,card.read_count);
  end
 endtask
 initial begin
  if(!$value$plusargs("FIXTURE=%s",fixture))$fatal(1,"Missing fixture");
  if(!$value$plusargs("WIDTH=%d",expected_width))$fatal(1,"Missing width");
  if(!$value$plusargs("HEIGHT=%d",expected_height))$fatal(1,"Missing height");
  if(!$value$plusargs("STRIDE=%d",expected_stride))$fatal(1,"Missing stride");
  if(!$value$plusargs("TOP=%d",expected_top))expected_top=0;
  if(!$value$plusargs("ERROR=%d",expected_error))expected_error=0;
  if(!$value$plusargs("CRC=%h",expected_crc))expected_crc=0;
  if(!$value$plusargs("RETRY=%d",retry))retry=0;
  $readmemh({fixture,"/scaled.hex"},expected_scaled,0,575);
  $readmemh({fixture,"/indexed.hex"},expected_indexed,0,575);
  run_once;
  if(retry)run_once;
  $finish;
 end
 initial begin #200000000;$fatal(1,"SPI dynamic watchdog");end
endmodule
