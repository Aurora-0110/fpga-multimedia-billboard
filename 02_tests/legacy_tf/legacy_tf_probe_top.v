// VF-E20NG88 EG4S20NG88, 24MHz. Standalone TF read test, NOT HDMI.
`timescale 1ns/1ps
module tf_probe_top #(parameter integer POR_CYCLES=65536,KEY_CYCLES=480000,
 HALF_DIV=60,POWER_WAIT_CYCLES=2400000,INIT_GAP_CYCLES=24000,
 HEART_HALF_CYCLES=12000000,LED_DIV=120)(
 input wire clk24m,key0_n,tf_miso,
 output wire tf_cs_n,tf_sck,tf_mosi,led_sclk,led_dout,led_latch);
 reg [31:0] por_count=0;
 wire por_done=por_count==POR_CYCLES;
 always @(posedge clk24m) if(!por_done) por_count<=por_count+1'b1;
 // Explicit scalar two-flop template for TD synthesis. No generated clocks.
 reg key_meta,key_sample;
 always @(posedge clk24m) begin
  if(!por_done) begin key_meta<=1'b1;key_sample<=1'b1;end
  else begin key_meta<=key0_n;key_sample<=key_meta;end
 end
 reg [31:0] key_count;reg key_held,retry;
 always @(posedge clk24m) begin
  retry<=0;
  if(!por_done || key_sample) begin key_count<=0;key_held<=0;end
  else if(!key_held) begin
   if(key_count==KEY_CYCLES-1) begin retry<=1;key_held<=1;end
   else key_count<=key_count+1'b1;
  end
 end
 wire host_rst_n=por_done && !retry;
 reg [31:0] heartbeat_count;reg heartbeat;
 always @(posedge clk24m) begin
  if(!por_done) begin heartbeat_count<=0;heartbeat<=0;end
  else if(heartbeat_count==HEART_HALF_CYCLES-1) begin heartbeat_count<=0;heartbeat<=~heartbeat;end
  else heartbeat_count<=heartbeat_count+1'b1;
 end
 wire init_done,read_done,signature_ok;wire [3:0] error_code;
 sd_spi_probe #(.HALF_DIV(HALF_DIV),.POWER_WAIT_CYCLES(POWER_WAIT_CYCLES),
 .INIT_GAP_CYCLES(INIT_GAP_CYCLES)) probe(
 .clk(clk24m),.rst_n(host_rst_n),.miso(tf_miso),.sck(tf_sck),.mosi(tf_mosi),.cs_n(tf_cs_n),
 .init_done(init_done),.read_done(read_done),.signature_ok(signature_ok),.error_code(error_code),
 .high_capacity(),.data_crc(),.received_crc(),.data_sum(),.last_r1(),.last_cmd(),
 .data_valid(),.data_index(),.data_byte());
 wire [7:0] led_status={error_code,(read_done && signature_ok),read_done,init_done,heartbeat};
 led_595 #(.CNT(LED_DIV)) leds(.clk(clk24m),.rst_n(por_done),.data(led_status),
 .sclk(led_sclk),.dout(led_dout),.latch(led_latch));
endmodule
