`timescale 1ns/1ps
module tb_playlist_ctrl;
 reg stream_fault=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,key_press=0,load_rst_n=0,load_done=0,display_running=0;
 reg[1:0]phase=0;reg[7:0]load_error=0;
 wire mode_press=1'b0;wire auto_mode;
 wire restart,busy,failed;wire[1:0]image_index;wire[7:0]file_letter;
 tf_playlist_ctrl dut(.*);
 integer pulses=0;
 always @(posedge clk)if(restart)pulses=pulses+1;
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task key;begin key_press=1;tick(1);key_press=0;tick(1);end endtask
 task start_load;begin load_done=0;display_running=0;load_error=0;phase=0;load_rst_n=0;tick(5);phase=1;load_rst_n=1;tick(4);end endtask
 task complete_load;begin phase=2;load_done=1;tick(4);if(!busy)$fatal(1,"ready without video running");display_running=1;tick(5);if(busy||failed)$fatal(1,"not ready after display starts");end endtask
 task select_next(input integer idx);begin key; if(!busy||image_index!==idx||file_letter!==8'h41+idx)$fatal(1,"selection %0d",image_index);end endtask
 initial begin
 tick(3);rst_n=1;tick(2);if(image_index!==0||file_letter!=="A"||!busy)$fatal(1,"power reset");
 start_load();key();if(pulses!=0||image_index!=0)$fatal(1,"busy key queued");complete_load();
 select_next(1);load_error=8'h14;tick(10);if(failed||image_index!=1||pulses!=1)$fatal(1,"old error before new epoch");
 start_load();key();complete_load();if(pulses!=1)$fatal(1,"busy key not discarded");
 select_next(2);start_load();load_error=8'h14;tick(3);if(!failed||busy)$fatal(1,"missing C not failed");
 key();if(image_index!=2||pulses!=3||!busy)$fatal(1,"failed retry must stay C");
 // Old sticky error is ignored until content reset, then cleared by loader.
 tick(4);if(failed)$fatal(1,"stale error leaked across restart");start_load();complete_load();
 select_next(0);start_load();complete_load();if(pulses!=4)$fatal(1,"restart pulse count");
 rst_n=0;tick(3);rst_n=1;tick(3);if(image_index!=0||!busy)$fatal(1,"global reset");
 $display("PASS playlist_control A_B_C_retryC_A busy_keys stale_error index_reset pulses=%0d",pulses);$finish;
 end
 initial begin #100000;$fatal(1,"playlist timeout");end
endmodule
