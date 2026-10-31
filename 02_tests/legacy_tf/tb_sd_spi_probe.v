`timescale 1ns/1ps
module tb_sd_spi_probe;
 reg clk=0,rst_n=0;always #10 clk=~clk;
 wire miso,sck,mosi,cs_n,init_done,read_done,signature_ok,high_capacity,data_valid;
 wire [3:0] error_code;wire [15:0] data_crc,received_crc;wire [31:0] data_sum;
 wire [7:0] last_r1,data_byte;wire [5:0] last_cmd;wire [8:0] data_index;
 `ifdef PROD_DIV
 localparam DIV=60;
 `else
 localparam DIV=2;
 `endif
 sd_spi_probe #(.HALF_DIV(DIV),.POWER_WAIT_CYCLES(16),.INIT_GAP_CYCLES(4),
 .MAX_INIT_TRIES(4),.R1_MAX_BYTES(12),.TOKEN_MAX_BYTES(24)) dut(.*);
 reg card_rst_n=0;
 sd_card_model card(.rst_n(card_rst_n),.cs_n(cs_n),.sck(sck),.mosi(mosi),.miso(miso));
 integer mode=0,unused,count=0,expected_error=0,restart=0,round_num,keep_power=0;
 reg [31:0] expected_sum;reg [7:0] expected_byte;
 always @(posedge clk) begin
  if(!rst_n) count=0;
  else if(data_valid) begin
   expected_byte=count[7:0]^8'ha5;
   if(count==510) expected_byte=(mode==11)?8'h00:8'h55;
   if(count==511) expected_byte=8'haa;
   if(data_index!==count || data_byte!==expected_byte)
    $fatal(1,"Payload mismatch idx=%0d byte=%h expected=%h",data_index,data_byte,expected_byte);
   count=count+1;
  end
 end
 initial begin
  unused=$value$plusargs("CASE=%d",mode);restart=$test$plusargs("RESTART");keep_power=$test$plusargs("KEEP_CARD_POWER");
  case(mode)
   2:expected_error=1;3,7:expected_error=3;4:expected_error=5;
   5:expected_error=8;6:expected_error=10;8:expected_error=9;
   9:expected_error=6;10,15:expected_error=7;14:expected_error=4;
   default:expected_error=0;
  endcase
  for(round_num=0;round_num<=restart;round_num=round_num+1) begin
   rst_n=0;if(round_num==0 || !keep_power) card_rst_n=0;
   repeat(5) @(negedge clk);card_rst_n=1;rst_n=1;
   wait(dut.state==23 || dut.state==24);repeat(5) @(negedge clk);
   if(error_code!==expected_error) $fatal(1,"CASE%0d error %0d != %0d lastCMD%0d R1=%h",mode,error_code,expected_error,last_cmd,last_r1);
   if(!cs_n || sck || !mosi) $fatal(1,"Bus not idle at completion");
   if(expected_error==0) begin
    if(!init_done || !read_done || count!=512 || data_crc!=received_crc)
     $fatal(1,"Success missing 512-byte/CRC/init flags");
    if(signature_ok!==(mode!=11)) $fatal(1,"Signature mismatch");
    if(high_capacity!==(mode!=1)) $fatal(1,"Capacity flag mismatch");
    if(card.read_count!=((keep_power)?round_num+1:1)) $fatal(1,"Expected exactly one CMD17");
    if(card.setlen_count!=((mode==1)?((keep_power)?round_num+1:1):0)) $fatal(1,"Unexpected CMD16 count");
    if(mode==13 && card.cmd0_count!=2) $fatal(1,"CMD0 retry not observed");
    expected_sum=(mode==11)?32'd65269:32'd65354;
    if(data_sum!=expected_sum) $fatal(1,"Data checksum=%0d expected=%0d",data_sum,expected_sum);
   end else if(read_done) $fatal(1,"Error falsely reported successful read");
  end
  $display("PASS CASE=%0d restart=%0d bytes=%0d err=%0d crc=%h sum=%0d",mode,restart,count,error_code,data_crc,data_sum);$finish;
 end
 initial begin #100000000; $fatal(1,"Watchdog timeout (bounded test)");end
endmodule
