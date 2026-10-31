`timescale 1ns/1ps
module tb_v068_keys;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,k0=1,k1=1;
 wire key_press,mode_press,restart,busy,failed,auto_mode;wire[1:0]image_index;wire[7:0]file_letter;
 reg load_rst_n=0,load_done=0,display_running=0,stream_fault=0;reg[1:0]phase=0;reg[7:0]load_error=0;
 key_debounce #(.CNT(4)) d0(.clk(clk),.rst_n(rst_n),.key_n(k0),.press(key_press));
 key_debounce #(.CNT(4)) d1(.clk(clk),.rst_n(rst_n),.key_n(k1),.press(mode_press));
 tf_playlist_ctrl #(.AUTO_ENABLE(1),.MODE_SWITCH_ENABLE(1),.DWELL_CYCLES(500)) dut(.*);
 integer kp=0,mp=0,rp=0;
 always @(posedge clk)begin if(key_press)kp=kp+1;if(mode_press)mp=mp+1;if(restart)rp=rp+1;end
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task load;begin load_rst_n=0;phase=0;load_done=0;display_running=0;tick(8);load_rst_n=1;phase=1;tick(3);phase=2;load_done=1;display_running=1;tick(6);end endtask
 initial begin
  tick(3);rst_n=1;tick(2);
  // Short low/high chatter is rejected. Release chatter cannot re-arm a held key.
  k1=0;tick(1);k1=1;tick(1);k1=0;tick(1);k1=1;tick(8);
  if(mp||!auto_mode)$fatal(1,"K1 bounce accepted");
  k1=0;tick(40);if(mp!=1||auto_mode||rp)$fatal(1,"held K1 must toggle once");
  k1=1;tick(1);k1=0;tick(15);if(mp!=1)$fatal(1,"release chatter retriggered");
  k1=1;tick(10);load();
  tick(1000);if(rp||image_index!=0)$fatal(1,"manual timer active");
  k0=0;tick(50);if(kp!=1||rp!=1||image_index!=1)$fatal(1,"held K0 must next once");
  k0=1;tick(10);load();
  k0=0;k1=0;tick(20);if(kp!=2||mp!=2||rp!=1||!auto_mode||image_index!=1)$fatal(1,"two keys must not double step");
  k0=1;k1=1;tick(10);k1=0;tick(20);k1=1;tick(10);
  if(auto_mode||mp!=3||rp!=1)$fatal(1,"second K1 must return manual");
  tick(1000);if(rp!=1||image_index!=1)$fatal(1,"manual not holding after mode switch");
  $display("PASS v068_keys bounce/long-hold/release/repress/simultaneous/manual");$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
