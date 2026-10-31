`timescale 1ns/1ps
module tb_power_level;
 reg clk=0;always #5 clk=~clk;reg rst=0,start=0,cancel=0;
 reg[36:0]p=0;wire done;wire[7:0]level;
 spectrum_power_level d(clk,rst,start,cancel,p,done,level);
 integer checks=0,i,j,latency;reg[63:0]rnd=64'h092102577aaccee1;
 reg[36:0]v;
 function[7:0]reference;input[36:0]value;integer m,k;reg[8:0]a;begin
 m=0;for(k=0;k<37;k=k+1)if(value[k])m=k;
 if(value<256)reference=0;
 else begin a=(m-8)*6+((value>>(m-2))&3);reference=a>144?144:a[7:0];end
 end endfunction
 task check(input[36:0]value);begin
  @(negedge clk);p=value;start=1;@(negedge clk);start=0;latency=0;
  while(!done&&latency<40)begin @(negedge clk);latency++;end
  if(!done||level!==reference(value))$fatal(1,"log power=%d got=%d expected=%d latency%d",value,level,reference(value),latency);
  checks++;
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst=1;
  for(i=0;i<512;i++)check(i);
  for(i=1;i<37;i++)begin
   v=37'd1<<i;check(v-1);check(v);if(i<36)check(v+1);
   if(i>=2)begin check(v+(v>>2));check(v+(v>>1));check(v+(v>>1)+(v>>2));end
  end
  check(37'h1fffffffff);
  for(i=0;i<2048;i++)begin
   rnd=rnd^(rnd<<13);rnd=rnd^(rnd>>7);rnd=rnd^(rnd<<17);check(rnd[36:0]);
  end
  // Synchronous epoch abort cannot publish a stale level.
  @(negedge clk);p=37'h1fffffffff;start=1;
  @(negedge clk);start=0;repeat(4)@(negedge clk);cancel=1;
  @(negedge clk);cancel=0;repeat(45)begin @(negedge clk);if(done||level!=0)$fatal(1,"cancel stale");end
  check(256);check(37'h1fffffffff);
  $display("PASS power_level exact37bit boundaries/random checks=%0d max_latency<40 cancel",checks);$finish;
 end
 initial begin #5000000;$fatal(1,"power level timeout");end
endmodule
