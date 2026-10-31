`timescale 1ns/1ps
module tb_full_frame_packer;
 parameter WIDTH=1280,HEIGHT=720;
 localparam PIXELS=WIDTH*HEIGHT,BURSTS=PIXELS/16;
 reg clk=0,rst_n=0,pixel_valid=0,source_done=0,source_ok=0,req_ack=0;
 always #5 clk=~clk;
 reg [23:0] pixel_rgb=0;
 reg [15:0] pixel_x=0,pixel_y=0;
 reg [7:0] source_error=0;
 wire pixel_ready,req_valid,done;
 wire [18:0] req_addr;
 wire [127:0] req_data;
 wire [7:0] error_code;
 wire [31:0] pixel_count,burst_count;
 integer top=0,mode=0,sent=0,writes=0,acks=0,pending=0,delay_ack=0,lane,expect_row,expect_addr;
 reg [146:0] held_request;
 function [23:0] sample;
  input integer horizontal,vertical;
  reg [7:0] red,green,blue;
  begin red=(horizontal+vertical*3)&255;green=(horizontal*5+vertical*7)&255;blue=(horizontal*11+vertical*13)&255;sample={red,green,blue};end
 endfunction
 function [7:0] indexed;
  input integer horizontal,vertical;
  reg [23:0] rgb;
  begin rgb=sample(horizontal,vertical);indexed={rgb[23:21],rgb[15:13],rgb[7:6]};end
 endfunction
 bmp_pixel_packer #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) dut(.*,.enable(1'b1));
 always @(negedge clk)if(rst_n)begin
  if(!pixel_valid||pixel_ready)begin
   if(sent<PIXELS)begin
    pixel_valid=1;pixel_x=sent%WIDTH;pixel_y=top?sent/WIDTH:HEIGHT-1-sent/WIDTH;
    pixel_rgb=sample(pixel_x,pixel_y);
   end else pixel_valid=0;
  end
  if(sent==PIXELS)begin source_done=1;source_ok=1;end
  if(mode==1&&sent==16)begin source_done=1;source_ok=0;end
  if(mode==2&&acks==BURSTS-1&&pending)source_error=8'h55;
 end
 always @(posedge clk)if(rst_n)begin
  if(pixel_valid&&pixel_ready)sent=sent+1;
  if(done&&(acks!=BURSTS||sent!=PIXELS))$fatal(1,"Premature full frame publication");
  if(req_ack)begin req_ack<=0;pending=0;acks=acks+1;end
  else if(pending)begin
   if(error_code==0&&{req_addr,req_data}!==held_request)$fatal(1,"Unstable burst before registered ACK");
   if(delay_ack==0)req_ack<=1;else delay_ack=delay_ack-1;
  end else if(req_valid)begin
   expect_row=top?writes/(WIDTH/16):HEIGHT-1-writes/(WIDTH/16);
   expect_addr=expect_row*(WIDTH/16)+writes%(WIDTH/16);
   if(req_addr!==expect_addr)$fatal(1,"Full frame address got=%0d expected=%0d",req_addr,expect_addr);
   for(lane=0;lane<16;lane=lane+1)if(req_data[lane*8+:8]!==indexed((writes%(WIDTH/16))*16+lane,expect_row))$fatal(1,"Full frame content mismatch");
   writes=writes+1;pending=1;delay_ack=writes%11;held_request={req_addr,req_data};
  end
 end
 initial begin
  if(!$value$plusargs("TOP=%d",top))top=0;
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  repeat(5)@(negedge clk);rst_n=1;
  wait(done||error_code!=0);repeat(20)@(negedge clk);
  if(mode==0)begin
   if(!done||error_code||pixel_count!=PIXELS||burst_count!=BURSTS||writes!=BURSTS||acks!=BURSTS)$fatal(1,"Full frame counts");
  end else if(done||error_code!=(mode==1?8'h41:8'h55))$fatal(1,"Full frame error handling");
  $display("PASS packer %0dx%0d top=%0d mode=%0d pixels=%0d bursts=%0d error=%02h",WIDTH,HEIGHT,top,mode,pixel_count,burst_count,error_code);
  $finish;
 end
 initial begin #100000000;$fatal(1,"Full frame packer watchdog");end
endmodule
