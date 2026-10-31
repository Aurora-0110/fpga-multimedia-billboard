`timescale 1ns/1ps
module tb_v078_osd;
reg clk=0;always #5 clk=~clk;reg rst=0;reg[11:0]x=0,y=0;reg[23:0]rgb=0;
reg de=0,hs=1,vs=1,pv=0,mode=1;reg[1:0]idx=0;
wire[11:0]ox,oy;wire[23:0]out;wire od,oh,ov,op;
osd_layers #(.FRAMES_PER_SECOND(2))d(clk,rst,x,y,rgb,de,hs,vs,pv,mode,idx,ox,oy,out,od,oh,ov,op);
function[23:0]mix;input[23:0]a,b;input integer alpha;integer i,aa,v;begin
 aa=alpha<0?0:(alpha>16?16:alpha);
 for(i=0;i<3;i++)begin v=(a[i*8+:8]*(16-aa)+b[i*8+:8]*aa+8)/16;mix[i*8+:8]=v;end end endfunction
reg[23:0]q[0:2];reg[27:0]c[0:2];reg[23:0]e;integer n=0,checks=0,panels=0,logos=0,texts=0;
always @(posedge clk)if(rst)begin
 e=rgb;
 if(d.panel)begin e=mix(e,24'h102040,8);panels++;end
 if(d.logo_zone&&d.logo_pixel!=0)begin e=mix(e,d.logo_pixel==2?24'hcf1830:24'h183858,12);logos++;end
 if(d.text_pixel)begin e=mix(e,24'hffffff,16);texts++;end
 q[2]=q[1];q[1]=q[0];q[0]=e;c[2]=c[1];c[1]=c[0];c[0]={x,y,de,hs,vs,pv};
 n++;#1;
 if(n>=3)begin
  checks++;if(out!==q[2]||{ox,oy,od,oh,ov,op}!==c[2])$fatal(1,"OSD latency/composite n%d xy%d,%d got%h expected%h",n,ox,oy,out,q[2]);
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
 repeat(4)@(negedge clk);
 if(panels<60000||logos<100||texts<500)$fatal(1,"coverage panels%d logo%d text%d",panels,logos,texts);
 $display("PASS OSD %0d timed pixels + 4864 alpha endpoints/clamp/rounding checks; panel=%0d logo=%0d text=%0d",checks,panels,logos,texts);$finish;
end
endmodule
