`timescale 1ns/1ps
module tb_v103_playlist;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,k=0,m=0,init=0,ld=0,run=0,fault=0,td=0,progress=0;reg[7:0]err=0;
 wire lr,le,bank,front,tr,busy,fail,am;wire[7:0]letter,code;wire[1:0]im,li;
 tf_double_playlist #(.AUTO_ENABLE(0),.DWELL_CYCLES(40),.RESET_CYCLES(3),
 .LOAD_TIMEOUT_CYCLES(12),.AUTO_RETRIES(2),.RETRY_DELAY_CYCLES(5)) d(
 .clk(clk),.rst_n(rst),.key_press(k),.mode_press(m),.init_done(init),.load_done(ld),
 .load_error(err),.display_running(run),.stream_fault(fault),.transition_done(td),
 .load_rst_n(lr),.load_enable(le),.dest_bank(bank),.file_letter(letter),.image_index(im),
 .load_index(li),.front_valid(front),.transition_request(tr),.busy(busy),.failed(fail),
 .auto_mode(am),.error_latched(code),.load_progress(progress));
 integer checks=0,scenarios=0,i,j;reg oldbank;
 task ck(input bit ok,input string msg);begin checks++;if(!ok)$fatal(1,"%s state=%d watchdog=%d retries=%d",msg,d.state,d.watchdog,d.retry_count);end endtask
 task tick(input integer n);repeat(n)@(negedge clk);endtask
 task reset;begin rst=0;k=0;m=0;init=0;ld=0;run=0;fault=0;td=0;progress=0;err=0;tick(3);rst=1;tick(2);end endtask
 task start;begin reset();init=1;wait(le);tick(1);progress=1;tick(1);progress=0;end endtask
 task success;begin ld=1;tick(1);ld=0;end endtask
 task key;begin k=1;tick(1);k=0;end endtask
 task background;begin start();success();run=1;wait(le);tick(1);progress=1;tick(1);progress=0;ck(front&&bank&&im==0&&li==1,"background B");end endtask
 initial begin
  reset();tick(50);ck(!le&&!front&&code==0,"must not load/time out before init");scenarios++;
  start();tick(11);ck(le&&!fail&&code==0,"timeout not early");tick(1);
  ck(fail&&code==8'he0&&!front&&!tr,"exact inactivity expiry / never publish first partial");
  tick(4);ck(fail&&!le&&d.retry_count==0,"retry delay not early");tick(1);
  ck(!fail&&!le&&d.retry_count==1,"retry after five clocks");wait(le);tick(1);
  ck(letter=="A"&&!bank,"retry same first file/bank");wait(fail);tick(1);
  wait(le);tick(1);ck(d.retry_count==2,"second retry budget");wait(fail);tick(1);tick(80);
  ck(fail&&!le&&d.retry_count==2&&!front,"bounded initial+two retries; no infinite loop");
  key();wait(le);tick(1);ck(d.retry_count==0&&code==0,"manual key grants fresh retry budget");success();ck(front,"manual recovery publishes complete frame");scenarios++;
  start();for(i=0;i<25;i++)begin tick(10);ck(le&&!fail,"long total transfer allowed with progress");progress=1;tick(1);progress=0;end
  success();ck(front&&!fail,"continuous accepted bursts complete >20 watchdog periods");scenarios++;
  start();tick(11);progress=1;tick(1);progress=0;ck(le&&d.watchdog==0,"progress wins coincident deadline");
  tick(11);ld=1;tick(1);ld=0;ck(front&&!fail,"done wins coincident deadline");scenarios++;
  start();tick(11);ld=1;err=8'h35;progress=1;tick(1);ld=0;err=0;progress=0;
  ck(fail&&code==8'h35&&!front,"error wins done/progress/deadline");scenarios++;
  for(j=0;j<4;j++)begin
   start();case(j)0:err=8'h25;1:err=8'h32;2:err=8'h34;3:err=8'h38;endcase
   tick(1);err=0;tick(80);ck(fail&&!le&&d.retry_count==0,"missing/format/coordinate never auto retry");scenarios++;
  end
  for(j=0;j<3;j++)begin
   start();case(j)0:err=8'h14;1:err=8'h2d;2:err=8'h35;endcase
   tick(1);err=0;wait(le);tick(1);ck(d.retry_count==1&&code==0,"transport error is retryable");success();ck(front&&d.retry_count==0,"success resets budget");scenarios++;
  end
  background();oldbank=bank;tick(12);ck(fail&&code==8'he0&&front&&!tr&&im==0&&li==1&&bank==oldbank,"failed preload holds current frame/banks/index");
  wait(le);tick(1);ck(front&&li==1&&bank==oldbank,"retry same inactive bank");success();
  ck(d.retry_count==0&&!fail,"background retry success");key();wait(tr);tick(1);ck(im==0&&bank==oldbank,"no early bank reuse");
  tick(8);ck(tr&&front&&im==0&&bank==oldbank,"slide handshake must drain old reads");td=1;tick(1);td=0;
  ck(im==1&&li==2&&bank!=oldbank&&front,"commit only after transition done");scenarios++;
  start();fault=1;tick(4);err=8'h35;tick(1);err=0;tick(50);
  ck(fail&&!le&&d.retry_count==0,"stream fault prohibits automatic retry");scenarios++;
  background();err=8'h35;tick(1);err=0;tick(4);m=1;tick(1);m=0;
  ck(fail&&d.retry_count==0,"mode key cannot consume retry/double act");tick(1);ck(d.retry_count==1,"retry deferred one clock on mode key");scenarios++;
  $display("PASS v103_playlist scenarios=%0d checks=%0d exact-inactivity/progress/priority/bounded-retry/no-partial-publish/bank-safe/manual/stream-fault",scenarios,checks);$finish;
 end
 initial begin #1000000;$fatal(1,"test watchdog");end
endmodule
