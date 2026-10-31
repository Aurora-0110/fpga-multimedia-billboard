`timescale 1ns/1ps
module tb_overlay;
reg clk=0;always #5 clk=~clk;reg rst=0;reg[11:0]x=1,y=1;reg[23:0]rgb=0;
reg de=0,hs=1,vs=1,pv=1,en=1,lv=0,epoch=0,pcm=1;reg[127:0]levels=0;
wire[11:0]ox,oy;wire[23:0]out;wire od,oh,ov,op;
spectrum_overlay #(.TIMEOUT_CYCLES(100))d(clk,rst,x,y,rgb,de,hs,vs,pv,en,levels,lv,epoch,pcm,ox,oy,out,od,oh,ov,op);
`include "video/osd_font.vh"
function[7:0]letter;input integer n;reg[8*23-1:0]s;begin s="PCM DEMO SPECTRUM 24BIT";letter=n<23?s[(22-n)*8+:8]:" ";end endfunction
reg[23:0]q[0:2];reg[27:0]cq[0:2];reg[23:0]e;reg panel,bar,pk,txt;reg[4:0]glyph;
integer a,b,i,n=0,checks=0,paint=0,band,tx;reg monitor=0;
always @(posedge clk)if(rst&&monitor)begin
 e=rgb;panel=en&&pv&&de&&x>=120&&x<1160&&y>=432&&y<624;bar=0;pk=0;txt=0;
 if(panel)begin
  if(x>=128&&x<1152&&(x-128)%64>=8&&(x-128)%64<56)begin
   band=(x-128)/64;
   bar=y<608&&y>=608-d.height[band];
   pk=d.peak[band]!=0&&y>=606-d.peak[band]&&y<608-d.peak[band];
  end
  tx=x-136;glyph=fontrow(letter(tx/16),(y-440)/2);
  if(x>=136&&x<520&&y>=440&&y<454&&tx%16<10)txt=glyph[4-(tx%16)/2];
  if(txt||pk)e=24'hffffff;
  else if(bar)e=y<512?24'hff6040:y<560?24'hffe040:24'h30e0b0;
  else e={1'b0,rgb[23:17],1'b0,rgb[15:9],1'b0,rgb[7:1]}+24'h040810;
  paint++;
 end
 for(i=2;i>0;i--)begin q[i]=q[i-1];cq[i]=cq[i-1];end
 q[0]=e;cq[0]={x,y,de,hs,vs,pv};n++;#1;
 if(n>=3)begin checks++;if(out!==q[2]||{ox,oy,od,oh,ov,op}!==cq[2])$fatal(1,"visual pixel/control x%0d y%0d got%h want%h",ox,oy,out,q[2]);end
end
task tick(input integer k);repeat(k)@(negedge clk);endtask
task frame;begin x=0;y=0;de=1;tick(1);x=1;tick(18);end endtask
initial begin
 tick(3);rst=1;tick(2);levels={16{8'd120}};lv=1;tick(1);lv=0;
 repeat(5)frame;if(d.height[0]!=120)$fatal(1,"attack");
 frame;if(d.peak[0]!=120)$fatal(1,"peak");
 monitor=1;
 for(b=0;b<720;b++)for(a=0;a<1280;a++)begin @(negedge clk);x=a;y=b;de=1;rgb={a[7:0],b[7:0],8'h80};end
 for(a=0;a<200;a++)begin @(negedge clk);de=0;hs=a[0];vs=a[1];pv=a[2];rgb=$random;x=a;y=740;end
 pv=1;en=0;
 for(b=430;b<625;b++)for(a=110;a<1170;a++)begin @(negedge clk);x=a;y=b;de=1;rgb=$random;end
 tick(4);monitor=0;en=1;
 // Frame-exact track reset wins when epoch coincides with first active pixel.
 epoch=1;frame;epoch=0;if(d.fade!=8||d.height[0]!=102)$fatal(1,"epoch priority");
 repeat(7)frame;if(d.height[0]!=0||d.peak[0]!=0)$fatal(1,"old spectrum did not fade");
 levels={16{8'd120}};lv=1;tick(1);lv=0;repeat(6)frame;
 if(d.height[0]!=120)$fatal(1,"new track recovery");
 pcm=0;tick(105);repeat(20)frame;if(d.height[0]!=0)$fatal(1,"PCM loss timeout");
 $display("PASS spectrum full720 raster/control/mask checks=%0d panelpixels=%0d attack/release/peak/epoch/timeout",checks,paint);$finish;
end
initial begin #20000000;$fatal(1,"visual watchdog");end
endmodule
