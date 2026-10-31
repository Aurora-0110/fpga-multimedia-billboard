`timescale 1ns/1ps
module audio_choice_cdc(input pclk,sclk,rst_n,input [1:0] choice,
 output reg [1:0] sd_choice,output reg changed,output pending);
 reg [1:0] payload;reg request,ack;
 (* ASYNC_REG="TRUE" *) reg [1:0] rq,ak;
 assign pending=choice!=payload||request!=ak[1];
 always @(posedge pclk or negedge rst_n)
 if(!rst_n)begin payload<=0;request<=0;ak<=0;end
 else begin ak<={ak[0],ack};if(ak[1]==request&&choice!=payload)begin payload<=choice;request<=~request;end end
 always @(posedge sclk or negedge rst_n)
 if(!rst_n)begin rq<=0;ack<=0;sd_choice<=0;changed<=0;end
 else begin rq<={rq[0],request};changed<=0;if(rq[1]!=ack)begin sd_choice<=payload;changed<=1;ack<=rq[1];end end
endmodule
