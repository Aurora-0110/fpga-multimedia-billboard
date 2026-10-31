`timescale 1ns/1ps
// v099: actual POST-GAIN stereo PCM activity, not I2S clock/sample presence.
// Absolute L/R independently avoids stereo phase cancellation. Thresholds are
// integer 24-bit PCM units. Hysteresis/4-sample attack rejects isolated clicks;
// 19200 quiet samples at 48kHz hold through 400ms gaps. Missing samples instead
// have a 100ms clock watchdog. No multiplier, RAM, audio delay or backpressure.
module pcm_activity_gate #(
 parameter ON_THRESHOLD=4096, OFF_THRESHOLD=2048, ATTACK_SAMPLES=4,
 parameter RELEASE_SAMPLES=19200, TIMEOUT_CYCLES=7425000
)(input wire clk,rst_n,input wire signed[23:0]pcm_l,pcm_r,
 input wire pcm_valid,stream_active,track_change,output reg sound_active);
 localparam AW=ATTACK_SAMPLES>1?$clog2(ATTACK_SAMPLES+1):1;
 localparam QW=RELEASE_SAMPLES>1?$clog2(RELEASE_SAMPLES+1):1;
 localparam WW=TIMEOUT_CYCLES>1?$clog2(TIMEOUT_CYCLES+1):1;
 wire[23:0]mag_l=pcm_l[23]?(~pcm_l+24'd1):pcm_l;
 wire[23:0]mag_r=pcm_r[23]?(~pcm_r+24'd1):pcm_r;
 wire above_on=(mag_l>=ON_THRESHOLD)||(mag_r>=ON_THRESHOLD);
 wire above_off=(mag_l>=OFF_THRESHOLD)||(mag_r>=OFF_THRESHOLD);
 reg[AW-1:0]attack_count;reg[QW-1:0]quiet_count;reg[WW-1:0]watchdog;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin sound_active<=0;attack_count<=0;quiet_count<=0;watchdog<=TIMEOUT_CYCLES;end
 else if(!stream_active||track_change)begin
  sound_active<=0;attack_count<=0;quiet_count<=0;watchdog<=TIMEOUT_CYCLES;
 end else if(pcm_valid)begin
  watchdog<=0;
  if(sound_active)begin
   attack_count<=0;
   if(above_off)quiet_count<=0;
   else if(quiet_count>=RELEASE_SAMPLES-1)begin sound_active<=0;quiet_count<=0;end
   else quiet_count<=quiet_count+1'b1;
  end else begin
   quiet_count<=0;
   if(!above_on)attack_count<=0;
   else if(attack_count>=ATTACK_SAMPLES-1)begin sound_active<=1;attack_count<=0;end
   else attack_count<=attack_count+1'b1;
  end
 end else if(watchdog<TIMEOUT_CYCLES)begin
  watchdog<=watchdog+1'b1;
  if(watchdog>=TIMEOUT_CYCLES-1)begin sound_active<=0;attack_count<=0;quiet_count<=0;end
 end
endmodule
