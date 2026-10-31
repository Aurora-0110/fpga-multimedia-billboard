`timescale 1ns/1ps
// Sparse direct DFT, N=256, 16 explicitly selected frequency lines at Fs=48kHz.
// All 24 signed PCM bits enter the exact split product. One shared 18x18 MAC
// multiplier handles high/low halves, real/imaginary terms and power squares.
// Two 256x24 sample banks overlap capture/computation. No audio backpressure.
// Per-bin power is Re^2+Im^2 after fixed normalization to signed18; not fake bars.
// Not a full-band FFT or a calibrated spectrum analyzer; rectangular window.
module pcm_spectrum_dft_v124_reference(
 input wire clk,rst_n,input wire signed[23:0]pcm_l,pcm_r,
 input wire pcm_valid,stream_active,track_change,
 output reg[127:0]levels,output reg levels_valid,output reg overrun,
 output reg bin_valid,output reg[3:0]bin_index,output reg[36:0]bin_energy);
`include "visual/dft_cos_q10.vh"
 function[7:0] frequency_bin;input[3:0]b;begin case(b)
 0:frequency_bin=1;1:frequency_bin=2;2:frequency_bin=3;3:frequency_bin=4;
 4:frequency_bin=5;5:frequency_bin=6;6:frequency_bin=8;7:frequency_bin=10;
 8:frequency_bin=13;9:frequency_bin=17;10:frequency_bin=22;11:frequency_bin=29;
 12:frequency_bin=38;13:frequency_bin=50;14:frequency_bin=66;15:frequency_bin=90;
 endcase end endfunction
 localparam IDLE=0,READ=1,WAIT_RAM=2,RHI=3,RWAIT=4,RLO=5,RLWAIT=6,RTERM=7,RACC=8,
 IHI=9,IWAIT=10,ILO=11,ILWAIT=12,ITERM=13,IACC=14,NORM=15,
 PR=16,PRWAIT=17,PI=18,PIWAIT=19,POWER=20,PUBLISH=21,LEVEL_START=22,LEVEL_WAIT=23;
 reg[4:0]state;reg cap_bank,read_bank,pending,pending_bank;reg[7:0]wp,n,phase;
 reg[3:0]band;reg[8:0]rd_addr;reg signed[23:0]sample_q;
 (* ram_style="block" *)reg[23:0]samples[0:511];
 wire signed[24:0]mono_sum={pcm_l[23],pcm_l}+{pcm_r[23],pcm_r};
 wire signed[23:0]mono=mono_sum>>>1;
 // No RAM reset/clear; epochs start only after a complete fresh 256-sample bank.
 always @(posedge clk)begin
  if(rst_n&&stream_active&&pcm_valid&&!track_change)samples[{cap_bank,wp}]<=mono;
  sample_q<=samples[rd_addr];
 end
 reg signed[11:0]cr,ci;reg signed[17:0]ma,mb;reg signed[35:0]product;
 always @(posedge clk)product<=ma*mb;
 reg signed[42:0]partial,term,ar,ai;reg signed[17:0]nr,ni;
 reg[35:0]square_r;reg[36:0]power_q;reg[127:0]working;
 wire[7:0]encoded_level;wire level_done;
 spectrum_power_level encode_power(.clk(clk),.rst_n(rst_n),
  .start(state==LEVEL_START&&stream_active&&!track_change),
  .cancel(track_change||!stream_active),.power_i(power_q),
  .done(level_done),.level(encoded_level));
 wire signed[42:0]extended_product={{7{product[35]}},product};
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  state<=IDLE;cap_bank<=0;read_bank<=0;pending<=0;pending_bank<=0;wp<=0;n<=0;phase<=0;band<=0;rd_addr<=0;
  cr<=0;ci<=0;ma<=0;mb<=0;partial<=0;term<=0;ar<=0;ai<=0;nr<=0;ni<=0;square_r<=0;power_q<=0;working<=0;
  levels<=0;levels_valid<=0;overrun<=0;bin_valid<=0;bin_index<=0;bin_energy<=0;
 end else begin
  levels_valid<=0;bin_valid<=0;
  if(track_change||!stream_active)begin
   state<=IDLE;cap_bank<=0;pending<=0;wp<=0;n<=0;phase<=0;band<=0;
   working<=0;levels<=0;overrun<=0;ar<=0;ai<=0;
  end else begin
   if(pcm_valid)begin
    if(wp==255)begin
     wp<=0;
     // In normal 48k operation the <63k compute clocks fit in 396k capture clocks.
     // Overspeed must DROP a block rather than overwrite an active computation.
     if(pending||state!=IDLE)overrun<=1;
     else begin pending<=1;pending_bank<=cap_bank;cap_bank<=!cap_bank;end
    end else wp<=wp+1'b1;
   end
   case(state)
    IDLE:if(pending)begin
     pending<=0;read_bank<=pending_bank;band<=0;n<=0;phase<=0;ar<=0;ai<=0;working<=0;state<=READ;
    end
    READ:begin rd_addr<={read_bank,n};cr<=cos_q10(phase);ci<=cos_q10(phase+8'd64);state<=WAIT_RAM;end
    WAIT_RAM:state<=RHI;
    RHI:begin ma<={{6{sample_q[23]}},sample_q[23:12]};mb<={{6{cr[11]}},cr};state<=RWAIT;end
    RWAIT:state<=RLO;
    RLO:begin partial<=extended_product<<<12;ma<={6'b0,sample_q[11:0]};mb<={{6{cr[11]}},cr};state<=RLWAIT;end
    RLWAIT:state<=RTERM;
    RTERM:begin term<=partial+extended_product;state<=RACC;end
    RACC:begin ar<=ar+term;state<=IHI;end
    IHI:begin ma<={{6{sample_q[23]}},sample_q[23:12]};mb<={{6{ci[11]}},ci};state<=IWAIT;end
    IWAIT:state<=ILO;
    ILO:begin partial<=extended_product<<<12;ma<={6'b0,sample_q[11:0]};mb<={{6{ci[11]}},ci};state<=ILWAIT;end
    ILWAIT:state<=ITERM;
    ITERM:begin term<=partial+extended_product;state<=IACC;end
    IACC:begin
     ai<=ai+term;
     if(n==255)state<=NORM;
     else begin n<=n+1'b1;phase<=phase+frequency_bin(band);state<=READ;end
    end
    NORM:begin nr<=ar>>>24;ni<=ai>>>24;state<=PR;end
    PR:begin ma<=nr;mb<=nr;state<=PRWAIT;end
    PRWAIT:state<=PI;
    PI:begin square_r<=product;ma<=ni;mb<=ni;state<=PIWAIT;end
    PIWAIT:state<=POWER;
    POWER:begin power_q<={1'b0,square_r}+{1'b0,product};state<=LEVEL_START;end
    LEVEL_START:state<=LEVEL_WAIT;
    LEVEL_WAIT:if(level_done)state<=PUBLISH;
    PUBLISH:begin
     working[band*8+:8]<=encoded_level;bin_valid<=1;bin_index<=band;bin_energy<=power_q;
     if(band==15)begin levels<={encoded_level,working[119:0]};levels_valid<=1;state<=IDLE;end
     else begin band<=band+1'b1;n<=0;phase<=0;ar<=0;ai<=0;state<=READ;end
    end
    default:state<=IDLE;
   endcase
  end
 end
endmodule

