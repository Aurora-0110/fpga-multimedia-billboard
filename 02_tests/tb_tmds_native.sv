`timescale 1ns/1fs
module tb_tmds_native;
 reg clk=0,pix=0,rst=1;reg [9:0] din=0;
 always #1.346801347 clk=~clk;
 initial begin #0.37;forever #6.734006735 pix=~pix;end
 wire q,qc;
 tmds_serializer d(.clk_pix(pix),.clk_5x(clk),.rst(rst),.rst_pix_n(~rst),.din(din),.q(q));
 tmds_clock_lane c(.clk_pix(pix),.clk_5x(clk),.rst(rst),.rst_pix_n(~rst),.q(qc));
 reg [9:0] expected[0:4095];integer put=0,get=0,phase=5,checks=0,words=0,epoch=0;
 reg marker=0,s0=0,s1=0,seen=0;reg [9:0] word=0;
 reg lo,hi,clo,chi,load_ref;reg [9:0] nextword;
 always @(posedge pix or posedge rst)
 if(rst)begin marker<=0;put=0;end
 else begin nextword=$random;din<=nextword;expected[put]=nextword;put=put+1;marker<=~marker;end
 always @(posedge rst)begin get=0;phase=5;s0=0;s1=0;seen=0;word=0;end
 always @(posedge clk)begin
  if(!rst && $time>40)begin
   lo=(phase<5)?word[2*phase]:0;hi=(phase<5)?word[2*phase+1]:0;
   clo=(phase<5)?(phase>=3):0;chi=(phase<5)?(phase>=2):0;
   load_ref=(s1!=seen);seen=s1;s1=s0;s0=marker;
   if(load_ref)begin
    if(get>=put)$fatal(1,"unissued pixel");
    if(phase!=5&&phase!=4)$fatal(1,"word overlap");
    word=expected[get];get=get+1;phase=0;words=words+1;
   end else if(phase<5)phase=phase+1;
   #0.25;
   if(q!==lo||qc!==clo)$fatal(1,"DDR positive mismatch word=%0d phase=%0d got=%b/%b exp=%b/%b",words,phase,q,qc,lo,clo);
   @(negedge clk);#0.25;
   if(q!==hi||qc!==chi)$fatal(1,"DDR negative mismatch word=%0d phase=%0d",words,phase);
   checks=checks+2;
  end
 end
 initial begin
  #83;rst=0;
  repeat(3)begin repeat(600)@(negedge pix);rst=1;#43.7;epoch=epoch+1;rst=0;end
  repeat(100)@(negedge pix);#4;
  if(checks<18000||words<1800||epoch!=3)$fatal(1,"coverage");
  $display("PASS native_ODDR DDR_bits=%0d words=%0d reset_retries=%0d marker_word_alignment_and_clock",checks,words,epoch);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
