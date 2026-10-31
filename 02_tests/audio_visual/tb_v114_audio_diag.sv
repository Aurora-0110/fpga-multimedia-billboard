`timescale 1ns/1ps
module tb_v114_audio_diag;
 reg clk=0,rst=0;always #5 clk=~clk;
 reg[11:0]x=0,y=0;reg[23:0]rgb=24'h123456;reg de=0,hs=1,vs=1,pic=1,en=1;
 reg[7:0]status=0;reg[12:0]aq=13'h12ab,amin=13'h0034,afirst=0;reg[7:0]flags=8'ha2;
 wire[11:0]xo,yo;wire[23:0]ro;wire deo,hso,vso,po;
 display_diagnostics_osd #(.FAULT_ONLY(0),.VERSION_MAJOR(1),.VERSION_TENS(1),.VERSION_ONES(4),.ALWAYS_SHOW_FAULTS(1),.AUDIO_DEBUG(1)) dut(
 .clk(clk),.rst_n(rst),.x(x),.y(y),.rgb(rgb),.de(de),.hs(hs),.vs(vs),.picture_visible(pic),.image_index(2'd0),
 .status(status),.tf_error(8'd0),.fifo_used(13'd4000),.enable(en),.audio_used(aq),.audio_minimum(amin),.audio_first_used(afirst),.audio_first_flags(flags),
 .x_out(xo),.y_out(yo),.rgb_out(ro),.de_out(deo),.hs_out(hso),.vs_out(vso),.picture_visible_out(po));
 reg[4:0]font[0:2047];reg[7:0]text[0:55];reg[2047:0]fpath,tpath;
 reg[51:0]expected[0:2];integer warm=0,checks=0;reg red=0;reg[23:0]out_rgb;integer tx,row,col;reg panel,glyph;
 always @(posedge clk)begin
  if(!rst)warm=0;
  else begin
   panel=(en||red)&&de&&x>=8&&x<912&&y>=8&&y<66;
   out_rgb=rgb;
   if(panel)begin
    out_rgb=red?24'h601020:24'h102848;
    if(x>=16&&x<896&&y>=48&&y<62)begin
     tx=x-16;row=(y-48)/2;col=(tx%16)/2;
     if(tx%16<10&&font[text[tx/16]*8+row][4-col])out_rgb=24'hffffff;
    end
   end
   expected[2]=expected[1];expected[1]=expected[0];expected[0]={x,y,out_rgb,de,hs,vs,pic};
   warm=warm+1;
   #0.1;
   if(warm>=3&&{xo,yo,ro,deo,hso,vso,po}!==expected[2])$fatal(1,"diag pipeline/raster x=%0d y=%0d got=%h expected=%h chr=%h bits=%b col=%d row=%d aq=%h",xo,yo,{xo,yo,ro,deo,hso,vso,po},expected[2],dut.char0,dut.bits1,dut.col1,dut.row0,dut.aq);
   if(warm>=3)checks=checks+1;
  end
 end
 task send(input integer xx,input integer yy);begin
  @(negedge clk);x=xx;y=yy;rgb={xx[7:0],yy[7:0],8'h59};de=1;hs=xx[0];vs=yy[0];pic=xx[1];
 end endtask
 task frame;begin send(0,0);send(1,0);repeat(5)@(negedge clk);end endtask
 task raster;begin for(integer yy=46;yy<68;yy=yy+1)for(integer xx=0;xx<928;xx=xx+1)send(xx,yy);end endtask
 initial begin
  if(!$value$plusargs("FONT=%s",fpath)||!$value$plusargs("TEXT=%s",tpath))$fatal(1,"args");
  $readmemh(fpath,font);$readmemh(tpath,text);
  repeat(5)@(negedge clk);rst=1;frame;
  for(integer c=0;c<56;c=c+1)if(dut.audio_line(c)!==text[c])$fatal(1,"audio char%0d",c);
  aq=0;amin=0;afirst=13'h0100;flags=8'hff;
  // Values changed after frame snapshot MUST not tear the currently shown text.
  raster;en=0;raster;
  // Restore known values, inject a real fault then verify hidden UI cannot
  // suppress the persistent red diagnostic row. Frame snapshot stays identical.
  aq=13'h12ab;amin=13'h0034;afirst=0;flags=8'ha2;status=8'h20;red=1;
  repeat(5)@(negedge clk);status=0;frame;raster;
  repeat(5)@(negedge clk);
  $display("PASS audio debug third line glyphs/Q/=, frame snapshot, sticky hidden fault,3-cycle control/RGB alignment pixels=%0d",checks);$finish;
 end
endmodule
