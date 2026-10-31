`timescale 1ns/1ps
module tb_v125_ui;
 reg clk=0;always #5 clk=~clk;
 reg rst=0;reg [11:0] x=1,y=0;reg [23:0] rgb=0;reg de=0,hs=1,vs=1,pv=0;
 reg [1:0] keys=0,field=0,image=0;reg signed [7:0] br=0;reg [2:0] gain=4;
 reg [3:0] volume=10;reg mode=1,osd=1,loading=0,failed=0,audio=0;reg [7:0] error=0,aerror=0;
 reg [2:0] status=0;reg select_audio=0,pin=0,paused=0;reg [1:0] choice=0;
 wire [11:0] ox,oy;wire [23:0] out;wire od,oh,ov,op,visible;
 media_ui_overlay #(.TIMEOUT_FRAMES(6))d(.clk(clk),.rst_n(rst),.x(x),.y(y),.rgb(rgb),.de(de),.hs(hs),.vs(vs),.picture_visible(pv),
 .volume_level(volume),.keys_down(keys),.brightness(br),.contrast_q2(gain),.edit_field(field),.auto_mode(mode),.overlays_enabled(osd),.image_index(image),
 .loading(loading),.load_failed(failed),.tf_error(error),.audio_error(aerror),.audio_status(status),.audio_active(audio),.audio_select(select_audio),.audio_paused(paused),.audio_choice(choice),.ui_toggle(pin),.x_out(ox),.y_out(oy),.rgb_out(out),.de_out(od),.hs_out(oh),.vs_out(ov),.picture_visible_out(op),.ui_visible(visible));
 reg [63:0] vectors[0:1023];reg [6:0] text_memory[0:262143];reg [15:0] font_memory[0:2047];
 reg [6:0] reference_text[0:251];
 reg ref_visible=0,ref_failed=0,ref_audio=0,ref_audio_failed=0;reg [1:0] ref_keys=0,ref_field=0;
 integer ncases,ci,row,col,i,j,checks=0,chars=0,frame_pixels=0,llen,slen,off;
 reg [1023:0] vp,tp,fp,preview;
 task cycles(input integer n);repeat(n)@(negedge clk);endtask
 task frame;begin @(negedge clk);x=0;y=0;de=1;@(negedge clk);x=1;de=0;cycles(44);if(!d.layout_ready)$fatal(1,"frame layout deadline");end endtask
 task expected_visible(input bit want);begin if(visible!==want)$fatal(1,"visibility expected %b got %b",want,visible);end endtask
 task load_case(input integer which);reg [63:0] v;reg [6:0] got;begin
  @(negedge clk);rst=0;keys=0;cycles(3);rst=1;v=vectors[which];
  @(negedge clk);br=v[7:0];gain=v[10:8];field=v[12:11];mode=v[13];osd=v[14];image=v[16:15];loading=v[17];failed=v[18];error=v[26:19];audio=v[27];pv=v[28];keys=v[30:29];select_audio=v[31];choice=v[33:32];pin=0;status=v[37:35];aerror=v[45:38];paused=v[46];volume=v[50:47];
  cycles(3);frame();
  // Read the ACTUAL post-text-ROM/override pipeline, not a duplicate text function.
  for(row=0;row<14;row++)for(col=0;col<18;col++)begin
   llen=7;while(llen>0&&text_memory[which*252+row*18+llen-1]==0)llen--;
   slen=11;while(slen>0&&text_memory[which*252+row*18+7+slen-1]==0)slen--;
   if((col<7&&col<llen)||(col>=7&&col<7+slen))begin
    @(negedge clk);x=col<7?448-llen*16+col*32:768-slen*16+(col-7)*32;y=80+row*40;de=1;cycles(4);
    got=d.override1?d.override_glyph1:d.text_glyph1;
    if(got!==text_memory[which*252+row*18+col])$fatal(1,"Chinese centered text case=%0d row=%0d col=%0d got=%0d expected=%0d",which,row,col,got,text_memory[which*252+row*18+col]);
    chars++;
   end
  end
  @(negedge clk);x=1;de=0;
 end endtask
 reg pixel_check=0,render_tag=0;reg [23:0] q[0:4];reg [27:0] ctl[0:4];reg [4:0] tagq;
 reg [23:0] expect_rgb,shade,ink;integer lx,ly,rr,cc,fx,fy;reg [15:0] bits;
 // Mathematical rounded-rectangle oracle, NOT the RTL inset tables.
 function automatic bit rounded(input integer px,py,l,t,r,b,rad);
  integer dx,dy,cx,cy;begin
   rounded=0;
   if(px>=l&&px<r&&py>=t&&py<b)begin
    cx=px<l+rad?l+rad:(px>=r-rad?r-rad:2*px+1);
    cy=py<t+rad?t+rad:(py>=b-rad?b-rad:2*py+1);
    dx=(px<l+rad||px>=r-rad)?2*px+1-2*cx:0;
    dy=(py<t+rad||py>=b-rad)?2*py+1-2*cy:0;
    rounded=dx*dx+dy*dy<=4*rad*rad;
   end
  end
 endfunction
 function [23:0] glass;input [23:0] bg,t;integer k,v;begin
  for(k=0;k<3;k++)begin v=bg[k*8+:8]+3*t[k*8+:8]+2;glass[k*8+:8]=v/4;end
 end endfunction
 function [23:0] shadow_mix;input [23:0] bg;integer k,v,shade;begin
  for(k=0;k<3;k++)begin shade=k==2?128:(k==1?152:172);v=7*bg[k*8+:8]+shade+4;shadow_mix[k*8+:8]=v/8;end
 end endfunction
 integer left_length,right_length,startl,startr;bit lh,rh;
 integer k,pipe_cycles=0,fh=0;
 always @(posedge clk)if(rst&&pixel_check)begin
  expect_rgb=rgb;
  if(ref_visible&&de)begin
   if(rounded(x,y,294,72,998,664,24))expect_rgb=shadow_mix(rgb);
   if(rounded(x,y,288,64,992,656,24))begin
    rr=(y>=80&&y<640)?(y-80)/40:15;
    shade=24'heaf4fc;
    if((ref_field==1&&rr==6)||(ref_field==2&&rr==7))shade=24'hd5f4e8;
    else if(rr==10&&ref_keys!=0)shade=24'hfcebd5;
    else if(y<112)shade=24'hf5fbff;
    else if(rr==1)shade=24'hedf6fc;
    expect_rgb=glass(rgb,shade);
    if(rr<14)begin
     left_length=7;while(left_length>0&&reference_text[rr*18+left_length-1]==0)left_length--;
     right_length=11;while(right_length>0&&reference_text[rr*18+7+right_length-1]==0)right_length--;
     startl=448-left_length*16;startr=768-right_length*16;
     lh=x>=startl&&x<startl+left_length*32;rh=x>=startr&&x<startr+right_length*32;
     ink=lh?24'h42566c:24'h173b54;
     if(rr<=1)ink=24'h163046;
     else if(rr==4&&ref_failed)ink=24'hba332c;
     else if(rr==9&&ref_audio_failed)ink=24'hba332c;
     else if(rr==9&&ref_audio)ink=24'h00796b;
     else if(rr==10&&ref_keys!=0)ink=24'h885718;
     if((lh||rh)&&(y-80)%40<32)begin
      lx=x-(rh?startr:startl);cc=(rh?7:0)+lx/32;fx=(lx%32)/2;fy=((y-80)%40)/2;
      bits=font_memory[reference_text[rr*18+cc]*16+fy];
      if(bits[15-fx])expect_rgb=ink;
     end
    end
    if(!rounded(x,y,290,66,990,654,22)||(x>=576&&x<578&&y>=120&&y<640)||(y>=158&&y<160))expect_rgb=24'hf9fdff;
   end
  end
  for(k=4;k>0;k--)begin q[k]=q[k-1];ctl[k]=ctl[k-1];tagq[k]=tagq[k-1];end
  q[0]=expect_rgb;ctl[0]={x,y,de,hs,vs,pv};tagq[0]=render_tag;pipe_cycles++;
  #1;
  if(pipe_cycles>=5)begin
   if(out!==q[4]||{ox,oy,od,oh,ov,op}!==ctl[4])$fatal(1,"RGB/control latency xy=%0d,%0d got=%h expected=%h ctl=%h want=%h",ox,oy,out,q[4],{ox,oy,od,oh,ov,op},ctl[4]);
   checks++;
   if(tagq[4])begin $fwrite(fh,"%c%c%c",out[23:16],out[15:8],out[7:0]);frame_pixels++;end
  end
 end
 task reference_case(input integer which);begin
  for(i=0;i<252;i++)reference_text[i]=text_memory[which*252+i];
  ref_visible=visible;ref_keys=keys;ref_field=field;ref_failed=failed||error!=0;ref_audio=audio;ref_audio_failed=aerror!=0||status==4;
 end endtask
 task raster(input integer capture);begin
  if(capture!=0)begin fh=$fopen($sformatf("%0s_%0d.ppm",preview,capture),"wb");if(!fh)$fatal(1,"preview file");$fwrite(fh,"P6\n1280 720\n255\n");end
  for(j=0;j<720;j++)for(i=0;i<1280;i++)begin
   @(negedge clk);x=i;y=j;de=1;hs=i[0];vs=j[0];rgb=capture==1?24'hffffff:{i[7:0],j[7:0],8'h60};render_tag=(capture!=0);
  end
  @(negedge clk);render_tag=0;de=0;x=1;cycles(6);
  if(capture!=0)begin $fclose(fh);fh=0;end
 end endtask
 initial begin
  if(!$value$plusargs("VECTORS=%s",vp)||!$value$plusargs("TEXT=%s",tp)||!$value$plusargs("FONT=%s",fp)||!$value$plusargs("CASES=%d",ncases)||!$value$plusargs("PREVIEW=%s",preview))$fatal(1,"missing data");
  $readmemh(vp,vectors,0,ncases-1);$readmemh(tp,text_memory,0,ncases*252-1);$readmemh(fp,font_memory);
  #23;rst=1;cycles(3);expected_visible(1);
  for(i=0;i<2048;i++)if(d.font_memory[i]!==font_memory[i])$fatal(1,"font row differs from independent source-font raster at %0d",i);
  for(ci=0;ci<ncases;ci++)load_case(ci);
  // Snapshot atomically at frame start, with no mid-frame parameter tearing.
  @(negedge clk);br=48;x=600;y=200;de=0;cycles(5);
  if(d.shown_brightness===8'sd48)$fatal(1,"mid-frame parameter tear");
  frame();if(d.shown_brightness!==8'sd48)$fatal(1,"frame parameter not committed");
  @(negedge clk);keys=0;field=1;failed=0;error=0;aerror=0;status=0;loading=0;cycles(3);frame();
  repeat(12)begin frame();expected_visible(1);end
  @(negedge clk);field=0;cycles(3);frame();expected_visible(1);
  repeat(5)begin frame();expected_visible(1);end
  frame();expected_visible(0);
  @(negedge clk);image=image+1;loading=1;audio=~audio;cycles(3);frame();expected_visible(0);
  // A short pulse between frame boundaries is remembered and wakes on next frame.
  @(negedge clk);keys=1;cycles(3);keys=0;cycles(3);expected_visible(0);
  frame();expected_visible(1);
  repeat(6)frame();expected_visible(0);
  @(negedge clk);osd=0;keys=2;cycles(3);expected_visible(0);frame();expected_visible(1);
  repeat(12)begin frame();expected_visible(1);end
  @(negedge clk);keys=0;cycles(3);frame();repeat(6)frame();expected_visible(0);
  @(negedge clk);failed=1;error=8'he0;cycles(3);frame();repeat(12)begin frame();expected_visible(1);end
  // Three fully rendered Chinese screens and two bypass/gate-low rasters.
  for(ci=ncases-3;ci<ncases;ci++)begin
   load_case(ci);reference_case(ci);pixel_check=1;pipe_cycles=0;raster(ci-(ncases-3)+1);pixel_check=0;
  end
  load_case(ncases-3);@(negedge clk);keys=0;field=0;cycles(3);repeat(7)frame();expected_visible(0);
  reference_case(ncases-3);ref_visible=0;pixel_check=1;pipe_cycles=0;raster(0);pixel_check=0;
  // Entire fifth raster uses independently generated text/state, never DUT ROM data.
  load_case(ncases-4);expected_visible(1);reference_case(ncases-4);
  if(pv!==0)$fatal(1,"low picture gate vector missing");
  pixel_check=1;pipe_cycles=0;raster(0);pixel_check=0;
  if(frame_pixels!=3*1280*720)$fatal(1,"preview frame size");
  $display("PASS v108 Chinese UI: %0d independent centered text cases / %0d actual glyph cells / 2048 font rows / %0d aligned pixels, five720p rasters; timeout, snapshots, hidden wake, keys/edit/errors, no raised picture gate",ncases,chars,checks);$finish;
 end
 initial begin #220000000;$fatal(1,"timeout");end
endmodule
