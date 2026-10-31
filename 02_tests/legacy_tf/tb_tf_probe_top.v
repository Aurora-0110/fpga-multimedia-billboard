`timescale 1ns/1ps
module tb_tf_probe_top;
 reg clk24m=0,key0_n=1;always #10 clk24m=~clk24m;
 wire tf_cs_n,tf_sck,tf_mosi,tf_miso,led_sclk,led_dout,led_latch;
 tf_probe_top #(.POR_CYCLES(8),.KEY_CYCLES(8),.HALF_DIV(2),
 .POWER_WAIT_CYCLES(16),.INIT_GAP_CYCLES(4),.HEART_HALF_CYCLES(200),.LED_DIV(2)) dut(.*);
 reg card_rst_n=0;initial begin #25;card_rst_n=1;end
 sd_card_model card(.rst_n(card_rst_n),.cs_n(tf_cs_n),.sck(tf_sck),.mosi(tf_mosi),.miso(tf_miso));
 reg [7:0] led_shift=0,latched=0;integer latch_count=0,edges=0,retries=0;
 always @(posedge led_sclk) begin led_shift={led_shift[6:0],led_dout};edges=edges+1;end
 always @(posedge led_latch) begin
  if(edges!=8) $fatal(1,"595 expected 8 rising clocks per latch, got %0d",edges);
  latched=led_shift;edges=0;latch_count=latch_count+1;
 end
 always @(posedge clk24m) if(dut.retry) retries=retries+1;
 initial begin
  wait(dut.probe.read_done);repeat(500) @(negedge clk24m);
  if(latched[7:1]!==7'b0000111 || latch_count<2) $fatal(1,"Wrong LED success encoding %b",latched);
  // A short key pulse must not restart.
  key0_n=0;repeat(2) @(negedge clk24m);key0_n=1;repeat(20) @(negedge clk24m);
  if(retries!=0 || !dut.probe.read_done) $fatal(1,"Short key bounce caused retry");
  key0_n=0;wait(dut.retry);wait(!dut.probe.read_done);
  wait(dut.probe.read_done);repeat(40) @(negedge clk24m);
  if(card.read_count!=2) $fatal(1,"Retry must reread with card remaining powered");
  if(retries!=1) $fatal(1,"Held key must trigger exactly one retry");
  key0_n=1;repeat(20) @(negedge clk24m);
  $display("PASS TOP POR, 595 LED encoding, key debounce, one-shot retry");$finish;
 end
 initial begin #20000000;$fatal(1,"Top watchdog");end
endmodule
