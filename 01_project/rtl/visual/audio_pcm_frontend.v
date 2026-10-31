`timescale 1ns/1ps
// Fixed 48k/24-bit stereo contract. External TF PCM and internal I2S demo
// share pause silence and identical DFT/HDMI output samples. Pause never stops I2S.
// VOLUME_ENABLE=1 (board top) adds 11-level smooth gain below the original -12dB
// ceiling. Legacy parameter0 is retained only for independent baseline tests.
module audio_pcm_frontend #(parameter DEMO_BEAT_SAMPLES=3000,VOLUME_ENABLE=0)(
 input clk_pix,rst_n,input [3:0] volume_level,input paused,input [1:0]demo_track,input use_external,
 input signed [23:0]external_l,external_r,input external_valid,external_epoch,
 output signed [23:0]pcm_l,pcm_r,output pcm_valid,output wire pcm_epoch,
 output bclk,lrclk,sdata);
 wire [1:0]serial_track;wire signed [23:0]il,ir;wire iv;
 i2s_visual_demo #(.BEAT_SAMPLES(DEMO_BEAT_SAMPLES)) source(.clk_pix(clk_pix),.rst_n(rst_n),.track(demo_track),.paused(paused),
 .bclk(bclk),.lrclk(lrclk),.sdata(sdata),.sample_track(serial_track));
 i2s_pcm_receive receiver(.clk_pix(clk_pix),.rst_n(rst_n),.bclk(bclk),.lrclk(lrclk),.sdata(sdata),.left(il),.right(ir),.valid(iv));
 wire signed [23:0]chosen_l=paused?24'sd0:(use_external?external_l:il);
 wire signed [23:0]chosen_r=paused?24'sd0:(use_external?external_r:ir);
 wire chosen_valid=use_external?external_valid:iv;
 generate if(VOLUME_ENABLE)begin:adjustable
 pcm_volume gain(.volume_level(volume_level),.clk_pix(clk_pix),.rst_n(rst_n),.left_in(chosen_l),.right_in(chosen_r),
 .valid_in(chosen_valid),.left(pcm_l),.right(pcm_r),.valid(pcm_valid));
 end else begin:legacy
 pcm_attenuate gain(.clk_pix(clk_pix),.rst_n(rst_n),.left_in(chosen_l),.right_in(chosen_r),
 .valid_in(chosen_valid),.left(pcm_l),.right(pcm_r),.valid(pcm_valid));
 end endgenerate
 reg sample_epoch;
 reg [1:0]seen_track;reg pending_epoch,source_prev,pause_prev;
 always @(posedge clk_pix or negedge rst_n)
 if(!rst_n)begin seen_track<=0;pending_epoch<=0;source_prev<=0;pause_prev<=0;sample_epoch<=0;end
 else begin
  sample_epoch<=0;source_prev<=use_external;pause_prev<=paused;
  if(paused!=pause_prev||use_external!=source_prev||external_epoch&&use_external)pending_epoch<=1;
  if(chosen_valid)begin
   // Simultaneous with gain.valid: a change discards this first sample in DFT,
   // requiring a fresh complete 256-sample window. It does not reset HDMI.
   sample_epoch<=pending_epoch||(paused!=pause_prev)||(use_external!=source_prev)||
     (use_external?external_epoch:serial_track!=seen_track);
   seen_track<=serial_track;pending_epoch<=0;
  end
 end
 // Gain has two cycles only in the active production branch. Delay the epoch
 // by the identical extra cycle; no left/right/valid/track tag skew is allowed.
 generate if(VOLUME_ENABLE)begin:epoch_align
  reg epoch_q;
  always @(posedge clk_pix or negedge rst_n)
  if(!rst_n)epoch_q<=0;else epoch_q<=sample_epoch;
  assign pcm_epoch=epoch_q;
 end else begin:epoch_legacy
  assign pcm_epoch=sample_epoch;
 end endgenerate
endmodule

// Audible, explicitly labelled demo, NOT simulated/fake spectrum animation.
// A/B/C/D select 375/750/1125/1875Hz. Real 120BPM volume envelopes are encoded
// on I2S and therefore heard and analyzed together. Slots are32 bits with24
// payload bits and a one-bit delay. Source changes occur only at stereo start.
module i2s_visual_demo #(parameter BEAT_SAMPLES=3000)(input clk_pix,rst_n,input paused,input [1:0]track,
 output reg bclk,lrclk,sdata,output reg[1:0]sample_track);
 `include "visual/dft_cos_q10.vh"
 reg [26:0]acc;wire [27:0]sum={1'b0,acc}+28'd6144000;
 reg [5:0]slot;wire [5:0]next_slot=slot+6'd1;
 reg [7:0]phase;reg [11:0]beat_count;reg[2:0]beat;
 reg signed [23:0]word;
 wire changing=sample_track!=track;
 wire [7:0]step=track==0?8'd2:track==1?8'd4:track==2?8'd6:8'd10;
 wire [1:0]atten=beat[2]?beat[1:0]:~beat[1:0];
 wire signed[11:0]c=cos_q10(changing?8'd0:phase);
 wire signed[23:0]fullword={{12{c[11]}},c}<<<10;
 always @(posedge clk_pix or negedge rst_n)
 if(!rst_n)begin acc<=0;bclk<=1;lrclk<=1;sdata<=0;slot<=63;phase<=0;word<=0;
  beat_count<=0;beat<=0;sample_track<=0;end
 else if(sum>=28'd74250000)begin
  acc<=sum-28'd74250000;bclk<=~bclk;
  if(bclk)begin
   slot<=next_slot;lrclk<=next_slot[5];
   if(next_slot==0)begin
    sample_track<=track;word<=paused?24'sd0:(fullword>>>(changing?2'd3:atten));
    if(!paused)phase<=changing?step:phase+step;
    if(paused)begin end
    else if(changing)begin beat_count<=0;beat<=0;end
    else if(beat_count==BEAT_SAMPLES-1)begin beat_count<=0;beat<=beat+1'b1;end
    else beat_count<=beat_count+1'b1;
   end
   if(next_slot[4:0]>=1&&next_slot[4:0]<=24)sdata<=word[24-next_slot[4:0]];
   else sdata<=0;
  end
 end else acc<=sum[26:0];
endmodule
