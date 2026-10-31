`timescale 1ns/1ps
module tb_pair_display;
 reg clk=0,rst_n=0,timing_rst_n=0,enable=0,frame_start=0,de=0,hs=0,vs=0,window=0;
 always #5 clk=~clk;
 reg empty=0;reg [12:0] used=4096;reg [23:0] data=0;
 wire pop;wire [23:0] rgb;wire [1:0] displayed_index;wire [5:0] displayed_step;
 wire de_d,hs_d,vs_d,running,fault,picture_visible;
 idx_pair_display #(.PREFILL(4)) dut(.*);
 integer fetched=0,seen=0,checks=0,epochs=0;reg expected_valid;
 function [7:0] color(input integer n);begin color=n*37+19;end endfunction
 function [7:0] tag(input integer n);begin tag={2'((n/20)%4),6'((n/20)%41)};end endfunction
 function [23:0] expand(input [7:0] c);begin expand={c[7:5],c[7:5],c[7:6],c[4:2],c[4:2],c[4:3],c[1:0],c[1:0],c[1:0],c[1:0]};end endfunction
 always @(posedge clk)begin
  if(!rst_n)fetched<=0;
  else if(pop)begin data<={tag(fetched*2),color(fetched*2+1),color(fetched*2)};fetched<=fetched+1;end
 end
 task tick;begin
  @(posedge clk);
  expected_valid=rst_n&&enable&&!fault&&(running||dut.start_now)&&window;
  #0.002;
  checks=checks+1;
  if(timing_rst_n&&{de_d,hs_d,vs_d}!={de,hs,vs})$fatal(1,"pair control latency/reset");
  if(expected_valid&&!fault)begin
   if(!picture_visible||rgb!==expand(color(seen))||{displayed_index,displayed_step}!==tag(seen))
    $fatal(1,"pair display pixel=%0d rgb=%h expected=%h tag=%h exp_tag=%h",seen,rgb,expand(color(seen)),{displayed_index,displayed_step},tag(seen));
   seen=seen+1;
  end
  @(negedge clk);
 end endtask
 task fresh;begin
  rst_n=0;enable=0;window=0;frame_start=0;empty=0;used=4096;seen=0;
  repeat(3)tick();rst_n=1;enable=1;repeat(12)tick();
  if(picture_visible||running)$fatal(1,"visible before frame start");
  frame_start=1;tick();frame_start=0;
  if(!running||picture_visible)$fatal(1,"pair startup");
  window=1;de=1;epochs=epochs+1;
 end endtask
 integer i;
 initial begin
  #1;timing_rst_n=1;fresh();
  // Odd-width active segments exercise both lanes across blanking.
  for(i=0;i<20;i=i+1)begin repeat(17)tick();window=0;de=0;repeat(5)tick();if(!picture_visible)$fatal(1,"visibility lost during blanking");window=1;de=1;end
  enable=0;tick();if(picture_visible||running)$fatal(1,"disable visibility");
  fresh();repeat(7)tick();empty=1;
  repeat(15)tick();if(!fault||running||picture_visible)$fatal(1,"missing sticky underflow");
  empty=0;repeat(8)tick();if(!fault||picture_visible)$fatal(1,"underflow not sticky");
  fresh();repeat(41)tick();window=0;tick();
  // Either-domain content reset may not disturb timing control cadence.
  rst_n=0;de=1;hs=1;vs=1;repeat(4)tick();
  fresh();repeat(43)tick();
  $display("PASS pair_display checks=%0d epochs=%0d lanes/tags/blanking/underflow/reset/retry",checks,epochs);$finish;
 end
 initial begin #100000;$fatal(1,"pair display watchdog");end
endmodule
