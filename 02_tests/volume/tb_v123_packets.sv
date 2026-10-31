`timescale 1ns/1ps
module tb_v123_packets;
 reg clk=0;always #5 clk=~clk;reg rst=0,valid=0;
 reg [3:0]volume=10;reg signed[23:0]l=0,r=0;
 wire signed[23:0]pl,pr;wire pv;wire[11:0]x,y;wire hs,vs,de,fs;
 pcm_volume v(clk,rst,l,r,valid,volume,pl,pr,pv);
 video_timing #(.H_ACTIVE(1280),.H_FP(110),.H_SYNC(40),.H_BP(220),.V_ACTIVE(720),.V_FP(5),.V_SYNC(5),.V_BP(20))timing(clk,rst,x,y,hs,vs,de,fs);
 wire overflow;wire[9:0]ab,ag,ar;wire vp,ip,aux;wire gate=y[8];
 hdmi_audio_packets #(.GATE_ENABLE(1))packets(clk,rst,x,y,pl,pr,pv,gate,vp,ip,aux,ab,ag,ar,hs,vs,overflow);
 integer count=0,acc=0,seed=8997,wp=0,rp=0,checks=0,muted=0,sounded=0,zeros=0;
 reg[47:0]queue[0:2047],expected[0:3];reg pop;integer j;
 always @(negedge clk)if(rst)begin
  valid=0;acc=acc+48000;
  if(acc>=74250000)begin
   acc=acc-74250000;valid=1;l=$random(seed);r=$random(seed);
   volume=count<300?10:(count<600?0:(count<900?5:10));
   if(count>=900&&count<950)begin l=0;r=0;end
   count++;
  end
 end
 always @(posedge clk)if(rst)begin
  pop=packets.pop4;
  if(pop)begin
   if(rp+4>wp)$fatal(1,"HDMI popped unpublished sample");
   for(j=0;j<4;j++)expected[j]=gate?queue[rp+j]:48'd0;
   rp+=4;
  end
  if(packets.push)begin queue[wp]={pr,pl};wp++;if(pl==0&&pr==0)zeros++;end
  #1;
  if(pop)begin
   if(packets.header[7:0]!=8'h02||packets.s0[47:0]!==expected[0]||packets.s1[47:0]!==expected[1]||packets.s2[47:0]!==expected[2]||packets.s3[47:0]!==expected[3])$fatal(1,"volume->HDMI packet sample order/gate");
   checks++;if(gate)sounded++;else muted++;
  end
  if(overflow)$fatal(1,"volume caused HDMI FIFO overflow");
 end
 initial begin
  #23;rst=1;wait(count>=1300);repeat(3000)@(negedge clk);
  if(checks<300||muted<20||sounded<20||zeros<80)$fatal(1,"coverage: packets%0d muted%0d sounded%0d zeros%0d",checks,muted,sounded,zeros);
  $display("PASS active volume->HDMI %0d ordered stereo packets,48k cadence,11-level pipeline,mute,pause-silence,picture gate,zero overflow",checks);$finish;
 end
 initial begin #23000000;$fatal(1,"timeout");end
endmodule
