`timescale 1ns/1ps
// Clock/lock substitutes and an undriven SDRAM shell: only top control wiring tested.
module pll_sdram(input clk_in,rst_n,output clk_sd,clk_24,locked);
 reg sd=0;always #10.101 sd=~sd;
 assign clk_sd=sd;assign clk_24=clk_in;assign locked=rst_n;
endmodule
module EG_PHY_SDRAM_2M_32(input clk,ras_n,cas_n,we_n,input [10:0]addr,input [1:0]ba,
 inout [31:0]dq,input cs_n,dm0,dm1,dm2,dm3,cke);
endmodule
module tb_v070_top;
 reg clk24m=0,key0_n=1,key1_n=1;always #20.833333 clk24m=~clk24m;
 wire tf_cs_n,tf_sck,tf_mosi,led_sclk,led_dout,led_latch,hdmi_clk_p;wire[2:0]hdmi_d_p;
 idx_video_top #(.START_BITS(4),.KEY_CNT(4),.AUTO_DWELL_CYCLES(150)) dut(
 .clk24m(clk24m),.key0_n(key0_n),.key1_n(key1_n),.tf_miso(1'b1),
 .tf_cs_n(tf_cs_n),.tf_sck(tf_sck),.tf_mosi(tf_mosi),.led_sclk(led_sclk),.led_dout(led_dout),.led_latch(led_latch),.hdmi_clk_p(hdmi_clk_p),.hdmi_d_p(hdmi_d_p));
 integer checks=0,starts=0;reg monitor=0;
 always @(posedge dut.sd)if(dut.playlist_restart)starts=starts+1;
 always @(posedge dut.pix)if(monitor)begin
  if(!dut.rp)$fatal(1,"mode/next reset independent video");checks=checks+1;
 end
 task tick(input integer n);begin repeat(n)@(negedge dut.sd);end endtask
 task reload;begin
  force dut.lrst=0;force dut.phase=0;force dut.ldone=0;force dut.run=0;tick(8);
  force dut.lrst=1;force dut.phase=1;tick(5);
  force dut.ldone=1;force dut.phase=2;force dut.run=1;tick(6);
 end endtask
 initial begin
  force dut.len=0;force dut.load_error=0;force dut.fault=0;force dut.of=0;
  force dut.lrst=0;force dut.phase=0;force dut.ldone=0;force dut.run=0;
  wait(dut.rs&&dut.rp);@(negedge dut.sd);monitor=1;
  if(dut.auto_mode!==1)$fatal(1,"production default not AUTO");
  key1_n=0;tick(20);key1_n=1;tick(12);
  if(dut.auto_mode!==0||starts)$fatal(1,"K1 wiring/busy mode");
  reload();tick(500);if(starts||dut.image_index!=0)$fatal(1,"manual A hold");
  repeat(8)@(negedge clk24m);
  if(dut.status_sync[7]!==0||dut.status[0]!==dut.hb[21])$fatal(1,"MANUAL L0 fast indicator");
  key0_n=0;tick(22);key0_n=1;tick(12);
  if(starts!=1||dut.image_index!=1||dut.auto_mode!==0)$fatal(1,"K0 wiring");
  reload();tick(180);if(starts!=1)$fatal(1,"manual B auto advanced");
  key1_n=0;tick(20);key1_n=1;tick(12);
  if(dut.auto_mode!==1)$fatal(1,"K1 AUTO wiring");
  repeat(8)@(negedge clk24m);
  if(dut.status_sync[7]!==1||dut.status[0]!==dut.hb[24])$fatal(1,"AUTO L0 slow indicator");
  wait(dut.playlist_restart);tick(2);
  if(starts!=2||dut.image_index!=2)$fatal(1,"AUTO C missing");
  reload();wait(dut.playlist_restart);tick(2);
  if(starts!=3||dut.image_index!=3||dut.file_letter!="D")$fatal(1,"AUTO D missing");
  reload();wait(dut.playlist_restart);tick(2);
  if(starts!=4||dut.image_index!=0||dut.file_letter!="A")$fatal(1,"AUTO D to A missing");
  // Status bits L1..L7 retain old semantics while the mode changes.
  repeat(8)@(negedge clk24m);
  if(dut.status[7:1]!=={1'b0,1'b0,1'b1,dut.fr,dut.init,1'b1,1'b1})$fatal(1,"status bits shifted");
  if(checks<1000)$fatal(1,"too few active video clocks");
  $display("PASS v070_top real-top K0/K1, mode CDC/LED mapping, continuous video checks=%0d",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
