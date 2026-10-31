`timescale 1ns/1ps
// HDMI packet layout/BCH adapted from hdl-util/hdmi, Sameer Puri, MIT.
// See 07_reference/hdl_util_hdmi for original sources, license and provenance.
// Fixed 720p60 / 74.25MHz / 48k stereo 24-bit LPCM. No generic mode claim.
module hdmi_audio_packets #(parameter GATE_ENABLE=0)(input clk_pix,rst_n,input [11:0] cx,cy,
 input [23:0] pcm_l,pcm_r,input pcm_valid,input audio_enable,
 output wire video_preamble,island_preamble,
 output wire aux_period,output wire [9:0] aux_b,aux_g,aux_r,
 input hs,vs,output reg overflow);
 // One 32-clock packet per line. Keep >=4 control clocks before preamble,
 // 2 guard clocks each side, and a separate 8+2 video preamble/guard.
 wire island=(cx>=1294 && cx<1326);
 wire iguard=(cx>=1292 && cx<1294)||(cx>=1326 && cx<1328);
 wire next_active=(cy<719 || cy==749);
 wire vguard=next_active && cx>=1648 && cx<1650;
 assign island_preamble=(cx>=1284 && cx<1292);
 assign video_preamble=next_active && cx>=1640 && cx<1648;
 assign aux_period=island||iguard||vguard;
 wire select_packet=(cx==1280);
 // Eight stereo frames, single pixel domain. Pops are atomic groups of four.
 reg [47:0] fifo[0:7];reg [2:0] wp,rp;reg [3:0] count;
 reg acr_pending,avi_pending,info_pending;reg [5:0] acr_count;
 wire pop4=select_packet && !acr_pending && count>=4;
 wire push=pcm_valid && (count<8 || pop4);
 wire [2:0] rp1=rp+3'd1,rp2=rp+3'd2,rp3=rp+3'd3;
 reg [7:0] frame_index;
 reg [23:0] header;
 reg [55:0] s0,s1,s2,s3;
 // IEC60958 consumer, PCM, copyright not asserted, stereo, 48k, 24-bit.
 // Byte0=04,byte1=00,byte2=L10/R20,byte3=02,byte4=0b.
 function cstatus;
 input [7:0] idx;input right_ch;
 reg [39:0] cs;
 begin cs=right_ch?40'h0b02200004:40'h0b02100004;
 cstatus=(idx<40)?cs[idx]:1'b0;end
 endfunction
 function [55:0] audio_sub;
 input [47:0] samples;input [7:0] idx;
 reg cl,cr,pl,pr;
 begin cl=cstatus(idx,0);cr=cstatus(idx,1);
 pl=^{samples[23:0],cl};pr=^{samples[47:24],cr};
 audio_sub={{pr,cr,2'b00,pl,cl,2'b00},samples};end
 endfunction
 always @(posedge clk_pix or negedge rst_n)
 if(!rst_n)begin
  wp<=0;rp<=0;count<=0;overflow<=0;acr_count<=0;acr_pending<=1;
  avi_pending<=1;info_pending<=1;frame_index<=0;header<=0;s0<=0;s1<=0;s2<=0;s3<=0;
 end else begin
  if(push)begin fifo[wp]<={pcm_r,pcm_l};wp<=wp+1'b1;end
  if(pcm_valid && !push)overflow<=1;
  case({push,pop4})
   2'b10:count<=count+1'b1;2'b01:count<=count-4;2'b11:count<=count-3;
   default:count<=count;
  endcase
  if(cx==0 && cy==0)begin avi_pending<=1;info_pending<=1;end
  if(select_packet)begin
   header<=0;s0<=0;s1<=0;s2<=0;s3<=0; // HDMI Null packet, deterministic zeros
   if(acr_pending)begin
    header<=24'h000001;
    // Little-endian payload bytes: reserved,CTS[19:16],CTS[15:8],CTS[7:0],
    // N[19:16],N[15:8],N[7:0]. N=6144, CTS=74250.
    s0<=56'h0018000a220100;s1<=56'h0018000a220100;
    s2<=56'h0018000a220100;s3<=56'h0018000a220100;
    acr_pending<=0;
   end else if(pop4)begin
    // Gate AFTER FIFO, BEFORE IEC60958 parity/BCH. A queued tone can never
    // leak into a newly selected muted packet. Do not stop I2S/PCM/ACR or
    // reset the HDMI link on a picture transition. Already selected packet
    // completes atomically; external sink/display latency is not guaranteed.
    header<={frame_index==0?4'b0001:4'b0000,4'b0000,4'b0000,4'b1111,8'h02};
    s0<=audio_sub((!GATE_ENABLE || audio_enable)?fifo[rp]:48'd0,frame_index);
    s1<=audio_sub((!GATE_ENABLE || audio_enable)?fifo[rp1]:48'd0,frame_index+8'd1);
    s2<=audio_sub((!GATE_ENABLE || audio_enable)?fifo[rp2]:48'd0,frame_index+8'd2);
    s3<=audio_sub((!GATE_ENABLE || audio_enable)?fifo[rp3]:48'd0,frame_index+8'd3);
    rp<=rp+3'd4;frame_index<=frame_index==188?0:frame_index+8'd4;
   end else if(avi_pending)begin
    header<=24'h0d0282;s0<=56'h0000040828102b;avi_pending<=0;
   end else if(info_pending)begin
    header<=24'h0a0184;s0<=56'h00000000000170;info_pending<=0;
   end
  end
  // Set takes precedence on the rare packet-select/48th-sample coincidence.
  if(pcm_valid)begin
   if(acr_count==47)begin acr_count<=0;acr_pending<=1;end
   else acr_count<=acr_count+1'b1;
  end
 end
 // Streaming BCH: one header bit and two bits from each subpacket per clock.
 // This avoids a long combinational 56-bit polynomial cascade.
 reg [7:0] eh,e0,e1,e2,e3;
 wire [4:0] k=cx-12'd1294;
 wire [5:0] k2={k,1'b0};
 wire [31:0] hb={eh,header};
 wire [63:0] b0={e0,s0},b1={e1,s1},b2={e2,s2},b3={e3,s3};
 function [7:0] ecc;
 input [7:0] e;input bit_in;
 begin ecc=(e>>1)^((e[0]^bit_in)?8'h83:8'h00);end
 endfunction
 always @(posedge clk_pix or negedge rst_n)
 if(!rst_n)begin eh<=0;e0<=0;e1<=0;e2<=0;e3<=0;end
 else if(!island)begin eh<=0;e0<=0;e1<=0;e2<=0;e3<=0;end
 else begin
  if(k<24)eh<=ecc(eh,header[k]);
  if(k<28)begin
   e0<=ecc(ecc(e0,s0[k2]),s0[k2+6'd1]);
   e1<=ecc(ecc(e1,s1[k2]),s1[k2+6'd1]);
   e2<=ecc(ecc(e2,s2[k2]),s2[k2+6'd1]);
   e3<=ecc(ecc(e3,s3[k2]),s3[k2+6'd1]);
  end
 end
 wire [8:0] pdata={b3[k2+6'd1],b2[k2+6'd1],b1[k2+6'd1],b0[k2+6'd1],
                       b3[k2],b2[k2],b1[k2],b0[k2],hb[k]};
 function [9:0] terc4;
 input [3:0] n;
 begin case(n)
  0:terc4=10'b1010011100;1:terc4=10'b1001100011;
  2:terc4=10'b1011100100;3:terc4=10'b1011100010;
  4:terc4=10'b0101110001;5:terc4=10'b0100011110;
  6:terc4=10'b0110001110;7:terc4=10'b0100111100;
  8:terc4=10'b1011001100;9:terc4=10'b0100111001;
  10:terc4=10'b0110011100;11:terc4=10'b1011000110;
  12:terc4=10'b1010001110;13:terc4=10'b1001110001;
  14:terc4=10'b0101100011;15:terc4=10'b1011000011;
 endcase end
 endfunction
 assign aux_b=vguard?10'b1011001100:
              iguard?terc4({2'b11,vs,hs}):terc4({1'b1,pdata[0],vs,hs});
 assign aux_g=vguard||iguard?10'b0100110011:terc4(pdata[4:1]);
 assign aux_r=vguard?10'b1011001100:iguard?10'b0100110011:terc4(pdata[8:5]);
endmodule
