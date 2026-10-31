`timescale 1ns/1ps
module tb_v089_controls;
reg clk=0;always #5 clk=~clk;reg rst=0,k0=1,k1=1;wire nt,mt,osd;wire signed[7:0]br;wire[2:0]gain;wire[1:0]field;
wire [1:0] keys;
picture_controls_osd #(.DEBOUNCE_CYCLES(3),.HOLD_CYCLES(8))d(clk,rst,k0,k1,nt,mt,br,gain,field,osd,keys);
integer nc=0,mc=0,i;reg prevn=0,prevm=0;
always @(negedge clk)if(rst)begin if(nt!=prevn)nc++;if(mt!=prevm)mc++;prevn=nt;prevm=mt;end else begin prevn=0;prevm=0;end
task tick(input integer n);repeat(n)@(negedge clk);endtask
task single(input bit key);begin if(key)k1=0;else k0=0;tick(12);k0=1;k1=1;tick(14);end endtask
task chord;begin k0=0;k1=0;tick(32);k0=1;tick(10);k1=1;tick(14);end endtask
initial begin
 // Held-at-reset key must not become a next-image gesture on release.
 k0=0;#23;rst=1;tick(24);k0=1;tick(24);
 if(nc||mc||field||br||gain!=4||!osd)$fatal(1,"boot-held key action");
 // Both edges of bounce shorter than stable-time requirement.
 repeat(4)begin k0=0;tick(1);k0=1;tick(2);end tick(20);
 if(nc||mc)$fatal(1,"bounce generated action");
 single(0);single(1);if(nc!=1||mc!=1)$fatal(1,"normal actions");
 // Short overlapping chord and staggered release suppress single actions.
 k0=0;tick(7);k1=0;tick(7);k0=1;tick(8);k1=1;tick(15);
 if(nc!=1||mc!=1||field||osd)$fatal(1,"short chord must toggle only OSD");
 chord();if(field!=1||!osd)$fatal(1,"enter brightness or held autorepeated");
 for(i=0;i<8;i++)single(1);if(br!=64)$fatal(1,"bright high clamp");
 for(i=0;i<12;i++)single(0);if(br!= -64)$fatal(1,"bright low clamp");
 for(i=0;i<4;i++)single(1);if(br!=0)$fatal(1,"bright default");
 chord();if(field!=2)$fatal(1,"enter contrast");
 for(i=0;i<8;i++)single(1);if(gain!=6)$fatal(1,"contrast high clamp");
 for(i=0;i<8;i++)single(0);if(gain!=2)$fatal(1,"contrast low clamp");
 single(1);single(1);if(gain!=4)$fatal(1,"contrast default");
 chord();if(field!=0||nc!=1||mc!=1)$fatal(1,"exit editing/chord generated playlist action");
 single(0);single(1);if(nc!=2||mc!=2)$fatal(1,"restored playlist controls");
 rst=0;tick(2);rst=1;tick(24);if(br||gain!=4||field||nt||mt||!osd)$fatal(1,"reset defaults");
 nc=0;mc=0;
 // Repeat short chords; neither press bounce nor staggered release may
 // create extra switches or leak a playlist command.
 k0=0;k1=0;tick(7);k0=1;tick(8);k1=1;tick(15);
 if(osd||nc||mc||field)$fatal(1,"short-chord default toggle");
 k1=0;tick(6);k0=0;tick(7);k1=1;tick(7);k0=1;tick(16);
 if(!osd||nc||mc||field)$fatal(1,"reverse-order short chord");
 // Boot-held chord: release is not a new gesture.
 rst=0;k0=0;k1=0;tick(2);rst=1;tick(30);k0=1;k1=1;tick(30);
 if(!osd||field||nc||mc)$fatal(1,"boot-held chord toggled OSD");
 $display("PASS v089_controls: OSD-short-chord/default-on/long-hold-auto-show/no-playlist/both-order/bounce/staggered-release/boot-held/clamps/reset; legacy controls: boot-held/bounce/release/chord/staggered-release/one-per-hold/clamps/no-playlist-in-edit/reset");$finish;
end
initial begin #1000000;$fatal(1,"watchdog");end
endmodule
