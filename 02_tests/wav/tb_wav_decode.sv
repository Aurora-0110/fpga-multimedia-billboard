`timescale 1ns/1ps
module tb_wav_decode;
 reg clk=0;always #5 clk=~clk;reg rst=0;
 reg bv=0,pr=0;wire br,pv,ok,done;wire signed[23:0]l,rr;wire[3:0]err;wire[31:0]ds;
 reg [7:0] bytes[0:65535];reg [47:0] expect_pcm[0:10000];
 integer nb,np,fail_expected,partial,n=0,k=0,cycles=0;reg[31:0]random=32'h716d42b8;
 reg [2047:0] f,g;
 wav_pcm_decode dut(.clk(clk),.rst_n(rst),.byte_valid(bv),.byte_ready(br),.byte_data(bytes[n]),.file_size(nb),
 .left(l),.right(rr),.pcm_valid(pv),.pcm_ready(pr),.header_ok(ok),.done(done),.error_code(err),.data_size(ds));
 initial begin
  if(!$value$plusargs("BYTES=%s",f)||!$value$plusargs("PCM=%s",g)||!$value$plusargs("NB=%d",nb)||!$value$plusargs("NP=%d",np)||!$value$plusargs("ERR=%d",fail_expected))$fatal(1,"args");
  $readmemh(f,bytes,0,nb-1);if(np>0)$readmemh(g,expect_pcm,0,np-1);
  repeat(6)@(negedge clk);rst=1;
 end
 always @(negedge clk)begin
  random={random[30:0],random[31]^random[21]^random[1]^random[0]};
  bv=rst&&n<nb&&random[1:0]!=0;pr=random[3:2]!=0;
 end
 always @(posedge clk)if(rst)begin
  cycles=cycles+1;
  if(bv&&br)n<=n+1;
  if(pv&&pr)begin
   if(!fail_expected)begin
    if(k>=np||{l,rr}!==expect_pcm[k])$fatal(1,"PCM mismatch k=%0d got=%h expected=%h",k,{l,rr},expect_pcm[k]);
   end
   k=k+1;
  end
  if(done&&!pv)begin
   if(fail_expected)begin if(err==0)$fatal(1,"expected rejection");end
   else if(err!=0||!ok||k!=np)$fatal(1,"incomplete err=%0d ok=%0d k=%0d np=%0d",err,ok,k,np);
   $display("PASS wav samples=%0d bytes=%0d err=%0d cycles=%0d",k,n,err,cycles);$finish;
  end
  if(cycles>200000)$fatal(1,"timeout n=%0d state=%0d",n,dut.state);
 end
endmodule

