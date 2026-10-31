`timescale 1ns/1ps
// Count accepted, enabled PCM stereo frames, including digital silence.
// No pixel-clock wall-time estimate: 48 accepted samples == 1 ms at 48 kHz.
// Epoch wins over valid and discards the boundary sample, as the DFT does.
// Disabled playback pauses time. A future WAV source must share this contract.
module pcm_subtitle_timeline #(parameter SAMPLES_PER_MS=48)(
 input wire clk,rst_n,sample_valid,playback_enable,track_epoch,
 output reg [31:0] elapsed_ms,output reg [15:0] time_bcd,
 output wire [2:0] cue_index,output wire cue_active,output reg started,
 output reg ms_tick);
 `include "visual/subtitle_cues.vh"
 localparam SW=SAMPLES_PER_MS>1?$clog2(SAMPLES_PER_MS):1;
 reg [SW-1:0] sample_part;reg [9:0] subsecond;
 reg [2:0] index;assign cue_index=index;
 assign cue_active=started&&elapsed_ms>=cue_start(index)&&elapsed_ms<cue_end(index);
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin elapsed_ms<=0;time_bcd<=0;sample_part<=0;subsecond<=0;index<=0;started<=0;ms_tick<=0;end
 else begin
  ms_tick<=0;
  if(track_epoch)begin elapsed_ms<=0;time_bcd<=0;sample_part<=0;subsecond<=0;index<=0;started<=0;end
  else if(sample_valid&&playback_enable&&elapsed_ms!=32'hffffffff)begin
   started<=1;
   if(sample_part==SAMPLES_PER_MS-1)begin
    sample_part<=0;elapsed_ms<=elapsed_ms+1'b1;ms_tick<=1;
    if(index<CUE_COUNT-1&&elapsed_ms+32'd1>=cue_end(index))index<=index+1'b1;
    if(subsecond==999)begin
     subsecond<=0;
     if(time_bcd[3:0]!=9)time_bcd[3:0]<=time_bcd[3:0]+1'b1;
     else begin
      time_bcd[3:0]<=0;
      if(time_bcd[7:4]!=5)time_bcd[7:4]<=time_bcd[7:4]+1'b1;
      else begin
       time_bcd[7:4]<=0;
       if(time_bcd[11:8]!=9)time_bcd[11:8]<=time_bcd[11:8]+1'b1;
       else begin
        time_bcd[11:8]<=0;
        time_bcd[15:12]<=time_bcd[15:12]==9?0:time_bcd[15:12]+1'b1;
       end
      end
     end
    end else subsecond<=subsecond+1'b1;
   end else sample_part<=sample_part+1'b1;
  end
 end
endmodule
