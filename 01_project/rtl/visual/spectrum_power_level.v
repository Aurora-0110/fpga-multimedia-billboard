`timescale 1ns/1ps
// Exact serialized version of the previous log-energy mapping:
//   m=floor(log2(power)); level=min(144,6*(m-8)+top2_fraction).
// power<256 maps to zero. Constant one-bit shifts replace the long priority
// encoder + variable 37-bit barrel shifter. No precision/timing exceptions.
module spectrum_power_level(
 input wire clk,rst_n,start,cancel,input wire[36:0]power_i,
 output reg done,output reg[7:0]level);
 localparam IDLE=0,SHIFT=1,CLAMP=2;
 reg[1:0]state;reg[36:0]work;
 reg signed[8:0]log_gain;reg[8:0]sum;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin state<=IDLE;work<=0;log_gain<=0;sum<=0;done<=0;level<=0;end
 else begin
  done<=0;
  if(cancel)begin state<=IDLE;level<=0;end
  else case(state)
   IDLE:if(start)begin
    if(power_i<37'd256)begin level<=0;done<=1;end
    else begin work<=power_i;log_gain<=-9'sd36;state<=SHIFT;end
   end
   SHIFT:if(|work[36:3])begin
    work<={1'b0,work[36:1]};log_gain<=log_gain+9'sd6;
   end else begin sum<=log_gain+{7'd0,work[1:0]};state<=CLAMP;end
   CLAMP:begin level<=sum>9'd144 ? 8'd144:sum[7:0];done<=1;state<=IDLE;end
   default:state<=IDLE;
  endcase
 end
endmodule
