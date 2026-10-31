`timescale 1ns/1ps
module tb_bilinear_stream_scaler;
 parameter OW=13,OH=9,MW=1280,MH=1024;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0,top_down=0,in_valid=0,out_ready=0;
 reg[15:0]src_width=0,src_height=0;reg[23:0]in_rgb=0;
 wire busy,done,error,in_ready,out_valid;wire[3:0]error_code;
 wire[23:0]out_rgb;wire[15:0]out_x,out_y;
 bilinear_stream_scaler #(.OUT_WIDTH(OW),.OUT_HEIGHT(OH),.MAX_WIDTH(MW),.MAX_HEIGHT(MH)) dut(.*);
 reg[23:0]source[0:MW*MH-1],expected[0:921599];
 integer w,h,td,np,no,sent=0,received=0,cycles=0,ex,ey,i;
 reg held_in=0,held_out=0;reg[55:0]last_out;reg[31:0]rng=32'h87bb1a91;
 function[31:0]prng;input[31:0]v;reg[31:0]q;begin q=v^(v<<13);q=q^(q>>17);prng=q^(q<<5);end endfunction
 task launch;input[15:0]ww,hh;begin
  @(negedge clk);src_width=ww;src_height=hh;start=1;
  @(negedge clk);start=0;
 end endtask
 initial begin
  if(!$value$plusargs("W=%d",w)||!$value$plusargs("H=%d",h)||!$value$plusargs("TD=%d",td))$fatal(1,"args");
  np=w*h;no=OW*OH;top_down=td;
  $readmemh("source.hex",source,0,np-1);$readmemh("expected.hex",expected,0,no-1);
  repeat(3)@(negedge clk);rst_n=1;
  launch(0,10);if(!error||busy||error_code!=1)$fatal(1,"zero width not rejected");
  launch(MW+1,1);if(!error||busy)$fatal(1,"oversize not rejected");
  launch(1,0);if(!error||busy)$fatal(1,"zero height not rejected");
  launch(1,MH+1);if(!error||busy)$fatal(1,"oversize height not rejected");
  // Abort a frame after partial row input, then restart with both reset and
  // different geometry. Old RAM data must never become a valid new pixel.
  launch(8,8);in_valid=1;in_rgb=24'habcdef;repeat(5)@(negedge clk);
  rst_n=0;in_valid=0;repeat(3)@(negedge clk);rst_n=1;
  launch(w,h);
  while(!done)begin
   if(!held_in)begin
    rng=prng(rng);in_valid=(sent<np)&&(rng[2:0]!=0);
    if(in_valid)in_rgb=source[sent];
   end
   rng=prng(rng);out_ready=(cycles>=300&&cycles<420)?0:(rng[2:0]>1);
   // External geometry changes and start while busy must be ignored.
   if(cycles==150)begin start=1;src_width=0;src_height=0;top_down=!td;end
   if(cycles==151)start=0;
   @(posedge clk);
   if(error)$fatal(1,"scaler error %0d",error_code);
   if(held_out&&{out_valid,out_x,out_y,out_rgb}!=={1'b1,last_out})$fatal(1,"unstable stalled output");
   held_out=out_valid&&!out_ready;last_out={out_x,out_y,out_rgb};
   if(out_valid&&out_ready)begin
    ex=received%OW;ey=td?received/OW:OH-1-received/OW;
    if(out_x!==ex||out_y!==ey||out_rgb!==expected[received])
     $fatal(1,"scale %0dx%0d -> %0dx%0d td=%0d pixel=%0d got xy=%0d,%0d rgb=%h expected xy=%0d,%0d rgb=%h",w,h,OW,OH,td,received,out_x,out_y,out_rgb,ex,ey,expected[received]);
    received=received+1;
   end
   held_in=in_valid&&!in_ready;if(in_valid&&in_ready)sent=sent+1;
   cycles=cycles+1;
   @(negedge clk);
   if(cycles>no*50+np*5+2000)$fatal(1,"stream timeout");
  end
  in_valid=0;out_ready=1;
  if(sent!=np||received!=no||busy||error)$fatal(1,"final count input=%0d/%0d output=%0d/%0d",sent,np,received,no);
  repeat(12)begin @(negedge clk);if(out_valid||!done||busy)$fatal(1,"extra output or nonsticky done");end
  // Start a new frame without reset. A completed kernel must not leak stale
  // valid/data, and done must clear on the launch handshake.
  top_down=1;launch(1,1);if(!busy||done||error)$fatal(1,"restart failed");
  if(OW<1280)begin
   sent=0;i=0;in_valid=1;in_rgb=24'h39ab82;out_ready=1;
   while(!done)begin
    @(posedge clk);
    if(in_valid&&in_ready)sent=sent+1;
    if(out_valid&&out_ready)begin
     if(out_rgb!==24'h39ab82||out_x!==i%OW||out_y!==i/OW)$fatal(1,"restart stale data/tag");
     i=i+1;end
    @(negedge clk);if(sent!=0)in_valid=0;
   end
   if(i!=no||sent!=1)$fatal(1,"restart count");
  end
  $display("PASS scaler src=%0dx%0d dst=%0dx%0d td=%0d pixels=%0d cycles=%0d invalid4 reset restart stalls busy_start_ignored",w,h,OW,OH,td,received,cycles);$finish;
 end
endmodule
