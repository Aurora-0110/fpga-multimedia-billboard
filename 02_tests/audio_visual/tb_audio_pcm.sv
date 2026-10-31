`timescale 1ns/1ps
module tb_audio_pcm;
reg clk=0;always #5 clk=~clk;reg rst=0;reg[1:0]track=0;
reg ext=0,ev=0,ee=0;reg signed[23:0]el=0,er=0;
wire signed[23:0]pl,pr;wire valid,epoch,bc,lc,sd;
audio_pcm_frontend #(.DEMO_BEAT_SAMPLES(8))d(clk,rst,4'd10,1'b0,track,ext,el,er,ev,ee,pl,pr,valid,epoch,bc,lc,sd);
wire[11:0]x,y;wire hs,vs,de,fs;video_timing #(.H_ACTIVE(1280),.H_FP(110),.H_SYNC(40),.H_BP(220),.V_ACTIVE(720),.V_FP(5),.V_SYNC(5),.V_BP(20))vt(clk,rst,x,y,hs,vs,de,fs);
wire gate=y[3];wire overflow;wire[9:0]ab,ag,ar;wire vp,ip,aux;
hdmi_audio_packets #(.GATE_ENABLE(1))packets(clk,rst,x,y,pl,pr,valid,gate,vp,ip,aux,ab,ag,ar,hs,vs,overflow);
// Independent pin-level I2S deserializer: payload starts one rising edge
// AFTER each LR transition, 24 bits MSB first, then ignore seven pad bits.
reg last_lr=1;integer bits=0;reg[23:0]shift=0,left=0;
reg[47:0]serial_queue[0:1023];integer sw=0,sr=0,samples=0,epochs=0,negatives=0,changes=0;
always @(posedge bc)if(rst)begin
 if(lc!=last_lr)begin bits=0;shift=0;last_lr=lc;end
 else if(bits<24)begin
  shift={shift[22:0],sd};bits++;
  if(bits==24)begin
   if(!lc)left=shift;else begin
    if(left!==shift)$fatal(1,"stereo channels differ");
    serial_queue[sw]={shift,left};sw++;
   end
  end
 end
end
reg [47:0]fifo[0:4095];integer wp=0,rp=0,packet_checks=0,muted=0,sounded=0;
reg pop;reg[47:0]expected[0:3];integer j;reg old_gate;
reg signed[23:0]sl,srr;reg[23:0]last=0;
always @(posedge clk)if(rst)begin
 if(valid)begin
  if(!ext)begin
   if(sr>=sw)$fatal(1,"unissued serial frame");
   sl=serial_queue[sr][23:0];srr=serial_queue[sr][47:24];sr++;
   if(pl!==(sl>>>2)||pr!==(srr>>>2))$fatal(1,"24bit serial gain mismatch");
   if(pl[23])negatives++;
   if(pl!=last)changes++;last=pl;
  end else if(pl!==(el>>>2)||pr!==(er>>>2))$fatal(1,"external PCM contract mismatch");
  samples++;if(epoch)epochs++;
 end
 pop=packets.pop4;old_gate=gate;
 if(pop)for(j=0;j<4;j++)expected[j]=old_gate?fifo[rp+j]:48'd0;
 if(packets.push)begin fifo[wp]={pr,pl};wp++;end
 if(pop)rp+=4;
 #1;
 if(pop)begin
  if(packets.header[7:0]!=8'h02||packets.s0[47:0]!==expected[0]||packets.s1[47:0]!==expected[1]||packets.s2[47:0]!==expected[2]||packets.s3[47:0]!==expected[3])$fatal(1,"HDMI sample/gate mismatch");
  packet_checks++;if(old_gate)sounded++;else muted++;
 end
 if(overflow)$fatal(1,"audio overflow");
end
task tick(input integer n);repeat(n)@(negedge clk);endtask
integer i,start;
initial begin
 tick(3);rst=1;
 for(i=0;i<4;i++)begin track=i;start=samples;wait(samples>=start+96);end
 if(epochs!=3||negatives<80||changes<300||sounded<10||muted<10)$fatal(1,"insufficient demo coverage ep%d neg%d changed%d sound%d mute%d",epochs,negatives,changes,sounded,muted);
 // Existing 24bit contract accepts future TF PCM, without implementing TF audio.
 @(negedge clk);ext=1;ee=1;el=-24'sd8388607;er=24'sd4194305;ev=1;
 tick(1);ee=0;ev=0;tick(5);
 if(epochs!=4)$fatal(1,"external epoch not forwarded");
 for(i=0;i<8;i++)begin el=-24'sd4097+i;er=24'sd4095-i;ev=1;tick(1);ev=0;tick(1546);end
 if(epoch)$fatal(1,"epoch stuck");
 $display("PASS PCM I2S24 independent decode/gain/demo_tracks/external_hook samples=%0d epochs=%0d HDMI_packets=%0d sounded=%0d muted=%0d",samples,epochs,packet_checks,sounded,muted);$finish;
end
initial begin #20000000;$fatal(1,"audio watchdog");end
endmodule
