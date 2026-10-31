`timescale 1ns/1ps
module tb_v099_activity;
 reg clk=0;always #5 clk=~clk;reg rst=0;
 reg signed[23:0]l=0,r=0;reg valid=0,stream=1,epoch=0;wire active;
 pcm_activity_gate #(.ATTACK_SAMPLES(4),.RELEASE_SAMPLES(8),.TIMEOUT_CYCLES(80)) d(
 .clk(clk),.rst_n(rst),.pcm_l(l),.pcm_r(r),.pcm_valid(valid),.stream_active(stream),.track_change(epoch),.sound_active(active));
 reg signed[23:0]pl=0;reg pv=0;wire pa;
 pcm_activity_gate production(.clk(clk),.rst_n(rst),.pcm_l(pl),.pcm_r(24'sd0),
 .pcm_valid(pv),.stream_active(1'b1),.track_change(1'b0),.sound_active(pa));
 integer checks=0;
 task tick(input integer n);repeat(n)@(negedge clk);endtask
 task expect_active(input bit want);begin checks++;if(active!==want)$fatal(1,"activity expected%0d got%0d check%0d",want,active,checks);end endtask
 task sample(input integer a,b);begin l=a;r=b;valid=1;tick(1);valid=0;tick(1);end endtask
 task reset_gate;begin rst=0;tick(2);rst=1;tick(1);end endtask
 initial begin
  tick(2);rst=1;tick(1);expect_active(0);
  repeat(24)sample(0,0);expect_active(0); // valid I2S zeros must NOT show
  repeat(10)sample(1024,-1024);expect_active(0); // small noise
  repeat(3)sample(8192,0);expect_active(0);sample(0,0);expect_active(0); // click reject
  repeat(3)sample(4096,0);expect_active(0);sample(4096,0);expect_active(1); // exact on threshold
  repeat(20)sample(3000,0);expect_active(1); // hysteresis between thresholds
  repeat(7)sample(0,0);expect_active(1);sample(2048,0);expect_active(1); // exact off resets release
  repeat(7)sample(0,0);expect_active(1);sample(0,0);expect_active(0);
  repeat(4)sample(0,-8192);expect_active(1); // right-only negative
  epoch=1;tick(1);epoch=0;expect_active(0);
  repeat(4)sample(32768,-32768);expect_active(1); // anti-phase must NOT cancel
  stream=0;tick(1);expect_active(0);repeat(8)sample(8388607,8388607);expect_active(0);
  stream=1;repeat(4)sample(-8388608,0);expect_active(1); // abs(-2^23) no overflow
  tick(78);expect_active(1);tick(1);expect_active(0); // last sample had 1 idle clock
  repeat(4)sample(0,8388607);expect_active(1);
  rst=0;tick(1);expect_active(0);rst=1;tick(1);
  // Default production release is EXACTLY19200 accepted quiet samples=400ms
  // at48k; continuous valid accelerates simulation, not the configured count.
  pl=8192;pv=1;tick(3);if(pa)$fatal(1,"default early attack");tick(1);if(!pa)$fatal(1,"default attack");
  pl=0;tick(19199);if(!pa)$fatal(1,"default early release");tick(1);if(pa)$fatal(1,"default release");pv=0;
  if(production.TIMEOUT_CYCLES!=7425000||production.ON_THRESHOLD!=4096||production.OFF_THRESHOLD!=2048)$fatal(1,"production defaults");
  $display("PASS v099 PCM activity checks=%0d valid-silence/noise/hysteresis/exact-400ms/missing-data/stereo-antiphase/min-negative/epoch/gate/reset",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"activity watchdog");end
endmodule
