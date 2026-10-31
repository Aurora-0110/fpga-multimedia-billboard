`timescale 1ns/1ps
module tb_public_logo;
 reg clk=0;always #5 clk=~clk;
 // Start away from the first address so combinational event scheduling is exercised.
 reg[6:0]x=127;reg[5:0]y=63;
 wire[1:0]a,b,c;
 official_logo a0(x,y,a);
 official_logo_sync b0(clk,x,y,b);
 official_logo_compact_sync c0(clk,x,y,c);
 integer xx,yy,checks=0,visible=0;
 reg[1:0]expected;
 initial begin
  for(yy=0;yy<64;yy=yy+1)for(xx=0;xx<128;xx=xx+1)begin
   @(negedge clk);x=xx;y=yy;#1;expected=a;
   if(xx>=112||yy>=56)if(expected!==0)$fatal(1,"padding not clear");
   @(posedge clk);#1;
   if(b!==expected||c!==expected)$fatal(1,"logo equivalence/latency x=%d y=%d a=%d b=%d c=%d",xx,yy,expected,b,c);
   if(expected!=0)visible=visible+1;checks=checks+1;
  end
  if(visible==0)$fatal(1,"all transparent");
  $display("PASS public logo all=%0d visible=%0d combinational/sync/compact equivalence, padded coordinates, one-clock latency",checks,visible);$finish;
 end
endmodule
