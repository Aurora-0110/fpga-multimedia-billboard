`timescale 1ns/1ps
// Synthesized controller + physical SDRAM bus model. Synthetic burst writer.
module tb_pair_memory;
 parameter HEIGHT=8,STOP_STEP=40;
 reg sd=0,pc=0,rst=0,front=0,bank=0,tr=0,lv=0;
 always #10.101 sd=~sd;always #6.734007 pc=~pc;
 reg [1:0] target=1;reg [18:0] la=0;reg [127:0] wd=0;
 wire [11:0] x,y;wire hs,vs,de,fs;
 video_timing #(.H_ACTIVE(1280),.H_FP(110),.H_SYNC(40),.H_BP(220),.V_ACTIVE(HEIGHT),.V_FP(5),.V_SYNC(5),.V_BP(20)) timing(pc,rst,x,y,hs,vs,de,fs);
 wire td,ack,dd,hd,vd,init,run,fault,vis,of,cke,cs,ras,cas,we,oe;
 wire [23:0] rgb;wire [1:0] idx;wire [5:0] step;wire [10:0] ma;wire [1:0] ba;wire [3:0] dm;wire [31:0] dout;tri [31:0] dq;assign dq=oe?dout:32'bz;
 idx_pair_pipeline #(.HEIGHT(HEIGHT)) d(
 .clk_sd(sd),.clk_pix(pc),.rst_sd_n(rst),.rst_pix_n(rst),.front_valid(front),.dest_bank(bank),.transition_request(tr),.target_index(target),.transition_done(td),
 .frame_start(fs),.de(de),.hs(~hs),.vs(~vs),.window(de),.load_valid(lv),.load_addr(la),.load_data(wd),.load_ack(ack),
 .rgb(rgb),.de_d(dd),.hs_d(hd),.vs_d(vd),.init_done(init),.display_running(run),.display_fault(fault),.picture_visible(vis),.overflow_fault(of),.displayed_index(idx),.displayed_step(step),
 .mem_cke(cke),.mem_cs_n(cs),.mem_ras_n(ras),.mem_cas_n(cas),.mem_we_n(we),.mem_addr(ma),.mem_ba(ba),.mem_dm(dm),.dq_out(dout),.dq_oe(oe),.dq_in(dq));
 IS42s32200 mem(.Clk(sd),.Cke(cke),.Cs_n(cs),.Ras_n(ras),.Cas_n(cas),.We_n(we),.Addr(ma),.Ba(ba),.Dqm(dm),.Dq(dq));
 function [7:0] bytecolor(input integer image,xx,yy);begin bytecolor=(image*71+xx*3+yy*17) ^ (xx>>3);end endfunction
 function [23:0] expand(input [7:0] c);begin expand={c[7:5],c[7:5],c[7:6],c[4:2],c[4:2],c[4:3],c[1:0],c[1:0],c[1:0],c[1:0]};end endfunction
 integer writes=0,reads=0,pixels=0,frames=0,concurrent_writes=0,min_used=4096,first=0,last=0;
 reg emit;integer xx,yy,src,im,st,frame_idx=-1,frame_step=-1;reg [23:0] exp;
 always @(posedge sd)if(rst)begin
  if(ack)begin writes=writes+1;if(run)concurrent_writes=concurrent_writes+1;end
  if(d.ack&&d.grant==1)begin
   reads=reads+1;
   if(d.ra[16:0]==0)first=first+1;
   if(d.ra[16:0]==80*HEIGHT-1)last=last+1;
  end
  if(d.resp&&d.grant!=1)$fatal(1,"pair memory response owner mismatch");
  if(d.fw&&d.ff)$fatal(1,"pair memory FIFO overflow");
  if(of)$fatal(1,"pair memory reader/address fault");
 end
 always @(posedge pc)if(rst&&d.prst)begin
  if(fault||of)$fatal(1,"pair memory fault x=%0d y=%0d used_pairs=%0d",x,y,d.ru);
  emit=d.display.consume;xx=x;yy=y;
  if(emit&&d.ru<min_used)min_used=d.ru;
  #0.002;
  if(emit)begin
   if(!dd||!vis)$fatal(1,"pair emit outside delayed active/visible");
   im=idx;st=step;
   if(xx==0&&yy==0)begin
    if(frames>0&&frame_step>0&&frame_step<40&&st!=frame_step+1)$fatal(1,"pair noncontinuous transition");
    frame_idx=im;frame_step=st;frames=frames+1;
    $display("FRAME pair height=%0d number=%0d idx=%0d step=%0d",HEIGHT,frames,im,st);$fflush();
   end
   if(im!=frame_idx||st!=frame_step)$fatal(1,"pair metadata tear");
   src=xx+st*32;
   if(st>0)begin if(src>=1280)src=src-1280;else im=im-1;end
   exp=expand(bytecolor(im,src,yy));
   if(rgb!==exp)$fatal(1,"pair memory xy=%0d,%0d tag=%0d/%0d got=%h exp=%h",xx,yy,idx,step,rgb,exp);
   pixels=pixels+1;
  end
 end
 integer a,b;
 task load(input integer image,input bit dest);begin
  @(negedge sd);bank=dest;
  for(a=0;a<80*HEIGHT;a=a+1)begin
   for(b=0;b<16;b=b+1)wd[b*8+:8]=bytecolor(image,(a%80)*16+b,a/80);
   la=a;lv=1;
   do @(posedge sd);while(!ack);
   @(negedge sd);lv=0;
  end
  wait(d.idle&&d.grant==0);
 end endtask
 initial begin
  repeat(8)@(negedge sd);rst=1;wait(init);
  load(0,0);front=1;wait(run);
  load(1,1);@(negedge sd);tr=1;
  if(STOP_STEP==40)begin
   wait(td);@(negedge sd);tr=0;load(2,0);
   wait(frame_step==0&&frame_idx==1);
   wait(pixels%(HEIGHT*1280)==0);repeat(5)@(negedge pc);
  end else begin
   wait(frame_step==STOP_STEP);wait(pixels%(HEIGHT*1280)==0);repeat(5)@(negedge pc);
  end
  if(concurrent_writes<80*HEIGHT||d.ctrl.refresh_count==0||first<2||last<2)$fatal(1,"pair missing concurrent/refresh/last-address coverage");
  $display("PASS pair_memory height=%0d pixels=%0d frames=%0d writes=%0d reads=%0d concurrent=%0d min_used_pairs=%0d refresh=%0d first=%0d last=%0d",HEIGHT,pixels,frames,writes,reads,concurrent_writes,min_used,d.ctrl.refresh_count,first,last);$finish;
 end
 always begin #20000000;$display("PROGRESS pair_memory height=%0d pixels=%0d frames=%0d writes=%0d reads=%0d",HEIGHT,pixels,frames,writes,reads);$fflush();end
 initial begin #500000000;$fatal(1,"pair memory watchdog");end
endmodule
