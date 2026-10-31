`timescale 1ns/1ps
module tb_spi_byte;
 reg clk=0,rst_n=0,start=0,miso=1;always #10 clk=~clk;
 wire fast_mode=0;
 reg [7:0] tx=0;wire sck,mosi,busy,done;wire [7:0] rx;
 spi_byte #(.HALF_DIV(2)) dut(.*);
 integer value,bit_num,edges=0;reg [7:0] response;reg [7:0] observed;
 initial begin
  repeat(4) @(negedge clk);rst_n=1;
  for(value=0;value<256;value=value+1) begin
   tx=value[7:0];response=~tx;observed=0;miso=response[7];
   @(negedge clk);start=1;@(negedge clk);start=0;
   for(bit_num=7;bit_num>=0;bit_num=bit_num-1) begin
    @(posedge sck);observed[bit_num]=mosi;@(negedge sck);
    if(bit_num>0) miso=response[bit_num-1];
   end
   @(negedge clk);
   if(!done || busy || rx!==response || observed!==tx || sck!==0)
    $fatal(1,"SPI mode0/MSB mismatch tx=%h rx=%h expected=%h",tx,rx,response);
   @(negedge clk);if(done) $fatal(1,"done wider than one cycle");
  end
  // Reset in the middle of a byte; outputs must immediately return safe idle.
  start=1;@(negedge clk);start=0;repeat(4) @(negedge clk);rst_n=0;#1;
  if(sck || busy || !mosi) $fatal(1,"Reset mid-byte did not idle");
  $display("PASS SPI 256 values mode0 MSB and reset-abort");$finish;
 end
 initial begin #10000000;$fatal(1,"SPI watchdog");end
endmodule
