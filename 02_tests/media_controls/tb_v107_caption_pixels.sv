`timescale 1ns/1ps
module tb_v107_caption_pixels;
 reg clk=0;always #5 clk=~clk;reg rst=0;
 reg [11:0] x=0,y=0;reg [23:0]rgb=24'hffffff;reg de=0,hs=1,vs=1,pv=1,en=1,started=1,active=1;
 reg [31:0]ms=5000;reg [15:0]bcd=16'h0005;reg[2:0]cue=0;
 wire[11:0]ox,oy;wire[23:0]out;wire od,oh,ov,op;
 subtitle_overlay d(clk,rst,x,y,rgb,de,hs,vs,pv,en,started,ms,bcd,cue,active,ox,oy,out,od,oh,ov,op);
 reg [15:0]font[0:2047];reg[6:0]textmem[0:255];integer lengths[0:7];
 reg[1023:0]fp,tp,preview;integer a,b,frame,n,k,px,col,fx,fy,ch,checks=0,glyphchecks=0,panelchecks=0,handle=0;
 reg [23:0]expected,qq[0:3];reg[27:0]ctl[0:3];reg[3:0]tags;reg capture=0,checking=0;integer piped=0;
 reg[15:0]bits;reg painted;integer progress;
 always @(posedge clk)if(rst&&checking)begin
  expected=rgb;painted=0;
  if(en&&started&&pv&&de&&x>=64&&x<1216&&y>=664&&y<716)begin
   expected={1'b0,rgb[23:17],1'b0,rgb[15:9],1'b0,rgb[7:1]};panelchecks++;
   progress=ms>=16000?1000:ms/16;
   if(y>=708&&y<712&&x>=140&&x<1140)expected=x<140+progress?24'h64dccc:24'h657078;
   if(active&&x>=(1280-lengths[cue]*32)/2&&x<(1280+lengths[cue]*32)/2&&y>=672&&y<704)begin
    px=x-(1280-lengths[cue]*32)/2;col=px/32;fx=(px%32)/2;fy=(y-672)/2;
    ch=textmem[cue*32+col];bits=font[ch*16+fy];if(bits[15-fx])begin expected=24'hffffff;painted=1;glyphchecks++;end
   end
   if(x>=80&&x<160&&y>=680&&y<696)begin
    col=(x-80)/16;fx=(x-80)%16;fy=y-680;
    case(col)
     0:ch=1+bcd[15:12];1:ch=1+bcd[11:8];2:ch=11;3:ch=1+bcd[7:4];4:ch=1+bcd[3:0];
    endcase
    bits=font[ch*16+fy];if(bits[15-fx])begin expected=24'h8cebe1;painted=1;glyphchecks++;end
   end
  end
  qq[0]<=expected;ctl[0]<={x,y,de,hs,vs,pv};tags[0]<=capture&&de;
  for(k=1;k<4;k++)begin qq[k]<=qq[k-1];ctl[k]<=ctl[k-1];tags[k]<=tags[k-1];end
  piped++;
  #1;
  if(piped>=4)begin
   if(out!==qq[3]||{ox,oy,od,oh,ov,op}!==ctl[3])$fatal(1,"caption pixel/alignment frame=%0d xy=%0d,%0d got=%h want=%h ctl=%h/%h",frame,ox,oy,out,qq[3],{ox,oy,od,oh,ov,op},ctl[3]);
   checks++;
   if(tags[3]&&handle)$fwrite(handle,"%c%c%c",out[23:16],out[15:8],out[7:0]);
  end
 end
 initial begin
  if(!$value$plusargs("FONT=%s",fp)||!$value$plusargs("TEXT=%s",tp)||!$value$plusargs("PREVIEW=%s",preview))$fatal(1,"oracle args");
  $readmemh(fp,font);$readmemh(tp,textmem);
  lengths[0]=12; // overwritten by independently generated LENGTHS plusarg file.
  if(!$value$plusargs("LENGTHS=%s",tp))$fatal(1,"lengths args");$readmemh(tp,lengths);
  #23;rst=1;repeat(4)@(negedge clk);checking=1;
  for(frame=0;frame<5;frame++)begin
   @(negedge clk);en=frame!=3;pv=frame!=4;started=1;active=frame!=1;cue=frame==2?2:0;
   ms=frame==2?7000:(frame==1?5200:1500);bcd=frame==2?16'h0007:(frame==1?16'h0005:16'h0001);
   if(frame==0||frame==2)begin handle=$fopen($sformatf("%0s_%0d.ppm",preview,frame),"wb");$fwrite(handle,"P6\n1280 720\n255\n");capture=1;end
   else begin handle=0;capture=0;end
   for(b=0;b<720;b++)for(a=0;a<1280;a++)begin
    @(negedge clk);x=a;y=b;de=1;hs=a<1240;vs=b<710;
    rgb={(8'd100+{4'd0,x[3:0]}),(8'd150+{4'd0,y[3:0]}),8'd240};
   end
   @(negedge clk);de=0;capture=0;x=1280;y=720;repeat(5)@(negedge clk);
   if(handle)$fclose(handle);handle=0;
  end
  if(checks<5*1280*720||glyphchecks<1000||panelchecks<10000)$fatal(1,"coverage");
  $display("PASS v107 subtitle overlay: %0d independently checked pixels, %0d glyph pixels, five full720p rasters; Chinese text/time/bar, cue gaps, transparent disabled/no-picture, four-stage RGB XY DE HS VS visibility alignment",checks,glyphchecks);$finish;
 end
 initial begin #100000000;$fatal(1,"caption timeout");end
endmodule
