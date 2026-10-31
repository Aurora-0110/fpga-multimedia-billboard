`timescale 1ns/1ps
// Pixel-clock UI. Each physical input has a synchronizer and stable-time filter.
// Single-key actions occur on RELEASE. A chord suppresses both single actions.
// Hold both for HOLD_CYCLES: VIEW -> BRIGHTNESS -> CONTRAST -> VIEW.
// A fresh all-released state is required after reset and after each gesture.
module picture_controls #(parameter DEBOUNCE_CYCLES=742500,HOLD_CYCLES=74250000)(
 input wire clk,rst_n,key0_n,key1_n,
 output reg next_toggle,mode_toggle,
 output reg signed [7:0] brightness,
 output reg [2:0] contrast_q2,output reg [1:0] edit_field);
 localparam DBW=DEBOUNCE_CYCLES>1?$clog2(DEBOUNCE_CYCLES):1;
 localparam HW=HOLD_CYCLES>1?$clog2(HOLD_CYCLES):1;
 (* ASYNC_REG="TRUE" *) reg [1:0] k0sync,k1sync;
 reg down0,down1;reg [DBW-1:0] db0,db1;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin k0sync<=2'b11;k1sync<=2'b11;down0<=0;down1<=0;db0<=0;db1<=0;end
 else begin
  k0sync<={k0sync[0],key0_n};k1sync<={k1sync[0],key1_n};
  if((!k0sync[1])==down0)db0<=0;
  else if(db0==DEBOUNCE_CYCLES-1)begin down0<=!k0sync[1];db0<=0;end
  else db0<=db0+1'b1;
  if((!k1sync[1])==down1)db1<=0;
  else if(db1==DEBOUNCE_CYCLES-1)begin down1<=!k1sync[1];db1<=0;end
  else db1<=db1+1'b1;
 end
 localparam AW=$clog2(DEBOUNCE_CYCLES+4);
 reg [AW-1:0] arm_count;
 reg ready,session,chord,held,first_key;reg [HW-1:0] hold_count;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  ready<=0;arm_count<=0;session<=0;chord<=0;held<=0;first_key<=0;hold_count<=0;
  next_toggle<=0;mode_toggle<=0;brightness<=0;contrast_q2<=4;edit_field<=0;
 end else if(!ready)begin
  // Raw inputs participate ONLY in startup inhibition, never in an action.
  // Require a complete synchronized, debounced release after boot-held keys.
  if(key0_n&&key1_n&&(&k0sync)&&(&k1sync)&&!down0&&!down1)begin
   if(arm_count==DEBOUNCE_CYCLES+2)ready<=1;else arm_count<=arm_count+1'b1;
  end else arm_count<=0;
 end
 else if(!session)begin
  hold_count<=0;held<=0;chord<=0;
  if(down0||down1)begin session<=1;first_key<=down1;chord<=down0&&down1;end
 end else if(!down0&&!down1)begin
  session<=0;hold_count<=0;
  if(!chord)begin
   case(edit_field)
    0:if(first_key)mode_toggle<=!mode_toggle;else next_toggle<=!next_toggle;
    1:if(first_key)begin if(brightness<64)brightness<=brightness+8'sd16;end
      else if(brightness> -64)brightness<=brightness-8'sd16;
    2:if(first_key)begin if(contrast_q2<6)contrast_q2<=contrast_q2+1'b1;end
      else if(contrast_q2>2)contrast_q2<=contrast_q2-1'b1;
    default:edit_field<=0;
   endcase
  end
 end else if(down0&&down1)begin
  chord<=1;
  if(!held)begin
   if(hold_count==HOLD_CYCLES-1)begin
    held<=1;hold_count<=0;edit_field<=edit_field==2?0:edit_field+1'b1;
   end else hold_count<=hold_count+1'b1;
  end
 end else hold_count<=0;
endmodule
