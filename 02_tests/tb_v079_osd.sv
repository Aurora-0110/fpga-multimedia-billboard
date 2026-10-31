`timescale 1ns/1ps
module tb_v079_osd;
reg clk=0;always #5 clk=~clk;reg rst=0;reg[11:0]x=0,y=0;reg[23:0]rgb=0;
reg de=0,hs=1,vs=1,pv=0,mode=1;reg[1:0]idx=0;
wire[11:0]ox,oy;wire[23:0]out;wire od,oh,ov,op;
osd_layers #(.FRAMES_PER_SECOND(2))d(clk,rst,x,y,rgb,de,hs,vs,pv,mode,idx,ox,oy,out,od,oh,ov,op);
function[23:0]mix;input[23:0]a,b;input integer alpha;integer i,aa,v;begin
 aa=alpha<0?0:(alpha>16?16:alpha);
 for(i=0;i<3;i++)begin v=(a[i*8+:8]*(16-aa)+b[i*8+:8]*aa+8)/16;mix[i*8+:8]=v;end end endfunction
reg[23:0]q[0:5];reg[27:0]c[0:5];reg[23:0]e;integer n=0,checks=0,panels=0,logos=0,texts=0;
wire panel=de&&pv&&x>=320&&x<960&&((y>=120&&y<188)||(y>=564&&y<600));
wire logo_zone=de&&pv&&x>=328&&x<440&&y>=126&&y<182;wire[1:0]logo_pixel;
wire[6:0]lx=x-328;wire[5:0]ly=y-126;official_logo ref_logo(lx,ly,logo_pixel);
wire[9:0]hx=x-456;wire[10:0]sx0=x-328+d.scroll;wire[10:0]sx=sx0>=768?sx0-768:sx0;
wire[4:0]hb=d.fontrow(d.header(hx/16),(y-144)/2),sb=d.fontrow(d.slogan(sx/16),(y-576)/2);
wire text_pixel=(de&&pv&&x>=456&&x<936&&y>=144&&y<158&&hx%16<10&&hb[4-(hx%16)/2])||
(de&&pv&&x>=328&&x<952&&y>=576&&y<590&&sx%16<10&&sb[4-(sx%16)/2]);
integer k;
always @(posedge clk)if(rst)begin
 e=rgb;
 if(panel)begin e=mix(e,24'h102040,8);panels++;end
 if(logo_zone&&logo_pixel!=0)begin e=mix(e,logo_pixel==2?24'hcf1830:24'h183858,12);logos++;end
 if(text_pixel)begin e=mix(e,24'hffffff,16);texts++;end
 for(k=5;k>0;k=k-1)begin q[k]=q[k-1];c[k]=c[k-1];end q[0]=e;c[0]={x,y,de,hs,vs,pv};
 n++;#1;
 if(n>=6)begin
  checks++;if(out!==q[5]||{ox,oy,od,oh,ov,op}!==c[5])$fatal(1,"OSD latency/composite n%d xy%d,%d got%h expected%h",n,ox,oy,out,q[5]);
 end
end
integer a,b,al,i,j;
initial begin
 for(al=-1;al<=17;al++)for(a=0;a<=255;a+=17)for(b=0;b<=255;b+=17)
 if(d.blend({3{a[7:0]}},{3{b[7:0]}},al)!==mix({3{a[7:0]}},{3{b[7:0]}},al))$fatal(1,"alpha arithmetic");
 if(d.fontrow("A",0)!==5'b01110||d.fontrow("A",3)!==5'b11111)$fatal(1,"font known glyph");
 #23;rst=1;
 // Six frame pulses = three seconds, and scrolling advances exactly per frame.
 for(i=0;i<6;i++)begin @(negedge clk);de=1;x=0;y=0;@(negedge clk);de=0;x=1;end
 @(negedge clk);if(d.s0!=3||d.scroll!=6)$fatal(1,"uptime/scroll");
 // Every pixel in both panels, plus bypass, blanking, hidden audio gate cases.
 for(j=120;j<188;j++)for(i=320;i<960;i++)begin
  @(negedge clk);x=i;y=j;de=1;pv=1;rgb=(i*977+j*3989);hs=i[0];vs=j[0];
 end
 for(j=564;j<600;j++)for(i=320;i<960;i++)begin
  @(negedge clk);x=i;y=j;rgb=i*7323+j*17;
 end
 for(i=0;i<2000;i++)begin @(negedge clk);x=$urandom_range(0,1649);y=$urandom_range(0,749);rgb=$random;de=i[0];pv=i[1];end
 repeat(8)@(negedge clk);
 if(panels<60000||logos<100||texts<500)$fatal(1,"coverage panels%d logo%d text%d",panels,logos,texts);
 $display("PASS OSD %0d timed pixels + 4864 alpha endpoints/clamp/rounding checks; panel=%0d logo=%0d text=%0d",checks,panels,logos,texts);$finish;
end
endmodule
