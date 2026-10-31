`timescale 1ns/1ps
module tb_fat_spi_integration;
 wire [15:0] source_width,source_height;wire [31:0] row_stride;
 wire [7:0] file_letter=8'h41;
 reg clk=0,rst_n=0;always #10 clk=~clk;
 wire sd_ready,sd_read_done;wire [3:0] sd_error;
 wire data_valid;wire [8:0] data_index;wire [7:0] data_byte;
 wire read_req,mounted,file_found,bmp_ok,done,top_down;
 wire [31:0] read_lba,file_size,pixel_offset,file_cluster;wire [3:0] error_code;wire [15:0] sectors_scanned;
 wire [31:0] data_base,fat_base,cluster_max;
 wire [7:0] mounted_spc;
 wire [3:0] mounted_shift;
 wire miso,sck,mosi,cs_n;
 `ifdef PROD_DIV
 localparam DIV=60;
 `else
 localparam DIV=2;
 `endif
 sd_spi_reader #(.HALF_DIV(DIV),.POWER_WAIT_CYCLES(16),.INIT_GAP_CYCLES(4),
 .R1_MAX_BYTES(12),.TOKEN_MAX_BYTES(24)) reader(.clk(clk),.rst_n(rst_n),.miso(miso),
 .sck(sck),.mosi(mosi),.cs_n(cs_n),.read_req(read_req),.read_lba(read_lba),.ready(sd_ready),
 .read_done(sd_read_done),.error_code(sd_error),.data_valid(data_valid),.data_index(data_index),.data_byte(data_byte));
 fat32_bmp_probe #(.MAX_DIR_SECTORS(4),.INIT_TIMEOUT_CYCLES(4000000),.READ_TIMEOUT_CYCLES(2000000)) dut(.*);
 sd_fat_card_model card(.rst_n(rst_n),.cs_n(cs_n),.sck(sck),.mosi(mosi),.miso(miso));
 `include "fixture_setup.vh"
 always @(posedge clk) if(rst_n && sd_ready && read_req) note_request(read_lba);
 integer restart=0,saved_reads,saved_cmds,bytes_seen=0,success_before;
 always @(posedge clk) begin
  if(!rst_n) bytes_seen<=0;
  else if(data_valid) begin
   if(data_index!==(bytes_seen%512)) $fatal(1,"SPI byte index mismatch");
   bytes_seen<=bytes_seen+1;
  end
 end
 initial begin
  restart=$test$plusargs("RESTART");
  repeat(5) @(negedge clk);rst_n=1;
  wait(done);repeat(10) @(negedge clk);check_result;
  if(sd_error==0 && (bytes_seen!=512*expected_reads || !cs_n || sck || !mosi)) $fatal(1,"Incomplete SPI transfer or bus not idle");
  if(card.read_count!=expected_reads || card.setlen_count!=sdsc_mode) $fatal(1,"SPI command count incorrect");
  saved_reads=request_count;saved_cmds=card.command_count;
  repeat(500) @(negedge clk);
  if(request_count!=saved_reads || card.command_count!=saved_cmds) $fatal(1,"Unexpected traffic after terminal result");
  if(restart) begin
   rst_n=0;request_count=0;repeat(5) @(negedge clk);rst_n=1;
   wait(done);repeat(10) @(negedge clk);check_result;
  end
  $display("PASS SPI+FAT %s divider=%0d reads=%0d err=%0d reset=%0d",fixture_path,DIV,request_count,error_code,restart);$finish;
 end
 initial begin #300000000;$fatal(1,"SPI integration watchdog");end
endmodule
