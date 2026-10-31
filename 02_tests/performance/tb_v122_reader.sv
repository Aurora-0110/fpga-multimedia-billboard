`timescale 1ns/1ps
module tb_v122_reader;
 parameter B=4,L=3,S=2,CYCLES=100000;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,en=0,ff=0,tr=0,ack=0,rsp=0;reg[12:0]used=0;reg[1:0]target=0;reg[127:0]rdata=0;
 wire td,sl,rv,fw,fault;wire[5:0]step;wire[18:0]addr;wire[23:0]data;
 wire rtd,rsl,rrv,rfw,rfault;wire[5:0]rstep;wire[18:0]raddr;wire[23:0]rd;
 idx_pair_reader #(.LINE_BURSTS(B),.LINES(L),.TRANSITION_STEPS(S))dut(.clk(clk),.rst_n(rst_n),.enable(en),.fifo_used(used),.fifo_full(ff),.transition_request(tr),.target_index(target),.transition_done(td),.sliding(sl),.step(step),.req_valid(rv),.req_addr(addr),.req_ready(ack),.rsp_valid(rsp),.rsp_rdata(rdata),.fifo_we(fw),.fifo_wdata(data),.protocol_fault(fault));
 v119_idx_pair_reader_reference #(.LINE_BURSTS(B),.LINES(L),.TRANSITION_STEPS(S))refdut(.clk(clk),.rst_n(rst_n),.enable(en),.fifo_used(used),.fifo_full(ff),.transition_request(tr),.target_index(target),.transition_done(rtd),.sliding(rsl),.step(rstep),.req_valid(rrv),.req_addr(raddr),.req_ready(ack),.rsp_valid(rsp),.rsp_rdata(rdata),.fifo_we(rfw),.fifo_wdata(rd),.protocol_fault(rfault));
 integer n=0,checks=0,transactions=0,writes=0,delay_count=-1,done_count=0;
 reg[31:0]rng=32'h28f13a9d;reg[18:0]pending_addr;
 always @(posedge clk)begin
  if(rst_n)begin if(ack)transactions=transactions+1;if(fw)writes=writes+1;if(td)done_count=done_count+1;end
  #1;
  if({td,sl,step,rv,addr,fw,data,fault}!={rtd,rsl,rstep,rrv,raddr,rfw,rd,rfault})$fatal(1,"AB reader mismatch B=%0d L=%0d S=%0d n=%0d addr=%0d ref=%0d",B,L,S,n,addr,raddr);
  if(rst_n&&dut.row_base!==dut.row*B)$fatal(1,"Independent row-base invariant mismatch");
  if(fault)$fatal(1,"Protocol fault");checks=checks+1;
 end
 always @(negedge clk)begin
  n=n+1;rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};ack=0;rsp=0;
  if(n==4||n==CYCLES/2+4)rst_n=1;
  if(n==CYCLES/2)begin rst_n=0;delay_count=-1;end
  if(!rst_n)begin en=0;ff=0;used=0;tr=0;end
  else begin
   en=rng[4:0]!=0;ff=rng[5:0]==0;used=rng[7:0]==0?4090:3000;
   if(n%1500==100)begin tr=1;target=target+1'b1;end
   if(n%1500==1400)tr=0;
   if(delay_count>=0)begin
    if(delay_count==0)begin rsp=1;delay_count=-1;rdata={4{13'b0,pending_addr}};end
    else delay_count=delay_count-1;
   end else if(rv&&rng[8])begin ack=1;pending_addr=addr;delay_count=1+rng[12:9];end
  end
  if(n==CYCLES)begin
   if(transactions<10||writes<40)$fatal(1,"Insufficient traffic");
   $display("PASS v122 reader B=%0d L=%0d S=%0d checks=%0d transactions=%0d pairs=%0d transition_done=%0d reset=2",B,L,S,checks,transactions,writes,done_count);$finish;
  end
 end
endmodule