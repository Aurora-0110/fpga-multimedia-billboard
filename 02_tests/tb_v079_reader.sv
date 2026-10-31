`timescale 1ns/1ps
module tb_v079_reader;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,tr=0;reg[1:0]target=1;reg[12:0]used=0;
 wire done,sliding,rv,fw;wire[5:0]step;wire[18:0]addr;wire[15:0]data;
 reg ack=0,resp=0;reg[127:0]rd=0;
 idx_slide_reader #(.LINES(2))dut(clk,rst,1'b1,used,tr,target,done,sliding,step,rv,addr,ack,resp,rd,fw,data);
 integer cyc=0,delay=0;reg work=0;reg[18:0]saved;
 integer i,yy,xx,bank,val;
 always @(negedge clk)begin
  ack=0;resp=0;cyc=cyc+1;used=(cyc%239<59)?4050:0;
  if(!rst)begin work=0;delay=0;end
  else if(!work&&rv)begin
   work=1;saved=addr;delay=3+(cyc%7);ack=1;
  end else if(work)begin
   if(delay==0)begin
    bank=saved[17];
    for(i=0;i<16;i=i+1)begin
     yy=saved[14:0]/40;xx=(saved[14:0]%40)*16+i;
     val=(xx+yy*7+bank*71)&255;rd[i*8+:8]=val;
    end
    resp=1;work=0;
   end else delay=delay-1;
  end
 end
 integer count=0,frame=0,pix=0,st=0,idx=0,prevst=0,previdx=0,changes=0,completions=0;
 integer expbank,sx,sy,ev;
 always @(posedge clk)if(rst)begin
  if(done)begin completions=completions+1;tr<=0;end
  if(fw)begin
   st=data[13:8];idx=data[15:14];
   if(pix==0)begin
    frame=frame+1;
    if(st!=prevst)begin
     if(!((prevst==0&&st==1)||(prevst<40&&st==prevst+1)||(prevst==40&&st==0)))$fatal(1,"step discontinuity %d->%d",prevst,st);
     changes=changes+1;
    end
    prevst=st;previdx=idx;
    if(frame==2)tr<=1;
    if(completions>0&&completions<4&&st==0&&idx==completions)begin target<=idx+1;tr<=1;end
   end else if(st!=prevst||idx!=previdx)$fatal(1,"tag tear in frame");
   if(st>40)$fatal(1,"step out of range");
   xx=pix%640;sy=pix/640;
   if(st==0)begin expbank=idx%2;sx=xx;end
   else if(xx<640-st*16)begin expbank=(idx+3)%2;sx=xx+st*16;end
   else begin expbank=idx%2;sx=xx-(640-st*16);end
   ev=(sx+sy*7+expbank*71)&255;
   if(data[7:0]!==ev[7:0])$fatal(1,"pixel %d frame%d step%d idx%d actual%h expected%h",pix,frame,st,idx,data[7:0],ev[7:0]);
   count=count+1;pix=pix+1;
   if(pix==1280)begin
    pix=0;
    if(completions==4&&st==0&&idx==0)begin
     if(changes!=164)$fatal(1,"missing transition steps %d",changes);
     $display("PASS reader %0d pixels %0d frames, both banks, all 40 steps four times including D-to-A wrap, ACK latency and backpressure",count,frame);$finish;
    end
   end
  end
 end
 initial begin #50;rst=1;#30000000;$fatal(1,"timeout");end
endmodule
