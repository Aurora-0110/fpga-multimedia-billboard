`timescale 1ns/1ps
module tb_v107_ui_pin;
 reg clk=0;always #5 clk=~clk;reg rst=0,k0=1,k1=1;
 reg [11:0] x=1;reg de=0,fail=0;wire [1:0]keys,field,choice;
 wire nt,mt,osd,sel,pin,paused;wire signed[7:0]br;wire[2:0]gain;wire visible;
 media_controls #(.DEBOUNCE_CYCLES(3),.HOLD_CYCLES(40))c(clk,rst,k0,k1,nt,mt,br,gain,field,osd,keys,sel,choice,pin,paused,);
 media_ui_overlay #(.TIMEOUT_FRAMES(3))d(.clk(clk),.rst_n(rst),.x(x),.y(12'd0),.rgb(24'hffffff),.de(de),.hs(1'b1),.vs(1'b1),.picture_visible(1'b1),
 .volume_level(4'd10),.keys_down(keys),.brightness(br),.contrast_q2(gain),.edit_field(field),.auto_mode(1'b1),.overlays_enabled(osd),.image_index(2'd0),.loading(1'b0),.load_failed(fail),.tf_error(8'd0),.audio_active(!paused),.audio_select(sel),.audio_choice(choice),.audio_status(paused?3'd1:3'd0),.ui_toggle(pin),.ui_visible(visible),.x_out(),.y_out(),.rgb_out(),.de_out(),.hs_out(),.vs_out(),.picture_visible_out());
 task cycles(input integer n);repeat(n)@(negedge clk);endtask
 task frame;begin x=0;de=1;cycles(1);x=1;de=0;cycles(50);end endtask
 task release_all;begin k0=1;k1=1;cycles(16);end endtask
 task long_key(input bit which);begin
  if(which)k1=0;else k0=0;cycles(16);frame();frame();release_all();frame();
 end endtask
 task short_key(input bit which);begin
  if(which)k1=0;else k0=0;cycles(16);release_all();frame();
 end endtask
 initial begin
  #23;rst=1;cycles(25);repeat(5)frame();if(visible)$fatal(1,"auto hide");
  long_key(1);if(!visible)$fatal(1,"long K1 must SHOW from timeout even if key-down temporarily wakes UI");
  repeat(10)frame();if(!visible)$fatal(1,"manual SHOW timed out");
  long_key(0);if(!sel||!visible||nt)$fatal(1,"enter audio mode");
  short_key(1);if(choice!=1||mt)$fatal(1,"music selection leaked mode");
  long_key(1);if(visible)$fatal(1,"audio selection forced UI open after CLOSE");
  repeat(10)frame();if(visible)$fatal(1,"hidden selection UI reopened");
  short_key(0);if(!paused||!sel||visible||nt)$fatal(1,"pause must not exit or wake hidden UI");
  long_key(1);if(!visible||!paused)$fatal(1,"paused UI SHOW");
  repeat(10)frame();if(!visible)$fatal(1,"paused UI timeout");
  short_key(0);if(paused||!sel||!visible)$fatal(1,"resume command");
  long_key(1);if(visible)$fatal(1,"playing UI CLOSE");
  short_key(1);if(choice!=2||visible||paused)$fatal(1,"switch source must not wake hidden UI");
  long_key(0);if(sel||visible||nt)$fatal(1,"exit audio selection preserves hidden UI and image");
  short_key(0);if(!nt||visible)$fatal(1,"image action with hidden UI");
  fail=1;frame();if(!visible)$fatal(1,"live fault may not be hidden");
  fail=0;frame();if(visible)$fatal(1,"fault clear must restore manual HIDE");
  long_key(1);if(!visible)$fatal(1,"independent reopen outside audio mode");
  $display("PASS v110 integrated gestures/UI: SHOW/CLOSE during play and pause, frame-crossing long hold, hidden source/image actions, no release reopen, real fault override/restore, no image/mode leakage");$finish;
 end
 initial begin #1000000;$fatal(1,"UI timeout");end
endmodule
