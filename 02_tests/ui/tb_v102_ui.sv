`timescale 1ns/1ps
module tb_v102_ui;
 reg clk=0;always #5 clk=~clk;
 reg rst=0;reg [11:0] x=1,y=0;reg [23:0] rgb=0;reg de=0,hs=1,vs=1,pv=0;
 reg [1:0] keys=0,field=0,image=0;reg signed [7:0] br=0;reg [2:0] gain=4;
 reg mode=1,osd=1,loading=0,failed=0,audio=0;reg [7:0] error=0;
 wire [11:0] ox,oy;wire [23:0] out;wire od,oh,ov,op,visible;
 ui_help_overlay #(.TIMEOUT_FRAMES(6))d(.clk(clk),.rst_n(rst),.x(x),.y(y),.rgb(rgb),.de(de),.hs(hs),.vs(vs),.picture_visible(pv),
 .keys_down(keys),.brightness(br),.contrast_q2(gain),.edit_field(field),.auto_mode(mode),.overlays_enabled(osd),.image_index(image),
 .loading(loading),.load_failed(failed),.tf_error(error),.audio_active(audio),.x_out(ox),.y_out(oy),.rgb_out(out),.de_out(od),.hs_out(oh),.vs_out(ov),.picture_visible_out(op),.ui_visible(visible));
 reg [63:0] vectors[0:255];reg [7:0] text_memory[0:65535];reg [4:0] font_memory[0:1791];
 reg [7:0] reference_text[0:255];reg ref_visible=0;reg[1:0]ref_keys=0;
 integer ncases,ci,row,col,i,j,checks=0,chars=0,frame_pixels=0;
 reg[1023:0]vp,tp,fp,preview;
 task cycles(input integer n);repeat(n)@(negedge clk);endtask
 task frame;begin @(negedge clk);x=0;y=0;de=1;@(negedge clk);x=1;de=0;cycles(2);end endtask
 task expected_visible(input bit want);begin if(visible!==want)$fatal(1,"UI visibility expected %b got %b",want,visible);end endtask
 task load_case(input integer which);reg[63:0]v;begin
  @(negedge clk);keys=0;cycles(3);v=vectors[which];
  @(negedge clk);br=v[7:0];gain=v[10:8];field=v[12:11];mode=v[13];osd=v[14];image=v[16:15];loading=v[17];failed=v[18];error=v[26:19];audio=v[27];pv=v[28];keys=v[30:29];
  cycles(3);frame();
  for(row=0;row<4;row++)for(col=0;col<64;col++)begin
   if(d.ui_char(row,col)!==text_memory[which*256+row*64+col])$fatal(1,"text case=%0d row=%0d col=%0d got=%h expected=%h",which,row,col,d.ui_char(row,col),text_memory[which*256+row*64+col]);
   chars=chars+1;
  end
 end endtask
 reg pixel_check=0,render_tag=0;reg [23:0] q[0:3];reg[27:0]ctl[0:3];reg[3:0]tagq;
 reg [23:0] expect_rgb,shade;reg [8:0] a,b,c;integer lx,ly,rr,cc,fx,fy;reg[4:0]bits;
 function [23:0] blend_half;input[23:0] bg,tint;integer k,v;begin
 for(k=0;k<3;k++)begin v=bg[k*8+:8]+tint[k*8+:8]+1;blend_half[k*8+:8]=v/2;end end endfunction
 integer k,pipe_cycles=0,fh;
 always @(posedge clk)if(rst&&pixel_check)begin
  expect_rgb=rgb;
  if(ref_visible&&de&&x>=48&&x<1232&&y>=184&&y<312)begin
   shade=24'h0e2038;
   if(y>=222&&y<242&&((ref_keys[0]&&x>=60&&x<304)||(ref_keys[1]&&x>=396&&x<656)))shade=24'h186050;
   expect_rgb=blend_half(rgb,shade);
   if(x>=64&&x<1088&&y>=192&&y<302)begin
    lx=x-64;ly=y-192;rr=ly/32;cc=lx/16;fx=(lx%16)/2;fy=(ly%32)/2;
    if(ly%32<14&&lx%16<10)begin bits=font_memory[reference_text[rr*64+cc]*7+fy];if(bits[4-fx])expect_rgb=24'hffffff;end
   end
   if(x<50||x>=1230||y<186||y>=310)expect_rgb=24'h40c8b0;
  end
  for(k=3;k>0;k--)begin q[k]=q[k-1];ctl[k]=ctl[k-1];tagq[k]=tagq[k-1];end
  q[0]=expect_rgb;ctl[0]={x,y,de,hs,vs,pv};tagq[0]=render_tag;pipe_cycles++;
  #1;
  if(pipe_cycles>=4)begin
   if(out!==q[3]||{ox,oy,od,oh,ov,op}!==ctl[3])$fatal(1,"RGB/control latency xy=%0d,%0d got=%h expected=%h ctl=%h want=%h",ox,oy,out,q[3],{ox,oy,od,oh,ov,op},ctl[3]);
   checks++;
   if(tagq[3])begin $fwrite(fh,"%c%c%c",out[23:16],out[15:8],out[7:0]);frame_pixels++;end
  end
 end
 task raster(input bit capture);begin
  for(j=0;j<720;j++)for(i=0;i<1280;i++)begin
   @(negedge clk);x=i;y=j;de=1;hs=i[0];vs=j[0];rgb={i[7:0],j[7:0],8'h60};render_tag=capture;
  end
  @(negedge clk);render_tag=0;de=0;x=1;cycles(6);
 end endtask
 initial begin
  if(!$value$plusargs("VECTORS=%s",vp)||!$value$plusargs("TEXT=%s",tp)||!$value$plusargs("FONT=%s",fp)||!$value$plusargs("CASES=%d",ncases)||!$value$plusargs("PREVIEW=%s",preview))$fatal(1,"missing data");
  $readmemh(vp,vectors,0,ncases-1);$readmemh(tp,text_memory,0,ncases*256-1);$readmemh(fp,font_memory);
  if(font_memory["X"*7]!==5'b10001||font_memory["X"*7+3]!==5'b00100)$fatal(1,"known X glyph");
  #23;rst=1;cycles(3);expected_visible(1);
  for(ci=0;ci<ncases;ci++)load_case(ci);
  // No mid-frame status/parameter changes; every new frame captures atomically.
  @(negedge clk);br=48;x=600;y=200;de=0;cycles(5);
  if(d.shown_brightness===8'sd48)$fatal(1,"mid-frame parameter tear");
  frame();if(d.shown_brightness!==8'sd48)$fatal(1,"frame parameter not committed");
  // Persistent editing, then exact timeout and no automatic-image wakeups.
  @(negedge clk);keys=0;field=1;failed=0;error=0;loading=0;cycles(3);frame();
  repeat(12)begin frame();expected_visible(1);end
  @(negedge clk);field=0;cycles(3);frame();expected_visible(1);
  repeat(5)begin frame();expected_visible(1);end
  frame();expected_visible(0);
  @(negedge clk);image=image+1;loading=1;audio=~audio;cycles(3);frame();expected_visible(0);
  // Debounced key level wakes only at a frame boundary, overlays may stay off.
  @(negedge clk);osd=0;cycles(3);frame();repeat(6)frame();expected_visible(0);
  @(negedge clk);keys=1;cycles(3);expected_visible(0);frame();expected_visible(1);
  if(d.shown_keys!=1||d.shown_last!=1||d.shown_overlays)$fatal(1,"hidden-overlay key/status wiring");
  @(negedge clk);keys=3;cycles(3);frame();if(d.shown_last!=3)$fatal(1,"chord not recorded");
  @(negedge clk);keys=1;cycles(3);frame();if(d.shown_last!=3)$fatal(1,"staggered chord release lost BOTH");
  @(negedge clk);keys=0;failed=1;error=8'hA7;cycles(3);frame();repeat(12)begin frame();expected_visible(1);end
  // The first four vectors describe VIEW and all legal parameter cases.
  // Explicit final case has B:+32/C:125%, editor, manual, overlays off, K0 down.
  load_case(ncases-1);
  for(i=0;i<256;i++)reference_text[i]=text_memory[(ncases-1)*256+i];ref_keys=keys;ref_visible=1;
  fh=$fopen(preview,"wb");if(!fh)$fatal(1,"preview open");$fwrite(fh,"P6\n1280 720\n255\n");
  pixel_check=1;raster(1);
  if(frame_pixels!=921600)$fatal(1,"incomplete actual DUT preview %0d",frame_pixels);$fclose(fh);
  // Same visible UI but no video picture: its pixels must never unmute audio.
  @(negedge clk);pv=0;frame();
  reference_text[195]="W";reference_text[196]="A";reference_text[197]="I";reference_text[198]="T";reference_text[199]=" ";
  reference_text[209]="W";reference_text[210]="A";reference_text[211]="I";reference_text[212]="T";
  raster(0);if(op)$fatal(1,"UI raised picture/audio gate");
  // Hide after return to VIEW: exact RGB/coordinate/DE/HS/VS passthrough.
  pixel_check=0;@(negedge clk);keys=0;field=0;failed=0;error=0;cycles(3);frame();repeat(6)frame();expected_visible(0);
  ref_visible=0;ref_keys=0;pixel_check=1;pipe_cycles=0;raster(0);
  for(i=0;i<2000;i++)begin @(negedge clk);x=$urandom_range(1,1649);y=$urandom_range(0,749);rgb=$random;de=i[0];hs=i[1];vs=i[2];pv=i[3];end
  cycles(5);
  $display("PASS v102 UI chars=%0d cases=%0d timed_pixels=%0d full720p_rasters=3 auto-hide/edit/staggered-chord/frame-commit/overlay-off/audio-gate/passthrough",chars,ncases,checks);$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog");end
endmodule
