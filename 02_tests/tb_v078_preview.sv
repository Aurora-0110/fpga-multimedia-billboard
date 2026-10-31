`timescale 1ns/1ps
// Raster preview of real osd_layers RTL only, not SDRAM/HDMI or physical output.
module tb_v078_preview;
reg clk=0,rst=0,de=0,pv=0;always #5 clk=~clk;
reg [11:0] x=0,y=0;reg [23:0] rgb=0;
wire [11:0] ox,oy;wire [23:0] out;wire od,oh,ov,op;
reg [23:0] bg[0:921599];integer f,n=0,i;reg [4095:0] source,dest;
osd_layers d(.clk(clk),.rst_n(rst),.x(x),.y(y),.rgb(rgb),.de(de),.hs(1'b1),.vs(1'b1),.picture_visible(pv),.auto_mode(1'b1),.image_index(2'd1),.x_out(ox),.y_out(oy),.rgb_out(out),.de_out(od),.hs_out(oh),.vs_out(ov),.picture_visible_out(op));
always @(posedge clk)begin
 #0.001;
 if(od)begin
  if(ox!==n%1280||oy!==n/1280)$fatal(1,"preview coordinate mismatch");
  $fdisplay(f,"%06x",out);n=n+1;
 end
end
initial begin
 if(!$value$plusargs("SOURCE=%s",source)||!$value$plusargs("DEST=%s",dest))$fatal(1,"paths missing");
 $readmemh(source,bg);f=$fopen(dest,"w");
 repeat(4)@(negedge clk);rst=1;
 for(i=0;i<921600;i=i+1)begin
  @(negedge clk);x=i%1280;y=i/1280;rgb=bg[i];de=1;pv=x>=320&&x<960&&y>=120&&y<600;
 end
 @(negedge clk);de=0;pv=0;repeat(5)@(negedge clk);
 if(n!=921600)$fatal(1,"preview missing pixels");
 $fclose(f);$display("PASS preview pixels=%0d",n);$finish;
end
endmodule
