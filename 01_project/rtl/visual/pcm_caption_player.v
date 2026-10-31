`timescale 1ns/1ps
// V129: per-track precompiled captions driven ONLY by accepted WAV stereo frames.
// MUSIC and third audio share one player; separate64-cue banks avoid an address adder.
// Pause produces no consume events; mute still consumes. HDMI keepalive/DFT epochs
// and picture visibility are deliberately NOT used as a playback clock/reset.
module pcm_caption_player(
 input wire clk,rst_n,input wire [1:0] choice,
 input wire session_ready,sample_consumed,first_sample,finished,input wire [7:0] error_code,
 output reg [31:0] sample_position,output wire cue_active,
 output reg [10:0] text_offset,output reg [4:0] text_length,
 output reg [5:0] cue_index
);
 `include "visual/music_caption_config.vh"
 (* rom_style="block" *) reg [17:0] metadata[0:511];
 initial begin
  `include "visual/music_caption_meta_init.vh"
 end
 reg [1:0] previous_choice;reg [2:0] load_step;
 reg [17:0] meta_q;reg [23:0] start_sample,end_sample;
 reg started;
 wire caption_track=(choice==2'd1)||(choice==2'd3);
 wire good=caption_track&&session_ready&&!finished&&(error_code==0);
 wire [5:0] last_cue=(choice==2'd3)?THIRD_CUE_COUNT-1:MUSIC_CUE_COUNT-1;
 wire ready=(load_step==5);
 assign cue_active=good&&(choice==previous_choice)&&started&&ready&&(sample_position>={8'd0,start_sample})&&
                   (sample_position<{8'd0,end_sample})&&(text_length!=0);
 always @(posedge clk)meta_q<=metadata[{(choice==2'd3),cue_index,load_step[1:0]}];
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  previous_choice<=0;sample_position<=0;cue_index<=0;load_step<=0;
  start_sample<=0;end_sample<=0;text_offset<=0;text_length<=0;started<=0;
 end else begin
  previous_choice<=choice;
  if(!good||choice!=previous_choice)begin
   sample_position<=0;cue_index<=0;load_step<=0;started<=0;
  end else begin
   if(first_sample&&sample_consumed)begin
    // The first output frame is counted, not discarded like a DFT boundary.
    sample_position<=1;started<=1;cue_index<=0;load_step<=0;
   end else begin
    if(sample_consumed)begin
     started<=1;
     if(sample_position!=32'hffffffff)sample_position<=sample_position+1'b1;
    end
    // Two64-cue banks fit the existing single512x18 native9K ROM.
    case(load_step)
     0:load_step<=1;
     1:begin start_sample[17:0]<=meta_q;load_step<=2;end
     2:begin end_sample[17:0]<=meta_q;load_step<=3;end
     3:begin text_offset<=meta_q[15:5];text_length<=meta_q[4:0];load_step<=4;end
     4:begin start_sample[23:18]<=meta_q[11:6];end_sample[23:18]<=meta_q[5:0];load_step<=5;end
     5:if(started&&sample_position>={8'd0,end_sample}&&cue_index<last_cue)begin
       cue_index<=cue_index+1'b1;load_step<=0;
      end
     default:load_step<=0;
    endcase
   end
  end
 end
endmodule
