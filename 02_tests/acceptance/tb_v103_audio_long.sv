`timescale 1ns/1ps
// Nominal 48k/74.25M sample schedule; independent FIFO/IEC60958 sample oracle.
// This checks packet selection payload, not a replacement for native TMDS/BCH tests.
module tb_v103_audio_long;
 reg clk=0;always #5 clk=~clk;reg rst=0;wire[11:0]x,y;wire hs,vs,de,fs;
 video_timing #(.H_ACTIVE(1280),.H_FP(110),.H_SYNC(40),.H_BP(220),.V_ACTIVE(720),.V_FP(5),.V_SYNC(5),.V_BP(20)) vt(clk,rst,x,y,hs,vs,de,fs);
 reg[23:0]l=0,r=0;reg valid=0,gate=1;wire overflow,vp,ip,aux;wire[9:0]ab,ag,ar;
 hdmi_audio_packets #(.GATE_ENABLE(1)) d(clk,rst,x,y,l,r,valid,gate,vp,ip,aux,ab,ag,ar,hs,vs,overflow);
 localparam N=8192;reg[47:0]q[0:N+16];integer wr=0,rd=0,fi=0,packets=0,muted=0,sounded=0,simultaneous=0,nulls=0;
 reg auto_schedule=1;integer phase=0,acc=0,issued=0,i,j,accepts=0;reg[47:0]e[0:3];reg pop,was_null,oldgate;reg[23:0]eh;
 function[23:0]value;input integer n;input bit right;reg[31:0]mix;begin
  mix=(n*32'h0019660d+32'h3c6ef35f)^(right?32'h005ac389:32'h00310fe2);
  case(n%16)0:value=0;1:value=24'h800000;2:value=24'h7fffff;3:value=24'hffffff;4:value=1;
   5:value=right?24'h0000ff:24'h00ff00;default:value=mix[23:0];endcase
 end endfunction
 function cs;input integer idx;input bit right;begin
  cs=(idx==2)||(idx==25)||(idx==32)||(idx==33)||(idx==35)||(right?(idx==21):(idx==20));
 end endfunction
 function[55:0]sub;input[47:0]v;input integer idx;reg cl,cr;begin cl=cs(idx,0);cr=cs(idx,1);
  sub[47:0]=v;sub[49:48]=0;sub[50]=cl;sub[51]=^{v[23:0],cl};
  sub[53:52]=0;sub[54]=cr;sub[55]=^{v[47:24],cr};end endfunction
 always @(negedge clk)if(rst&&phase==0&&auto_schedule)begin
  valid=0;acc=acc+48000;
  if(acc>=74250000)begin acc=acc-74250000;
   if(issued<N)begin l=value(issued,0);r=value(issued,1);gate=((issued/97)%3)!=1;valid=1;issued++;end
  end
 end
 always @(posedge clk)if(rst&&phase==0)begin
  if(d.count!==wr-rd)$fatal(1,"queue count mismatch ref=%d dut=%d",wr-rd,d.count);
  pop=(x==1280)&&!d.acr_pending&&((wr-rd)>=4);
  if(d.pop4!==pop)$fatal(1,"group scheduling mismatch");
  oldgate=gate;was_null=(x==1280)&&!pop&&!d.acr_pending&&!d.avi_pending&&!d.info_pending;
  if(pop)begin
   for(j=0;j<4;j++)e[j]=oldgate?q[rd+j]:48'd0;
   eh=(fi==0?24'h100000:0)|24'h000f02;
   rd=rd+4;if(valid)simultaneous++;
  end
  if(valid)begin
   if(!d.push)$fatal(1,"nominal PCM rejected");q[wr]={r,l};wr++;
  end
  #1;
  if(pop)begin
   if(d.header!==eh||d.s0!==sub(e[0],fi)||d.s1!==sub(e[1],fi+1)||d.s2!==sub(e[2],fi+2)||d.s3!==sub(e[3],fi+3))
    $fatal(1,"stereo payload/parity/channel-status/frame-index/gate packet=%d fi=%d",packets,fi);
   fi=(fi+4)%192;packets++;if(oldgate)sounded++;else muted++;
  end
  if(was_null)begin nulls++;if(d.header!==0||d.s0!==0||d.s1!==0||d.s2!==0||d.s3!==0)$fatal(1,"stale audio in empty/null packet");end
  if(overflow)$fatal(1,"nominal overflow");
 end
 task tick(input integer n);repeat(n)@(negedge clk);endtask
 initial begin
  tick(4);rst=1;wait(issued==N);tick(8000);
  if(wr!=N||rd!=N||packets!=N/4||muted<100||sounded<100||nulls<100)
   $fatal(1,"incomplete nominal coverage wr%d rd%d packets%d mute%d sound%d simultaneous%d null%d",wr,rd,packets,muted,sounded,simultaneous,nulls);
  // Natural nominal phase has no push/pop collision. Construct one explicitly.
  auto_schedule=0;valid=0;
  while(x!=1000)tick(1);
  for(i=0;i<4;i++)begin l=value(N+i,0);r=value(N+i,1);valid=1;tick(1);end
  valid=0;while(x!=1280)tick(1);
  l=value(N+4,0);r=value(N+4,1);valid=1;tick(1);valid=0;tick(100);
  if(simultaneous<1||wr!=N+5||rd!=N+4||d.count!=1)$fatal(1,"explicit atomic push/pop coverage");
  // Deliberately illegal producer flood; must latch overflow, not wrap count.
  phase=1;rst=0;valid=0;tick(3);force x=0;force y=0;rst=1;tick(2);
  for(i=0;i<24;i++)begin valid=1;l=value(i,0);r=value(i,1);tick(1);end
  valid=0;tick(3);if(!overflow||d.count!=8)$fatal(1,"flood not bounded/sticky");
  tick(10);if(!overflow)$fatal(1,"overflow not sticky");
  rst=0;tick(3);if(overflow||d.count!=0||d.wp!=0||d.rp!=0)$fatal(1,"reset does not clear overflow/queue");
  release x;release y;rst=1;tick(4000);
  if(overflow||d.count!=0||d.header[7:0]==8'h02)$fatal(1,"reset replayed stale PCM");
  $display("PASS v103_audio_long samples=%0d packets=%0d sounded=%0d muted=%0d simultaneous_push_pop=%0d null_packets=%0d stereo24/IEC60958/parity/wrap/mute/no-stale/flood/reset",wr,packets,sounded,muted,simultaneous,nulls);$finish;
 end
 initial begin #300000000;$fatal(1,"audio long watchdog");end
endmodule
