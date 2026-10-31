`timescale 1ns/1ps
module tb_fifo_prefix;
 parameter AW=12; parameter integer PHASE_PS=1375;
 reg wc=0,rc=0;always #5.5 wc=~wc;initial begin #(PHASE_PS/1000.0);forever #7.25 rc=~rc;end
 reg wrst=0,rrst=0,we=0,re=0;reg[47:0]wd=0;
 wire of,nf,oe,ne;wire[AW:0]ou,nu,orused,nrused;wire[47:0]od,nd;
 async_fifo_v125_reference #(.AW(AW),.WIDTH(48)) old(wc,wrst,we,wd,of,ou,rc,rrst,re,od,oe,orused);
 async_fifo #(.AW(AW),.WIDTH(48)) candidate(wc,wrst,we,wd,nf,nu,rc,rrst,re,nd,ne,nrused);
 reg [AW:0] oracle; integer j;
 integer i,k=0,mode=0,ws=8917,rs=9081,wchecks=0,rchecks=0,writes=0,reads=0;
 always @(negedge wc)begin
  if(!wrst)begin we=0;wd=0;end
  else begin we=mode==1?1:(mode==3?($random(ws)&1):0);wd={$random(ws),16'($random(ws))};end
 end
 always @(negedge rc)begin
  if(!rrst)re=0;else re=mode==2?1:(mode==3?($random(rs)&1):0);
 end
 always @(posedge wc)begin
  if(wrst&&we&&!of)writes++;
  #0.1;if({of,ou}!=={nf,nu})$fatal(1,"write flag/count mismatch AW%0d",AW);wchecks++;
 end
 always @(posedge rc)begin
  if(rrst&&re&&!oe)reads++;
  #0.1;if({oe,orused,od}!=={ne,nrused,nd})$fatal(1,"read data/flag/count mismatch AW%0d",AW);rchecks++;
 end
 initial begin
  for(i=0;i<(1<<(AW+1));i++)begin
   for(j=0;j<=AW;j++)oracle[j]=^(i>>j);
   if(old.gray2bin(i)!==oracle || candidate.gray2bin(i)!==oracle)$fatal(1,"gray conversion oracle AW%0d g%h",AW,i);
  end
  #35.7;wrst=1;rrst=1;mode=1;
  repeat((1<<AW)+8)@(negedge wc);#1;if(!of)$fatal(1,"full not covered");
  mode=2;repeat((1<<AW)+8)@(negedge rc);#1;if(!oe)$fatal(1,"empty not covered");
  mode=3;repeat(3)begin
   repeat(12000)@(negedge wc);#2.375;wrst=0;rrst=0;#31.75;wrst=1;rrst=1;
  end
  repeat(12000)@(negedge wc);
  if(writes<1000||reads<1000)$fatal(1,"coverage");
  $display("PASS FIFO prefix AW%0d exhaustive_gray=%0d same-cycle writes=%0d reads=%0d wchecks=%0d rchecks=%0d full/empty/wrap/async-reset/independent-clock-phase",AW,1<<(AW+1),writes,reads,wchecks,rchecks);$finish;
 end
 initial begin #2000000;$fatal(1,"bounded FIFO timeout");end
endmodule
