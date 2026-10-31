`timescale 1ns/1ps
module tb_fat_board;
 reg clk24m=0,key0_n=1;always #10 clk24m=~clk24m;
 wire tf_cs_n,tf_sck,tf_mosi,tf_miso,led_sclk,led_dout,led_latch;
 tf_probe_top #(.POR_CYCLES(8),.KEY_CYCLES(8),.HALF_DIV(2),.POWER_WAIT_CYCLES(16),
 .INIT_GAP_CYCLES(4),.HEART_HALF_CYCLES(200),.LED_DIV(2)) dut(.*);
 reg card_rst_n=0;initial begin #25;card_rst_n=1;end
 sd_fat_card_model card(.rst_n(card_rst_n),.cs_n(tf_cs_n),.sck(tf_sck),.mosi(tf_mosi),.miso(tf_miso));
 wire mounted=dut.mounted,file_found=dut.file_found,bmp_ok=dut.bmp_ok,done=dut.done,top_down=dut.probe.top_down;
 wire [3:0] error_code=dut.error_code;
 wire [31:0] file_cluster=dut.probe.file_cluster,pixel_offset=dut.probe.pixel_offset,file_size=dut.probe.file_size;
 `include "fixture_setup.vh"
 always @(posedge clk24m) if(dut.ready && dut.read_req) note_request(dut.read_lba);
 reg [7:0] led_shift=0,latched=0;integer edges=0,latch_count=0,retries=0;
 always @(posedge led_sclk) begin led_shift={led_shift[6:0],led_dout};edges=edges+1;end
 always @(posedge led_latch) begin
  if(edges!=8) $fatal(1,"595 expected 8 clocks, got %0d",edges);
  latched=led_shift;edges=0;latch_count=latch_count+1;
 end
 always @(posedge clk24m) if(dut.retry) retries=retries+1;
 initial begin
  wait(done);repeat(500) @(negedge clk24m);check_result;
  if(latched[7:1]!==7'b0000111 || latch_count<2) $fatal(1,"Bad new LED status %b",latched);
  key0_n=0;repeat(2) @(negedge clk24m);key0_n=1;repeat(20) @(negedge clk24m);
  if(retries || !done) $fatal(1,"Key bounce caused restart");
  request_count=0;key0_n=0;wait(dut.retry);wait(!done);wait(done);
  repeat(500) @(negedge clk24m);check_result;
  if(card.read_count!=2*expected_reads || retries!=1) $fatal(1,"Powered-card retry / held-key one-shot failed");
  if(latched[7:1]!==7'b0000111) $fatal(1,"Bad retry LED status");
  $display("PASS new board top: POR, 595 encoding, bounce rejection, held-key one-shot and powered-card retry");$finish;
 end
 initial begin #30000000;$fatal(1,"New top watchdog");end
endmodule
