`timescale 1ns/1ps
module tb_pair_reader;
 parameter LINES=3,COMPLETIONS=4,STOP_AFTER_STEP=0;
 reg clk=0,rst=0,tr=0,full=0;reg [1:0] target=1;reg [12:0] used=0;
 always #5 clk=~clk;
 wire done,sliding,rv,fw,fault;wire [5:0] step;wire [18:0] addr;wire [23:0] data;
 reg ack=0,resp=0;reg [127:0] rd=0;
 idx_pair_reader #(.LINES(LINES)) dut(.clk(clk),.rst_n(rst),.enable(1'b1),.fifo_used(used),.fifo_full(full),
 .transition_request(tr),.target_index(target),.transition_done(done),.sliding(sliding),.step(step),
 .req_valid(rv),.req_addr(addr),.req_ready(ack),.rsp_valid(resp),.rsp_rdata(rd),.fifo_we(fw),.fifo_wdata(data),.protocol_fault(fault));
 integer cyc=0,delay=0;reg work=0;reg [18:0] saved;
 integer i,yy,xx,bank,val,reads=0,first=0,last=0,stalls=0;
 reg held=0;reg [23:0] hold_data;
 always @(negedge clk)begin
  ack=0;resp=0;cyc=cyc+1;
  used=(cyc%239<59)?4073:0;full=cyc%307<9;
  if(!rst)begin work=0;delay=0;end
  else if(!work&&rv)begin
   if(addr[18]||addr[16:0]>=80*LINES)$fatal(1,"pair reader address outside banks/frame: %0d",addr);
   work=1;saved=addr;delay=2+cyc%9;ack=1;reads=reads+1;
   if(addr[16:0]==0)first=first+1;if(addr[16:0]==80*LINES-1)last=last+1;
  end else if(work)begin
   if(delay==0)begin
    bank=saved[17];
    for(i=0;i<16;i=i+1)begin
     yy=saved[16:0]/80;xx=(saved[16:0]%80)*16+i;
     val=(xx+yy*7+bank*71)&255;rd[i*8+:8]=val;
    end
    resp=1;work=0;
   end else delay=delay-1;
  end
 end
 integer count=0,frame=0,pix=0,st=0,idx=0,prevst=0,previdx=0,changes=0,completions=0;
 integer expbank,sx,sy,ev,lane;
 always @(posedge clk)if(rst)begin
  if(fault)$fatal(1,"pair reader protocol fault");
  if(held&&data!==hold_data)$fatal(1,"pair data changed while FIFO full");
  held=dut.pushing&&full;hold_data=data;if(held)stalls=stalls+1;
  if(done)begin completions=completions+1;tr<=0;end
  if(fw)begin
   st=data[21:16];idx=data[23:22];
   if(pix==0)begin
    frame=frame+1;
    if(st!=prevst)begin
     if(!((prevst==0&&st==1)||(prevst<40&&st==prevst+1)||(prevst==40&&st==0)))$fatal(1,"step discontinuity %d->%d",prevst,st);
     changes=changes+1;
    end
    prevst=st;previdx=idx;
    if(frame==2)tr<=1;
    if(completions>0&&completions<COMPLETIONS&&st==0&&idx==completions%4)begin target<=idx+1;tr<=1;end
   end else if(st!=prevst||idx!=previdx)$fatal(1,"pair reader tag tear");
   if(st>40)$fatal(1,"pair step out of range");
   for(lane=0;lane<2;lane=lane+1)begin
    xx=pix%1280;sy=pix/1280;
    if(st==0)begin expbank=idx%2;sx=xx;end
    else if(xx<1280-st*32)begin expbank=(idx+3)%2;sx=xx+st*32;end
    else begin expbank=idx%2;sx=xx-(1280-st*32);end
    ev=(sx+sy*7+expbank*71)&255;
    if(data[lane*8+:8]!==ev[7:0])$fatal(1,"pair pixel=%d step=%d idx=%d actual=%h expected=%h",pix,st,idx,data[lane*8+:8],ev[7:0]);
    count=count+1;pix=pix+1;
   end
   if(pix==1280*LINES)begin
    pix=0;
    if((STOP_AFTER_STEP!=0&&st==STOP_AFTER_STEP)||(STOP_AFTER_STEP==0&&completions==COMPLETIONS&&st==0&&idx==COMPLETIONS%4))begin
     if((STOP_AFTER_STEP==0&&changes!=COMPLETIONS*41)||first<2||last<2||stalls==0)$fatal(1,"missing address/step/stall coverage");
     $display("PASS pair_reader lines=%0d pixels=%0d frames=%0d reads=%0d changes=%0d completions=%0d first=%0d last=%0d full_stalls=%0d",LINES,count,frame,reads,changes,completions,first,last,stalls);$finish;
    end
   end
  end
 end
 initial begin repeat(6)@(negedge clk);rst=1;end
 initial begin #100000000;$fatal(1,"pair reader watchdog");end
endmodule
