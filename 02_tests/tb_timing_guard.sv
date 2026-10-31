`timescale 1ns/1ps
module timing_case #(parameter W=1280,H=720,FP=110,SP=40,BP=220,VFP=5,VSP=5,VBP=20)(output reg done=0);
 reg clk=0,rst_n=0;always #5 clk=~clk;
 wire [11:0] x,y;wire hs,vs,de,fs;
 video_timing #(.H_ACTIVE(W),.H_FP(FP),.H_SYNC(SP),.H_BP(BP),.V_ACTIVE(H),.V_FP(VFP),.V_SYNC(VSP),.V_BP(VBP)) d(.clk(clk),.rst_n(rst_n),.x(x),.y(y),.hs(hs),.vs(vs),.de(de),.frame_start(fs));
 localparam HT=W+FP+SP+BP,VT=H+VFP+VSP+VBP;
 integer cycles=0,active=0,hslow=0,vslow=0,frames=0;reg seen=0;
 always @(negedge clk)if(rst_n&&!done)begin
  if(fs)begin
   if(x!==0||y!==0||!de)$fatal(1,"frame_start misaligned W=%0d",W);
   if(seen)begin
    if(cycles!=HT*VT||active!=W*H||hslow!=SP*VT||vslow!=VSP*HT)$fatal(1,"frame accounting W=%0d c=%0d a=%0d h=%0d v=%0d",W,cycles,active,hslow,vslow);
    frames=frames+1;
   end
   seen=1;cycles=0;active=0;hslow=0;vslow=0;
   if(frames==2)begin done=1;$display("PASS timing_guard W=%0d H=%0d frames=2 async_blank=1 origin_aligned=1",W,H);end
  end
  if(seen)begin cycles=cycles+1;if(de)active=active+1;if(!hs)hslow=hslow+1;if(!vs)vslow=vslow+1;end
 end
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;
  if(de!==0||fs!==0)$fatal(1,"reset must blank");
  @(negedge clk);#0.01;rst_n=1;#0.01;
  if(de!==0||fs!==0)$fatal(1,"must wait for local posedge");
  @(posedge clk);#0.01;if(x!==0||y!==0||!de||!fs)$fatal(1,"first active pixel lost");
 end
endmodule
module tb_timing_guard;
 wire a,b;
 timing_case a720(a);
 timing_case #(.W(640),.H(480),.FP(16),.SP(96),.BP(48),.VFP(10),.VSP(2),.VBP(33)) a480(b);
 initial begin wait(a&&b);$finish;end
 initial begin #30000000;$fatal(1,"timeout");end
endmodule
