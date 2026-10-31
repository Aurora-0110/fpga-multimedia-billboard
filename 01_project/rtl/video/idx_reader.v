`timescale 1ns/1ps
// RGB332 burst reader: active unpack buffer + one queued response buffer.
// One request outstanding. A queued response cannot overwrite the active burst.
// Reserve 48 FIFO slots for active/queued bytes and registered occupancy lag.
// req_ready is registered acceptance ACK, not a combinational ready signal.
module idx_reader #(parameter integer LAST_BURST=19199)(
 input wire clk,rst_n,enable,input wire [12:0] fifo_used,
 output wire req_valid,output wire [1:0] req_bank,output wire [10:0] req_row,
 output wire [5:0] req_col,input wire req_ready,rsp_valid,
 input wire [127:0] rsp_rdata,output wire fifo_we,output wire [7:0] fifo_wdata);
 reg pending,pushing,queued;reg [18:0] baddr;
 reg [127:0] sh,next_data;reg [3:0] pcnt;
 assign req_valid=enable&&(fifo_used<=13'd4048)&&!pending&&!queued;
 assign req_bank=baddr[18:17];assign req_row=baddr[16:6];assign req_col=baddr[5:0];
 assign fifo_we=pushing;assign fifo_wdata=sh[7:0];
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin pending<=0;pushing<=0;queued<=0;baddr<=0;sh<=0;next_data<=0;pcnt<=0;end
 else begin
  if(pushing)begin
   sh<={8'd0,sh[127:8]};pcnt<=pcnt+1'b1;
   if(pcnt==15)begin
    if(queued)begin sh<=next_data;pcnt<=0;queued<=0;end
    else pushing<=0;
   end
  end
  if(rsp_valid&&pending)begin
   pending<=0;
   if(!pushing||(pcnt==15&&!queued))begin sh<=rsp_rdata;pcnt<=0;pushing<=1;end
   else begin next_data<=rsp_rdata;queued<=1;end
  end
  if(req_ready)begin pending<=1;baddr<=(baddr==LAST_BURST)?19'd0:baddr+1'b1;end
 end
endmodule
