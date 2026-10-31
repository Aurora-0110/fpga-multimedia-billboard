`timescale 1ns/1ps
module tb_idx_chain;
parameter real SD_HALF=10.101;
parameter integer NEGATIVE=0;
reg sd=0,pc=0;always #(SD_HALF) sd=~sd;always #6.734007 pc=~pc;
reg lock=0,restart=0;wire rst,prst;
reset_release r0(.clk(sd),.async_n(lock),.rst_n(rst));
reset_release r1(.clk(pc),.async_n(lock),.rst_n(prst));
wire [11:0] x,y;wire hs,vs,de,fs;
video_timing #(.H_ACTIVE(1280),.H_FP(110),.H_SYNC(40),.H_BP(220),
.V_ACTIVE(720),.V_FP(5),.V_SYNC(5),.V_BP(20)) timing(.clk(pc),.rst_n(prst),
.x(x),.y(y),.hs(hs),.vs(vs),.de(de),.frame_start(fs));
wire win=de&&x>=320&&x<960&&y>=120&&y<600;
wire [23:0] rgb;wire dd,hd,vd,init,fr,ren,run,fault,of;wire [1:0] phase;
wire cke,cs,ras,cas,we,oe;wire [10:0] ma;wire [1:0] ba;wire [3:0] dm;
wire [31:0] dout;tri [31:0] dq;assign dq=oe?dout:32'bz;
idx_pipeline dut(.clk_sd(sd),.clk_pix(pc),.rst_sd_n(rst),.rst_pix_n(prst),.restart(restart),
.frame_start(fs),.de(de),.hs(~hs),.vs(~vs),.window(win),.rgb(rgb),.de_d(dd),.hs_d(hd),.vs_d(vd),
.init_done(init),.frame_ready(fr),.read_enable(ren),.display_running(run),.display_fault(fault),.overflow_fault(of),.phase(phase),
.mem_cke(cke),.mem_cs_n(cs),.mem_ras_n(ras),.mem_cas_n(cas),.mem_we_n(we),.mem_addr(ma),.mem_ba(ba),.mem_dm(dm),
.dq_out(dout),.dq_oe(oe),.dq_in(dq));
IS42s32200 mem(.Clk(sd),.Cke(cke),.Cs_n(cs),.Ras_n(ras),.Cas_n(cas),.We_n(we),.Addr(ma),.Ba(ba),.Dqm(dm),.Dq(dq));
integer pixels=0,writes=0,reads=0,epochs=0,frames=0;
integer min_used=4096,max_used=0,byteidx=0;
reg inject=0,waspop,expde,exphs,expvs;reg[23:0] expected;
function [23:0] color;
input integer xx,yy;
begin
 if(xx==0||xx==639||yy==0||yy==479||xx%64==0||yy%64==0)color=24'hffffff;
 else case(xx/80)
 0:color=24'hffffff;1:color=24'hffff00;2:color=24'h00ffff;3:color=24'h00ff00;
 4:color=24'hff00ff;5:color=24'hff0000;6:color=24'h0000ff;default:color=0;
 endcase
end endfunction
always @(posedge sd)begin
 if(rst)begin
 if(dut.resp&&dut.reader.pending&&dut.reader.queued)$fatal(1,"response queue overwrite");
 if(of)$fatal(1,"FIFO overflow");
 if(dut.ack&&dut.ow)writes=writes+1;
 if(dut.ack&&dut.orr)reads=reads+1;
 if(dut.fw&&dut.ff)$fatal(1,"overflow write attempt");
 if(dut.wu>4096)$fatal(1,"invalid fifo count");
 end
end
always @(negedge dut.pipe)if(rst)begin
 epochs=epochs+1;
 if(!dut.idle)$fatal(1,"epoch reset before controller idle");
end
always @(posedge pc)begin
 waspop=dut.pop;
 expde=de;exphs=~hs;expvs=~vs;
 expected=waspop?color(x-320,y-120):0;
 if(dut.prst)begin
 if(fault&&!inject)$fatal(1,"unexpected video underflow x=%0d y=%0d",x,y);
 // During orderly retry drain, enable drops before running is cleared/reset.
 // This interval intentionally blanks pixels; consumption is required only
 // while display enable is still asserted (same active predicate as DUT).
 if(run&&dut.display.enable&&win&&!inject&&!waspop)$fatal(1,"pixel not consumed x=%0d y=%0d used=%0d empty=%b",x,y,dut.ru,dut.fe);
 if(!dut.display.enable&&waspop)$fatal(1,"consume while display disabled");
 if(waspop)begin
 if(!win)$fatal(1,"consume outside centered image");
 if(byteidx%307200!==((y-120)*640+x-320))$fatal(1,"frame origin/wrap mismatch");
 byteidx=byteidx+1;pixels=pixels+1;
 if(dut.ru<min_used)min_used=dut.ru;
 if(dut.ru>max_used)max_used=dut.ru;
 end
 #0.001;
 if(dut.prst)begin
 if(rgb!==expected)$fatal(1,"SDRAM pixel mismatch x=%0d y=%0d got=%h expected=%h",x,y,rgb,expected);

 end
 end
end
always @(posedge pc) begin
 if(prst) begin
  expde=de;exphs=~hs;expvs=~vs;
  #0.002;
  if(prst && (dd!==expde||hd!==exphs||vd!==expvs))
   $fatal(1,"outgoing HDMI timing broken during retry: content_reset=%b",dut.prst);
 end
end
// Per-frame 720p timing independent of image readiness.
integer act=0,hcount=0,vcount=0,cycles=0;reg frame_seen=0;
always @(negedge pc)if(prst)begin
 if(fs)begin
 if(frame_seen && (cycles!=1237500 || act!=921600 || hcount!=30000 || vcount!=8250))
 $fatal(1,"720p timing cycles=%0d active=%0d hs=%0d vs=%0d",cycles,act,hcount,vcount);
 if(frame_seen)frames=frames+1;frame_seen=1;
 cycles=0;act=0;hcount=0;vcount=0;
 end
 if(frame_seen)begin cycles=cycles+1;if(de)act=act+1;if(!hs)hcount=hcount+1;if(!vs)vcount=vcount+1;end
end
always @(negedge dut.prst)byteidx=0;
task retry;begin @(negedge sd);restart=1;@(negedge sd);restart=0;end endtask
initial begin
 repeat(8)@(negedge sd);lock=1;
 wait(dut.ctrl.state==15);$display("STAGE write_retry t=%0t",$time);retry();wait(!dut.pipe);wait(phase==1);
 wait(dut.ctrl.state==13);$display("STAGE read_retry t=%0t",$time);retry();wait(!dut.pipe);wait(phase==1);
 // Third retry after real display starts, in the active image mid-line.
 wait(pixels>=200);wait(x==600 && y==121 && run);$display("STAGE active_retry t=%0t pixels=%0d",$time,pixels);retry();
 wait(!dut.pipe);wait(phase==1);
 if(NEGATIVE)begin
 wait(byteidx>=200);@(negedge pc);inject=1;force dut.fe=1;
 repeat(10)@(negedge pc);
 if(!fault||run||dut.pop)$fatal(1,"injected empty did not latch/stop");
 release dut.fe;
 repeat(1000)@(negedge pc);
 if(!fault||dut.pop)$fatal(1,"fault incorrectly recovered mid-frame");
 retry();wait(!dut.pipe);wait(phase==1);inject=0;
 wait(byteidx>=307200);
 $display("PASS idx_chain injected_underflow_latched=1 recovery_after_retry=1 pixels=%0d epochs=%0d",pixels,epochs);$finish;
 end else begin
 wait(byteidx>=614400);
 if(epochs<3||frames<2||reads<38400)$fatal(1,"insufficient coverage");
 $display("PASS idx_chain full_640x480_frames=2 pixels=%0d complete_720p_frames=%0d epochs=%0d reads=%0d writes=%0d min_fifo=%0d max_fifo=%0d sd_half=%f",pixels,frames,epochs,reads,writes,min_used,max_used,SD_HALF);$finish;
 end
end
always begin #5000000; $display("PROGRESS ns=%0t phase=%0d ctrl=%0d pixels=%0d frames=%0d writes=%0d reads=%0d",$time,phase,dut.ctrl.state,pixels,frames,writes,reads);$fflush();end
initial begin #140000000;$fatal(1,"timeout phase=%0d pixels=%0d",phase,pixels);end
endmodule
