`timescale 1ns/1ps
module tb_v119_controls;
 reg clk=0;always #5 clk=~clk;reg rst=0,k0=1,k1=1;
 wire nt,mt,osd,sel,pin,paused;wire signed [7:0] br;wire [2:0] gain;wire [1:0] field,keys,choice;
 media_controls #(.DEBOUNCE_CYCLES(3),.HOLD_CYCLES(40))d(clk,rst,k0,k1,nt,mt,br,gain,field,osd,keys,sel,choice,pin,paused,);
 integer nc=0,mc=0,i;reg pn=0,pm=0;
 always @(negedge clk)if(rst)begin if(pn!=nt)nc++;if(pm!=mt)mc++;pn=nt;pm=mt;end else begin pn=0;pm=0;nc=0;mc=0;end
 task cycles(input integer n);repeat(n)@(negedge clk);endtask
 task release_all;begin k0=1;k1=1;cycles(16);end endtask
 task short_key(input bit which);begin if(which)k1=0;else k0=0;cycles(15);release_all();end endtask
 task long_key(input bit which);begin if(which)k1=0;else k0=0;cycles(100);release_all();end endtask
 task long_chord;begin k0=0;k1=0;cycles(100);release_all();end endtask
 initial begin
  // Reset with K0 down: all long/short actions inhibited until full release.
  k0=0;#23;rst=1;cycles(110);release_all();cycles(20);
  if(nt||mt||sel||pin||field||choice||paused||br||gain!=4||!osd)$fatal(1,"boot-held single");
  repeat(5)begin k0=0;cycles(1);k0=1;cycles(2);end cycles(20);
  if(nt||sel)$fatal(1,"short bounce");
  short_key(0);short_key(1);if(nc!=1||mc!=1)$fatal(1,"legacy short release");
  long_key(0);if(!sel||nc!=1||mc!=1||choice!=0)$fatal(1,"enter selection long K0 leaked short");
  short_key(1);if(choice!=1||mc!=1)$fatal(1,"select tone A leaked mode");
  short_key(1);if(choice!=2||mc!=1)$fatal(1,"select tone B");
  short_key(1);if(choice!=3||mc!=1)$fatal(1,"select extra WAV");
  short_key(1);if(choice!=0||mc!=1)$fatal(1,"four-source selection wrap");
  short_key(1);short_key(0);if(!sel||!paused||choice!=1||nc!=1)$fatal(1,"short K0 pause");
  short_key(0);if(paused||!sel||nc!=1)$fatal(1,"short K0 resume");
  short_key(0);short_key(1);if(paused||choice!=2||mc!=1)$fatal(1,"source selection must start new source");
  short_key(0);long_key(0);if(sel||!paused||choice!=2||nc!=1)$fatal(1,"long K0 exit must retain paused position");
  long_key(0);short_key(0);if(!sel||paused)$fatal(1,"reenter resume");
  long_key(0);if(sel||choice!=2||nc!=1)$fatal(1,"long K0 exit/repeated hold");
  long_key(1);if(!pin||mc!=1)$fatal(1,"pin long K1 leaked mode");
  long_key(1);if(pin||mc!=1)$fatal(1,"unpin long K1 leaked mode");
  // Short overlapping chords own the session, either order, staggered release.
  k0=0;cycles(10);k1=0;cycles(12);k0=1;cycles(10);k1=1;cycles(16);
  if(osd||field||sel||pin||nc!=1||mc!=1)$fatal(1,"short overlap chord");
  k1=0;cycles(9);k0=0;cycles(12);k1=1;cycles(9);k0=1;cycles(16);
  if(!osd||nc!=1||mc!=1)$fatal(1,"reverse chord");
  long_chord();if(field!=1||!osd)$fatal(1,"brightness entry");
  for(i=0;i<8;i++)short_key(1);if(br!=64)$fatal(1,"brightness high clamp");
  for(i=0;i<12;i++)short_key(0);if(br!= -64)$fatal(1,"brightness low clamp");
  long_chord();if(field!=2)$fatal(1,"contrast entry");
  for(i=0;i<8;i++)short_key(1);if(gain!=6)$fatal(1,"contrast high clamp");
  for(i=0;i<8;i++)short_key(0);if(gain!=2)$fatal(1,"contrast low clamp");
  long_chord();if(field||nc!=1||mc!=1)$fatal(1,"edit exit/chord leaked");
  // A late second button after a fired single long cannot add a chord action.
  k0=0;cycles(80);if(!sel)$fatal(1,"long held missing");k1=0;cycles(100);release_all();
  if(!sel||field||nc!=1||mc!=1)$fatal(1,"late chord added second action");
  // A chord arriving BEFORE threshold cancels both individual longs.
  long_key(0);if(sel)$fatal(1,"selection exit");
  k0=0;cycles(25);k1=0;cycles(30);k0=1;cycles(10);k1=1;cycles(16);
  if(sel||pin||field||osd)$fatal(1,"early chord wrong long or OSD");
  // Held chord at reset is never a new command.
  rst=0;k0=0;k1=0;cycles(3);rst=1;cycles(110);release_all();cycles(20);
  if(nt||mt||sel||pin||field||choice||paused||br||gain!=4||!osd)$fatal(1,"reset defaults/held chord");
  short_key(0);short_key(1);if(nc!=1||mc!=1)$fatal(1,"rearm after reset");
  $display("PASS v119 media controls: short/long K0 K1, modal choice/wrap/retention, one-per-hold, bounce, both chord orders, early/late chord arbitration, staggered release, startup/reset, parameter clamps, no leaked image/mode action");$finish;
 end
 initial begin #1000000;$fatal(1,"controls timeout");end
endmodule
