`timescale 1ns/1fs
// Exercises the PRODUCTION dual-domain wrapper and installed TD ODDR model.
// Digital lock injection is not an electrical PLL or metastability model.
module tb_v072_audio_native;
 parameter integer PHASE_PS=370;
 reg pix=0,fast=0,lock=0;
 always #1.346801347 fast=~fast;
 initial begin #(PHASE_PS/1000.0); forever #6.734006735 pix=~pix; end
 wire prst;
 reset_release #(.RELEASE_FALLING_EDGE(1)) rp(.clk(pix),.async_n(lock),.rst_n(prst));
 reg[23:0] rgb=0;reg de=0,hs=0,vs=0;
 wire cp;wire[2:0] dp;
 wire [11:0] cx,cy;wire hsync,vsync,vde,fs;
 video_timing #(.H_ACTIVE(1280),.H_FP(110),.H_SYNC(40),.H_BP(220),.V_ACTIVE(720),.V_FP(5),.V_SYNC(5),.V_BP(20))
 vt(.clk(pix),.rst_n(prst),.x(cx),.y(cy),.hs(hsync),.vs(vsync),.de(vde),.frame_start(fs));
 hdmi_tx_wrap #(.INDEPENDENT_SERIAL_RESET(1),.HDMI_AUDIO_ENABLE(1)) dut(.clk_pix(pix),.clk_5x(fast),.rst_n(prst),
 .serial_async_n(lock),.r(rgb[23:16]),.g(rgb[15:8]),.b(rgb[7:0]),.de(vde),.hs(~hsync),.vs(~vsync),.cx(cx),.cy(cy),
 .tmds_clk_p(cp),.tmds_clk_n(),.tmds_d_p(dp),.tmds_d_n());
 wire srst=dut.serial_rst_n;
 always @(negedge pix) if(prst)begin rgb<=$random;de<=$random;hs<=$random;vs<=$random;end
 reg marker=0;reg[29:0] queue[0:8191];integer put=0,get=0,phase=5;
 integer words=0,bits=0,epochs=0,independent_cycles=0;
 reg s0=0,s1=0,seen=0,load_ref;reg[39:0] word=0;
 reg[3:0] lo,hi;real last_rise=0;
 always @(posedge fast) last_rise=$realtime;
 always @(posedge srst)begin
  if($realtime>1 && (($realtime-last_rise)>0.005))$fatal(1,"serial reset not released on LOCAL rising edge");
 end
 always @(posedge pix or negedge prst)
 if(!prst)begin marker<=0;put=0;end
 else begin
  marker<=~marker;
  // Encoder output updates on this pixel edge, stays valid through capture.
  #0.002; queue[put]={dut.symbol_r,dut.symbol_g,dut.symbol_b};put=put+1;
  if(put>=8192)$fatal(1,"queue capacity");
 end
 always @(posedge fast or negedge srst)begin
  if(!srst)begin get=0;phase=5;s0=0;s1=0;seen=0;word=0;hi=0;end
  else begin
   if(!prst)independent_cycles=independent_cycles+1;
   lo=0;hi=0;
   if(phase<5)begin
    lo={word[30+2*phase],word[20+2*phase],word[10+2*phase],word[2*phase]};
    hi={word[31+2*phase],word[21+2*phase],word[11+2*phase],word[1+2*phase]};
   end
   load_ref=(s1!=seen);seen=s1;s1=s0;s0=marker;
   if(load_ref)begin
    if(get>=put)$fatal(1,"unissued pixel");
    if(phase!=5&&phase!=4)$fatal(1,"word overlap");
    word={10'b1111100000,queue[get]};get=get+1;phase=0;words=words+1;
   end else if(phase<5)phase=phase+1;
   #0.250;
   if(srst && {cp,dp}!==lo)$fatal(1,"positive 4-lane mismatch got=%b expected=%b word=%0d phase=%0d",{cp,dp},lo,words,phase);
   if(srst)bits=bits+4;
  end
 end
 always @(negedge fast)begin
  #0.250;
  if(srst)begin
   if({cp,dp}!==hi)$fatal(1,"negative 4-lane mismatch got=%b expected=%b word=%0d phase=%0d",{cp,dp},hi,words,phase);
   bits=bits+4;
  end
 end
 initial begin
  #83.371;lock=1;
  repeat(2)begin
   repeat(8000)@(negedge pix);
   #(0.137+epochs*0.111);lock=0;
   #0.002;if(prst!==0||srst!==0)$fatal(1,"loss must assert both resets asynchronously");
   #(47.319+epochs*1.217);epochs=epochs+1;lock=1;
  end
  repeat(2000)@(negedge pix);#3;
  if(epochs!=2||words<2500||bits<100000||independent_cycles<20)$fatal(1,"coverage words=%0d bits=%0d independent=%0d",words,bits,independent_cycles);
  $display("PASS audio_native phase_ps=%0d four_lane_bits=%0d words=%0d lock_retries=%0d independent_cycles=%0d",PHASE_PS,bits,words,epochs,independent_cycles);$finish;
 end
 initial begin #300000;$fatal(1,"timeout");end
endmodule
