`timescale 1ns/1ps
module tb_v103_diagnostics;
 reg clk=0;always #5 clk=~clk;reg rst=0,en=0;reg[11:0]x=20,y=10;
 reg[7:0]status=8'h47,err=0;reg pic=1;wire[23:0]rgb,legacy_rgb;wire[11:0]ox,oy;wire de,hs,vs,pv;
 display_diagnostics_osd #(.ALWAYS_SHOW_FAULTS(1),.VERSION_MAJOR(1),.VERSION_TENS(0),.VERSION_ONES(3)) d(
 .clk(clk),.rst_n(rst),.x(x),.y(y),.rgb(24'h234567),.de(1'b1),.hs(1'b1),.vs(1'b0),.picture_visible(pic),
 .image_index(2'd1),.status(status),.tf_error(err),.fifo_used(13'd2048),.enable(en),
 .x_out(ox),.y_out(oy),.rgb_out(rgb),.de_out(de),.hs_out(hs),.vs_out(vs),.picture_visible_out(pv));
 display_diagnostics_osd legacy(.clk(clk),.rst_n(rst),.x(x),.y(y),.rgb(24'h234567),.de(1'b1),.hs(1'b1),.vs(1'b0),.picture_visible(pic),
 .image_index(2'd1),.status(status),.tf_error(err),.fifo_used(13'd2048),.enable(en),.rgb_out(legacy_rgb));
 integer checks=0,i;reg[4:0]mask;
 task tick(input integer n);repeat(n)@(negedge clk);endtask
 task ck(input bit ok,input string msg);begin checks++;if(!ok)$fatal(1,"%s rgb=%h history=%h",msg,rgb,d.history);end endtask
 task snapshot;begin x=0;y=0;tick(1);x=20;y=10;tick(7);end endtask
 initial begin
  for(i=0;i<5;i++)begin
   rst=0;en=0;status=8'h47;err=0;pic=1;tick(3);rst=1;tick(8);snapshot();
   ck(rgb==24'h234567&&legacy_rgb==24'h234567&&d.history==0,"healthy hidden exact bypass");
   ck(d.header(1)=="1"&&d.header(2)=="0"&&d.header(3)=="3"&&legacy.header(1)=="0"&&legacy.header(3)=="9","version actual103/default089");
   case(i)0:begin status[3]=1;mask=1;end
    1:begin status[4]=1;mask=2;end
    2:begin status[5]=1;mask=4;end
    3:begin err=8'he0;mask=8;end
    4:begin status[6]=0;mask=16;end
   endcase
   tick(8);snapshot();
   ck((d.history&mask)==mask&&rgb==24'h601020,"hidden fault must remain red");
   ck(de&&hs&&!vs&&pv&&ox==20&&oy==10,"fault overlay never changes timing or raises visibility");
   if(i==3)ck(d.first_error==8'he0,"first TF error recorded");
   status=8'h47;err=0;tick(8);snapshot();
   ck(rgb==24'h601020&&(d.history&mask)==mask,"cleared live fault retains non-hideable evidence");
   ck(legacy_rgb==24'h234567,"default legacy enable behavior unchanged");
   pic=0;tick(8);ck(!pv&&de,"diagnostic pixels never unmute failed framebuffer");
  end
  rst=0;tick(2);ck(d.history==0&&d.first_error==0,"explicit reset clears history");
  $display("PASS v103_diagnostics sources=5 checks=%0d hidden/current+historical-fault/version/timing/audio-gate/legacy",checks);$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
