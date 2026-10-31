`timescale 1ns/1ps
module tb_v068_modes;
 parameter DWELL=8, DEFAULT_AUTO=1;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,key_press=0,mode_press=0,load_rst_n=0,load_done=0,display_running=0,stream_fault=0;
 reg [1:0] phase=0;reg[7:0]load_error=0;
 wire restart,busy,failed,auto_mode;wire[1:0]image_index;wire[7:0]file_letter;
 tf_playlist_ctrl #(.AUTO_ENABLE(DEFAULT_AUTO),.MODE_SWITCH_ENABLE(1),.DWELL_CYCLES(DWELL)) dut(.*);
 integer checks=0;
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task ck(input bit ok,input string msg);begin checks=checks+1;if(!ok)$fatal(1,"%s idx=%0d mode=%b state=%0d count=%0d",msg,image_index,auto_mode,dut.state,dut.dwell_count);end endtask
 task mode;begin mode_press=1;tick(1);mode_press=0;ck(!restart,"K1 must not restart");end endtask
 task next_image(input integer idx);begin key_press=1;tick(1);key_press=0;ck(restart&&image_index==idx&&file_letter==8'h41+idx,"K0 next/retry");tick(1);ck(!restart,"restart pulse width");end endtask
 task start_load;begin load_rst_n=0;phase=0;load_done=0;display_running=0;load_error=0;stream_fault=0;tick(6);load_rst_n=1;phase=1;tick(4);end endtask
 task ready;begin phase=2;load_done=1;tick(DWELL+5);ck(busy&&!restart,"wait for visible display");display_running=1;wait(dut.state==2);@(negedge clk);end endtask
 task expect_auto(input integer idx);integer i;begin
  for(i=0;i<DWELL-1;i=i+1)begin tick(1);ck(!restart,"fresh full dwell");end
  tick(1);ck(restart&&image_index==idx,"AUTO advances after dwell");tick(1);ck(!restart,"single auto restart");
 end endtask
 initial begin
  tick(3);rst_n=1;tick(1);ck(auto_mode==DEFAULT_AUTO,"reset default");
  if(auto_mode)mode();ck(!auto_mode,"enter manual during startup");
  start_load();key_press=1;tick(1);key_press=0;ck(!restart&&image_index==0,"busy K0 ignored");
  mode();ck(auto_mode,"busy K1 remembered");mode();ck(!auto_mode,"busy return manual");ready();
  tick(DWELL*4+4);ck(!restart&&image_index==0&&!busy,"MANUAL never expires");
  next_image(1);start_load();ready();tick(DWELL*3+3);ck(image_index==1&&!restart,"B stays in MANUAL");
  next_image(2);start_load();ready();next_image(0);start_load();ready();
  // Both debounced events on the same SD cycle: K1 takes priority, no page step.
  mode_press=1;key_press=1;tick(1);mode_press=0;key_press=0;
  ck(auto_mode&&!restart&&image_index==0&&dut.dwell_count==0,"simultaneous K0 K1 -> mode only");
  // Leave AUTO exactly when the old counter would expire. Must not change image.
  if(DWELL>1)tick(DWELL-1);
  mode();ck(!auto_mode&&image_index==0,"K1 wins at AUTO deadline");
  tick(DWELL*3+4);ck(!restart&&image_index==0,"no queued autoplay");
  mode();expect_auto(1);tick(DWELL*2+3);ck(image_index==1&&!restart,"no duplicate before loader reset");
  start_load();mode();ck(!auto_mode,"mode persists through loader reset");ready();
  mode();
  // Removing visible-ready must discard elapsed time; it must not auto switch.
  display_running=0;phase=1;tick(DWELL*2+5);ck(!restart,"invisible display cannot expire");
  phase=2;display_running=1;wait(dut.run_sync);@(negedge clk);expect_auto(2);
  start_load();load_error=8'h14;tick(2);ck(failed&&!busy,"TF error halts load");
  tick(DWELL*4+4);ck(image_index==2&&!restart,"AUTO never skips failed file");
  mode_press=1;key_press=1;tick(1);mode_press=0;key_press=0;
  ck(failed&&!auto_mode&&!restart,"mode only on simultaneous failed input");
  next_image(2);start_load();ready();ck(!auto_mode,"MANUAL persists on retry");
  stream_fault=1;tick(4);ck(failed,"stream fault halts");mode();ck(auto_mode&&failed,"K1 cannot clear fault");
  key_press=1;tick(1);key_press=0;ck(restart&&image_index==2,"retry current file on stream fault");
  rst_n=0;tick(2);rst_n=1;tick(1);ck(auto_mode==DEFAULT_AUTO&&image_index==0&&busy&&!restart,"whole reset restores defaults");
  $display("PASS v068_modes DWELL=%0d DEFAULT_AUTO=%0d checks=%0d",DWELL,DEFAULT_AUTO,checks);$finish;
 end
 initial begin #200000;$fatal(1,"watchdog");end
endmodule
