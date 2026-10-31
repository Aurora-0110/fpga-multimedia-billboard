`timescale 1ns/1ps
module tb_v116_diag_persistent;
 reg clk=0,rst=0;always #5 clk=~clk;
 reg[12:0] used=3000,minimum=13'h1fff,first_used=0;reg[7:0]first_flags=0;
 display_diagnostics_osd #(.AUDIO_DEBUG(1))dut(.clk(clk),.rst_n(rst),.x(12'd500),.y(12'd500),.rgb(24'd0),
 .de(1'b1),.hs(1'b1),.vs(1'b1),.picture_visible(1'b1),.image_index(2'd0),.status(8'd0),.tf_error(8'd0),.fifo_used(13'd4096),.enable(1'b0),
 .audio_used(used),.audio_minimum(minimum),.audio_first_used(first_used),.audio_first_flags(first_flags),
 .x_out(),.y_out(),.rgb_out(),.de_out(),.hs_out(),.vs_out(),.picture_visible_out());
 initial begin
  repeat(4)@(negedge clk);rst=1;repeat(4)@(negedge clk);
  // A one-clock first-error report, nowhere near the video frame snapshot.
  first_used=13'd7;first_flags=8'ha2;@(negedge clk);first_used=0;first_flags=0;
  repeat(20)@(negedge clk);
  if(dut.afirst!=7||dut.aflags!=8'ha2)$fatal(1,"first A3 was lost on source reset/UI exit");
  first_used=13'd4;first_flags=8'hb2;repeat(3)@(negedge clk);
  if(dut.afirst!=7||dut.aflags!=8'ha2)$fatal(1,"second A3 overwrote first evidence");
  rst=0;@(negedge clk);first_used=0;first_flags=0;rst=1;repeat(3)@(negedge clk);
  if(dut.afirst!=0||dut.aflags!=0)$fatal(1,"global reset did not clear evidence");
  $display("PASS persistent A3 single-cycle capture, survives source-reset/UI-exit, first-only, global-reset");$finish;
 end
endmodule
