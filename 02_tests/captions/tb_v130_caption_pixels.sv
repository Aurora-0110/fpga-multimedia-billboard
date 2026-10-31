`timescale 1ns/1ps
module tb_v130_caption_pixels;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,de=0,hs=1,vs=1,pv=1,en=0,active=0;reg[11:0]x=0,y=0;reg[23:0]rgb=0;
 reg[10:0]offset=0;reg[4:0]length=0;
 wire[11:0]ox,oy;wire[23:0]out;wire od,oh,ov,op;
 subtitle_overlay d(clk,rst,x,y,rgb,de,hs,vs,pv,en,active,offset,length,ox,oy,out,od,oh,ov,op);
 reg[11:0]font[0:5119];reg[8:0]textmem[0:1023];reg[95:0]cues[0:127];
 reg[2047:0]fp,tp,cp,preview;integer count,xx,yy,mode,c,n,checks=0,lit=0,dim=0,clear=0,fd;
 reg shown=0;integer off=0,len=0,startx=640,lx,gy,id;reg[23:0]gold;
 reg[23:0]qrgb[0:3];reg[11:0]qx[0:3],qy[0:3];reg[3:0]qctl[0:3];integer warm=0;
 always @(posedge clk)begin
  if(!rst)begin shown=0;off=0;len=0;startx=640;warm=0;end
  else begin
   if(de&&x==0&&y==0)begin shown=en&&active;off=offset;len=length;startx=(1280-len*48)/2;end
   gold=rgb;
   if(shown&&pv&&de&&x>=64&&x<1216&&y>=648&&y<704)begin
    gold={(rgb[23:16]>>1),(rgb[15:8]>>1),(rgb[7:0]>>1)};dim=dim+1;
    if(x>=startx&&x<startx+len*48&&y>=658&&y<694)begin
     lx=(x-startx)%48-6;gy=(y-658)/3;id=textmem[off+(x-startx)/48];
     if(lx>=0&&lx<36&&font[id*16+gy][11-lx/3])begin gold=24'hffffff;lit=lit+1;end
    end
   end else clear=clear+1;
   for(n=3;n>0;n=n-1)begin qrgb[n]=qrgb[n-1];qx[n]=qx[n-1];qy[n]=qy[n-1];qctl[n]=qctl[n-1];end
   qrgb[0]=gold;qx[0]=x;qy[0]=y;qctl[0]={de,hs,vs,pv};warm=warm+1;
   #1;
   if(warm>=4)begin
    if({out,ox,oy,od,oh,ov,op}!=={qrgb[3],qx[3],qy[3],qctl[3]})$fatal(1,"caption pixels mode=%0d xy=%0d,%0d got=%h exp=%h",mode,qx[3],qy[3],out,qrgb[3]);
    checks=checks+1;
    if(fd&&od&&mode==1)$fwrite(fd,"%c%c%c",out[23:16],out[15:8],out[7:0]);
   end
  end
 end
 task feed(input integer px,py,input bit gate);begin
  @(negedge clk);x=px;y=py;de=gate;hs=(px%17!=0);vs=(py%19!=0);rgb={px[7:0],py[7:0],8'hb6};
 end endtask
 initial begin
  fd=0;
  if(!$value$plusargs("FONT=%s",fp)||!$value$plusargs("TEXT=%s",tp)||!$value$plusargs("CUES=%s",cp)||!$value$plusargs("COUNT=%d",count)||!$value$plusargs("PREVIEW=%s",preview))$fatal(1,"args");
  $readmemh(fp,font);$readmemh(tp,textmem);$readmemh(cp,cues,0,count-1);
  repeat(4)@(negedge clk);rst=1;
  for(mode=0;mode<6;mode=mode+1)begin
   en=mode!=2;active=mode!=0;pv=mode!=3;c=mode==4?count-1:0;offset=cues[c][31:21];length=cues[c][20:16];
   if(mode==1)begin fd=$fopen(preview,"wb");$fwrite(fd,"P6\n1280 720\n255\n");end
   for(yy=0;yy<720;yy=yy+1)begin
    // Two full720p rasters, plus bottom regions of other cases. y0 snapshots every case.
    if(mode==0||mode==1||mode==4||yy==0||yy>=640)begin
     for(xx=0;xx<1280;xx=xx+1)begin
      if(mode==5&&yy==640&&xx==50)begin active=0;offset=cues[count-1][31:21];length=cues[count-1][20:16];end
      feed(xx,yy,1);
     end
     feed(1280,yy,0);
    end
   end
   repeat(5)feed(1281,719,0);
   if(fd)begin $fclose(fd);fd=0;end
  end
  // Every displayed character of the public cues, including bank1.
  mode=6;en=1;active=1;pv=1;
  for(c=0;c<count;c=c+1)begin
   offset=cues[c][31:21];length=cues[c][20:16];feed(0,0,1);
   for(yy=658;yy<694;yy=yy+1)
    for(xx=(1280-length*48)/2-4;xx<(1280+length*48)/2+4;xx=xx+1)feed(xx,yy,1);
   repeat(5)feed(1281,719,0);
  end
  if(lit<1000||dim<10000||clear<900000)$fatal(1,"insufficient pixel coverage");
  $display("PASS v130 caption pixels=%0d white_glyph=%0d panel=%0d clear=%0d latency=4 no_progress_bar_no_DEMO frame_snapshot all_public_cues_all_displayed_glyphs",checks,lit,dim,clear);$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog pixels");end
endmodule
