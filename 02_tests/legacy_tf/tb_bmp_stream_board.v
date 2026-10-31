`timescale 1ns/1ps
module tb_bmp_stream_board;
 reg clk24m=0,key0_n=1;always #5 clk24m=~clk24m;
 wire tf_cs_n,tf_sck,tf_mosi,tf_miso,led_sclk,led_dout,led_latch;
 bmp_stream_top #(.POR_CYCLES(8),.KEY_CYCLES(8),.HALF_DIV(1),.POWER_WAIT_CYCLES(16),
 .INIT_GAP_CYCLES(4),.HEART_HALF_CYCLES(200),.LED_DIV(2)) dut(.*);
 reg card_rst_n=0;initial begin #13;card_rst_n=1;end
 sd_bmp_card_model card(.rst_n(card_rst_n),.cs_n(tf_cs_n),.sck(tf_sck),.mosi(tf_mosi),.miso(tf_miso));
 reg [7:0] shift=0,latched=0;integer edges=0,latches=0,retries=0,expected_error=0,flip=0;
 always @(posedge led_sclk) begin shift={shift[6:0],led_dout};edges=edges+1;end
 always @(posedge led_latch) begin
  if(edges!=8) $fatal(1,"595 framing %0d",edges);
  latched=shift;edges=0;latches=latches+1;
 end
 always @(posedge clk24m) if(dut.retry) retries=retries+1;
 initial begin
  if(!$value$plusargs("ERROR=%d",expected_error)) expected_error=0;
  if(!$value$plusargs("FLIP=%d",flip)) flip=0;
  wait(dut.done);repeat(30) @(negedge clk24m);
  if(!dut.bmp_ok || !dut.mounted || !dut.file_found) $fatal(1,"Metadata failed %0d",dut.error_code);
  // Bounce must not restart. Held key must restart once without power cycling SD.
  key0_n=0;repeat(2) @(negedge clk24m);key0_n=1;repeat(20) @(negedge clk24m);
  if(retries) $fatal(1,"Bounce retriggered");
  key0_n=0;wait(dut.retry);wait(!dut.done);wait(dut.done);
  wait(dut.stream_done);repeat(500) @(negedge clk24m);
  if(retries!=1 || dut.error_code!==expected_error) $fatal(1,"Final status %0d expected %0d retry %0d",dut.error_code,expected_error,retries);
  if(expected_error==0) begin
   if(!dut.stream_ok || !dut.checksum_ok || dut.pixel_count!=307200 || dut.payload_crc32!==32'h04f227f4) $fatal(1,"Full payload check failed");
   if(latched[7:1]!==7'b0000111) $fatal(1,"Success LED %b",latched);
  end else begin
   if(latched[7:4]!==expected_error || latched[3]!==0) $fatal(1,"Error LED %b",latched);
   if(expected_error==9 && (!dut.stream_ok || dut.checksum_ok || dut.pixel_count!=307200)) $fatal(1,"Checksum mismatch not differentiated");
   if(expected_error==1 && dut.pixel_count!=0) $fatal(1,"CRC failed sector escaped");
  end
  repeat(300) @(negedge clk24m);
  if(retries!=1 || !dut.stream_done) $fatal(1,"Held key restarted again");
  $display("PASS full SPI board reads=%0d pixels=%0d CRC=%08x err=%0d LED=%b retry=%0d",card.read_count,dut.pixel_count,dut.payload_crc32,dut.error_code,latched,retries);$finish;
 end
 initial begin #1000000000;$fatal(1,"Full SPI board watchdog");end
endmodule
