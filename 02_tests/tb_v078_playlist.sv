`timescale 1ns/1ps
module tb_v078_playlist;
reg clk=0;always #5 clk=~clk;
reg rst=0,k=0,m=0,init=0,ld=0,run=0,fault=0,td=0;reg[7:0]err=0;
wire lr,le,bank,front,tr,busy,fail,auto_mode;wire[7:0]fileletter,ecode;wire[1:0]im,li;
tf_double_playlist #(.DWELL_CYCLES(40),.RESET_CYCLES(3))d(clk,rst,k,m,init,ld,err,run,fault,td,lr,le,bank,fileletter,im,li,front,tr,busy,fail,auto_mode,ecode,1'b0);
integer checks=0;
task ck(input bit ok,input string name);begin checks++;if(!ok)$fatal(1,"%s",name);end endtask
task tick;begin @(negedge clk);end endtask
task key;begin tick;k=1;tick;k=0;end endtask
task mode;begin tick;m=1;tick;m=0;end endtask
task complete_slide;begin tick;td=1;tick;td=0;end endtask
task loadok;begin wait(le);tick;ld=1;tick;ld=0;repeat(2)tick;end endtask
initial begin
 #23;rst=1;repeat(5)tick;ck(!le&&!front,"no load before init");init=1;
 wait(le);ck(fileletter=="A"&&!bank,"first bank A");loadok();ck(front,"front valid");
 run=1;wait(le);ck(fileletter=="B"&&bank,"background B");
 repeat(50)tick;ck(!tr&&front,"auto overdue cannot reveal incomplete next image");
 loadok();wait(tr);ck(bank&&im==0&&li==1,"bank locked during slide");repeat(8)tick;ck(bank&&front,"old bank protected");
 complete_slide();repeat(2)tick;ck(!bank&&im==1&&li==2,"safe recycle after drain");
 wait(le);mode();ck(!auto_mode,"manual mode");err=8'h32;tick;err=0;repeat(3)tick;
 ck(fail&&ecode==8'h32&&front&&!tr,"failed prefetch retains picture and error");
 key();wait(le);ck(fileletter=="C"&&!bank&&ecode==0,"retry same inactive file");
 key();loadok();wait(tr);ck(front,"queued manual key after preload");complete_slide();
 loadok();repeat(80)tick;ck(!tr&&im==2,"manual holds even after dwell");
 mode();wait(tr);ck(auto_mode&&li==3,"auto dwell resumes");
 complete_slide();wait(le);ck(fileletter=="A"&&li==0,"four-image wrap");
 fault=1;repeat(4)tick;ck(fail,"stream fault visible");
 $display("PASS playlist %0d checks: preload, bank safety, 4-image wrap, manual/auto, queued key, retry",checks);$finish;
end
initial begin #100000;$fatal(1,"playlist timeout state %d",d.state);end
endmodule

