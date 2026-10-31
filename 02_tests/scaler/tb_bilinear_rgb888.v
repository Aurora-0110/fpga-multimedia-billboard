`timescale 1ns/1ps
module tb_bilinear_rgb888;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,in_valid=0,out_ready=0;
 wire in_ready,out_valid;reg [23:0]p00,p10,p01,p11;reg[7:0]fx,fy;
 reg[31:0]in_tag;wire[23:0]out_rgb;wire[31:0]out_tag;
 reg[135:0] vectors[0:99999];integer n,epoch,issue,expect_idx,limit,total=0,cycles;
 reg hold_in,held_out;reg[55:0]last_out;reg[31:0]rng=32'h38bcaa11;
 bilinear_rgb888 dut(.*);
 function[31:0]prng;input[31:0]v;reg[31:0]q;begin q=v^(v<<13);q=q^(q>>17);prng=q^(q<<5);end endfunction
 initial begin
  if(!$value$plusargs("N=%d",n))$fatal(1,"missing N");
  $readmemh("kernel_vectors.hex",vectors,0,n-1);
  for(epoch=0;epoch<4;epoch=epoch+1)begin
   @(negedge clk);rst_n=0;in_valid=0;out_ready=0;held_out=0;hold_in=0;
   repeat(3)@(negedge clk);rst_n=1;
   issue=0;expect_idx=0;cycles=0;limit=(epoch==0)?n:511;
   while(expect_idx<limit)begin
    // epoch1 and2 reset a nonempty pipeline after 40 cycles; epoch3 drains.
    if(!hold_in)begin
     rng=prng(rng);in_valid=(issue<limit)&&((epoch==0&&cycles<1000)||rng[2:0]!=0);
     if(in_valid)begin
      {p00,p10,p01,p11,fx,fy}=vectors[issue][135:24];in_tag=issue;
     end
    end
    rng=prng(rng);out_ready=(epoch==0&&cycles<1000)?1:(rng[2:0]>2);
    if(epoch==0&&cycles>=1000&&cycles<1120)out_ready=0;
    if(epoch==2&&cycles>=32)out_ready=0;
    @(posedge clk);
    if(held_out&&{out_valid,out_tag,out_rgb}!=={1'b1,last_out})$fatal(1,"output changed while stalled");
    held_out=out_valid&&!out_ready;last_out={out_tag,out_rgb};
    if(epoch==0&&cycles>=4&&cycles<1000&&!out_valid)$fatal(1,"throughput bubble");
    if(out_valid&&out_ready)begin
     if(out_tag!==expect_idx||out_rgb!==vectors[expect_idx][23:0])
      $fatal(1,"kernel epoch=%0d item=%0d tag=%0d got=%h exp=%h",epoch,expect_idx,out_tag,out_rgb,vectors[expect_idx][23:0]);
     total=total+1;expect_idx=expect_idx+1;
    end
    hold_in=in_valid&&!in_ready;
    if(in_valid&&in_ready)issue=issue+1;
    cycles=cycles+1;
    @(negedge clk);
    if(cycles>3*n+1000)$fatal(1,"kernel timeout");
    if((epoch==1||epoch==2)&&cycles==40)begin
     if(issue<=expect_idx)$fatal(1,"reset test requires inflight data");
     expect_idx=limit;
    end
   end
   in_valid=0;out_ready=1;
   if(epoch==0&&cycles<n)$fatal(1,"bad cycle counter");
  end
  $display("PASS kernel compared=%0d epochs=4 stalls reset_inflight throughput_first1000",total);$finish;
 end
endmodule

