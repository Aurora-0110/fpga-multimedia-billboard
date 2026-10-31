`timescale 1ns/1ps
module tb_autoplay_ctrl;
 parameter integer DWELL=8;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,key_press=0,load_rst_n=0,load_done=0,display_running=0,stream_fault=0;
 reg [1:0] phase=0;reg[7:0]load_error=0;
 wire mode_press=1'b0;wire auto_mode;
 wire restart,busy,failed;wire[1:0]image_index;wire[7:0]file_letter;
 tf_playlist_ctrl #(.AUTO_ENABLE(1),.DWELL_CYCLES(DWELL)) dut(.*);
 integer pulses=0;always @(posedge clk)if(restart)pulses=pulses+1;
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task key;begin key_press=1;tick(1);key_press=0;tick(1);end endtask
 task start_load;begin load_rst_n=0;phase=0;load_done=0;display_running=0;load_error=0;stream_fault=0;tick(8);load_rst_n=1;phase=1;tick(4);end endtask
 task complete_load;begin
  load_done=1;phase=2;tick(2*DWELL+8);
  if(!busy||restart)$fatal(1,"timer counts before display running");
  display_running=1;wait(dut.state==2);@(negedge clk);
 end endtask
 task expect_auto(input integer idx);integer n;begin
  for(n=0;n<(DWELL>1?DWELL:1)-1;n=n+1)begin tick(1);if(restart)$fatal(1,"early autoplay");end
  tick(1);if(!restart||image_index!==idx||file_letter!==8'h41+idx)$fatal(1,"autoplay selection idx=%0d",image_index);
  tick(DWELL+8);if(restart||dut.state!=4)$fatal(1,"duplicate restart before reset");
 end endtask
 integer before_pulses;
 initial begin
  tick(3);rst_n=1;start_load();key();tick(2*DWELL+8);
  if(pulses||image_index!=0)$fatal(1,"busy key/timer advanced");
  complete_load();expect_auto(1);start_load();complete_load();expect_auto(2);
  start_load();load_error=8'h14;tick(5);
  if(!failed)$fatal(1,"missing C must stop");before_pulses=pulses;tick(DWELL*3+9);
  if(pulses!=before_pulses||image_index!=2)$fatal(1,"failed file skipped");
  key();if(image_index!=2||!busy)$fatal(1,"retry must stay C");
  start_load();complete_load();expect_auto(0);
  // Any loss of display-running clears accumulated dwell, not immediate advance.
  if(DWELL>=8)begin
   start_load();complete_load();tick(2);display_running=0;tick(5);
   if(dut.dwell_count!=0||restart)$fatal(1,"display drop did not reset dwell");
   display_running=1;wait(dut.run_sync);@(negedge clk);expect_auto(1);
   start_load();complete_load();
   // Coincident manual key + timer fires once, never skips two images.
   tick(DWELL-1);key_press=1;tick(1);key_press=0;
   if(!restart||image_index!=2)$fatal(1,"key timer coincidence");
   tick(4);start_load();complete_load();stream_fault=1;tick(4);
   if(!failed||restart)$fatal(1,"stream fault must inhibit autoplay");
   before_pulses=pulses;tick(3*DWELL);
   if(pulses!=before_pulses)$fatal(1,"stream failure loop");
   key();if(image_index!=2)$fatal(1,"stream fault retry skipped file");
  end
  rst_n=0;tick(3);rst_n=1;tick(3);if(image_index!=0||!busy)$fatal(1,"reset must select A");
  $display("PASS autoplay_control DWELL=%0d load_wait dwell wrap same_file_retry no_duplicate drop fault coincidence pulses=%0d",DWELL,pulses);$finish;
 end
 initial begin #1000000;$fatal(1,"autoplay timeout");end
endmodule
