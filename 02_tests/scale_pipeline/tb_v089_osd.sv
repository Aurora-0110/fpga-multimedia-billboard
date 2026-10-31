`timescale 1ns/1ps
module tb_v089_osd;
reg clk=0;always #5 clk=~clk;reg rst=0;reg[11:0]x=0,y=0;reg[23:0]rgb=0;
reg de=0,hs=1,vs=1,pv=0,mode=1,show_osd=1;reg[1:0]idx=0;reg signed[7:0]br=0;reg[2:0]gain=4;reg[1:0]field=0;
wire[11:0]ox,oy;wire[23:0]out;wire od,oh,ov,op;
osd_layers_full720 #(.FRAMES_PER_SECOND(2),.SHOW_PARAMS(1))d(clk,rst,x,y,rgb,de,hs,vs,pv,mode,idx,show_osd,br,gain,field,ox,oy,out,od,oh,ov,op);
function[23:0]mix;input[23:0]a,b;input integer alpha;integer i,aa,v;begin
 aa=alpha<0?0:(alpha>16?16:alpha);
 for(i=0;i<3;i++)begin v=(a[i*8+:8]*(16-aa)+b[i*8+:8]*aa+8)/16;mix[i*8+:8]=v;end end endfunction
reg[23:0]q[0:5];reg[27:0]c[0:5];reg[23:0]e;integer n=0,checks=0,panels=0,logos=0,texts=0;
wire panel=de&&pv&&show_osd&&x>=16&&x<1264&&((y>=24&&y<168)||(y>=640&&y<704));
wire logo_zone=de&&pv&&show_osd&&x>=24&&x<248&&y>=40&&y<152;wire[1:0]logo_pixel;
wire[6:0]lx=(x-24)/2;wire[5:0]ly=(y-40)/2;official_logo ref_logo(lx,ly,logo_pixel);
wire[10:0]hx=x-272;wire[12:0]sx0=x-24+d.scroll;wire[12:0]sx=sx0>=1536?sx0-1536:sx0;
wire[4:0]hb=d.fontrow(d.header(hx/32),(y-54)/4),sb=d.fontrow(d.slogan(sx/32),(y-658)/4);
wire param_zone=y>=102&&y<130;
wire[4:0]pb=d.fontrow(d.parameter_text(hx/32),(y-102)/4);
wire text_pixel=(de&&pv&&show_osd&&x>=272&&x<1232&&param_zone&&hx%32<20&&pb[4-(hx%32)/4])||
(de&&pv&&show_osd&&x>=272&&x<1232&&y>=54&&y<82&&hx%32<20&&hb[4-(hx%32)/4])||
(de&&pv&&show_osd&&x>=24&&x<1256&&y>=658&&y<686&&sx%32<20&&sb[4-(sx%32)/4]);
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
integer a,b,al,i,j,g,bright,f;reg[8*30-1:0] expected_text;reg[7:0] expected_char;integer mag;
initial begin
 for(al=-1;al<=17;al++)for(a=0;a<=255;a+=17)for(b=0;b<=255;b+=17)
 if(d.blend({3{a[7:0]}},{3{b[7:0]}},al)!==mix({3{a[7:0]}},{3{b[7:0]}},al))$fatal(1,"alpha arithmetic");
 if(d.fontrow("A",0)!==5'b01110||d.fontrow("A",3)!==5'b11111)$fatal(1,"font known glyph");
 #23;rst=1;
 // Six frame pulses = three seconds, and scrolling advances exactly per frame.
 for(i=0;i<6;i++)begin @(negedge clk);de=1;x=0;y=0;@(negedge clk);de=0;x=1;end
 @(negedge clk);if(d.s0!=3||d.scroll!=12)$fatal(1,"uptime/scroll");
 // All legal UI values, independently formatted expected characters.
 for(bright=-64;bright<=64;bright+=16)for(g=2;g<=6;g++)for(f=0;f<3;f++)begin
  @(negedge clk);br=bright;gain=g;field=f;de=1;x=0;y=0;
  @(negedge clk);x=1;
  mag=bright<0?-bright:bright;
  for(i=0;i<30;i++)begin
   expected_char=" ";case(i)
    0:expected_char="B";1:expected_char=":";2:expected_char=bright<0?"-":"+";
    3:expected_char="0"+mag/10;4:expected_char="0"+mag%10;
    7:expected_char="C";8:expected_char=":";
    9:expected_char="0"+(g*25)/100;10:expected_char="0"+((g*25)/10)%10;11:expected_char="0"+(g*25)%10;
    12:expected_char="%";
    16:expected_char=f==0?"V":"E";17:expected_char=f==0?"I":"D";18:expected_char=f==0?"E":"I";19:expected_char=f==0?"W":"T";
    20:expected_char=f==0?" ":":";21:expected_char=f==1?"B":(f==2?"C":" ");
   endcase
   if(d.parameter_text(i)!==expected_char)$fatal(1,"parameter text i%d br%d gain%d field%d got%h want%h",i,bright,g,f,d.parameter_text(i),expected_char);
  end
  for(j=102;j<130;j+=4)for(i=272;i<976;i+=32)begin @(negedge clk);x=i;y=j;de=1;pv=1;rgb=i*3721+j*19;end
 end
 // Full active 1280x720 reference composite, followed by a whole hidden
 // raster. Hidden mode must be exact RGB/control/audio-gate passthrough.
 show_osd=1;pv=1;de=1;
 for(j=0;j<720;j++)for(i=0;i<1280;i++)begin
  @(negedge clk);x=i;y=j;rgb=(i*977+j*3989);hs=i[0];vs=j[0];
 end
 @(negedge clk);show_osd=0;
 for(j=0;j<720;j++)for(i=0;i<1280;i++)begin
  @(negedge clk);x=i;y=j;rgb=(i*7323+j*17);hs=i[0];vs=j[0];
 end
 for(i=0;i<2000;i++)begin @(negedge clk);x=$urandom_range(0,1649);y=$urandom_range(0,749);rgb=$random;de=i[0];pv=i[1];end
 repeat(8)@(negedge clk);
 // 56 rows x 112 2-bit ROM entries contain 2017 nonzero pixels.
 // A full 2x-expanded logo therefore covers 2017*4=8068 opaque pixels.
 if(panels<200000||logos<8068||texts<3000)$fatal(1,"coverage panels%d logo%d text%d",panels,logos,texts);
 $display("PASS v089_full720_OSD two_complete_active_rasters=1843200 enabled_and_hidden %0d timed pixels + 4864 alpha endpoints/clamp/rounding checks; panel=%0d logo=%0d text=%0d",checks,panels,logos,texts);$finish;
end
endmodule
