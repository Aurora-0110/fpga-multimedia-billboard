`timescale 1ns/1ps
// True pin-level SDRAM model, no forced datapath. Synthetic burst loader, NOT real TF.
module tb_v079_memory;
parameter HEIGHT=8, STOP_STEP=40;
localparam Y0=HEIGHT==480?120:4;
reg sd=0,pc=0,rst=0,front=0,bank=0,tr=0,lv=0;
always #10.101 sd=~sd;always #6.734007 pc=~pc;
reg [1:0] target=1;reg [18:0] la=0;reg [127:0] wd=0;
wire [11:0] x,y;wire hs,vs,de,fs;
video_timing #(.H_ACTIVE(1280),.H_FP(110),.H_SYNC(40),.H_BP(220),.V_ACTIVE(HEIGHT==480?720:HEIGHT+8),.V_FP(5),.V_SYNC(5),.V_BP(HEIGHT==480?20:6)) timing(pc,rst,x,y,hs,vs,de,fs);
wire win=de&&x>=320&&x<960&&y>=Y0&&y<Y0+HEIGHT;
wire td,ack,dd,hd,vd,init,run,fault,vis,of,cke,cs,ras,cas,we,oe;
wire [23:0] rgb;wire [1:0] idx;wire [5:0] step;wire [10:0] ma;wire [1:0] ba;wire [3:0] dm;wire [31:0] dout;tri [31:0] dq;assign dq=oe?dout:32'bz;
idx_dual_pipeline d(.clk_sd(sd),.clk_pix(pc),.rst_sd_n(rst),.rst_pix_n(rst),.front_valid(front),.dest_bank(bank),.transition_request(tr),.target_index(target),.transition_done(td),
.frame_start(fs),.de(de),.hs(~hs),.vs(~vs),.window(win),.load_valid(lv),.load_addr(la),.load_data(wd),.load_ack(ack),
.rgb(rgb),.de_d(dd),.hs_d(hd),.vs_d(vd),.init_done(init),.display_running(run),.display_fault(fault),.picture_visible(vis),.overflow_fault(of),.displayed_index(idx),.displayed_step(step),
.mem_cke(cke),.mem_cs_n(cs),.mem_ras_n(ras),.mem_cas_n(cas),.mem_we_n(we),.mem_addr(ma),.mem_ba(ba),.mem_dm(dm),.dq_out(dout),.dq_oe(oe),.dq_in(dq));
defparam d.reader.LINES=HEIGHT;
IS42s32200 mem(.Clk(sd),.Cke(cke),.Cs_n(cs),.Ras_n(ras),.Cas_n(cas),.We_n(we),.Addr(ma),.Ba(ba),.Dqm(dm),.Dq(dq));
function [7:0] bytecolor(input integer image,xx,yy);begin bytecolor=(image*71+xx*3+yy*17) ^ (xx>>3);end endfunction
function [23:0] expand(input [7:0] c);begin expand={c[7:5],c[7:5],c[7:6],c[4:2],c[4:2],c[4:3],c[1:0],c[1:0],c[1:0],c[1:0]};end endfunction
integer writes=0,reads=0,pixels=0,frames=0,concurrent_writes=0,min_used=4096;
reg prevpop;integer xx,yy,src,im,st,frame_idx=-1,frame_step=-1;reg [23:0] exp;
always @(posedge sd)if(rst)begin
 if(ack)begin writes++;if(run)concurrent_writes++;end
 if(d.ack&&d.grant==1)reads++;
 if(d.resp&&d.grant!=1)$fatal(1,"response owner mismatch");
 if(d.fw&&d.ff)$fatal(1,"FIFO overflow");
end
always @(posedge pc)if(rst&&d.prst)begin
 if(fault||of)$fatal(1,"fault x=%0d y=%0d occupancy=%0d",x,y,d.ru);
 prevpop=d.pop;xx=x-320;yy=y-Y0;
 if(prevpop)begin
  if(!win)$fatal(1,"out of window pop");
  if(d.ru<min_used)min_used=d.ru;
 end
 #0.002;
 if(prevpop)begin
  im=idx;st=step;
  if(xx==0&&yy==0)begin
   if(frames>0&&frame_step>0&&frame_step<40&&st!=frame_step+1)$fatal(1,"noncontinuous step %0d -> %0d",frame_step,st);
   frame_idx=im;frame_step=st;frames++;
   $display("FRAME height=%0d number=%0d idx=%0d step=%0d",HEIGHT,frames,im,st);$fflush();
  end
  if(im!=frame_idx||st!=frame_step)$fatal(1,"tag tearing within frame");
  src=xx+st*16;
  if(st>0)begin if(src>=640)begin src=src-640;end else im=im-1;end
  exp=expand(bytecolor(im,src,yy));
  if(rgb!==exp)$fatal(1,"pixel height=%0d xy=%0d,%0d tag=%0d/%0d got=%h exp=%h",HEIGHT,xx,yy,idx,step,rgb,exp);
  pixels++;
 end
end
integer seqw=0,seqack=0;
always @(posedge sd) if(rst)begin
 if(d.ack&&d.grant==1)begin
  if(seqack>=315&&seqack<328)$display("DBGACK n=%0d addr=%0d row=%0d col=%0d t=%0t",seqack,d.ra,d.reader.row,d.reader.col,$time);
  seqack++;
 end
 if(d.fw)begin
  if(seqw>=5088&&seqw<5168&&seqw%16==0)$display("DBGWRITE n=%0d data=%h pcnt=%0d queued=%b t=%0t",seqw,d.fwd,d.reader.pcnt,d.reader.queued,$time);
  seqw++;
 end
end
integer a,b;
task load(input integer image,input bit dest);begin
 @(negedge sd);bank=dest;
 for(a=0;a<40*HEIGHT;a++)begin
  for(b=0;b<16;b++)wd[b*8+:8]=bytecolor(image,(a%40)*16+b,a/40);
  la=a;lv=1;
  do @(posedge sd);while(!ack);
  @(negedge sd);lv=0; // Stable through the registered ACK; controller has latched payload.
 end
 wait(d.idle&&d.grant==0);
end endtask
initial begin
 repeat(8)@(negedge sd);rst=1;wait(init);
 load(0,0);front=1;wait(run);
 load(1,1);@(negedge sd);tr=1;
 if(STOP_STEP==40)begin
  wait(td);@(negedge sd);tr=0;
  load(2,0); // Reuse old bank while final old-frame bytes may still reside in FIFO.
  wait(frame_step==0&&frame_idx==1);
  wait(pixels% (HEIGHT*640)==0);repeat(5)@(negedge pc);
 end else begin
  wait(frame_step==STOP_STEP);wait(pixels%(HEIGHT*640)==0);repeat(5)@(negedge pc);
 end
 if(concurrent_writes<40*HEIGHT||d.ctrl.refresh_count==0)$fatal(1,"missing background/refresh coverage");
 $display("PASS memory height=%0d pixels=%0d frames=%0d writes=%0d reads=%0d concurrent=%0d min_fifo=%0d refresh=%0d",HEIGHT,pixels,frames,writes,reads,concurrent_writes,min_used,d.ctrl.refresh_count);$finish;
end
always begin #20000000;$display("PROGRESS height=%0d pixels=%0d frames=%0d writes=%0d",HEIGHT,pixels,frames,writes);$fflush();end
initial begin #300000000;$fatal(1,"memory watchdog height=%0d",HEIGHT);end
endmodule
