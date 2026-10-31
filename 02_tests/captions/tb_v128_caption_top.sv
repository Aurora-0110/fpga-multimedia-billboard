`timescale 1ns/1ps
// Actual idx_audio_visual_top caption wiring. No memory/TF/hardware is emulated as passing.
module pll_sdram(input clk_in,rst_n,output clk_sd,clk_24,locked);
 reg sd=0;always #10.101 sd=~sd;assign clk_sd=sd;assign clk_24=clk_in;assign locked=rst_n;
endmodule
module EG_PHY_SDRAM_2M_32(input clk,ras_n,cas_n,we_n,input[10:0]addr,input[1:0]ba,inout[31:0]dq,input cs_n,dm0,dm1,dm2,dm3,cke);endmodule
module tb_v128_caption_top;
 reg clk24m=0;always #20.833333 clk24m=~clk24m;
 idx_audio_visual_top #(.START_BITS(4),.KEY_CNT(4),.UI_HOLD_CYCLES(40),.USE_TF(1))dut(.clk24m(clk24m),.key0_n(1'b1),.key1_n(1'b1),.tf_miso(1'b1),.tf_cs_n(),.tf_sck(),.tf_mosi(),.led_sclk(),.led_dout(),.led_latch(),.hdmi_clk_p(),.hdmi_d_p());
 reg [1:0]choice=0;reg ready=0,real_sample=0,first=0,finished=0,pause=0,keepalive=0;reg[7:0]error=0;reg[3:0]volume=10;
 reg picture=0,osd=1;reg signed[23:0]left_sample=0,right_sample=0;
 reg[31:0]expected=0;reg[1:0]previous=0;reg old_real,old_first,monitor=0;integer n,checks=0,sent=0,muted=0,frozen=0;
 task tick(input integer k);repeat(k)@(negedge dut.pix);endtask
 always @(posedge dut.pix)if(monitor)begin
  old_real=dut.caption_real_pipe[1];old_first=dut.caption_first_pipe[1];
  if(choice!=1||choice!=previous||!ready||finished||error!=0)expected=0;
  else if(old_real)begin if(old_first)expected=1;else expected=expected+1;end
  previous=choice;
  #0.1;
  if(dut.caption_samples!==expected)$fatal(1,"ACTUAL top consumed sample mismatch actual=%0d expected=%0d",dut.caption_samples,expected);
  if(dut.caption_real_pipe[1]&&!dut.pcm_valid)$fatal(1,"ACTUAL top gain/event misalignment");
  if(dut.captions.enable!==(osd&&choice==1))$fatal(1,"ACTUAL subtitle enable independent of demo or UI");
  checks=checks+1;
 end
 initial begin
  force dut.ui_audio_choice=choice;force dut.ui_audio_paused=pause;force dut.ui_volume=volume;
  force dut.wav_session_ready=ready;force dut.wav_consumed=real_sample;force dut.wav_epoch=first;
  force dut.wav_finished=finished;force dut.wav_error=error;force dut.wav_under=0;
  force dut.wav_valid=keepalive;force dut.wav_l=left_sample;force dut.wav_r=right_sample;
  force dut.op=picture;force dut.active_osd_enabled=osd;
  force dut.len=0;wait(dut.rp&&dut.rs);tick(8);monitor=1;
  choice=1;ready=1;tick(8);
  for(n=0;n<60000;n=n+1)begin
   keepalive=(n%53==0);real_sample=keepalive&&!pause&&n>=500&&n<59500;
   first=real_sample&&sent==0;if(real_sample)sent=sent+1;
   left_sample=real_sample&&n%2?24'sd1000000:0;right_sample=-left_sample;
   if(n==5000)picture=1;if(n==12000)picture=0;if(n==20000)picture=1;
   if(n==8000)pause=1;if(n==15000)pause=0;
   if(n==22000)volume=0;if(n==32000)volume=10;
   if(n==36000)osd=0;if(n==44000)osd=1;
   if(volume==0&&real_sample)muted=muted+1;if(pause&&keepalive)frozen=frozen+1;
   tick(1);
  end
  real_sample=0;first=0;keepalive=0;tick(10);
  if(dut.caption_samples!==sent||muted<100||frozen<50)$fatal(1,"ACTUAL top accounting sent=%0d pos=%0d mute=%0d freeze=%0d",sent,dut.caption_samples,muted,frozen);
  choice=2;tick(8);if(dut.caption_samples||dut.subtitle_active)$fatal(1,"AD stale MUSIC");
  choice=3;tick(8);if(dut.caption_samples||dut.subtitle_active)$fatal(1,"EXTRA stale MUSIC");
  choice=1;tick(8);first=1;real_sample=1;keepalive=1;tick(1);first=0;real_sample=0;keepalive=0;tick(8);
  if(dut.caption_samples!=1)$fatal(1,"first sample not counted on restart");
  finished=1;tick(8);if(dut.caption_samples||dut.subtitle_active)$fatal(1,"EOF not cleared");
  $display("PASS v128 ACTUAL top caption/gain/event wiring checks=%0d real_samples=%0d muted=%0d pause_keepalive=%0d picture_loss_OSD_not_reset_no_DEMO",checks,sent,muted,frozen);$finish;
 end
 initial begin #2000000;$fatal(1,"top caption watchdog");end
endmodule
