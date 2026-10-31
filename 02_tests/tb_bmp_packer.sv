`timescale 1ns/1ps
module tb_bmp_packer;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,enable=1,pixel_valid=0,source_done=0,source_ok=0,req_ack=0;
reg [23:0] pixel_rgb;reg [15:0] pixel_x,pixel_y;reg[7:0] source_error=0;
wire pixel_ready,req_valid,done;wire [18:0]req_addr;wire [127:0]req_data;
wire [7:0]error_code;wire [31:0]pixel_count,burst_count;
bmp_pixel_packer dut(.*);
integer top=0,mode=0,x,y,k,row,n=0,waiting=0,checked=0,cycle=0;
reg [127:0]saved;reg[18:0]sa;reg holding=0;
function [23:0] pattern(input integer xx,yy);begin pattern={8'(xx*3+yy),8'(xx+yy*5),8'(xx^yy)};end endfunction
function [7:0] idx(input integer xx,yy);reg[23:0]p;begin p=pattern(xx,yy);idx={p[23:21],p[15:13],p[7:6]};end endfunction
always @(negedge clk)begin
 if(!rst_n)begin req_ack=0;waiting=0;holding=0;checked=0;cycle=0;end
 else begin
 cycle=cycle+1;enable=cycle%19>3;
 if(holding&&(!req_valid||req_addr!==sa||req_data!==saved))$fatal(1,"request changed before registered ack");
 if(req_valid&&!req_ack)begin
  if(!holding)begin
   saved=req_data;sa=req_addr;holding=1;
   row=top?checked/40:479-checked/40;
   if(req_addr!==row*40+checked%40)$fatal(1,"address %0d expected row %0d burst %0d",req_addr,row,checked);
   for(k=0;k<16;k=k+1)if(req_data[k*8+:8]!==idx((checked%40)*16+k,row))$fatal(1,"packed pixel mismatch");
  end
  waiting=waiting+1;
  if(waiting==7)begin req_ack=1;waiting=0;holding=0;checked=checked+1;end
 end else req_ack=0;
 end
end
task reset;begin @(posedge clk);#1;rst_n=0;repeat(5)@(posedge clk);#1;rst_n=1;end endtask
initial begin
 if($value$plusargs("TOP=%d",top))begin end
 if($value$plusargs("MODE=%d",mode))begin end
 reset();
 if(mode==1)begin
  @(negedge clk);source_done=1;source_ok=1;repeat(5)@(posedge clk);#1;
  if(done||error_code!=8'h42)$fatal(1,"early done not rejected");
 end else if(mode==2)begin
  @(negedge clk);pixel_valid=1;pixel_x=1;pixel_y=0;pixel_rgb=0;
  do @(posedge clk);while(!pixel_ready);#1;
  if(done||error_code!=8'h43)$fatal(1,"bad coordinate not rejected");
 end else if(mode==3)begin
  @(negedge clk);source_error=8'h1a;repeat(5)@(posedge clk);#1;
  if(done||error_code!=8'h1a)$fatal(1,"source error lost");
 end else begin
 for(y=0;y<480;y=y+1)for(x=0;x<640;x=x+1)begin
  @(posedge clk);#1;pixel_valid=1;pixel_x=x;pixel_y=top?y:479-y;pixel_rgb=pattern(x,pixel_y);
  do @(posedge clk);while(!pixel_ready);
  #1;pixel_valid=0;
 end
 source_done=1;source_ok=1;
 // The last write still has to be acknowledged, source EOF alone is insufficient.
 if(done)$fatal(1,"premature completion");
 wait(done);#1;
 if(error_code||pixel_count!=307200||burst_count!=19200||checked!=19200||req_valid)$fatal(1,"bad terminal counters");
 repeat(10)@(posedge clk);if(!done)$fatal(1,"done not sticky");
 end
 $display("PASS packer top=%0d mode=%0d pixels=%0d bursts=%0d",top,mode,pixel_count,burst_count);$finish;
end
initial begin #100000000;$fatal(1,"packer timeout");end
endmodule
