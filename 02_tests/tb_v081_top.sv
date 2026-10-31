`timescale 1ns/1ps
// Clock/lock substitutes and an undriven SDRAM shell: only top control wiring tested.
module pll_sdram(input clk_in,rst_n,output clk_sd,clk_24,locked);
 reg sd=0;always #10.101 sd=~sd;
 assign clk_sd=sd;assign clk_24=clk_in;assign locked=rst_n;
endmodule
module EG_PHY_SDRAM_2M_32(input clk,ras_n,cas_n,we_n,input [10:0]addr,input [1:0]ba,
 inout [31:0]dq,input cs_n,dm0,dm1,dm2,dm3,cke);
endmodule
module tb_v081_top;
 reg clk24m=0,key0_n=1,key1_n=1;always #20.833333 clk24m=~clk24m;
 wire tf_cs_n,tf_sck,tf_mosi,led_sclk,led_dout,led_latch,hdmi_clk_p;wire[2:0]hdmi_d_p;
 idx_video_top #(.START_BITS(4),.KEY_CNT(4),.UI_HOLD_CYCLES(12)) dut(
 .clk24m(clk24m),.key0_n(key0_n),.key1_n(key1_n),.tf_miso(1'b1),
 .tf_cs_n(tf_cs_n),.tf_sck(tf_sck),.tf_mosi(tf_mosi),.led_sclk(led_sclk),.led_dout(led_dout),.led_latch(led_latch),.hdmi_clk_p(hdmi_clk_p),.hdmi_d_p(hdmi_d_p));
 reg crst=0,tf=0,tw=0,empty=0;reg[12:0]used=0;
 integer checks=0,epochs=0;reg monitor=0;reg expected;
 always @(posedge dut.pix) if(monitor)begin
  expected=dut.op;#0.1;
  if(!dut.rp || !dut.hdmi.rst_n)$fatal(1,"content event reset HDMI");
  if(dut.hdmi.picture_q!==expected)$fatal(1,"picture gate not aligned with RGB register");
  if(dut.hdmi.audio.packets.audio_enable!==dut.hdmi.picture_q)$fatal(1,"packet gate disconnected");
  if(dut.hdmi.HDMI_AUDIO_GATE_ENABLE!=1)$fatal(1,"production gate parameter disabled");
  checks=checks+1;
 end
 integer retries=0,modes=0;
 always @(posedge dut.sd)begin if(dut.retry)retries++;if(dut.mode_press)modes++;end
 task tick(input integer n);repeat(n)@(negedge dut.pix);endtask
 task state(input bit want);begin
  tick(20);
  if(dut.picture_visible!==want || dut.hdmi.picture_q!==want)$fatal(1,"visibility/gate expected %b",want);
  if(dut.win_d && dut.screen_rgb !== (want?24'hff0000:24'h0))$fatal(1,"screen masking expected %b rgb=%h",want,dut.screen_rgb);
 end endtask
 initial begin
  // Real production display registers and top/wrapper. Only SDRAM/FIFO inputs,
  // content epoch reset and coordinate events are injected, NOT picture_visible.
  force dut.len=0;force dut.pipe.prst=crst;force dut.pipe.en=2'b11;
  force dut.pipe.fe=empty;force dut.pipe.ru=used;force dut.pipe.frd=16'h00e0;
  force dut.fs=tf;force dut.window=tw;force dut.edge_d=0;force dut.x=12'd500;force dut.y=12'd300;
  wait(dut.rp&&dut.rs);tick(2);monitor=1;
  state(0);
  repeat(3)begin
   crst=1;used=0;tw=1;state(0); // not yet frame-ready
   tw=0;used=4096;tf=1;tick(1);tf=0;state(0); // running, no real pixel
   tw=1;state(1); // first real pixel and gate high
   tw=0;state(1); // horizontal/vertical blanking must not mute
   crst=0;tw=1;state(0); // switch/restart does not reset HDMI
   epochs=epochs+1;
  end
  crst=1;used=4096;tf=1;tick(1);tf=0;state(1);
  empty=1;state(0);
  if(dut.pipe.display.fault!==1)$fatal(1,"underflow not latched");
  empty=0;state(0); // fault must not spontaneously resume tone
  crst=0;state(0);crst=1;tw=0;tf=1;tick(1);tf=0;tw=1;state(1);
  // UI edits must not issue playlist actions; only frame start commits values.
  force dut.dd=1;force dut.x_d=12'd500;force dut.y_d=12'd300;
  key0_n=0;key1_n=0;tick(32);key0_n=1;key1_n=1;tick(12);
  if(dut.ui_field!=1)$fatal(1,"top UI edit entry");
  key1_n=0;tick(12);key1_n=1;tick(12);
  if(dut.ui_brightness!=16||dut.active_brightness!=0)$fatal(1,"frame commit before first pixel");
  force dut.x_d=0;force dut.y_d=0;tick(1);
  force dut.x_d=500;force dut.y_d=300;tick(20);
  if(dut.active_brightness!=16||dut.overlay.shown_bright!=16)$fatal(1,"frame commit/OSD snapshot");
  if(dut.adjusted_rgb!==24'hff1010)$fatal(1,"top pixel adjustment got %h",dut.adjusted_rgb);
  // Exit both editors (one hold per field) then exercise event CDC.
  repeat(2)begin key0_n=0;key1_n=0;tick(32);key0_n=1;key1_n=1;tick(12);end
  key0_n=0;tick(12);key0_n=1;tick(16);
  key1_n=0;tick(12);key1_n=1;tick(16);
  if(retries!=1||modes!=1)$fatal(1,"playlist toggle CDC pulses retry%d mode%d",retries,modes);
  // ui_next/ui_mode are both 1. Memory-only reset must prime, not replay.
  force dut.l1=0;tick(10);release dut.l1;tick(24);
  if(retries!=1||modes!=1)$fatal(1,"replayed event after memory reset");
  if(!dut.rp)$fatal(1,"memory reset reset video");
  key0_n=0;tick(12);key0_n=1;tick(16);
  key1_n=0;tick(12);key1_n=1;tick(16);
  if(retries!=2||modes!=2)$fatal(1,"new actions lost after memory reset");
  // Source UI also resets on video loss; no trailing toggle may become a key.
  monitor=0;force dut.l2=0;tick(10);release dut.l2;wait(dut.rp);tick(30);monitor=1;
  if(retries!=2||modes!=2)$fatal(1,"phantom event after video reset");
  key0_n=0;tick(12);key0_n=1;tick(16);
  key1_n=0;tick(12);key1_n=1;tick(16);
  if(retries!=3||modes!=3)$fatal(1,"new actions lost after video reset");
  tick(150);
  $display("PASS v081_top first-real-pixel/top-RGB-mask/gate-alignment/blanking/restart/underflow/retry/independent-domain-reset epochs=%0d checks=%0d",epochs,checks);$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
