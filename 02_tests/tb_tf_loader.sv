`timescale 1ns/1ps
module tb_tf_loader;
 wire [7:0] file_letter=8'h41;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,enable=0,req_ack=0;wire miso,cs_n,sck,mosi,req_valid,done,sd_init,mounted,bmp_ok;
wire[18:0]req_addr;wire[127:0]req_data;wire[7:0]error_code;
tf_bmp_loader #(.HALF_DIV(1),.POWER_WAIT_CYCLES(16),.INIT_GAP_CYCLES(4)) dut(.*);
sd_bmp_card_model card(.rst_n(rst_n),.cs_n(cs_n),.sck(sck),.mosi(mosi),.miso(miso));
reg[7:0]image[0:921653];string path;integer expected_error=0,top=0,flip=0,seen=0,cycle=0,k,pos,row,tries=0;
reg[23:0]p;reg[7:0]q;
always @(negedge clk)begin
 req_ack=0;
 if(rst_n)begin
 cycle=cycle+1;enable=cycle%41>7;
 if(req_valid&&cycle%13==0)begin
  row=top?seen/40:479-seen/40;
  if(req_addr!==row*40+seen%40)$fatal(1,"loader address order %0d",req_addr);
  for(k=0;k<16;k=k+1)begin
   pos=54+((seen/40)*640+(seen%40)*16+k)*3;
   p={image[pos+2],image[pos+1],image[pos]};
   if(flip&&pos<=100&&pos+2>=100)begin
    if(pos==100)p[0]=~p[0];else if(pos+1==100)p[8]=~p[8];else p[16]=~p[16];
   end
   q={p[23:21],p[15:13],p[7:6]};
   if(req_data[k*8+:8]!==q)$fatal(1,"loader pixel %0d lane %0d got=%h expected=%h",seen,k,req_data[k*8+:8],q);
  end
  seen=seen+1;req_ack=1;
 end
 end
end
initial begin
 if(!$value$plusargs("IMAGE=%s",path))$fatal(1,"IMAGE required");$readmemh(path,image);
 if($value$plusargs("ERROR=%d",expected_error))begin end
 if($value$plusargs("TOP=%d",top))begin end
 if($value$plusargs("FLIP=%d",flip))begin end
 repeat(10)@(posedge clk);#1;rst_n=1;
 if(expected_error)begin
 wait(error_code!=0);if(error_code!==expected_error||done)$fatal(1,"wrong error %h expected %h",error_code,expected_error);
 repeat(100)@(posedge clk);if(done)$fatal(1,"error passed");
 end else begin
 wait(done||error_code!=0);
 if(error_code||seen!=19200||dut.packer.pixel_count!=307200||!sd_init||!mounted||!bmp_ok)$fatal(1,"loader completion failed %h seen %0d",error_code,seen);
 repeat(100)@(posedge clk);if(!done||req_valid)$fatal(1,"loader completion not sticky");
 end
 $display("PASS SPI loader reads=%0d bursts=%0d error=%h",card.read_count,seen,error_code);$finish;
end
initial begin #1000000000;$fatal(1,"loader timeout");end
endmodule
