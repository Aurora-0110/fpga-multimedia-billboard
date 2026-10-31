`timescale 1ns/1ps
// Background prefetch. A failed next file does NOT blank the current picture.
// K0 requests the NEXT preloaded image (queues during preload); K1 changes mode.
// No new write to the old bank until reader proves all old-bank reads drained.
module tf_double_playlist #(
 parameter IMAGE_COUNT=4,AUTO_ENABLE=1,DWELL_CYCLES=247500000,RESET_CYCLES=32,
 // Defaults preserve old instantiations; the board explicitly enables protection.
 LOAD_TIMEOUT_CYCLES=0,AUTO_RETRIES=0,RETRY_DELAY_CYCLES=49500000
)(input wire clk,rst_n,key_press,mode_press,init_done,load_done,
 input wire [7:0] load_error,input wire display_running,stream_fault,transition_done,
 output wire load_rst_n,load_enable,output reg dest_bank,
 output wire [7:0] file_letter,output reg [1:0] image_index,load_index,
 output reg front_valid,output wire transition_request,
 output wire busy,failed,output reg auto_mode,output reg [7:0] error_latched,
 input wire load_progress);
 localparam RESET_FIRST=0,FIRST=1,WAIT_DISPLAY=2,RESET_NEXT=3,LOAD_NEXT=4,READY=5,SLIDE=6,FAIL_FIRST=7,FAIL_NEXT=8;
 localparam CW=(DWELL_CYCLES>1)?$clog2(DWELL_CYCLES):1;
 reg [3:0] state;reg [7:0] reset_count;reg [CW-1:0] dwell;
 reg want_next;
 localparam WW=LOAD_TIMEOUT_CYCLES>1?$clog2(LOAD_TIMEOUT_CYCLES):1;
 localparam RW=RETRY_DELAY_CYCLES>1?$clog2(RETRY_DELAY_CYCLES):1;
 localparam NW=AUTO_RETRIES>0?$clog2(AUTO_RETRIES+1):1;
 reg [WW-1:0] watchdog;
 reg [RW-1:0] retry_wait;
 reg [NW-1:0] retry_count;
 wire loading=state==FIRST||state==LOAD_NEXT;
 // Only actual accepted framebuffer bursts count as progress, not toggling SPI.
 wire stalled=(LOAD_TIMEOUT_CYCLES>0)&&loading&&!load_progress&&(watchdog==LOAD_TIMEOUT_CYCLES-1);
 function retryable;input [7:0] code;begin
 // SPI errors, probe/stream transport timeout, or this guard's inactivity timeout.
 // Missing file/unsupported BMP/coordinate errors require explicit correction.
 retryable=(code[7:4]==4'h1)||(code==8'h2d)||(code==8'h35)||(code==8'he0);
 end endfunction
 (* ASYNC_REG="TRUE" *) reg run_meta,run_sync,fault_meta,fault_sync;
 wire failing=state==FAIL_FIRST||state==FAIL_NEXT;
 wire retry_allowed=(AUTO_RETRIES>0)&&(retry_count<AUTO_RETRIES)&&retryable(error_latched)&&!fault_sync;
 wire retry_due=retry_allowed&&((RETRY_DELAY_CYCLES<=1)||(retry_wait==RETRY_DELAY_CYCLES-1));
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin watchdog<=0;retry_wait<=0;end
 else begin
  if(!loading||load_progress||LOAD_TIMEOUT_CYCLES==0)watchdog<=0;
  else if(!stalled)watchdog<=watchdog+1'b1;
  if(!failing||!retry_allowed)retry_wait<=0;
  else if(!retry_due)retry_wait<=retry_wait+1'b1;
 end
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin run_meta<=0;run_sync<=0;fault_meta<=0;fault_sync<=0;end
 else begin run_meta<=display_running;run_sync<=run_meta;fault_meta<=stream_fault;fault_sync<=fault_meta;end
 assign file_letter="A"+load_index;
 assign load_rst_n=rst_n&&(state==FIRST||state==LOAD_NEXT);
 assign load_enable=init_done&&load_rst_n;
 assign transition_request=(state==SLIDE);
 assign busy=state!=READY;
 assign failed=state==FAIL_FIRST||state==FAIL_NEXT||fault_sync;
 wire due=auto_mode&&(dwell==DWELL_CYCLES-1);
 function [1:0] following;input [1:0] i;begin following=(i==IMAGE_COUNT-1)?0:i+1'b1;end endfunction
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  state<=RESET_FIRST;reset_count<=0;dest_bank<=0;image_index<=0;load_index<=0;
  front_valid<=0;auto_mode<=AUTO_ENABLE!=0;dwell<=0;want_next<=0;error_latched<=0;retry_count<=0;
 end else begin
  if(mode_press)begin auto_mode<=~auto_mode;dwell<=0;want_next<=0;end
  else if(front_valid&&run_sync&&state!=SLIDE&&auto_mode)begin
   if(!due)dwell<=dwell+1'b1;
  end else dwell<=0;
  if(key_press&&!mode_press&&front_valid&&state!=SLIDE)want_next<=1;
  case(state)
   RESET_FIRST,RESET_NEXT:begin
    if(init_done)begin
     if(reset_count==RESET_CYCLES-1)begin reset_count<=0;state<=state==RESET_FIRST?FIRST:LOAD_NEXT;end
     else reset_count<=reset_count+1'b1;
    end
   end
   FIRST:if(load_error!=0)begin state<=FAIL_FIRST;error_latched<=load_error;end
         else if(load_done)begin front_valid<=1;state<=WAIT_DISPLAY;retry_count<=0;end
         else if(stalled)begin state<=FAIL_FIRST;error_latched<=8'he0;end
   WAIT_DISPLAY:if(run_sync)begin dest_bank<=1;load_index<=following(image_index);state<=RESET_NEXT;reset_count<=0;end
   LOAD_NEXT:if(load_error!=0)begin state<=FAIL_NEXT;error_latched<=load_error;end
             else if(load_done)begin state<=READY;retry_count<=0;end
             else if(stalled)begin state<=FAIL_NEXT;error_latched<=8'he0;end
   READY:if(!mode_press&&!fault_sync&&(want_next||key_press||due))begin state<=SLIDE;want_next<=0;dwell<=0;end
   SLIDE:if(transition_done)begin
    image_index<=load_index;dest_bank<=~dest_bank;load_index<=following(load_index);
    state<=RESET_NEXT;reset_count<=0;dwell<=0;want_next<=0;
   end
   FAIL_FIRST:if(key_press&&!mode_press)begin state<=RESET_FIRST;reset_count<=0;error_latched<=0;retry_count<=0;end
              else if(retry_due&&!mode_press)begin state<=RESET_FIRST;reset_count<=0;error_latched<=0;retry_count<=retry_count+1'b1;end
   FAIL_NEXT:if(key_press&&!mode_press)begin state<=RESET_NEXT;reset_count<=0;want_next<=0;error_latched<=0;retry_count<=0;end
             else if(retry_due&&!mode_press)begin state<=RESET_NEXT;reset_count<=0;want_next<=0;error_latched<=0;retry_count<=retry_count+1'b1;end
   default:begin state<=RESET_FIRST;reset_count<=0;front_valid<=0;retry_count<=0;end
  endcase
 end
endmodule

