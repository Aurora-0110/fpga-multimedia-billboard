`timescale 1ns/1ps
// Same production two-stage PCM path and consume/first-event delay as board top.
module tb_v130_caption_alignment;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,pause=0,valid=0,real_sample=0,first=0,ready=0,finished=0;reg[1:0]choice=0;
 reg[3:0]volume=10;reg[7:0]error=0;reg signed[23:0]l=0,r=0;
 wire signed[23:0]ol,orr;wire ov,oe;
 audio_pcm_frontend #(.VOLUME_ENABLE(1)) front(.clk_pix(clk),.rst_n(rst),.volume_level(volume),.paused(pause),.demo_track(2'd0),.use_external(choice!=0),.external_l(l),.external_r(r),.external_valid(valid),.external_epoch(first),.pcm_l(ol),.pcm_r(orr),.pcm_valid(ov),.pcm_epoch(oe),.bclk(),.lrclk(),.sdata());
 reg[1:0]real_pipe,first_pipe;
 always @(posedge clk or negedge rst)if(!rst)begin real_pipe<=0;first_pipe<=0;end else begin real_pipe<={real_pipe[0],real_sample};first_pipe<={first_pipe[0],first};end
 wire[31:0]pos;wire active;wire[10:0]off;wire[4:0]len;wire[5:0]idx;
 pcm_caption_player captions(.clk(clk),.rst_n(rst),.choice(choice),.session_ready(ready),.sample_consumed(real_pipe[1]),.first_sample(first_pipe[1]),.finished(finished),.error_code(error),.sample_position(pos),.cue_active(active),.text_offset(off),.text_length(len),.cue_index(idx));
 integer n,sent=0,accepted=0,checks=0;reg[1:0]lastchoice=0;reg[31:0]expected=0;reg preal,pfirst;
 always @(posedge clk)begin
  preal=real_pipe[1];pfirst=first_pipe[1];
  if(!rst)begin expected=0;lastchoice=0;end
  else begin
   if((choice!=1&&choice!=3)||choice!=lastchoice||!ready||finished||error!=0)expected=0;
   else if(preal)begin if(pfirst)expected=1;else expected=expected+1;accepted=accepted+1;end
   lastchoice=choice;
  end
  #1;
  if(rst)begin
   if(pos!==expected)$fatal(1,"aligned counter mismatch");
   if(real_pipe[1]&&!ov)$fatal(1,"consume tag not aligned with gain valid");
   checks=checks+1;
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst=1;choice=1;ready=1;
  for(n=0;n<40000;n=n+1)begin
   @(negedge clk);valid=(n%53==0);real_sample=valid&&!pause&&n>=500&&n<39500;
   first=real_sample&&sent==0;if(real_sample)sent=sent+1;
   l=real_sample&&n%2?24'sd1200000:0;r=-l;
   if(n==9000)pause=1;if(n==13000)pause=0;
   if(n==20000)volume=0; // Mute must NOT stop caption progress.
   if(n==27000)volume=10;
  end
  @(negedge clk);valid=0;real_sample=0;first=0;repeat(10)@(negedge clk);
  if(pos!==sent||accepted!=sent)$fatal(1,"first/zero/mute/pause accounting sent=%0d accepted=%0d pos=%0d",sent,accepted,pos);
  choice=3;repeat(6)@(negedge clk);if(pos||active)$fatal(1,"third source reset");
  sent=0;accepted=0;
  for(n=0;n<14000;n=n+1)begin
   @(negedge clk);valid=(n%47==0);real_sample=valid&&!pause;
   first=real_sample&&sent==0;if(real_sample)sent=sent+1;
   l=0;r=0; // Real zero-valued PCM still advances, unlike keepalive.
   if(n==2000)pause=1;if(n==5000)pause=0;
   if(n==6000)volume=0;if(n==10000)volume=10;
  end
  @(negedge clk);valid=0;real_sample=0;first=0;repeat(10)@(negedge clk);
  if(pos!==sent||accepted!=sent)$fatal(1,"third alignment/real zero accounting");
  choice=2;repeat(4)@(negedge clk);if(pos||active)$fatal(1,"AD source reset");
  $display("PASS v130 gain/caption alignment clocks=%0d exact_real_zero_and_muted_samples=%0d pause_keepalive_does_not_count",checks,sent);$finish;
 end
endmodule
