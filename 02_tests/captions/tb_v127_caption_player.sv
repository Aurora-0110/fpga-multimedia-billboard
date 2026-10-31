`timescale 1ns/1ps
// Sample-count oracle plus accelerated endpoint injection (not a real-time audio simulation).
module tb_v127_caption_player;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,ready=0,consumed=0,first=0,finished=0;reg[1:0]choice=0;reg[7:0]err=0;
 wire[31:0]position;wire active;wire[10:0]offset;wire[4:0]length;wire[5:0]index;
 pcm_caption_player d(clk,rst,choice,ready,consumed,first,finished,err,position,active,offset,length,index);
 reg[95:0]cues[0:63];reg[2047:0]path;integer count,i,n,checks=0,pulses=0,holds=0;
 reg[31:0]expected_position=0;reg[1:0]old_choice=0;
 reg monitor=0;reg[31:0]seek_position;
 always @(posedge clk)begin
  if(!rst)begin expected_position=0;old_choice=0;end
  else begin
   if(choice!=1||!ready||finished||err!=0||choice!=old_choice)expected_position=0;
   else if(first&&consumed)expected_position=1;
   else if(consumed&&expected_position!=32'hffffffff)expected_position=expected_position+1;
   old_choice=choice;
   if(consumed)pulses=pulses+1;else holds=holds+1;
  end
  #1;
  if(monitor&&position!==expected_position)$fatal(1,"sample counter mismatch actual=%0d expected=%0d",position,expected_position);
  if(monitor&&(!ready||choice!=1||finished||err!=0)&&active)$fatal(1,"stale caption on inactive track/session");
  checks=checks+1;
 end
 task ticks(input integer k);begin repeat(k)@(negedge clk);end endtask
 task seek(input[31:0]p);begin
  @(negedge clk);consumed=0;first=0;d.sample_position=p;expected_position=p;
  ticks(8*count+20);
 end endtask
 task check_cue(input integer c,input bit on);begin
  if(index!==c||active!==on||offset!==cues[c][31:21]||length!==cues[c][20:16])
   $fatal(1,"cue c=%0d position=%0d active=%b expect=%b index=%0d offset=%0d length=%0d",c,position,active,on,index,offset,length);
 end endtask
 task restart;begin
  choice=0;ready=0;consumed=0;first=0;finished=0;err=0;ticks(4);
  choice=1;ready=1;ticks(15);consumed=1;first=1;ticks(1);consumed=0;first=0;ticks(8*count+20);
 end endtask
 initial begin
  if(!$value$plusargs("CUES=%s",path)||!$value$plusargs("COUNT=%d",count))$fatal(1,"args");$readmemh(path,cues,0,count-1);
  ticks(4);rst=1;monitor=1;ready=1;choice=1;ticks(400);
  if(position!=0||active)$fatal(1,"prefill/keepalive advanced captions");
  first=1;consumed=1;ticks(1);consumed=0;first=0;ticks(20);
  for(n=0;n<32000;n=n+1)begin
   // Irregular sample arrivals, true-zero samples and muted samples all count.
   consumed=(n%11<3);ticks(1);
  end
  consumed=0;seek_position=position;ticks(1000);
  if(position!=seek_position)$fatal(1,"pause changed position");
  consumed=1;ticks(1);consumed=0;ticks(12);
  if(position!=seek_position+1)$fatal(1,"resume lost sample");
  for(i=0;i<count;i=i+1)begin
   restart();seek(cues[i][95:64]-1);
   if(i>0&&cues[i-1][63:32]==cues[i][95:64])check_cue(i-1,1);else check_cue(i,0);
   // Narrow synchronous metadata lookup may take a few pixel clocks, far less than one stereo sample period.
   consumed=1;ticks(1);consumed=0;ticks(12);check_cue(i,1);
   seek(cues[i][63:32]-1);check_cue(i,1);
   consumed=1;ticks(1);consumed=0;ticks(14);
   if(i<count-1&&cues[i+1][95:64]==cues[i][63:32])check_cue(i+1,1);
   else if(active)$fatal(1,"end is not exclusive/gap rendered");
  end
  // Fault, EOF, source change and session reset clear position; unrelated picture/DFT states are absent by design.
  err=8'ha3;ticks(3);if(position!=0||active)$fatal(1,"fault not cleared");
  restart();finished=1;ticks(3);if(position||active)$fatal(1,"EOF not cleared");
  restart();choice=2;ticks(3);if(position||active)$fatal(1,"track2 stale");
  choice=3;ticks(3);if(position||active)$fatal(1,"track3 stale");
  restart();ready=0;ticks(3);if(position||active)$fatal(1,"session not cleared");
  restart();seek(32'hfffffffe);consumed=1;ticks(3);consumed=0;ticks(3);
  if(position!==32'hffffffff)$fatal(1,"counter overflow");
  $display("PASS v127 caption player count_checks=%0d real_events=%0d frozen_cycles=%0d cues=%0d all_half_open_endpoints_and_gaps",checks,pulses,holds,count);$finish;
 end
 initial begin #2000000;$fatal(1,"watchdog player");end
endmodule
