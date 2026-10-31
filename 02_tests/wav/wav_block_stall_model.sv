`timescale 1ns/1ps
// Transport abstraction, NOT physical SD SPI. Returns provisional bytes first,
// then CRC completion/error. Sparse sector contents generated independently.
module wav_block_stall_model #(parameter GAP=6)(
 input clk,rst_n,req,stall,input [31:0] lba,input [31:0] bad_lba,input [1:0] bad_kind,
 output reg ready,done,valid,output reg [8:0] index,output reg [7:0] data,output reg[3:0]error,
 output reg [31:0] active_lba,output reg [31:0] transactions);
 `include "wav_fixture.vh"
 reg active;integer i,waiter;reg[31:0]random=32'h7a8533a9;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin ready<=1;done<=0;valid<=0;index<=0;data<=0;error<=0;active<=0;i<=0;waiter<=0;active_lba<=0;transactions<=0;end
 else begin
  valid<=0;random<={random[30:0],random[31]^random[21]^random[1]^random[0]};
  if(req&&ready)begin active<=1;ready<=0;done<=0;i<=0;waiter<=8;active_lba<=lba;transactions<=transactions+1'b1;end
  else if(active&&!stall)begin
   if(waiter!=0)waiter<=waiter-1;
   else if(i<512)begin
    valid<=1;index<=(bad_kind==2&&active_lba==bad_lba&&i==64)?9'd63:i;data<=sector_byte(active_lba,i);i<=i+1;
    waiter<=GAP-1+(random[1:0]==0);
   end else begin active<=0;done<=1;if(bad_kind==1&&active_lba==bad_lba)begin ready<=0;error<=4'd9;end else ready<=1;end
  end
 end
endmodule
