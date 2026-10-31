`timescale 1ns/1ps
// V129: independent stereo-sample oracle and all half-open boundaries in both ROM banks.
module tb_v129_caption_player;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,ready=0,consumed=0,first=0,finished=0;reg[1:0]choice=0;reg[7:0]err=0;
 wire[31:0]position;wire active;wire[10:0]offset;wire[4:0]length;wire[5:0]index;
 pcm_caption_player d(clk,rst,choice,ready,consumed,first,finished,err,position,active,offset,length,index);
 reg[95:0]cues[0:127];reg[2047:0]path;integer count,music_count,third_count,track,local_count,base,i,n,checks=0,pulses=0,holds=0;
 reg[31:0]expected_position=0;reg[1:0]old_choice=0;reg monitor=0;reg[31:0]saved;
 always @(posedge clk)begin
  if(!rst)begin expected_position=0;old_choice=0;end
  else begin
   if((choice!=1&&choice!=3)||!ready||finished||err!=0||choice!=old_choice)expected_position=0;
   else if(first&&consumed)expected_position=1;
   else if(consumed&&expected_position!=32'hffffffff)expected_position=expected_position+1;
   old_choice=choice;
   if(consumed)pulses=pulses+1;else holds=holds+1;
  end
  #1;
  if(monitor&&position!==expected_position)$fatal(1,"sample mismatch choice=%0d actual=%0d expected=%0d",choice,position,expected_position);
  if(monitor&&(!ready||(choice!=1&&choice!=3)||finished||err!=0)&&active)$fatal(1,"stale caption on inactive session/AD/demo");
  checks=checks+1;
 end
 task ticks(input integer k);begin repeat(k)@(negedge clk);end endtask
 task seek(input[31:0]p);begin
  @(negedge clk);consumed=0;first=0;d.sample_position=p;expected_position=p;ticks(8*count+20);
 end endtask
 task check_cue(input integer c,input bit on);begin
  if(index!==c||active!==on||offset!==cues[base+c][31:21]||length!==cues[base+c][20:16])
   $fatal(1,"choice=%0d cue=%0d pos=%0d active=%b expected=%b index=%0d offset=%0d length=%0d",choice,c,position,active,on,index,offset,length);
 end endtask
 task restart(input[1:0]which);begin
  choice=0;ready=0;consumed=0;first=0;finished=0;err=0;ticks(4);
  choice=which;ready=1;ticks(15);consumed=1;first=1;ticks(1);consumed=0;first=0;ticks(8*count+20);
 end endtask
 initial begin
  if(!$value$plusargs("CUES=%s",path)||!$value$plusargs("COUNT=%d",count)||!$value$plusargs("MUSIC_COUNT=%d",music_count)||!$value$plusargs("THIRD_COUNT=%d",third_count))$fatal(1,"args");
  $readmemh(path,cues,0,count-1);ticks(4);rst=1;monitor=1;
  for(track=1;track<=3;track=track+2)begin
   base=track==1?0:music_count;local_count=track==1?music_count:third_count;
   ready=1;choice=track;ticks(400);if(position!=0||active)$fatal(1,"prefill/keepalive advanced captions");
   first=1;consumed=1;ticks(1);consumed=0;first=0;ticks(20);
   for(n=0;n<18000;n=n+1)begin consumed=(n%11<3);ticks(1);end
   consumed=0;saved=position;ticks(1000);if(position!=saved)$fatal(1,"pause changed position");
   consumed=1;ticks(1);consumed=0;ticks(12);if(position!=saved+1)$fatal(1,"resume lost sample");
   for(i=0;i<local_count;i=i+1)begin
    restart(track);seek(cues[base+i][95:64]-1);
    if(i>0&&cues[base+i-1][63:32]==cues[base+i][95:64])check_cue(i-1,1);else check_cue(i,0);
    consumed=1;ticks(1);consumed=0;ticks(12);check_cue(i,1);
    seek(cues[base+i][63:32]-1);check_cue(i,1);
    consumed=1;ticks(1);consumed=0;ticks(14);
    if(i<local_count-1&&cues[base+i+1][95:64]==cues[base+i][63:32])check_cue(i+1,1);
    else if(active)$fatal(1,"end not exclusive/gap rendered");
   end
   err=8'ha3;ticks(3);if(position||active)$fatal(1,"fault not cleared");
   restart(track);finished=1;ticks(3);if(position||active)$fatal(1,"EOF not cleared");
   restart(track);ready=0;ticks(3);if(position||active)$fatal(1,"session not cleared");
   restart(track);seek(32'hfffffffe);consumed=1;ticks(3);consumed=0;ticks(3);
   if(position!==32'hffffffff||active||index!==local_count-1)$fatal(1,"overflow or wrong bank limit");
   choice=0;ticks(4);
  end
  // Direct MUSIC -> third -> AD -> MUSIC; stale previous-bank text never survives.
  base=0;restart(1);seek(cues[0][95:64]);check_cue(0,1);
  choice=3;#1;if(active)$fatal(1,"old MUSIC visible immediately after source change");ticks(12);
  if(position||active||offset!==cues[music_count][31:21])$fatal(1,"third bank source reset");
  first=1;consumed=1;ticks(1);first=0;consumed=0;ticks(12);base=music_count;
  seek(cues[base][95:64]);check_cue(0,1);
  choice=2;#1;if(active)$fatal(1,"AD stale third text");ticks(20);if(position||active)$fatal(1,"AD not clear");
  choice=1;ticks(20);if(position||active||offset!==0)$fatal(1,"MUSIC restore bank");
  $display("PASS v129 caption player checks=%0d real_events=%0d frozen=%0d cues=%0d tracks=1,3 direct_1_3_2_1 all_boundaries",checks,pulses,holds,count);$finish;
 end
 initial begin #5000000;$fatal(1,"watchdog player");end
endmodule
