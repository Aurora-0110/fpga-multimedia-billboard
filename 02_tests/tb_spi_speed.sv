`timescale 1ns/1ps
module tb_spi_speed;
 parameter INIT_DIV=124, DATA_DIV=25;
 reg clk=0,rst_n=0,start=0,miso=1,fast_mode=0;always #5 clk=~clk;
 reg [7:0] tx=0;wire sck,mosi,busy,done;wire [7:0] rx;
 spi_byte #(.HALF_DIV(INIT_DIV),.DATA_HALF_DIV(DATA_DIV)) dut(.*);
 integer value,bit_num,cycles=0,begin_cycle,last_cycle,expected_div;
 reg [7:0] response,observed;
 always @(posedge clk) cycles=cycles+1;
 initial begin
  repeat(4) @(negedge clk);rst_n=1;
  for(value=0;value<256;value=value+1) begin
   fast_mode=value%2;expected_div=fast_mode?DATA_DIV:INIT_DIV;
   tx=value;response=~tx;observed=0;miso=response[7];
   @(negedge clk);start=1;@(negedge clk);start=0;begin_cycle=cycles;last_cycle=cycles;
   for(bit_num=7;bit_num>=0;bit_num=bit_num-1) begin
    @(posedge sck);
    if(cycles-last_cycle!=expected_div)$fatal(1,"rising half period %0d expected %0d",cycles-last_cycle,expected_div);
    last_cycle=cycles;observed[bit_num]=mosi;
    // Deliberately change the mode mid-byte: latched divider must not change.
    #1;fast_mode=~fast_mode;
    @(negedge sck);
    if(cycles-last_cycle!=expected_div)$fatal(1,"falling half period wrong");
    last_cycle=cycles;if(bit_num>0)miso=response[bit_num-1];
   end
   @(negedge clk);
   if(!done||busy||rx!==response||observed!==tx||sck!==0)$fatal(1,"byte data/status mismatch");
   if(cycles-begin_cycle!=16*expected_div)$fatal(1,"byte cycle count wrong");
   @(negedge clk);if(done)$fatal(1,"done wider than one cycle");
  end
  fast_mode=1;start=1;@(negedge clk);start=0;wait(sck);#1;rst_n=0;#1;
  if(sck||busy||!mosi||dut.data_mode)$fatal(1,"reset did not abort fast byte safely");
  @(negedge clk);rst_n=1;fast_mode=0;repeat(4)@(negedge clk);
  $display("PASS SPI speed 256 values init_div=%0d data_div=%0d mid-byte mode changes and reset",INIT_DIV,DATA_DIV);$finish;
 end
 initial begin #100000000;$fatal(1,"SPI watchdog");end
endmodule
