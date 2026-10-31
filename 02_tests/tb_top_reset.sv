`timescale 1ns/1ps
// Behavioral lock/clock injection ONLY; not a model of PLL electrical behavior.
module pll_sdram(input clk_in,rst_n,output clk_sd,clk_24,locked);
 reg sd=0;always #10.101 sd=~sd;
 assign clk_sd=sd;assign clk_24=clk_in;assign locked=rst_n;
endmodule
module EG_PHY_SDRAM_2M_32(input clk,ras_n,cas_n,we_n,input [10:0] addr,
 input [1:0] ba,inout [31:0] dq,input cs_n,dm0,dm1,dm2,dm3,cke);
 IS42s32200 model(.Clk(clk),.Cke(cke),.Cs_n(cs_n),.Ras_n(ras_n),.Cas_n(cas_n),.We_n(we_n),
 .Addr(addr),.Ba(ba),.Dqm({dm3,dm2,dm1,dm0}),.Dq(dq));
endmodule
module tb_top_reset;
 reg clk=0,key_n=1;always #20.833333 clk=~clk;
 wire ls,ld,ll,hc;wire[2:0] hd;
 idx_video_top #(.START_BITS(4),.KEY_CNT(8),.USE_TF(0)) dut(.clk24m(clk),.key0_n(key_n),.key1_n(1'b1),
 .led_sclk(ls),.led_dout(ld),.led_latch(ll),.hdmi_clk_p(hc),.hdmi_d_p(hd));
 integer checks=0,retries=0,por_cycles=0,losschecks=0,markerchecks=0;reg check=0,expect_video=0;
 reg ed,eh,ev,ew,ee;reg[23:0] ergb;
 reg txde,txhs,txvs;reg[23:0] txrgb;integer txchecks=0;
 always @(posedge clk)if(!dut.por_n)por_cycles=por_cycles+1;
 always @(posedge dut.retry)retries=retries+1;
 always @(posedge dut.pix)if(check)begin
  if(expect_video && !dut.rp)$fatal(1,"video reset due to SD lock/K0");
  if(dut.rp)begin
   txrgb=dut.screen_rgb;txde=dut.dd;txhs=dut.hd;txvs=dut.vd;
   ed=dut.de;eh=~dut.hs;ev=~dut.vs;ew=dut.window;
   ee=dut.de&&(dut.x<4||dut.x>=1276||dut.y<4||dut.y>=716);
   #0.002;
   if(dut.hdmi.rgb_q!==txrgb||dut.hdmi.de_q!==txde||dut.hdmi.hs_q!==txhs||dut.hdmi.vs_q!==txvs)
    $fatal(1,"HDMI input RGB/control pipeline misalignment");
   txchecks=txchecks+1;
   if(dut.dd!==ed||dut.hd!==eh||dut.vd!==ev)$fatal(1,"top timing mismatch");
   ergb=ee?24'hffffff:(ew?dut.rgb:24'h081830);
   if(dut.screen_rgb!==ergb)$fatal(1,"marker alignment");
   if(ee||(!ew&&ed))markerchecks=markerchecks+1;
   if(!dut.l1)losschecks=losschecks+1;
   checks=checks+1;
  end
 end
 initial begin
  #1;if(dut.por_n!==0)$fatal(1,"POR must start asserted");
  wait(dut.rp);check=1;expect_video=1;
  if(por_cycles!=15)$fatal(1,"POR cycles %0d",por_cycles);
  repeat(2000)@(negedge dut.pix);
  force dut.l1=0;
  repeat(10000)@(negedge dut.pix);
  if(dut.rs!==0||dut.rp!==1||dut.status_sync[1]!==0||dut.status_sync[0]!==1)$fatal(1,"independent PLL reset/status");
  release dut.l1;wait(dut.rs);
  // Wait for initialization and real write traffic, then K0 drain/reload.
  wait(dut.init);wait(dut.pipe.ack&&dut.pipe.ow);
  @(negedge clk);key_n=0;repeat(400)@(negedge clk);
  key_n=1;repeat(50)@(negedge clk);
  if(retries!=1)$fatal(1,"long hold produced %0d retries",retries);
  wait(dut.pipe.phase==1);
  repeat(300)@(negedge clk);
  key_n=0;repeat(30)@(negedge clk);key_n=1;repeat(100)@(negedge clk);
  if(retries!=2||checks<20000||losschecks<9000||markerchecks<100||txchecks<20000)$fatal(1,"insufficient top coverage");
  $display("PASS top_reset POR_cycles=%0d K0_retries=%0d continuous_controls=%0d SD_lock_loss_pixels=%0d markers=%0d tx_pipeline_checks=%0d",por_cycles,retries,checks,losschecks,markerchecks,txchecks);$finish;
 end
 initial begin #2000000;$fatal(1,"top timeout");end
endmodule
