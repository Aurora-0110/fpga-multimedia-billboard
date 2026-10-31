`timescale 1ns/1ps
module tb_v126_frontend;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,paused=0,v=0,ep=0;reg [3:0]level=10;reg signed[23:0]l=0,r=0;
 wire signed[23:0]ol,orr;wire ov,oe;
 audio_pcm_frontend #(.VOLUME_ENABLE(1))d(.clk_pix(clk),.rst_n(rst),.volume_level(level),.paused(paused),.demo_track(2'd0),.use_external(1'b1),.external_l(l),.external_r(r),.external_valid(v),.external_epoch(ep),.pcm_l(ol),.pcm_r(orr),.pcm_valid(ov),.pcm_epoch(oe),.bclk(),.lrclk(),.sdata());
 integer i,seed=9867,go=256,gain=256,checks=0;reg pp=0,pending=0,expected_epoch,previous_valid=0,previous_epoch=0;longint signed previous_l=0,previous_r=0;
 longint signed a,b;
 initial begin
  #13;rst=1;repeat(3)@(negedge clk);pending=1;
  for(i=0;i<2400;i++)begin
   @(negedge clk);v=i%5!=0;paused=i>=300&&i<400||i>=1350&&i<1390;
   ep=i==71||i==150||i==900;level=i<500?10:(i<1200?0:5);l=$random(seed);r=$random(seed);
   go=level==10?256:(level==0?0:128);
   if(paused!=pp||ep)pending=1;
   expected_epoch=0;
   if(v)begin
    if(gain<go)gain++;else if(gain>go)gain--;
    a=paused?0:$signed(l);b=paused?0:$signed(r);a=(a*gain)>>>10;b=(b*gain)>>>10;
    expected_epoch=pending;pending=0;
   end
   pp=paused;
   @(posedge clk);#1;
   if(ov!==previous_valid||oe!==previous_epoch)$fatal(1,"frontend sample/epoch alignment %0d",i);
   if(previous_valid&&(ol!==previous_l||orr!==previous_r))$fatal(1,"frontend pause/volume mismatch %0d",i);
   if(ov)checks++;
   previous_valid=v;previous_epoch=expected_epoch;previous_l=a;previous_r=b;
  end
  $display("PASS frontend %0d active-volume stereo samples with pause/resume/epoch/gaps and aligned two-cycle latency",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
