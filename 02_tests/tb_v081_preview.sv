`timescale 1ns/1ps
// Raster preview of real picture_adjust + osd_layers RTL; not SDRAM/HDMI/hardware.
module tb_v081_preview;
reg clk=0,rst=0,de=0,pv=0;always #5 clk=~clk;
reg [11:0] x=0,y=0;reg [23:0] rgb=0;
wire [11:0] ox,oy;wire [23:0] out;wire od,oh,ov,op;
reg [23:0] bg[0:921599];integer f,n=0,i;reg [4095:0] source,dest;
wire [11:0] ax,ay;wire [23:0] ar;wire ad,ah,av,ap;wire [1:0] ai;
picture_adjust adjust(.clk(clk),.rst_n(rst),.rgb(rgb),.x(x),.y(y),.de(de),.hs(1'b1),.vs(1'b1),.picture_visible(pv),.apply_pixel(pv),.image_index(2'd1),.brightness(8'sd16),.contrast_q2(3'd5),.rgb_out(ar),.x_out(ax),.y_out(ay),.de_out(ad),.hs_out(ah),.vs_out(av),.picture_visible_out(ap),.image_index_out(ai));
osd_layers #(.SHOW_PARAMS(1)) d(.clk(clk),.rst_n(rst),.x(ax),.y(ay),.rgb(ar),.de(ad),.hs(ah),.vs(av),.picture_visible(ap),.auto_mode(1'b1),.image_index(ai),.brightness(8'sd16),.contrast_q2(3'd5),.edit_field(2'd2),.x_out(ox),.y_out(oy),.rgb_out(out),.de_out(od),.hs_out(oh),.vs_out(ov),.picture_visible_out(op));
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
 @(negedge clk);de=0;pv=0;repeat(14)@(negedge clk);
 if(n!=921600)$fatal(1,"preview missing pixels");
 $fclose(f);$display("PASS preview pixels=%0d",n);$finish;
end
endmodule
