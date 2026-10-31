`timescale 1ns/1ps
module tb_v081_clock;
 reg clk=0,rst=0,de=0,mode=0;always #5 clk=~clk;
 wire [23:0] rgb;wire [11:0] x,y;wire d,h,v,p;
 osd_layers #(.FRAMES_PER_SECOND(1),.SHOW_PARAMS(1)) dut(.clk(clk),.rst_n(rst),.x(12'd0),.y(12'd0),.rgb(24'd0),
 .de(de),.hs(1'b1),.vs(1'b1),.picture_visible(1'b0),.auto_mode(mode),.image_index(2'd0),
 .brightness(8'sd16),.contrast_q2(3'd5),.edit_field(2'd2),.rgb_out(rgb),.x_out(x),.y_out(y),.de_out(d),.hs_out(h),.vs_out(v),.picture_visible_out(p));
 integer sec,hour,min,ss,checks=0;
 initial begin
  repeat(3)@(negedge clk);rst=1;
  for(sec=1;sec<=360001;sec=sec+1)begin
   de=1;mode=sec[0];@(negedge clk);de=0;
   hour=(sec/3600)%100;min=(sec/60)%60;ss=sec%60;
   if(dut.h1!==hour/10||dut.h0!==hour%10||dut.m1!==min/10||dut.m0!==min%10||dut.s1!==ss/10||dut.s0!==ss%10)
    $fatal(1,"BCD second=%0d got %0d%0d:%0d%0d:%0d%0d",sec,dut.h1,dut.h0,dut.m1,dut.m0,dut.s1,dut.s0);
   if(dut.scroll!==sec%768||dut.shown_mode!==mode)$fatal(1,"scroll/mode second=%0d",sec);
   if(dut.shown_bright!==16||dut.shown_contrast!==5||dut.shown_field!==2)$fatal(1,"frame parameter snapshot");
   checks=checks+1;@(negedge clk);
  end
  rst=0;@(negedge clk);
  if(dut.s0!==0||dut.h1!==0||dut.scroll!==0)$fatal(1,"reset");
  $display("PASS clock %0d seconds including minute/hour/100-hour wrap; scroll wrap; frame-latched mode and reset",checks);$finish;
 end
 initial begin #10000000;$fatal(1,"watchdog");end
endmodule
