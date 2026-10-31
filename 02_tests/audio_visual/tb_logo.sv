`timescale 1ns/1ps
module tb_logo;
reg clk=0;always #5 clk=~clk;reg[6:0]x=127;reg[5:0]y=63;
wire[1:0]ref_pixel,out;official_logo old(x,y,ref_pixel);
official_logo_compact_sync d(clk,x,y,out);integer a,b,n=0;reg[1:0]want;
initial begin
 for(b=0;b<64;b++)for(a=0;a<128;a++)begin
  @(negedge clk);x=a;y=b;#1;want=ref_pixel;
  @(posedge clk);#1;if(out!==want)$fatal(1,"logo x%0d y%0d out%h ref%h",a,b,out,want);n++;
 end
 $display("PASS compact logo exhaustive coordinates=%0d unchanged palette/one-cycle latency",n);$finish;
end
endmodule
