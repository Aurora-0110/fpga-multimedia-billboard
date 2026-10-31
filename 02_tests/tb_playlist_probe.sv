`timescale 1ns/1ps
module tb_playlist_probe;
 wire [15:0] source_width,source_height;wire [31:0] row_stride;
 reg clk=0,rst_n=0;always #10 clk=~clk;
 reg [7:0] file_letter=8'h41;integer letter=65,mutate=0;
 initial begin
  if($value$plusargs("LETTER=%d",letter))begin end
  if($value$plusargs("MUTATE=%d",mutate))begin end
  file_letter=letter;
  wait(rst_n);repeat(8)@(negedge clk);
  if(mutate)file_letter="Z";
 end
 reg sd_ready=0,sd_read_done=1;reg [3:0] sd_error=0;
 reg data_valid=0;reg [8:0] data_index=0;reg [7:0] data_byte=0;
 wire read_req,mounted,file_found,bmp_ok,done,top_down;
 wire [31:0] read_lba,file_size,pixel_offset,file_cluster;wire [3:0] error_code;wire [15:0] sectors_scanned;
 wire [31:0] data_base,fat_base,cluster_max;wire [7:0] mounted_spc;wire [3:0] mounted_shift;
 fat32_bmp_probe #(.RUNTIME_NAME(1),.MAX_DIR_SECTORS(4),.INIT_TIMEOUT_CYCLES(5000),.READ_TIMEOUT_CYCLES(5000)) dut(.*);
 `include "fixture_setup.vh"
 integer server_state=0,byte_pos=0,block_index=0;
 always @(posedge clk) begin
  data_valid<=0;
  if(!rst_n) begin sd_ready<=0;sd_read_done<=1;sd_error<=0;server_state<=0;end
  else case(server_state)
   0:if(sd_init_error) begin sd_error<=4;server_state<=5;end
     else if(stall_mode!=1) begin sd_ready<=1;server_state<=1;end
   1:if(read_req) begin
     note_request(read_lba);block_index=find_block(read_lba);
     if(block_index<0) $fatal(1,"No fixture sector %0d",read_lba);
     if(stall_mode==2) server_state<=5;
     else begin sd_ready<=0;sd_read_done<=0;byte_pos<=0;server_state<=(stall_mode==3)?5:2;end
    end
   2:begin data_valid<=1;data_index<=byte_pos;data_byte<=fixture_data[block_index*512+byte_pos];
     if(byte_pos==511) server_state<=3;else byte_pos<=byte_pos+1;
    end
   3:begin
    if(crc_read==request_count) sd_error<=10;
    else begin sd_ready<=1;sd_read_done<=1;end
    server_state<=1;
   end
   default:begin end
  endcase
 end
 reg [3:0] saved_error;reg [2:0] saved_flags;integer saved_count;
 initial begin
  repeat(5) @(negedge clk);rst_n=1;
  wait(done);repeat(5) @(negedge clk);check_result;
  saved_error=error_code;saved_flags={mounted,file_found,bmp_ok};saved_count=request_count;
  repeat(100) @(negedge clk);
  if(error_code!==saved_error || {mounted,file_found,bmp_ok}!==saved_flags || request_count!=saved_count || read_req)
    $fatal(1,"Terminal result not sticky or extra I/O after completion");
  $display("PASS FAT controller %s reads=%0d err=%0d",fixture_path,request_count,error_code);$finish;
 end
 initial begin #20000000;$fatal(1,"Controller TB watchdog");end
endmodule
