`timescale 1ns/1ps
// One RGB332 stream, 40 bursts/line. New configurations are latched ONLY at
// logical producer frame boundaries, never at a live pixel vsync. FIFO prefetch
// therefore cannot tear a frame. Buffers occupy SDRAM banks 0 and 1 (2MiB apart).
// req_ready is a REGISTERED acceptance acknowledgement, not ready/valid ready.
module idx_slide_reader #(
 parameter integer LINE_BURSTS=40, LINES=480
)(input wire clk,rst_n,enable,input wire [12:0] fifo_used,
 input wire transition_request,input wire [1:0] target_index,
 output reg transition_done,output reg sliding,output reg [5:0] step,
 output wire req_valid,output wire [18:0] req_addr,
 input wire req_ready,rsp_valid,input wire [127:0] rsp_rdata,
 output wire fifo_we,output wire [15:0] fifo_wdata);
 reg pending,pushing,queued,boundary,front_bank,request_seen;
 reg [1:0] current_index,next_index;
 reg [5:0] col;reg [8:0] row;
 reg [127:0] sh,next_data;reg [7:0] sh_tag,next_tag,pending_tag;
 reg [3:0] pcnt;
 wire use_new=(step!=0)&&(col>=LINE_BURSTS-step);
 wire buffer_bank=front_bank^use_new;
 wire [5:0] src_col=use_new?(col-(LINE_BURSTS-step)):(col+step);
 wire [14:0] offset=({6'd0,row}<<5)+({6'd0,row}<<3)+src_col;
 assign req_addr={1'b0,buffer_bank,2'b00,offset};
 assign req_valid=enable&&!boundary&&(fifo_used<=13'd4048)&&!pending&&!queued;
 assign fifo_we=pushing;assign fifo_wdata={sh_tag,sh[7:0]};
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  pending<=0;pushing<=0;queued<=0;boundary<=1;front_bank<=0;request_seen<=0;
  current_index<=0;next_index<=0;col<=0;row<=0;step<=0;sliding<=0;
  sh<=0;next_data<=0;sh_tag<=0;next_tag<=0;pending_tag<=0;pcnt<=0;transition_done<=0;
 end else begin
  transition_done<=0;
  if(!transition_request)request_seen<=0;
  if(boundary&&enable&&!pending&&!queued)begin
   boundary<=0;
   if(sliding)begin
    if(step==LINE_BURSTS)begin
     front_bank<=~front_bank;current_index<=next_index;step<=0;sliding<=0;
    end else step<=step+1'b1;
   end else if(transition_request&&!request_seen)begin
    next_index<=target_index;step<=1;sliding<=1;request_seen<=1;
   end
  end
  if(pushing)begin
   sh<={8'd0,sh[127:8]};pcnt<=pcnt+1'b1;
   if(pcnt==15)begin
    if(queued)begin sh<=next_data;sh_tag<=next_tag;pcnt<=0;queued<=0;end
    else pushing<=0;
   end
  end
  if(rsp_valid&&pending)begin
   pending<=0;
   if(!pushing||(pcnt==15&&!queued))begin
    sh<=rsp_rdata;sh_tag<=pending_tag;pcnt<=0;pushing<=1;
   end else begin next_data<=rsp_rdata;next_tag<=pending_tag;queued<=1;end
  end
  if(req_ready)begin
   pending<=1;pending_tag<={(step!=0)?next_index:current_index,step};
   if(row==0&&col==0&&step==LINE_BURSTS)transition_done<=1;
   if(col==LINE_BURSTS-1)begin
    col<=0;
    if(row==LINES-1)begin row<=0;boundary<=1;end else row<=row+1'b1;
   end else col<=col+1'b1;
  end
 end
endmodule
