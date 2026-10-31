`timescale 1ns/1ps
module tb_v080_adjust;
reg clk=0;always #5 clk=~clk;reg rst=0;
reg [23:0]rgb=0;reg[11:0]x=0,y=0;reg de=0,hs=1,vs=1,pv=0,ap=0;reg[1:0]tag=0;
reg signed[7:0]br=0;reg[2:0]gain=4;
wire[23:0]out;wire[11:0]ox,oy;wire od,oh,ov,op;wire[1:0]ot;
picture_adjust d(clk,rst,rgb,x,y,de,hs,vs,pv,ap,tag,br,gain,out,ox,oy,od,oh,ov,op,ot);
function[7:0] channel(input integer c,g,b);integer v;begin
 v=((c-128)*g);v=(v>>>2)+128+b;
 channel=v<0?0:(v>255?255:v);end endfunction
reg[23:0]q[0:3];reg[29:0]ctl[0:3];integer n=0,checks=0,k,c,g,b,i;
reg[23:0]e;
always @(posedge clk)if(rst)begin
 e=ap?{channel(rgb[23:16],gain,br),channel(rgb[15:8],gain,br),channel(rgb[7:0],gain,br)}:rgb;
 for(k=3;k>0;k=k-1)begin q[k]=q[k-1];ctl[k]=ctl[k-1];end
 q[0]=e;ctl[0]={x,y,de,hs,vs,pv,tag};n++;#1;
 if(n>=4)begin checks++;if(out!==q[3]||{ox,oy,od,oh,ov,op,ot}!==ctl[3])
 $fatal(1,"adjust n%0d got%h expected%h controls got%h expected%h",n,out,q[3],{ox,oy,od,oh,ov,op,ot},ctl[3]);end
end
initial begin
 #23;rst=1;
 for(g=2;g<=6;g++)for(b=-64;b<=64;b+=16)for(c=0;c<256;c++)begin
 @(negedge clk);gain=g;br=b;rgb={c[7:0],8'(255-c),8'((c*73)%256)};ap=1;x=c*7;y=c*11;de=c[0];hs=c[1];vs=c[2];pv=c[3];tag=c[5:4];end
 for(i=0;i<3000;i++)begin @(negedge clk);rgb=$random;ap=i[0];br=$urandom_range(0,128)-64;gain=$urandom_range(2,6);x=$random;y=$random;tag=$random;de=$random;hs=$random;vs=$random;pv=$random;end
 repeat(6)@(negedge clk);
 $display("PASS adjust: %0d pixels, exhaustive 256 channels x5 gains x9 brightness; signed floor/saturation/bypass/tag/sync/4-cycle",checks);$finish;
end
endmodule
