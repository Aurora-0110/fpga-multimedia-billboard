`timescale 1ns/1ps
// Tight regression: a content retry at each H phase must not change DE/HS/VS.
// OLD_DISPLAY reproduces the original v047 common reset without editing v047.
module tb_retry_timing;
reg clk=0;always #6.734 clk=~clk;
reg vr=0,cr=0;wire [11:0] x,y;wire de,hs,vs,fs;
video_timing #(.H_ACTIVE(16),.H_FP(2),.H_SYNC(3),.H_BP(3),
 .V_ACTIVE(8),.V_FP(1),.V_SYNC(2),.V_BP(1)) timing(
 .clk(clk),.rst_n(vr),.x(x),.y(y),.de(de),.hs(hs),.vs(vs),.frame_start(fs));
wire dd,hd,vd,pop,run,fault;wire [23:0] rgb;
idx_display #(.PREFILL(8)) dut(.clk(clk),.rst_n(cr),
`ifndef OLD_DISPLAY
 .timing_rst_n(vr),
`endif
 .enable(1'b1),.frame_start(fs),.de(de),.hs(~hs),.vs(~vs),.window(de),
 .empty(1'b0),.used(13'd64),.data(8'hff),.pop(pop),.rgb(rgb),
 .de_d(dd),.hs_d(hd),.vs_d(vd),.running(run),.fault(fault));
reg checking=0,ed,eh,ev;integer checks=0,retries=0,i;
always @(posedge clk)if(checking&&vr)begin
 ed=de;eh=~hs;ev=~vs;#0.001;
 if(dd!==ed||hd!==eh||vd!==ev)$fatal(1,"RETRY_TIMING_GLITCH retry=%0d content_rst=%b x=%0d y=%0d got=%b%b%b exp=%b%b%b",retries,cr,x,y,dd,hd,vd,ed,eh,ev);
 checks=checks+1;
end
initial begin
 repeat(4)@(negedge clk);vr=1;cr=1;wait(run);
 @(negedge clk);checking=1;
 // Cover active video, porch, H sync and V sync at all 24 line phases.
 for(i=0;i<24;i=i+1)begin
 wait(x==i && y==(i%12));#1.9;cr=0;retries=retries+1;
 #0.001;if(rgb!==0||pop!==0)$fatal(1,"content reset failed to blank");
 repeat(5+(i%4))@(negedge clk);#2.1;cr=1;
 wait(run);repeat(2)@(negedge clk);
 end
 // Hold content reset for several frames: still output valid black timing.
 #1.7;cr=0;retries=retries+1;repeat(900)@(negedge clk);cr=1;wait(run);
 repeat(300)@(negedge clk);
 if(retries!=25||checks<2000||fault)$fatal(1,"insufficient retry coverage");
 $display("PASS retry_timing retries=%0d uninterrupted_control_checks=%0d",retries,checks);$finish;
end
initial begin #2000000;$fatal(1,"retry regression timeout");end
endmodule
