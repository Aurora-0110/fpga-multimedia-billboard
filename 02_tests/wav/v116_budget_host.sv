`timescale 1ns/1ps
// Deterministic sector service-budget model, not an electrical SD model.
// GAP=4 and initial wait are scaled service times, no CRC error injection here.
module v116_budget_host(input clk,rst_n,req,input [31:0] lba,
 output reg ready,done,valid,output reg [8:0] index,output reg [7:0] data,
 output wire [3:0] error);
 `include "wav_fixture.vh"
 assign error=0;
 integer initial_wait,i,waiter;reg active;
 initial if(!$value$plusargs("BLOCK_WAIT=%d",initial_wait))initial_wait=250;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin ready<=1;done<=0;valid<=0;index<=0;data<=0;i<=0;waiter<=0;active<=0;end
 else begin
  valid<=0;
  if(req&&ready)begin active<=1;ready<=0;done<=0;i<=0;waiter<=initial_wait;end
  else if(active)begin
   if(waiter>0)waiter<=waiter-1;
   else if(i<512)begin valid<=1;index<=i;data<=sector_byte(lba,i);i<=i+1;waiter<=3;end
   else begin active<=0;done<=1;ready<=1;end
  end
 end
endmodule
