`timescale 1ns/1ps
// On-the-fly oracle avoids a million-element expected RAM. Every output is checked.
module tb_full_scaler;
 localparam OW=1280,OH=720;
 reg clk=0,rst_n=0,start=0,in_valid=0,out_ready=0,top_down=0;
 always #5 clk=~clk;
 reg [15:0] src_width=0,src_height=0;reg [23:0] in_rgb=0;
 wire busy,done,error,in_ready,out_valid;wire [3:0] error_code;
 wire [23:0] out_rgb;wire [15:0] out_x,out_y;
 bilinear_stream_scaler #(.OUT_WIDTH(OW),.OUT_HEIGHT(OH)) dut(.*);
 integer w,h,td,sent=0,received=0,cycles=0,file_y,x0,x1,y0,y1,fx,fy,dx,dy,i,shift;
 integer a,b,c,d,v,last_input=-1;reg [23:0] expect_rgb;reg stalled=0;reg [55:0] held;
 function [23:0] pattern(input integer x,y);
  begin pattern={8'((x*37+y*13+((x/3+y/5)%2)*255)&255),8'((x*7+y*53+(x*y)%251)&255),8'((x*91+y*19+67)&255)};end
 endfunction
 function [23:0] source_pixel(input integer x,r);
  begin source_pixel=pattern(x,td?r:h-1-r);end
 endfunction
 initial begin
  if(!$value$plusargs("W=%d",w)||!$value$plusargs("H=%d",h)||!$value$plusargs("TD=%d",td))$fatal(1,"arguments");
  src_width=w;src_height=h;top_down=td;
  repeat(4)@(negedge clk);rst_n=1;start=1;
  @(negedge clk);start=0;
  while(!done)begin
   in_valid=sent<w*h;
   if(sent!=last_input)begin in_rgb=source_pixel(sent%w,sent/w);last_input=sent;end
   out_ready=(cycles%257!=9)&&(cycles%257!=10);
   @(posedge clk);
   if(error)$fatal(1,"scaler error %h",error_code);
   if(stalled&&{out_x,out_y,out_rgb}!==held)$fatal(1,"stalled payload changed");
   stalled=out_valid&&!out_ready;held={out_x,out_y,out_rgb};
   if(in_valid&&in_ready)sent=sent+1;
   if(out_valid&&out_ready)begin
    dx=received%OW;dy=received/OW;
    x0=(dx*(w-1))/(OW-1);x1=(x0+1<w)?x0+1:x0;
    y0=(dy*(h-1))/(OH-1);y1=(y0+1<h)?y0+1:y0;
    fx=(((dx*(w-1))%(OW-1))*256)/(OW-1);
    fy=(((dy*(h-1))%(OH-1))*256)/(OH-1);
    expect_rgb=0;
    for(i=0;i<3;i=i+1)begin
     shift=i*8;
     a=(source_pixel(x0,y0)>>shift)&255;b=(source_pixel(x1,y0)>>shift)&255;
     c=(source_pixel(x0,y1)>>shift)&255;d=(source_pixel(x1,y1)>>shift)&255;
     v=(a*(256-fx)*(256-fy)+b*fx*(256-fy)+c*(256-fx)*fy+d*fx*fy+32768)/65536;
     expect_rgb=expect_rgb|(v<<shift);
    end
    if(out_x!==dx||out_y!==(td?dy:OH-1-dy)||out_rgb!==expect_rgb)
     $fatal(1,"full scaler pixel=%0d xy=%0d,%0d got=%h expected=%h",received,out_x,out_y,out_rgb,expect_rgb);
    received=received+1;
    if(received%(OW*120)==0)begin $display("PROGRESS full_scaler td=%0d pixels=%0d cycles=%0d",td,received,cycles);$fflush();end
   end
   cycles=cycles+1;
   @(negedge clk);
   if(cycles>OW*OH*45+w*h*5+2000)$fatal(1,"full scaler watchdog");
  end
  if(sent!=w*h||received!=OW*OH||error||busy)$fatal(1,"full scaler completion counts");
  repeat(10)@(negedge clk);
  if(!done||out_valid)$fatal(1,"nonsticky completion");
  $display("PASS full_scaler src=%0dx%0d top=%0d output=1280x720 pixels=%0d cycles=%0d",w,h,td,received,cycles);$finish;
 end
endmodule
