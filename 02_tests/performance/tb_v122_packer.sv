`timescale 1ns/1ps
module tb_v122_packer;
 parameter W=32,H=3,DOWN=0,DITHER=1,FAULT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,enable=0,pv=0,sdone=0,sok=1,ack=0;reg[7:0]serr=0;
 reg[23:0]rgb=0;reg[15:0]px=0,py=0;
 wire ready,rv,done;wire[18:0]addr;wire[127:0]data;wire[7:0]err;wire[31:0]pc,bc;
 wire rr,rrv,rdone;wire[18:0]raddr;wire[127:0]rdata;wire[7:0]rerr;wire[31:0]rpc,rbc;
 bmp_pixel_packer #(.WIDTH(W),.HEIGHT(H),.DITHER_ENABLE(DITHER)) dut(.clk(clk),.rst_n(rst_n),.enable(enable),.pixel_valid(pv),.pixel_ready(ready),.pixel_rgb(rgb),.pixel_x(px),.pixel_y(py),.source_done(sdone),.source_ok(sok),.source_error(serr),.req_valid(rv),.req_addr(addr),.req_data(data),.req_ack(ack),.done(done),.error_code(err),.pixel_count(pc),.burst_count(bc));
 v119_bmp_pixel_packer_reference #(.WIDTH(W),.HEIGHT(H),.DITHER_ENABLE(DITHER)) refdut(.clk(clk),.rst_n(rst_n),.enable(enable),.pixel_valid(pv),.pixel_ready(rr),.pixel_rgb(rgb),.pixel_x(px),.pixel_y(py),.source_done(sdone),.source_ok(sok),.source_error(serr),.req_valid(rrv),.req_addr(raddr),.req_data(rdata),.req_ack(ack),.done(rdone),.error_code(rerr),.pixel_count(rpc),.burst_count(rbc));
 integer sent=0,ticks=0,checks=0,burst_checks=0,expected,yy;
 reg[31:0]rng=32'h91abf035;
 always @(posedge clk)begin
  if(!rst_n)sent=0;
  else begin
   if(pv&&ready)sent=sent+1;
   if(rv&&ack)begin
    yy=DOWN?H-1-(bc/(W/16)):bc/(W/16);
    expected=yy*(W/16)+bc%(W/16);
    if(addr!==expected[18:0])$fatal(1,"Independent burst address mismatch bc=%0d actual=%0d expected=%0d",bc,addr,expected);
    burst_checks=burst_checks+1;
   end
  end
  #1;
  if({ready,rv,addr,data,done,err,pc,bc}!={rr,rrv,raddr,rdata,rdone,rerr,rpc,rbc})$fatal(1,"AB packer mismatch W=%0d H=%0d down=%0d tick=%0d sent=%0d addr=%0d ref=%0d",W,H,DOWN,ticks,sent,addr,raddr);
  checks=checks+1;
 end
 always @(negedge clk)if(rst_n)begin
  ticks=ticks+1;rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
  enable=rng[3:0]!=0;ack=rv&&rng[4];pv=(sent<W*H)&&rng[5];
  px=sent%W;py=DOWN?H-1-sent/W:sent/W;
  rgb={rng[7:0],rng[15:8],rng[23:16]};sdone=sent==W*H;
  if(FAULT==1&&sent==17)px=16'hf001;
  if(FAULT==2&&sent==17)serr=8'h8a;
  if(FAULT==3&&sent==17)begin sdone=1;sok=0;end
  if(FAULT==4&&sent==17)sdone=1;
  if(err!=0)begin
   if(FAULT==0)$fatal(1,"Unexpected packer error %h",err);
   $display("PASS v122 packer W=%0d H=%0d down=%0d dither=%0d fault=%0d checks=%0d bursts=%0d",W,H,DOWN,DITHER,FAULT,checks,burst_checks);$finish;
  end
  if(done)begin
   if(sent!=W*H||bc!=W*H/16)$fatal(1,"Incorrect completion");
   $display("PASS v122 packer W=%0d H=%0d down=%0d dither=%0d fault=%0d checks=%0d bursts=%0d",W,H,DOWN,DITHER,FAULT,checks,burst_checks);$finish;
  end
  if(ticks>W*H*12+2000)$fatal(1,"packer timeout");
 end
 initial begin repeat(4)@(negedge clk);rst_n=1;end
endmodule