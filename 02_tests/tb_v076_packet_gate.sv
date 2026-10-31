`timescale 1ns/1ps
module tb_v076_packet_gate;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,on=0;reg[11:0]x=0,y=0;reg valid=0;integer div=0;
 hdmi_audio_packets #(.GATE_ENABLE(1)) dut(.clk_pix(clk),.rst_n(rst_n),.cx(x),.cy(y),
 .pcm_l(24'h040000),.pcm_r(24'hfc0000),.pcm_valid(valid),.audio_enable(on),.hs(1'b0),.vs(1'b0));
 always @(negedge clk) if(!rst_n)begin x=0;y=0;valid=0;div=0;end
 else begin
  if(x==1649)begin x=0;y=(y==749)?0:y+1;end else x=x+1;
  valid=(div==1545);div=valid?0:div+1;
 end
 integer cycle=0,change_cycle=0,transitions=0,checks=0,groups=0,max_cycles=0;
 reg last=0,pending=0;reg[47:0]want;
 always @(posedge clk)if(rst_n)begin
  cycle=cycle+1;
  if(on!==last)begin last=on;change_cycle=cycle;pending=1;transitions=transitions+1;end
  if(pending && cycle-change_cycle>10000)$fatal(1,"mute/unmute exceeds digital bound");
  if(dut.pop4)begin
   want=on?48'hfc0000040000:48'd0;
   if(pending)begin
    if(cycle-change_cycle>max_cycles)max_cycles=cycle-change_cycle;
    pending=0;
   end
   #0.1;
   if(dut.s0[47:0]!==want || dut.s1[47:0]!==want || dut.s2[47:0]!==want || dut.s3[47:0]!==want)
    $fatal(1,"stale FIFO tone or missing unmuted sample");
   groups=groups+1;checks=checks+4;
  end
  if(dut.overflow)$fatal(1,"audio FIFO overflow");
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  repeat(15003)@(negedge clk);on=1;
  repeat(17049)@(negedge clk);on=0;
  repeat(11007)@(negedge clk);on=1;
  repeat(20006)@(negedge clk);on=0;
  repeat(15001)@(negedge clk);
  rst_n=0;on=0;repeat(4)@(negedge clk);rst_n=1;
  repeat(18037)@(negedge clk);on=1;
  repeat(16003)@(negedge clk);on=0;
  repeat(13009)@(negedge clk);
  if(pending||transitions!=6||groups<12)$fatal(1,"incomplete transition coverage");
  $display("PASS v076_packet_gate transition_count=%0d groups=%0d sample_checks=%0d max_gate_to_selection_cycles=%0d bound_cycles=10000",transitions,groups,checks,max_cycles);$finish;
 end
 initial begin #3000000;$fatal(1,"watchdog");end
endmodule
