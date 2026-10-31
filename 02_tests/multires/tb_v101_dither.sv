`timescale 1ns/1ps
// Independent /255 oracle, all 256 values at all 16 spatial phases.
module tb_v101_dither;
 parameter DITHER=1;
 localparam W=64,H=64,N=W*H,NB=N/16;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,enable=0,pixel_valid=0,source_done=0,source_ok=0;
 reg [23:0]pixel_rgb=0;reg[15:0]pixel_x=0,pixel_y=0;
 reg[7:0]source_error=0;reg req_ack=0;
 wire pixel_ready,req_valid,done;wire[18:0]req_addr;wire[127:0]req_data;
 wire[7:0]error_code;wire[31:0]pixel_count,burst_count;
 bmp_pixel_packer #(.WIDTH(W),.HEIGHT(H),.DITHER_ENABLE(DITHER)) dut(.*);
 integer td,sent,cycles,accepted=0,delay_left=0,stall_samples=0,last_wait=0;
 integer value,phase,t,mapped_y,burst_x,lane;reg waiting=0,held_req=0,held_in=0;
 reg[146:0]last_req;reg[31:0]rng=32'h142857ad;
 function[31:0]prng;input[31:0]v;reg[31:0]z;begin z=v^(v<<13);z=z^(z>>17);prng=z^(z<<5);end endfunction
 function integer rank;input integer x,y;begin
  case((y%4)*4+x%4)
   0:rank=0;1:rank=8;2:rank=2;3:rank=10;
   4:rank=12;5:rank=4;6:rank=14;7:rank=6;
   8:rank=3;9:rank=11;10:rank=1;11:rank=9;
   12:rank=15;13:rank=7;14:rank=13;15:rank=5;
  endcase
 end endfunction
 function[23:0]pattern;input integer x,y;integer v;reg[7:0]r,g,b;
  begin v=(y/4)*16+x/4;r=v;g=255-v;b=(v*73)&255;pattern={r,g,b};end
 endfunction
 function[7:0]oracle;input integer x,y;reg[23:0]rgb;integer th,r,g,b;
  begin rgb=pattern(x,y);th=rank(x,y)*16+8;
   if(DITHER)begin r=(rgb[23:16]*7+th)/255;g=(rgb[15:8]*7+th)/255;b=(rgb[7:0]*3+th)/255;end
   else begin r=rgb[23:21];g=rgb[15:13];b=rgb[7:6];end
   oracle={r[2:0],g[2:0],b[1:0]};
  end
 endfunction
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin req_ack<=0;accepted=0;waiting=0;delay_left=0;held_req=0;stall_samples=0;last_wait=0;end
  else begin
   req_ack<=0;
   if(held_req&&{req_valid,req_addr,req_data}!=={1'b1,last_req})$fatal(1,"request changed while awaiting registered ack");
   held_req=req_valid&&!req_ack;last_req={req_addr,req_data};
   if(req_valid&&!req_ack)begin
    stall_samples=stall_samples+1;
    if(!waiting)begin
     waiting=1;delay_left=(accepted==NB-1)?80:((accepted==2)?40:accepted%7);
    end else if(delay_left>0)begin
     delay_left=delay_left-1;
     if(accepted==NB-1)begin last_wait=last_wait+1;if(done)$fatal(1,"done before final acceptance");end
    end else begin req_ack<=1;waiting=0;end
   end
   if(req_valid&&req_ack)begin
    mapped_y=td?accepted/(W/16):H-1-accepted/(W/16);burst_x=(accepted%(W/16))*16;
    if(req_addr!==mapped_y*(W/16)+burst_x/16)$fatal(1,"wrong addr got=%0d burst=%0d y=%0d",req_addr,accepted,mapped_y);
    for(lane=0;lane<16;lane=lane+1)
     if(req_data[lane*8+:8]!==oracle(burst_x+lane,mapped_y))$fatal(1,"dither mismatch mode=%0d td=%0d burst=%0d lane=%0d got=%h expected=%h",DITHER,td,accepted,lane,req_data[lane*8+:8],oracle(burst_x+lane,mapped_y));
    accepted=accepted+1;if(accepted>NB)$fatal(1,"duplicate burst");
   end
   if(error_code)$fatal(1,"unexpected error %h",error_code);
   if(done&&(accepted!=NB||pixel_count!=N||burst_count!=NB))$fatal(1,"premature done");
  end
 end
 task drive_until;input integer limit;begin
  sent=0;cycles=0;held_in=0;
  while(sent<limit)begin
   if(!held_in)begin
    rng=prng(rng);pixel_valid=rng[2:0]!=0;
    pixel_x=sent%W;pixel_y=td?sent/W:H-1-sent/W;pixel_rgb=pattern(pixel_x,pixel_y);
   end
   @(posedge clk);held_in=pixel_valid&&!pixel_ready;
   if(pixel_valid&&pixel_ready)sent=sent+1;
   cycles=cycles+1;@(negedge clk);
   if(cycles>100000)$fatal(1,"pixel drive timeout");
  end
  pixel_valid=0;
 end endtask
 initial begin
  if(!$value$plusargs("TD=%d",td))$fatal(1,"TD missing");
  // Exhaust both exact quantizers, independently using integer division.
  for(value=0;value<256;value=value+1)for(phase=0;phase<16;phase=phase+1)begin
   t=phase*16+8;
   if(dut.quant3(value,t)!==(value*7+t)/255)$fatal(1,"quant3 exhaustive value=%0d phase=%0d",value,phase);
   if(dut.quant2(value,t)!==(value*3+t)/255)$fatal(1,"quant2 exhaustive value=%0d phase=%0d",value,phase);
  end
  repeat(3)@(negedge clk);rst_n=1;enable=1;
  drive_until(48);repeat(2)@(negedge clk);
  if(!req_valid||req_ack)$fatal(1,"reset test did not interrupt pending burst");
  rst_n=0;enable=0;source_done=0;source_ok=0;repeat(3)@(negedge clk);
  if(req_valid||done||pixel_count||burst_count)$fatal(1,"reset failed to clear pending transaction");
  rst_n=1;enable=1;drive_until(N);source_done=1;source_ok=1;
  cycles=0;while(!done)begin @(negedge clk);cycles=cycles+1;if(cycles>2000)$fatal(1,"drain timeout");end
  if(accepted!=NB||last_wait!=80||stall_samples<100)$fatal(1,"incomplete stalls/drain evidence");
  repeat(12)begin @(negedge clk);if(req_valid||!done)$fatal(1,"extra request/nonsticky done");end
  $display("PASS dither mode=%0d td=%0d pixels=%0d bursts=%0d exact_quantizer_comparisons=8192 reset_pending_ack hold_stability final_ack80 black_white_endpoints",DITHER,td,N,accepted);$finish;
 end
 initial begin #3000000;$fatal(1,"watchdog");end
endmodule
