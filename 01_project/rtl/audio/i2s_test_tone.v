`timescale 1ns/1ps
// v071: all state clocked by clk_pix=74.25MHz. Internal I2S only; no clock net
// generated from fabric. Fractional enable gives exactly 48k mean sample rate.
// 32-bit slots, 24 payload bits, standard one-bit I2S delay, identical L/R.
module i2s_test_tone(input clk_pix,rst_n,output reg bclk,lrclk,sdata);
 reg [26:0] acc; wire [27:0] sum={1'b0,acc}+28'd6144000;
 reg [5:0] slot,phase;
 reg signed [23:0] word;
 function signed [23:0] sine;
 input [5:0] n;
 begin case(n)
        6'd0: sine = 24'sd0;
        6'd1: sine = 24'sd136867;
        6'd2: sine = 24'sd271391;
        6'd3: sine = 24'sd401273;
        6'd4: sine = 24'sd524288;
        6'd5: sine = 24'sd638333;
        6'd6: sine = 24'sd741455;
        6'd7: sine = 24'sd831891;
        6'd8: sine = 24'sd908093;
        6'd9: sine = 24'sd968758;
        6'd10: sine = 24'sd1012847;
        6'd11: sine = 24'sd1039605;
        6'd12: sine = 24'sd1048576;
        6'd13: sine = 24'sd1039605;
        6'd14: sine = 24'sd1012847;
        6'd15: sine = 24'sd968758;
        6'd16: sine = 24'sd908093;
        6'd17: sine = 24'sd831891;
        6'd18: sine = 24'sd741455;
        6'd19: sine = 24'sd638333;
        6'd20: sine = 24'sd524288;
        6'd21: sine = 24'sd401273;
        6'd22: sine = 24'sd271391;
        6'd23: sine = 24'sd136867;
        6'd24: sine = 24'sd0;
        6'd25: sine = -24'sd136867;
        6'd26: sine = -24'sd271391;
        6'd27: sine = -24'sd401273;
        6'd28: sine = -24'sd524288;
        6'd29: sine = -24'sd638333;
        6'd30: sine = -24'sd741455;
        6'd31: sine = -24'sd831891;
        6'd32: sine = -24'sd908093;
        6'd33: sine = -24'sd968758;
        6'd34: sine = -24'sd1012847;
        6'd35: sine = -24'sd1039605;
        6'd36: sine = -24'sd1048576;
        6'd37: sine = -24'sd1039605;
        6'd38: sine = -24'sd1012847;
        6'd39: sine = -24'sd968758;
        6'd40: sine = -24'sd908093;
        6'd41: sine = -24'sd831891;
        6'd42: sine = -24'sd741455;
        6'd43: sine = -24'sd638333;
        6'd44: sine = -24'sd524288;
        6'd45: sine = -24'sd401273;
        6'd46: sine = -24'sd271391;
        6'd47: sine = -24'sd136867;
        default: sine=0;
 endcase end endfunction
 wire [5:0] next_slot=slot+6'd1;
 always @(posedge clk_pix or negedge rst_n)
 if(!rst_n)begin acc<=0;bclk<=1;lrclk<=1;sdata<=0;slot<=63;phase<=0;word<=0;end
 else if(sum>=28'd74250000)begin
  acc<=sum-28'd74250000;bclk<=~bclk;
  if(bclk)begin // falling BCLK: LR changes one bit BEFORE the new MSB
   slot<=next_slot;lrclk<=next_slot[5];
   if(next_slot==0)begin word<=sine(phase);phase<=phase==47?0:phase+1'b1;end
   if(next_slot[4:0]>=1 && next_slot[4:0]<=24)
    sdata<=word[24-next_slot[4:0]];
   else sdata<=0;
  end
 end else acc<=sum[26:0];
endmodule

// Receive the real serial stream, not a direct bypass from the tone table.
module i2s_pcm_receive(input clk_pix,rst_n,bclk,lrclk,sdata,
 output reg signed [23:0] left,right,output reg valid);
 reg bclk_d,lr_d;reg [4:0] bitno;
 reg [23:0] shift,left_hold;
 always @(posedge clk_pix or negedge rst_n)
 if(!rst_n)begin bclk_d<=1;lr_d<=1;bitno<=0;shift<=0;left_hold<=0;left<=0;right<=0;valid<=0;end
 else begin
  bclk_d<=bclk;valid<=0;
  if(bclk && !bclk_d)begin
   lr_d<=lrclk;
   if(lrclk!=lr_d)begin bitno<=0;shift<=0;end
   else if(bitno<24)begin
    shift<={shift[22:0],sdata};bitno<=bitno+1'b1;
    if(bitno==23)begin
     if(!lrclk)left_hold<={shift[22:0],sdata};
     else begin left<=left_hold;right<={shift[22:0],sdata};valid<=1;end
    end
   end
  end
 end
endmodule

// -12.04dB digital gain, with signed arithmetic (no wrapping on negatives).
module pcm_attenuate(input clk_pix,rst_n,input signed [23:0] left_in,right_in,
 input valid_in,output reg signed [23:0] left,right,output reg valid);
 always @(posedge clk_pix or negedge rst_n)
 if(!rst_n)begin left<=0;right<=0;valid<=0;end
 else begin valid<=valid_in;if(valid_in)begin left<=left_in>>>2;right<=right_in>>>2;end end
endmodule

`timescale 1ns/1ps
// 0..10 -> 0..100% of the previously validated -12.04dB output ceiling.
// One Q8 gain LSB per accepted stereo sample: <=256 samples to settle.
// Both signed multipliers use the SAME coefficient on the SAME edge.
// V125 TWO-cycle latency; accepts consecutive valid cycles; no backpressure/BRAM.
// Register samples+coefficient before DSP: the measured gain-adder->DSP path is cut.
module pcm_volume(input clk_pix,rst_n,input signed [23:0] left_in,right_in,
 input valid_in,input [3:0] volume_level,
 output reg signed [23:0] left,right,output reg valid);
 reg [8:0] gain_q8;
 function [8:0] volume_target;input [3:0] level;begin
  case(level)
   0:volume_target=0;1:volume_target=26;2:volume_target=51;3:volume_target=77;
   4:volume_target=102;5:volume_target=128;6:volume_target=154;7:volume_target=179;
   8:volume_target=205;9:volume_target=230;default:volume_target=256;
  endcase
 end endfunction
 wire [8:0] target_q8=volume_target(volume_level);
 wire [8:0] next_gain=gain_q8<target_q8?gain_q8+9'd1:
                        (gain_q8>target_q8?gain_q8-9'd1:gain_q8);
 reg signed [23:0] sample_l,sample_r;reg [8:0] coefficient_q;reg valid_q;
 wire signed [9:0] coefficient=$signed({1'b0,coefficient_q});
 (* use_dsp="yes" *) wire signed [33:0] product_l=sample_l*coefficient;
 (* use_dsp="yes" *) wire signed [33:0] product_r=sample_r*coefficient;
 always @(posedge clk_pix or negedge rst_n)
 if(!rst_n)begin gain_q8<=256;sample_l<=0;sample_r<=0;coefficient_q<=256;valid_q<=0;left<=0;right<=0;valid<=0;end
 else begin
  sample_l<=left_in;sample_r<=right_in;coefficient_q<=next_gain;valid_q<=valid_in;valid<=valid_q;
  if(valid_in)gain_q8<=next_gain;
  if(valid_q)begin
   // Floor signed result /1024 == Q8 gain then original /4 ceiling.
   left<=product_l[33:10];right<=product_r[33:10];
  end
 end
endmodule
