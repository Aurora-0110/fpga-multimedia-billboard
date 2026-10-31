`timescale 1ns/1ps
// Pixel-domain gestures. A stable release is required after boot/each session.
// Short actions run on RELEASE; each long action fires once while held.
// A chord observed before a single-long threshold owns the whole gesture.
// A chord added AFTER a fired single-long cannot trigger a second action.
module media_controls #(parameter DEBOUNCE_CYCLES=742500,HOLD_CYCLES=74250000)(
 input wire clk,rst_n,key0_n,key1_n,
 output reg next_toggle,mode_toggle,
 output reg signed [7:0] brightness,
 output reg [2:0] contrast_q2,output reg [1:0] edit_field,
 output reg osd_enabled,output wire [1:0] keys_down,
 output reg audio_select,output reg [1:0] audio_choice,output reg ui_toggle,output reg audio_paused,output reg [3:0] volume_level,output reg av_enabled);
 localparam DBW=DEBOUNCE_CYCLES>1?$clog2(DEBOUNCE_CYCLES):1;
 localparam HW=HOLD_CYCLES>1?$clog2(HOLD_CYCLES):1;
 localparam AW=$clog2(DEBOUNCE_CYCLES+4);
 (* ASYNC_REG="TRUE" *) reg [1:0] k0sync,k1sync;
 reg down0,down1;reg [DBW-1:0] db0,db1;
 assign keys_down={down1,down0};
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin k0sync<=3;k1sync<=3;down0<=0;down1<=0;db0<=0;db1<=0;end
 else begin
  k0sync<={k0sync[0],key0_n};k1sync<={k1sync[0],key1_n};
  if((!k0sync[1])==down0)db0<=0;
  else if(db0==DEBOUNCE_CYCLES-1)begin down0<=!k0sync[1];db0<=0;end
  else db0<=db0+1'b1;
  if((!k1sync[1])==down1)db1<=0;
  else if(db1==DEBOUNCE_CYCLES-1)begin down1<=!k1sync[1];db1<=0;end
  else db1<=db1+1'b1;
 end
 reg [AW-1:0] arm_count;reg [HW-1:0] hold_count;
 reg ready,session,chord,held,first_key;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  ready<=0;arm_count<=0;session<=0;chord<=0;held<=0;first_key<=0;hold_count<=0;
  next_toggle<=0;mode_toggle<=0;brightness<=0;contrast_q2<=4;edit_field<=0;
  osd_enabled<=1;av_enabled<=1;volume_level<=10;audio_select<=0;audio_choice<=0;ui_toggle<=0;audio_paused<=0;
 end else if(!ready)begin
  // Unsynchronized pads inhibit boot arming ONLY; never cause an action.
  if(key0_n&&key1_n&&(&k0sync)&&(&k1sync)&&!down0&&!down1)begin
   if(arm_count==DEBOUNCE_CYCLES+2)ready<=1;else arm_count<=arm_count+1'b1;
  end else arm_count<=0;
 end else if(!session)begin
  hold_count<=0;held<=0;chord<=0;
  if(down0||down1)begin session<=1;first_key<=down1;chord<=down0&&down1;end
 end else if(!down0&&!down1)begin
  session<=0;hold_count<=0;
  if(!held)begin
   // Short chord cycles independently composited visible layers, not playback.
   // 11 all ->10 base only ->01 audio-visual only ->00 clean picture ->11.
   if(chord){osd_enabled,av_enabled}<={osd_enabled,av_enabled}-2'd1;
   else if(audio_select)begin
    if(first_key)begin audio_choice<=audio_choice+1'b1; // 2-bit wrap: demo -> MUSIC -> ADVOICE -> extra WAV -> demo
      audio_paused<=0;end
    else audio_paused<=!audio_paused; // Long K0 exits; short K0 preserves the sample position.
   end else case(edit_field)
    0:if(first_key)mode_toggle<=!mode_toggle;else next_toggle<=!next_toggle;
    1:if(first_key)begin if(brightness<64)brightness<=brightness+8'sd16;end
      else if(brightness> -64)brightness<=brightness-8'sd16;
    2:if(first_key)begin if(contrast_q2<6)contrast_q2<=contrast_q2+1'b1;end
      else if(contrast_q2>2)contrast_q2<=contrast_q2-1'b1;
    3:if(first_key)begin if(volume_level<10)volume_level<=volume_level+1'b1;end
      else if(volume_level>0)volume_level<=volume_level-1'b1;
    default:edit_field<=0;
   endcase
  end
 end else if(down0&&down1)begin
  chord<=1;
  // The first cycle of a newly observed chord starts a NEW hold interval.
  if(!chord)hold_count<=0;
  else if(!held)begin
   if(hold_count==HOLD_CYCLES-1)begin
    held<=1;hold_count<=0;audio_select<=0;
    edit_field<=edit_field+1'b1;
    // browse -> brightness -> contrast -> volume -> browse
   end else hold_count<=hold_count+1'b1;
  end
 end else if(!chord&&!held)begin
  if(hold_count==HOLD_CYCLES-1)begin
   held<=1;hold_count<=0;edit_field<=0;
   if(first_key)ui_toggle<=!ui_toggle;
   else audio_select<=!audio_select;
  end else hold_count<=hold_count+1'b1;
 end else hold_count<=0;
endmodule
