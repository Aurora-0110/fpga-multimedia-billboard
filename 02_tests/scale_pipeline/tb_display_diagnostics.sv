`timescale 1ns/1ps
module tb_display_diagnostics;
 reg clk=0,rst=0;always #5 clk=~clk;
 reg [11:0] x=0,y=0;reg [23:0] rgb=24'h123456;
 reg de=0,hs=1,vs=1,vis=0;reg [1:0] idx=0;
 reg [7:0] st=8'h40,err=0;reg [12:0] used=4096;
 wire [11:0] ox,oy;wire [23:0] out;wire od,oh,ov,op;
 display_diagnostics d(clk,rst,x,y,rgb,de,hs,vs,vis,idx,st,err,used,ox,oy,out,od,oh,ov,op);
`include "video/osd_font.vh"
 string header="",footer="";reg red=0,monitor=0;integer checks=0,visible_banner_pixels=0;
 reg [51:0] q[0:2];integer valid=0,cc,rr;reg [7:0] ch;reg [4:0] bits;reg [23:0] expected;
 always @(posedge clk)begin
  if(!rst)valid=0;
  else if(monitor)begin
   expected=rgb;
   if(de&&x>=8&&x<912&&y>=8&&y<48)begin
    expected=red?24'h601020:24'h102848;
    if(x>=16&&x<896&&((y>=12&&y<26)||(y>=30&&y<44)))begin
     cc=(x-16)/16;rr=(y-(y>=30?30:12))/2;
     ch=" ";if(y>=30)begin if(cc<footer.len())ch=footer[cc];end else if(cc<header.len())ch=header[cc];
     bits=fontrow(ch,rr);
     if((x-16)%16<10&&bits[4-((x-16)%16)/2])expected=24'hffffff;
    end
    if(!vis)visible_banner_pixels=visible_banner_pixels+1;
   end
   q[2]=q[1];q[1]=q[0];q[0]={x,y,expected,de,hs,vs,vis};valid=valid+1;
   #0.001;
   if(valid>=3)begin
    if({ox,oy,out,od,oh,ov,op}!==q[2])$fatal(1,"diagnostic pixel/control/gate mismatch xy=%0d/%0d got=%h exp=%h",ox,oy,{ox,oy,out,od,oh,ov,op},q[2]);
    checks=checks+1;
   end
  end else valid=0;
 end
 task cycles(input integer n);repeat(n)@(negedge clk);endtask
 task frame;begin
  monitor=0;de=1;x=0;y=0;cycles(1);de=0;x=1200;y=100;cycles(5);
 end endtask
 task scan;integer a,b;begin
  monitor=1;
  for(b=0;b<7;b=b+1)for(a=8;a<920;a=a+1)begin x=a;y=12+2*b;de=1;hs=1;vs=1;cycles(1);end
  for(b=0;b<7;b=b+1)for(a=8;a<920;a=a+1)begin x=a;y=30+2*b;de=1;hs=1;vs=1;cycles(1);end
  // Arbitrary blanking and off-banner RGB, including audio visibility changes.
  for(a=0;a<80;a=a+1)begin x=1000+a;y=300+a;de=a%2;hs=a%3!=0;vs=a%5!=0;vis=a%7!=0;rgb=24'h023400+a;cycles(1);end
  cycles(4);monitor=0;
 end endtask
 initial begin
  cycles(4);rst=1;cycles(4);frame();
  header="V088 F=0001 IMG=A FR=0 RUN=0 VIS=0 UF=0 OF=0 AU=0 TF=00";
  footer="HIST UF=0 OF=0 AU=0 TF=00 SDR=0 Q=1000 MIN=1000";red=0;vis=0;scan();
  st=8'h47;used=2700;vis=1;idx=1;cycles(4);frame();
  header="V088 F=0002 IMG=B FR=1 RUN=1 VIS=1 UF=0 OF=0 AU=0 TF=00";
  footer="HIST UF=0 OF=0 AU=0 TF=00 SDR=0 Q=0A8C MIN=0A8C";scan();
  // Content underflow, live RGB hidden; diagnostic banner must survive and
  // its output picture_visible must remain FALSE, not falsely unmute audio.
  st=8'h49;used=0;vis=0;cycles(4);frame();
  header="V088 F=0003 IMG=B FR=1 RUN=0 VIS=0 UF=1 OF=0 AU=0 TF=00";
  footer="HIST UF=1 OF=0 AU=0 TF=00 SDR=0 Q=0000 MIN=0A8C";red=1;scan();
  st=8'h70;err=8'h1a;vis=0;cycles(4);frame();
  header="V088 F=0004 IMG=B FR=0 RUN=0 VIS=0 UF=0 OF=1 AU=1 TF=1A";
  footer="HIST UF=1 OF=1 AU=1 TF=1A SDR=0 Q=0000 MIN=0A8C";scan();
  // Transient fault clears and memory reset do not erase first error evidence.
  st=0;err=0;vis=0;cycles(4);frame();
  header="V088 F=0005 IMG=B FR=0 RUN=0 VIS=0 UF=0 OF=0 AU=0 TF=00";
  footer="HIST UF=1 OF=1 AU=1 TF=1A SDR=1 Q=0000 MIN=0A8C";scan();
  if(d.history!==5'b11111||d.first_error!==8'h1a)$fatal(1,"fault history lost");
  monitor=0;rst=0;cycles(3);rst=1;st=8'h40;err=0;idx=0;vis=0;used=4096;cycles(4);frame();
  if(d.history!=0||d.first_error!=0||d.frames!=1)$fatal(1,"diagnostic reset failed");
  header="V088 F=0001 IMG=A FR=0 RUN=0 VIS=0 UF=0 OF=0 AU=0 TF=00";
  footer="HIST UF=0 OF=0 AU=0 TF=00 SDR=0 Q=1000 MIN=1000";red=0;scan();
  if(checks<70000||visible_banner_pixels<10000)$fatal(1,"insufficient diagnostic coverage");
  $display("PASS display_diagnostics checks=%0d hidden_content_banner_pixels=%0d cases=6",checks,visible_banner_pixels);$finish;
 end
 initial begin #3000000;$fatal(1,"diagnostic watchdog");end
endmodule
