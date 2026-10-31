`timescale 1ns/1ps
module tb_v125_dft;
 reg clk=0;always #5 clk=~clk;reg rst=0,valid=0,active=0,epoch=0;
 reg signed[23:0]l=0,r=0;wire[127:0]levels;wire lv,overrun,bv;wire[3:0]bi;wire[36:0]energy;
 pcm_spectrum_dft d(clk,rst,l,r,valid,active,epoch,levels,lv,overrun,bv,bi,energy);
 wire[127:0]ref_levels;wire ref_lv,ref_overrun,ref_bv;wire[3:0]ref_bi;wire[36:0]ref_energy;
 pcm_spectrum_dft_v124_reference reference(clk,rst,l,r,valid,active,epoch,ref_levels,ref_lv,ref_overrun,ref_bv,ref_bi,ref_energy);
 integer ab_cycles=0;
 always @(posedge clk)if(rst)begin #2;
  if({lv,overrun,bv}!=={ref_lv,ref_overrun,ref_bv})$fatal(1,"DFT valid/overrun/epoch timing changed");
  if(lv&&levels!==ref_levels)$fatal(1,"DFT published levels not equivalent");
  if(bv&&{bi,energy}!=={ref_bi,ref_energy})$fatal(1,"DFT published bin not equivalent");
  ab_cycles++;
 end
 reg[47:0]stim[0:16383];reg[36:0]expect_energy[0:1023];reg[127:0]expect_levels[0:63];
 integer cancel_state,want_state;
 integer cases,ci=0,got=0,published=0,checks=0,spacing=300,j,k,stage=0;
 reg checking=0;reg[4095:0]path;
 always @(posedge clk)begin #1;
  if(checking&&bv)begin
   if(bi!==got[3:0]||energy!==expect_energy[ci*16+got])$fatal(1,"DFT ci=%0d band=%0d energy=%0d expect=%0d",ci,got,energy,expect_energy[ci*16+got]);
   got=got+1;checks++;
  end
  if(checking&&lv)begin
   if(got!=16||levels!==expect_levels[ci])$fatal(1,"DFT levels ci%0d got%h expect%h bins%d",ci,levels,expect_levels[ci],got);
   published++;if(stage==1)got=0;
  end
 end
 task tick(input integer n);repeat(n)@(negedge clk);endtask
 task start_epoch;begin epoch=1;tick(1);epoch=0;got=0;published=0;end endtask
 task sample(input[47:0]v,input integer interval);begin l=v[23:0];r=v[47:24];valid=1;tick(1);valid=0;tick(interval-1);end endtask
 initial begin
  if(!$value$plusargs("DATA=%s",path))$fatal; $readmemh(path,stim);
  if(!$value$plusargs("ENERGY=%s",path))$fatal; $readmemh(path,expect_energy);
  if(!$value$plusargs("LEVEL=%s",path))$fatal; $readmemh(path,expect_levels);
  if(!$value$plusargs("CASES=%d",cases))$fatal;
  tick(3);rst=1;active=1;tick(2);
  // Real-rate first frame, then accelerated capture still slower than DFT.
  for(ci=0;ci<cases;ci++)begin
   checking=0;start_epoch;checking=1;
   for(j=0;j<256;j++)sample(stim[ci*256+j],ci==0?1547:300);
   wait(published==1);tick(2);if(overrun)$fatal(1,"unexpected overrun");
  end
  checking=0;ci=cases-1;
  // Cancel a computed-but-unpublished bank; no stale epoch may be published.
  start_epoch;for(j=0;j<256;j++)sample(stim[ci*256+j],1);
  tick(3000);epoch=1;tick(1);epoch=0;tick(60000);
  if(lv||d.state!=0||d.pending)$fatal(1,"old epoch escaped cancellation");
  // Cancel incomplete capture on mute, require 256 entirely fresh samples.
  for(j=0;j<100;j++)sample(stim[ci*256+j],1);
  active=0;tick(1);active=1;tick(2);checking=1;got=0;published=0;
  for(j=0;j<256;j++)sample(stim[ci*256+j],300);
  wait(published==1);tick(2);
  // Overspeed drops extra blocks, never corrupting the bank being computed.
  checking=0;start_epoch;checking=1;
  for(j=0;j<256;j++)sample(stim[ci*256+j],1);
  for(j=0;j<768;j++)sample(48'h123456abcdef,1);
  wait(published==1);tick(2);if(!overrun)$fatal(1,"overspeed not reported");
  checking=0;start_epoch;checking=1;stage=1;
  // Ping-pong capture overlaps compute for three continuous complete blocks.
  for(k=0;k<3;k++)for(j=0;j<256;j++)sample(stim[ci*256+j],300);
  tick(60000);if(published!=3)$fatal(1,"missing continuous banks");if(overrun)$fatal(1,"normal ping-pong overrun");
  // Sweep every natural micro-state, then the final-band publish boundary.
  // The two final cases cancel via epoch and via stream_active respectively.
  checking=0;
  for(cancel_state=0;cancel_state<26;cancel_state++)begin
   start_epoch;tick(1);
   for(j=0;j<256;j++)sample(stim[ci*256+j],1);
   want_state=cancel_state<24?cancel_state:21;
   wait(d.state==want_state&&(cancel_state<24||d.band==15));
   @(negedge clk);
   if(cancel_state==25)active=0;else epoch=1;
   tick(1);epoch=0;active=1;tick(60000);
   if(lv||d.state!=0||d.pending)$fatal(1,"cancel escaped phase%0d",cancel_state);
  end
  $display("PASS DFT26 phase/final-publication epoch/mute cancellation cases");
  $display("PASS DFT valid-qualified A/B cycles=%0d including epoch, silence, incomplete-bank cancellation,overrun,continuous-bank stale-data rejection",ab_cycles);
  $display("PASS DFT exact24bit energy+levels checks=%0d cases=%0d epoch/mute/overrun/pingpong",checks,cases);$finish;
 end
 initial begin #150000000;$fatal(1,"DFT watchdog");end
endmodule
