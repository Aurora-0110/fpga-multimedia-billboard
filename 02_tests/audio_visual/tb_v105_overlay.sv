`timescale 1ns/1ps
module tb_v105_overlay;
 reg clk=0;always #5 clk=~clk;reg rst=0;reg[11:0]x=1,y=1;reg[23:0]rgb=0;
 reg de=0,hs=1,vs=1,pv=1,en=1,lv=0,epoch=0,sound=0;reg[127:0]levels=0;
 wire[11:0]ox,oy;wire[23:0]out;wire od,oh,ov,op;
 spectrum_overlay d(clk,rst,x,y,rgb,de,hs,vs,pv,en,levels,lv,epoch,sound,ox,oy,out,od,oh,ov,op);
 reg[23:0]color_table[0:15];
 function[23:0]gold_blend;input[23:0]bg,fg;input integer a;integer rr,gg,bb;begin
  rr=((16-a)*bg[23:16]+a*fg[23:16])/16;
  gg=((16-a)*bg[15:8]+a*fg[15:8])/16;
  bb=((16-a)*bg[7:0]+a*fg[7:0])/16;gold_blend={rr[7:0],gg[7:0],bb[7:0]};
 end endfunction
 reg[23:0]q[0:2],e,fg;reg[27:0]cq[0:2];reg bar,pk;
 integer a,b,i,qi,n=0,checks=0,paint=0,untouched=0,band,step,alpha,fd=0,captured=0,h,p,frac,nb,slot,memchecks=0;
 reg monitor=0,capture=0;reg[2047:0]preview_path;
 always @(posedge clk)if(rst&&monitor)begin
  e=rgb;bar=0;pk=0;alpha=0;
  if(en&&pv&&de&&d.draw_ready&&x>=128&&x<1152&&(x-128)%16>=4&&(x-128)%16<12)begin
   band=(x-128)/64;frac=((x-128)/16)%4;nb=band<15?band+1:15;slot=(x-128)%16;
   h=((4-frac)*d.height[band]+frac*d.height[nb]+2)/4;
   p=((4-frac)*d.peak[band]+frac*d.peak[nb]+2)/4;
   bar=h!=0&&y<608&&y>=608-h&&((slot!=4&&slot!=11)||(y>608-h&&y<607));
   pk=slot>=5&&slot<11&&p!=0&&y>=606-p&&y<608-p;
   if(bar||pk)begin
    fg=color_table[band];
    if(pk||y<536)fg={8'((3*fg[23:16]+255)/4),8'((3*fg[15:8]+255)/4),8'((3*fg[7:0]+255)/4)};
    alpha=d.opacity;e=gold_blend(rgb,fg,alpha);
   end
  end
  if(e!=rgb)paint++;else untouched++;
  for(qi=2;qi>0;qi--)begin q[qi]=q[qi-1];cq[qi]=cq[qi-1];end
  q[0]=e;cq[0]={x,y,de,hs,vs,pv};n++;#1;
  if(n>=3)begin
   checks++;
   if(out!==q[2]||{ox,oy,od,oh,ov,op}!==cq[2])$fatal(1,"transparent pixel/control x%0d y%0d got%h want%h alpha%0d",ox,oy,out,q[2],alpha);
   if(capture&&od&&captured<921600&&fd&&(captured!=0||(ox==0&&oy==0)))begin
    if(ox!=captured%1280||oy!=captured/1280)$fatal(1,"preview raster coordinate");$fwrite(fd,"%c%c%c",out[23:16],out[15:8],out[7:0]);captured++;end
  end
 end
 task tick(input integer k);repeat(k)@(negedge clk);endtask
 task verify_display;integer z,bb,nn,ff,hh,pp;begin
 for(z=0;z<64;z++)begin
  bb=z/4;nn=bb<15?bb+1:15;ff=z%4;
  hh=((4-ff)*d.height[bb]+ff*d.height[nn]+2)/4;
  pp=((4-ff)*d.peak[bb]+ff*d.peak[nn]+2)/4;
  if(d.display_memory[z]!=={8'(pp),8'(hh)})$fatal(1,"interpolation RAM cell%0d got%h h%0d p%0d",z,d.display_memory[z],hh,pp);
  memchecks++;
 end
 if(!d.draw_ready||d.updating||d.preparing)$fatal(1,"display preprocessing deadline");
end endtask
 task frame;begin x=0;y=0;de=1;tick(1);x=1;tick(258);verify_display;end endtask
 task check_strip;begin
 monitor=1;n=0;
 for(a=0;a<256;a++)begin @(negedge clk);x=136+a%48;y=590;rgb={a[7:0],~a[7:0],a[7:0]};end
 tick(4);monitor=0;
end endtask
 task publish(input integer h);begin levels={16{8'(h)}};lv=1;tick(1);lv=0;end endtask
 task heights(input integer h);begin for(integer z=0;z<16;z++)if(d.height[z]!=h)$fatal(1,"channel%0d h%0d want%0d",z,d.height[z],h);end endtask
 initial begin
  color_table[0]=24'hf15d6e;
  color_table[1]=24'hf77b54;
  color_table[2]=24'hf39f36;
  color_table[3]=24'hd5b32b;
  color_table[4]=24'h99bf3c;
  color_table[5]=24'h56bf65;
  color_table[6]=24'h2dbb91;
  color_table[7]=24'h25b6b8;
  color_table[8]=24'h27a7d8;
  color_table[9]=24'h438de8;
  color_table[10]=24'h6374ed;
  color_table[11]=24'h8b65e6;
  color_table[12]=24'ha661d8;
  color_table[13]=24'hbf62c8;
  color_table[14]=24'hd763ad;
  color_table[15]=24'he36891;
  tick(3);rst=1;tick(2);
  publish(120);repeat(3)frame;heights(0);if(d.opacity!=0)$fatal(1,"silent stale levels activated");
  sound=1;publish(120);
  // Every attack/fade step is measured; update all16 channels within64 cycles.
  for(i=1;i<=12;i++)begin frame;heights(i<5?i*24:120);if(d.opacity!=i)$fatal(1,"fade-in frame%0d",i);check_strip;end
  if(d.peak[0]!=120)$fatal(1,"peak tracking");
  // Nonuniform levels exercise ALL16 selectors, not identical-lane aliasing.
  for(i=0;i<16;i++)levels[i*8+:8]=24+(i*37)%121;
  lv=1;tick(1);lv=0;repeat(120)frame;
  for(i=0;i<16;i++)if(d.height[i]!=(24+(i*37)%121)||d.peak[i]!=d.height[i])$fatal(1,"nonuniform lane%0d",i);
  if($value$plusargs("PREVIEW=%s",preview_path))begin fd=$fopen(preview_path,"wb");if(!fd)$fatal(1,"preview path");$fwrite(fd,"P6\n1280 720\n255\n");end
  monitor=1;n=0;capture=1;
  for(b=0;b<720;b++)for(a=0;a<1280;a++)begin
   @(negedge clk);x=a;y=b;de=1;hs=1;vs=1;
   rgb=24'hffffff;
  end
  tick(1);de=0;tick(5);capture=0;if(fd)begin $fclose(fd);if(captured!=921600)$fatal(1,"preview count%0d",captured);end
  // Blanking, picture hide and UI bypass must preserve all24 original RGB bits.
  for(a=0;a<300;a++)begin @(negedge clk);de=a[3];hs=a[0];vs=a[1];pv=a[2];rgb=$random;x=a;y=740;end
  pv=1;en=0;
  for(b=460;b<625;b++)for(a=110;a<1170;a++)begin @(negedge clk);x=a;y=b;de=1;rgb=$random;end
  tick(4);monitor=0;
  en=1;publish(120);repeat(12)frame;
  // Track pulse between frames must be remembered; stale spectrum decays fully.
  epoch=1;tick(1);epoch=0;frame;
  if(d.opacity!=10||d.holdoff!=8)$fatal(1,"asynchronous epoch lost");heights(102);
  publish(120);repeat(8)frame;heights(0);if(d.opacity!=0)$fatal(1,"track old glow remained");
  repeat(12)frame;heights(120);if(d.opacity!=12)$fatal(1,"new track fade-in");
  // Epoch exactly at frame start must also win over a simultaneous new level.
  epoch=1;lv=1;x=0;y=0;de=1;tick(1);epoch=0;lv=0;x=1;tick(258);verify_display;if(d.opacity!=10)$fatal(1,"same-frame epoch priority");
  repeat(8)frame;heights(0);publish(255);repeat(12)frame;heights(144);if(d.opacity!=12)$fatal(1,"clamp fade recovery"); // hostile levels clamp
  sound=0;
  for(a=11;a>=0;a--)begin frame;if(d.opacity!=a)$fatal(1,"fade-out frame%0d got%0d",a,d.opacity);end
  if(d.opacity!=0)$fatal(1,"silence did not fully hide");heights(0);
  for(i=0;i<16;i++)if(d.peak[i]!=0)$fatal(1,"quiet old peak not cleared");
  sound=1;repeat(3)frame;if(d.opacity!=0)$fatal(1,"stale target revived after silence");
  publish(0);repeat(30)frame;heights(0);
  for(i=0;i<16;i++)if(d.peak[i]!=0)$fatal(1,"old peak resurrected on zero-level resume"); // no0-height baseline even while active
  monitor=1;n=0;
  for(b=450;b<625;b++)for(a=110;a<1170;a++)begin @(negedge clk);x=a;y=b;de=1;rgb=$random;end
  tick(4);monitor=0;
  if(paint==0||untouched<900000)$fatal(1,"coverage too small");
  $display("PASS v105 transparent full720 raster checks=%0d blended=%0d unchanged=%0d alpha/64 interpolated display bars/3cycle-sync/all16 measured channels/quiet/epoch/clamp/OSD-bypass/no-baseline",checks,paint,untouched);$display("PASS v105 all64 interpolation RAM checks=%0d / fixed256-clock preprocessing deadline / no new spectral bands claimed",memchecks);$finish;
 end
 initial begin #25000000;$fatal(1,"visual watchdog");end
endmodule
