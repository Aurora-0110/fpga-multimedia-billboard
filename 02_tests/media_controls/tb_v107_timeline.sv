`timescale 1ns/1ps
module tb_v107_timeline #(parameter SPM=3,MAX_MS=60005);
 reg clk=0;always #5 clk=~clk;reg rst=0,valid=0,en=0,epoch=0;
 wire [31:0] ms;wire [15:0] bcd;wire [2:0] index;wire active,started,tick;
 pcm_subtitle_timeline #(.SAMPLES_PER_MS(SPM))d(clk,rst,valid,en,epoch,ms,bcd,index,active,started,tick);
 integer samples=0,refms=0,checks=0,n,secs,idx,j;reg refstarted=0;reg [15:0] refbcd;reg refactive;reg reftick;
 integer starts[0:5];integer ends[0:5];
 always @(posedge clk)begin
  if(!rst||epoch)begin samples=0;refms=0;refstarted=0;reftick=0;end
  else begin
   reftick=0;
   if(valid&&en)begin samples++;refstarted=1;if(samples%SPM==0)begin refms++;reftick=1;end end
  end
  if(rst)begin
   secs=refms/1000;
   refbcd=((secs/600)%10)*4096+((secs/60)%10)*256+((secs/10)%6)*16+secs%10;
   idx=0;for(j=0;j<5;j++)if(refms>=ends[j])idx=j+1;
   refactive=refstarted&&refms>=starts[idx]&&refms<ends[idx];
   #1;
   if(ms!==refms||bcd!==refbcd||index!==idx||active!==refactive||started!==refstarted||tick!==reftick)
    $fatal(1,"timeline sample=%0d expectms=%0d ms=%0d bcd=%h/%h cue=%0d/%0d active=%b/%b tick=%b/%b",samples,refms,ms,bcd,refbcd,index,idx,active,refactive,tick,reftick);
   checks++;
  end
 end
 initial begin
  starts[0]=0;ends[0]=2000;starts[1]=2200;ends[1]=5000;starts[2]=5500;ends[2]=8000;
  starts[3]=8500;ends[3]=11000;starts[4]=11500;ends[4]=14500;starts[5]=15000;ends[5]=16000;
  #23;rst=1;
  for(n=0;n<MAX_MS*SPM;n++)begin
   @(negedge clk);valid=1;en=1;
   if(n%137==0)begin @(negedge clk);valid=0;repeat(2)@(negedge clk);valid=1;end
   if(n%113==0)begin @(negedge clk);en=0;repeat(2)@(negedge clk);en=1;end
  end
  @(negedge clk);valid=0;en=0;repeat(20)@(negedge clk);
  // Same-cycle epoch/valid discards boundary sample; next file restarts 00:00.
  epoch=1;valid=1;en=1;@(negedge clk);epoch=0;
  repeat(SPM*2300)@(negedge clk);valid=0;en=0;repeat(10)@(negedge clk);
  if(ms<2200||index!=1||!active)$fatal(1,"epoch and second cue replay");
  $display("PASS v107 timeline SPM=%0d: %0d checked cycles, exact valid-sample timing incl silence, sparse valid, pause, exclusive endpoints/gaps/end, BCD minute carry, epoch-valid priority",SPM,checks);$finish;
 end
 initial begin #100000000;$fatal(1,"timeline timeout");end
endmodule
