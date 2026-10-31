`timescale 1ns/1ps
module tb_v114_boundary;
 reg sd=0,pix=0,rst=0,permit=0;always #10.101010 sd=~sd;always #6.734007 pix=~pix;
 reg[1:0]choice=0;integer target=1;wire[47:0]now_pcm,old_pcm;
 wire nv,ov,nu,ou,nf,ofin;wire[7:0]ne,oe;
 tf_wav_playback #(.FIFO_AW(5),.PREFILL(1),.LOW_WATER(24)) now_dut(
 .clk_sd(sd),.clk_pix(pix),.rst_n(rst),.choice(choice),.paused(1'b0),.mounted(1'b1),
 .root_cluster(32'd2),.data_base(32'd600),.fat_base(32'd32),.cluster_max(32'd70000),.spc(8'd1),.shift(4'd0),
 .bus_reset_n(),.read_req(),.read_lba(),.urgent(),.sd_ready(1'b1),.sd_done(1'b0),.sd_error(4'd0),.data_valid(1'b0),.data_index(9'd0),.data_byte(8'd0),
 .left(now_pcm[47:24]),.right(now_pcm[23:0]),.valid(nv),.epoch(),.playing(),.underrun(nu),.error_pix(ne),.finished(nf),
 .audio_used(),.audio_minimum(),.first_underflow_used(),.first_underflow_flags());
 old_tf_wav_playback #(.FIFO_AW(5),.PREFILL(1),.LOW_WATER(24)) old_dut(
 .clk_sd(sd),.clk_pix(pix),.rst_n(rst),.choice(choice),.paused(1'b0),.mounted(1'b1),
 .root_cluster(32'd2),.data_base(32'd600),.fat_base(32'd32),.cluster_max(32'd70000),.spc(8'd1),.shift(4'd0),
 .bus_reset_n(),.read_req(),.read_lba(),.urgent(),.sd_ready(1'b1),.sd_done(1'b0),.sd_error(4'd0),.data_valid(1'b0),.data_index(9'd0),.data_byte(8'd0),
 .left(old_pcm[47:24]),.right(old_pcm[23:0]),.valid(ov),.epoch(),.playing(),.underrun(ou),.error_pix(oe),.finished(ofin));
 integer n=0,o=0,phase=0,cases=0,old_faults=0,waited=0;
 reg signed[23:0] want;
 always @(negedge pix)if(rst)begin
  if(now_dut.staged>3||now_dut.staged+now_dut.pending>3)$fatal(1,"sample capacity");
  if(nv&&now_pcm!=0)begin
   want=24'h100000+n;
   if(now_pcm!=={want,-want})$fatal(1,"new sample phase=%0d n=%0d got=%h",phase,n,now_pcm);
   n=n+1;
  end
  if(ov&&old_pcm!=0)begin
   want=24'h100000+o;
   if(old_pcm!=={want,-want})$fatal(1,"old sample phase=%0d n=%0d got=%h",phase,o,old_pcm);
   o=o+1;
  end
  if(nu||ne||oe)$fatal(1,"unexpected new underflow/error phase=%0d",phase);
 end
 task one(input integer p,input integer frames);begin
  @(posedge pix);#0.1;rst=0;choice=0;permit=0;n=0;o=0;target=frames;phase=p;
  repeat(10)@(negedge pix);rst=1;choice=1;
  wait(now_dut.pr&&old_dut.pr);repeat(p)@(negedge pix);permit=1;
  waited=0;
  while(!(nf&&ofin)&&waited<40000)begin @(negedge pix);waited=waited+1;end
  if(waited>=40000||n!=frames||o!=frames)$fatal(1,"finish p=%0d target=%0d n=%0d o=%0d",p,frames,n,o);
  if(ou)begin old_faults=old_faults+1;$display("OLD boundary A3 phase=%0d frames=%0d",p,frames);end
  cases=cases+1;
 end endtask
 initial begin
  for(integer p=0;p<1440;p=p+64)one(p,1);
  for(integer p=1440;p<1547;p=p+1)one(p,1);
  for(integer f=2;f<=3;f=f+1)begin one(0,f);one(1440,f);one(1480,f);one(1500,f);one(1520,f);one(1546,f);end
  one(0,17);one(1440,17);one(1480,17);one(1500,17);one(1520,17);one(1546,17);
  if(old_faults==0)$fatal(1,"negative control never exercised old boundary");
  $display("PASS differential real FIFO production clocks: cases=%0d old_A3=%0d new_A3=0 short lengths1..17; controlled reader NOT physical-root proof",cases,old_faults);$finish;
 end
endmodule
