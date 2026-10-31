`timescale 1ns/1ps
module tb_v116_arbiter_gap;
 reg clk=0,rst=0;always #10 clk=~clk;
 reg ar=1,br=1,urgent=1,areq=0,breq=0;
 wire ard,adone,brd,bdone,hreq,active,owner;wire[31:0]hl;
 reg hr=1,hd=0;integer hostwait=0,started=0,ended=0,gap=0,phase=0;
 integer ac=0,bc=0,phase_b=0,snapshot;reg ab=0,bb=0;
 `ifdef BASELINE
 media_sd_arbiter_v114
 `else
 media_sd_arbiter
 `endif
 dut(.clk(clk),.rst_n(rst),.bmp_reset_n(br),.aud_reset_n(ar),.audio_urgent(urgent),
 .b_req(breq),.b_lba(32'd900),.b_ready(brd),.b_done(bdone),.b_valid(),.b_error(),
 .a_req(areq),.a_lba(32'd100),.a_ready(ard),.a_done(adone),.a_valid(),.a_error(),
 .h_req(hreq),.h_lba(hl),.h_ready(hr),.h_done(hd),.h_valid(1'b0),.h_error(4'd0),.active(active),.owner_audio(owner));
 always @(posedge clk)if(rst)begin
  if(hreq)begin
   if(!hr)$fatal(1,"host overlap");hr<=0;hd<=0;hostwait<=20;
   if(owner)ac=ac+1;else begin bc=bc+1;if(phase==0)phase_b=phase_b+1;end
  end else if(!hr)begin if(hostwait==0)begin hr<=1;hd<=1;end else hostwait<=hostwait-1;end
 end
 always @(negedge clk)if(rst)begin
  areq=0;breq=0;
  if(adone&&ab)begin ab=0;ended=ended+1;gap=12;end
  if(gap>0)gap=gap-1;
  if(phase==0&&started<8&&!ab&&ard&&gap==0)begin areq=1;ab=1;started=started+1;end
  if(bdone&&bb)bb=0;
  if(!bb&&brd)begin breq=1;bb=1;end
 end
 initial begin
  repeat(4)@(negedge clk);rst=1;wait(ended==8);@(negedge clk);phase=1;
  `ifdef BASELINE
  if(phase_b==0)$fatal(1,"old scheduler gap not exposed");
  `else
  if(phase_b!=0)$fatal(1,"urgent audio sector bubble still grants BMP: %0d",phase_b);
  `endif
  snapshot=bc;repeat(130)@(negedge clk);
  if(bc<snapshot+2)$fatal(1,"bounded reservation deadlocked BMP when urgent but no audio requests");
  // A disabled/reset audio client must not reserve the bus.
  ar=0;snapshot=bc;repeat(90)@(negedge clk);
  if(bc<snapshot+3)$fatal(1,"reset audio client delayed BMP");
  $display("PASS arbiter-gap audio=%0d interposed_BMP=%0d total_BMP=%0d finite_grace_no_request_and_client_reset=PASS",ac,phase_b,bc);$finish;
 end
 initial begin #200000;$fatal(1,"unit timeout");end
endmodule
