`timescale 1ns/1ps
// Two RGB332 pixels + one frame tag per FIFO word. Full720p is 80 bursts/row.
// Producer boundaries, NOT pixel vsync, select the next complete frame config.
// Keep 40 transition frames: 80/40=2 bursts=32 pixels of motion per frame.
// req_ready is registered transaction acceptance (not combinational ready).
module v126_idx_pair_reader_reference #(
 parameter integer LINE_BURSTS=80,LINES=720,TRANSITION_STEPS=40
)(
 input wire clk,rst_n,enable,input wire [12:0] fifo_used,input wire fifo_full,
 input wire transition_request,input wire [1:0] target_index,
 output reg transition_done,output reg sliding,output reg [5:0] step,
 output wire req_valid,output wire [18:0] req_addr,
 input wire req_ready,rsp_valid,input wire [127:0] rsp_rdata,
 output wire fifo_we,output wire [23:0] fifo_wdata,output reg protocol_fault
);
 localparam COL_BITS=(LINE_BURSTS<=1)?1:$clog2(LINE_BURSTS);
 localparam ROW_BITS=(LINES<=1)?1:$clog2(LINES);
 localparam SHIFT_BURSTS=LINE_BURSTS/TRANSITION_STEPS;
 reg pending,pushing,queued,boundary,front_bank,request_seen;
 reg [1:0] current_index,next_index;
 reg [COL_BITS-1:0] col;reg [ROW_BITS-1:0] row;
 // v122: frame row base advances once per accepted complete line.
 // Removes the constant row multiplier from every SDRAM address request.
 reg [18:0] row_base;
 reg [127:0] sh,next_data;reg [7:0] sh_tag,next_tag,pending_tag;
 reg [2:0] pcnt;
 wire [15:0] shift_bursts=step*SHIFT_BURSTS;
 wire [15:0] split=LINE_BURSTS-shift_bursts;
 wire use_new=(step!=0)&&(col>=split);
 wire bank=front_bank^use_new;
 wire [15:0] src_col=use_new?(col-split):(col+shift_bursts);
 wire [18:0] offset=row_base+src_col;
 assign req_addr=(bank?19'd131072:19'd0)+offset;
 // Reserve space for current shifter, queued response, in-flight transaction,
 // and registered occupancy latency. FIFO words are PAIRS, never pixels.
 assign req_valid=enable&&!boundary&&(fifo_used<=13'd4072)&&!pending&&!queued&&!protocol_fault;
 assign fifo_we=pushing&&!fifo_full;
 assign fifo_wdata={sh_tag,sh[15:0]};
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  pending<=0;pushing<=0;queued<=0;boundary<=1;front_bank<=0;request_seen<=0;
  current_index<=0;next_index<=0;col<=0;row<=0;step<=0;sliding<=0;
  row_base<=0;sh<=0;next_data<=0;sh_tag<=0;next_tag<=0;pending_tag<=0;pcnt<=0;transition_done<=0;protocol_fault<=0;
 end else begin
  transition_done<=0;
  if(!transition_request)request_seen<=0;
  if(boundary&&enable&&!pending&&!queued)begin
   boundary<=0;
   if(sliding)begin
    if(step==TRANSITION_STEPS)begin
     front_bank<=~front_bank;current_index<=next_index;step<=0;sliding<=0;
    end else step<=step+1'b1;
   end else if(transition_request&&!request_seen)begin
    next_index<=target_index;step<=1;sliding<=1;request_seen<=1;
   end
  end
  if(fifo_we)begin
   sh<={16'd0,sh[127:16]};pcnt<=pcnt+1'b1;
   if(pcnt==7)begin
    if(queued)begin sh<=next_data;sh_tag<=next_tag;pcnt<=0;queued<=0;end
    else pushing<=0;
   end
  end
  if(rsp_valid)begin
   if(!pending)protocol_fault<=1;
   else begin
    pending<=0;
    if(!pushing||(fifo_we&&pcnt==7&&!queued))begin
     sh<=rsp_rdata;sh_tag<=pending_tag;pcnt<=0;pushing<=1;
    end else if(!queued)begin next_data<=rsp_rdata;next_tag<=pending_tag;queued<=1;end
    else protocol_fault<=1;
   end
  end
  if(req_ready)begin
   pending<=1;pending_tag<={(step!=0)?next_index:current_index,step};
   // By this acceptance there are no outstanding physical reads of the old
   // bank. Old pixels may remain in FIFO, but they are already immutable data.
   if(row==0&&col==0&&step==TRANSITION_STEPS)transition_done<=1;
   if(col==LINE_BURSTS-1)begin
    col<=0;
    if(row==LINES-1)begin row<=0;row_base<=0;boundary<=1;end
    else begin row<=row+1'b1;row_base<=row_base+LINE_BURSTS;end
   end else col<=col+1'b1;
  end
 end
endmodule
