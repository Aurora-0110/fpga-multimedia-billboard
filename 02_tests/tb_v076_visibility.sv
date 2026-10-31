`timescale 1ns/1ps
module tb_v076_visibility;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,tr=0,en=0,fs=0,win=0,empty=0;reg [12:0] used=4096;
 wire pop,vis,run,fault,dd,hd,vd;wire[23:0]rgb;
 idx_display dut(.clk(clk),.rst_n(rst),.timing_rst_n(tr),.enable(en),.frame_start(fs),
 .de(1'b1),.hs(1'b0),.vs(1'b0),.window(win),.empty(empty),.used(used),.data(8'hff),
 .pop(pop),.rgb(rgb),.de_d(dd),.hs_d(hd),.vs_d(vd),.running(run),.fault(fault),.picture_visible(vis));
 integer checks=0;
 task tick;begin @(posedge clk);#1;checks=checks+1;if(tr && dd!==1)$fatal(1,"HDMI DE reset by content");@(negedge clk);end endtask
 task check(input reg v);begin if(vis!==v)$fatal(1,"visible mismatch expected=%b got=%b",v,vis);end endtask
 task start;begin rst=1;en=1;fs=0;win=0;repeat(3)tick();check(0);
 fs=1;tick();fs=0;if(!run)$fatal(1,"frame start missing");check(0);
 repeat(3)tick();check(0);win=1;tick();check(1);if(rgb!==24'hffffff)$fatal(1,"first pixel mismatch");
 win=0;repeat(5)tick();check(1);end endtask
 initial begin
 #1;tr=1;repeat(3)tick();check(0);
 // Loading / prefill: enable without frame start cannot become visible.
 rst=1;en=1;win=1;used=0;fs=1;repeat(3)tick();check(0);
 used=4096;fs=0;repeat(3)tick();check(0);win=0;
 start(); // first frame / picture actually starts
 rst=0;#1;check(0);repeat(2)tick(); // manual/auto restart epoch
 start();en=0;tick();check(0); // disable
 rst=0;tick();start();win=1;empty=1;tick();check(0);
 if(!fault || run)$fatal(1,"underflow not sticky");empty=0;repeat(3)tick();check(0);
 rst=0;tick();start(); // error retry
 rst=0;tr=0;#1;check(0);tick();tr=1;tick();start(); // lock reset/recovery
 $display("PASS v076_visibility startup/prefill/first-pixel/blanking/restart/disable/underflow/retry checks=%0d",checks);$finish;
 end
 initial begin #20000;$fatal(1,"timeout");end
endmodule
