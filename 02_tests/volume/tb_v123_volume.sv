`timescale 1ns/1ps
module tb_v123_volume;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,valid=0;reg [3:0]level=10;reg signed[23:0]l=0,rr=0;
 wire signed[23:0]ol,orr;wire ov;
 pcm_volume d(clk,rst,l,rr,valid,level,ol,orr,ov);
 integer gain=256,target,n,lev,count=0,seed=123091;
 longint signed pl,pr;reg signed[23:0]el,er;
 function integer goal(input integer v);begin case(v)
  0:goal=0;1:goal=26;2:goal=51;3:goal=77;4:goal=102;5:goal=128;
  6:goal=154;7:goal=179;8:goal=205;9:goal=230;default:goal=256;endcase end endfunction
 task sample(input bit v,input integer ll,rl,lv);begin
  @(negedge clk);valid=v;l=ll;rr=rl;level=lv;
  target=goal(lv);
  if(v)begin
   if(gain<target)gain++;else if(gain>target)gain--;
   pl=$signed(l);pr=$signed(rr);pl=(pl*gain)>>>10;pr=(pr*gain)>>>10;el=pl;er=pr;
  end
  @(posedge clk);#1;
  if(ov!==v)$fatal(1,"valid latency");
  if(v&&(ol!==el||orr!==er))$fatal(1,"gain mismatch sample%0d gain%0d L%0d expected%0d R%0d expected%0d",count,gain,ol,el,orr,er);
  if(d.gain_q8!==gain)$fatal(1,"invalid cycles must not progress ramp");
  if(v&&(ol>2097151||ol< -2097152||orr>2097151||orr< -2097152))$fatal(1,"output ceiling");
  count++;
 end endtask
 initial begin
  #13;rst=1;
  for(n=0;n<512;n++)sample(1,$random(seed),$random(seed),10);
  for(lev=0;lev<=10;lev++)for(n=0;n<300;n++)sample(n%7!=0,n%2?-8388608:8388607,n%2?8388607:-8388608,lev);
  for(n=0;n<12000;n++)sample(($random(seed)&3)!=0,$random(seed),$random(seed),$unsigned($random(seed))%11);
  for(n=0;n<260;n++)sample(1,8388607,-8388608,0);
  if(ol||orr)$fatal(1,"mute not exact");
  @(negedge clk);rst=0;#1;gain=256;
  if(ov||ol||orr)$fatal(1,"reset must flush PCM");rst=1;
  sample(1,-8388608,8388607,10);
  if(ol!==-24'sd2097152||orr!==24'sd2097151)$fatal(1,"reset default mismatch");
  $display("PASS volume %0d exact stereo numeric checks,11levels,consecutive-valid,gaps,random,ramps,mute,reset",count);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
