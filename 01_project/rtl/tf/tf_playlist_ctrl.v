`timescale 1ns/1ps
// Single-buffer playlist. AUTO_ENABLE selects the reset mode.
// MODE_SWITCH_ENABLE=0 preserves the legacy compile-time mode.
// K1 mode event has priority over K0/automatic expiry on the same cycle.
// Mode changes never restart a load; entering AUTO gives a full fresh dwell.
// DWELL_CYCLES counts continuous display-ready SD clock cycles, not load time.
// Never skip a failed file. A key retries it; busy keys are discarded.
module tf_playlist_ctrl #(
 parameter integer IMAGE_COUNT=3, // supported range 1..4; production top selects 4
 parameter integer AUTO_ENABLE=0,
 parameter integer MODE_SWITCH_ENABLE=0,
 parameter integer DWELL_CYCLES=247500000
)(input wire clk,rst_n,key_press,mode_press,load_rst_n,
 input wire [1:0] phase,input wire load_done,input wire [7:0] load_error,
 input wire display_running,stream_fault,output reg restart,output reg [1:0] image_index,
 output wire [7:0] file_letter,output wire busy,failed,output reg auto_mode);
 localparam WAIT_START=0,LOADING=1,READY=2,FAILED=3,WAIT_RESET=4;
 localparam integer COUNT_W=(DWELL_CYCLES>1)?$clog2(DWELL_CYCLES):1;
 // Clamp 0 to one cycle so parameter overrides never create a zero-width counter.
 localparam [COUNT_W-1:0] LAST_COUNT=(DWELL_CYCLES>1)?DWELL_CYCLES-1:0;
 reg [2:0] state;
 reg [COUNT_W-1:0] dwell_count;
 (* ASYNC_REG="TRUE" *) reg run_meta,run_sync,fault_meta,fault_sync;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin run_meta<=0;run_sync<=0;fault_meta<=0;fault_sync<=0;end
  else begin
   run_meta<=display_running;run_sync<=run_meta;
   fault_meta<=stream_fault;fault_sync<=fault_meta;
  end
 wire visible_ready=load_rst_n && phase==2 && load_done && run_sync;
 wire mode_event=MODE_SWITCH_ENABLE && mode_press;
 wire auto_due=auto_mode && dwell_count==LAST_COUNT;
 assign file_letter=image_index==0?8'h41:image_index==1?8'h42:image_index==2?8'h43:8'h44;
 assign busy=(state!=READY && state!=FAILED);
 assign failed=(state==FAILED);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=WAIT_START;image_index<=0;restart<=0;dwell_count<=0;auto_mode<=(AUTO_ENABLE!=0);end
  else begin
   restart<=0;
   if(mode_event)auto_mode<=~auto_mode;
   if(state!=READY)dwell_count<=0;
   case(state)
    WAIT_START:if(load_rst_n && phase==1)state<=LOADING;
    LOADING:if(load_error!=0 || fault_sync)state<=FAILED;
            else if(visible_ready)state<=READY;
    READY:if(load_error!=0 || fault_sync)begin state<=FAILED;dwell_count<=0;end
          else if(mode_event || !visible_ready)dwell_count<=0;
          else if(key_press || auto_due)begin
           image_index<=image_index==IMAGE_COUNT-1?0:image_index+1'b1;
           restart<=1;state<=WAIT_RESET;dwell_count<=0;
          end
          else if(auto_mode)dwell_count<=dwell_count+1'b1;
    FAILED:if(key_press && !mode_event)begin restart<=1;state<=WAIT_RESET;end
    // Ignore sticky flags from the old epoch until its reset was observed.
    WAIT_RESET:if(!load_rst_n)state<=WAIT_START;
    default:begin state<=WAIT_START;dwell_count<=0;end
   endcase
  end
 end
endmodule
