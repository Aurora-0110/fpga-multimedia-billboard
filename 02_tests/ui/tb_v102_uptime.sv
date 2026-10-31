`timescale 1ns/1ps
module tb_v102_uptime;
 reg clk=0;always #5 clk=~clk;reg rst=0;reg[11:0]x=1,y=0;reg de=0;
 osd_layers_visual #(.FRAMES_PER_SECOND(1))d(.clk(clk),.rst_n(rst),.x(x),.y(y),.rgb(24'h123456),.de(de),.hs(1'b1),.vs(1'b1),.picture_visible(1'b1),.auto_mode(1'b1),.image_index(2'd0),.show_osd(1'b1),.brightness(8'sd0),.contrast_q2(3'd4),.edit_field(2'd0),.x_out(),.y_out(),.rgb_out(),.de_out(),.hs_out(),.vs_out(),.picture_visible_out());
 integer checks=0;
 task boundary(input[23:0]start,input[23:0]want);begin
  @(negedge clk);{d.h1,d.h0,d.m1,d.m0,d.s1,d.s0}=start;de=0;x=1;repeat(3)@(negedge clk);
  x=0;y=0;de=1;@(negedge clk);de=0;x=1;
  if({d.h1,d.h0,d.m1,d.m0,d.s1,d.s0}!==start)$fatal(1,"second pulse not registered");
  @(negedge clk);
  if({d.h1,d.h0,d.m1,d.m0,d.s1,d.s0}!==want)$fatal(1,"BCD boundary %h got=%h want=%h",start,{d.h1,d.h0,d.m1,d.m0,d.s1,d.s0},want);
  repeat(4)@(negedge clk);
  if({d.h1,d.h0,d.m1,d.m0,d.s1,d.s0}!==want)$fatal(1,"BCD increment repeated without frame");checks++;
 end endtask
 initial begin #23;rst=1;repeat(2)@(negedge clk);
 boundary(24'h000000,24'h000001);boundary(24'h000009,24'h000010);boundary(24'h000059,24'h000100);
 boundary(24'h005959,24'h010000);boundary(24'h095959,24'h100000);boundary(24'h995959,24'h000000);
 $display("PASS v102 registered second pulse BCD boundary tests=%0d; initialized rollover states, not 100-hour hardware endurance",checks);$finish;end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
