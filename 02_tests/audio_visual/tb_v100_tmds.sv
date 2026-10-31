`timescale 1ns/1ps
// Independent iterative DVI reference; no optimized prefix or half-delta formula.
module tb_v100_tmds;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=1, de=0; reg [7:0] din=0; reg [1:0] c=0;
 wire [9:0] q;
 tmds_encoder dut(.clk(clk),.rst_n(rst_n),.din(din),.de(de),.c(c),.q(q));
 integer checks=0, state_i, data_i, ctl_i, j, model_count=0;
 reg [9:0] expected_q;
 reg [4:0] expected_count;
 reg [31:0] rng=32'h6f8a4513;
 task reference_step;
   input [7:0] value; input active; input [1:0] ctrl; input integer count_in;
   output [9:0] symbol; output [4:0] count_out;
   reg [8:0] qm; reg xnor_choice; integer n1,n0,ones_d,z,next_count;
   begin
    if (!active) begin
      case(ctrl)
       0:symbol=10'b1101010100; 1:symbol=10'b0010101011;
       2:symbol=10'b0101010100; 3:symbol=10'b1010101011;
      endcase
      next_count=0;
    end else begin
      ones_d=0; for(z=0;z<8;z=z+1) if(value[z]) ones_d=ones_d+1;
      xnor_choice=(ones_d>4)||((ones_d==4)&&!value[0]);
      qm[0]=value[0];
      for(z=1;z<8;z=z+1) begin
        if(xnor_choice) qm[z]=~(qm[z-1]^value[z]);
        else qm[z]=qm[z-1]^value[z];
      end
      qm[8]=!xnor_choice;
      n1=0; n0=0;
      for(z=0;z<8;z=z+1) if(qm[z]) n1=n1+1; else n0=n0+1;
      if(count_in==0 || n1==n0) begin
        symbol={~qm[8],qm[8],8'b0};
        if(qm[8]) begin symbol[7:0]=qm[7:0]; next_count=count_in+n1-n0; end
        else begin symbol[7:0]=~qm[7:0]; next_count=count_in+n0-n1; end
      end else if((count_in>0 && n1>n0)||(count_in<0 && n0>n1)) begin
        symbol={1'b1,qm[8],~qm[7:0]}; next_count=count_in+n0-n1+2*qm[8];
      end else begin
        symbol={1'b0,qm[8],qm[7:0]}; next_count=count_in+n1-n0-2*(1-qm[8]);
      end
    end
    count_out=next_count;
   end
 endtask
 task compare_step;
   begin
     @(posedge clk); #1;
     if(q!==expected_q || dut.cnt!==expected_count) begin
       $display("ERROR tmds check=%0d data=%h de=%b c=%b got=%h count=%0d expected=%h count=%0d",checks,din,de,c,q,$signed(dut.cnt),expected_q,$signed(expected_count));
       $fatal(1,"TMDS symbol or next disparity mismatch");
     end
     checks=checks+1;
   end
 endtask
 initial begin
   #1; rst_n=0; #1; if(q!==10'b1101010100 || dut.cnt!==0) $fatal(1,"async initial reset");
   @(negedge clk); rst_n=1;
   // Exhaust ALL input bytes and ALL 5-bit disparity encodings, including
   // unreachable odd states.  c rotates while de=1 and must be ignored.
   for(state_i=-16;state_i<16;state_i=state_i+1)
    for(data_i=0;data_i<256;data_i=data_i+1) begin
      @(negedge clk); dut.cnt=state_i; din=data_i; de=1; c=data_i%4;
      reference_step(din,de,c,state_i,expected_q,expected_count); compare_step();
    end
   for(state_i=-16;state_i<16;state_i=state_i+1)
    for(ctl_i=0;ctl_i<4;ctl_i=ctl_i+1) begin
      @(negedge clk); dut.cnt=state_i; din=8'h96; de=0; c=ctl_i;
      reference_step(din,de,c,state_i,expected_q,expected_count); compare_step();
    end
   // Reachable continuous stream: blanking, all bytes, repeated edge values,
   // random symbols and asynchronous reset interruption; no state injection.
   model_count=0;
   for(j=0;j<100000;j=j+1) begin
      @(negedge clk);
      rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5);
      case((j/4096)%5)
       0:din=j; 1:din=0; 2:din=255; 3:din=(j%2)?8'haa:8'h55; 4:din=rng[7:0];
      endcase
      de=((j%1650)<1280) && (rng[15:13]!=3'b000); c=rng[19:18];
      reference_step(din,de,c,model_count,expected_q,expected_count);
      compare_step(); model_count=$signed(expected_count);
      if(expected_count[0]!==0) $fatal(1,"reachable disparity became odd");
      if((j%8192)==13) begin
        #1;rst_n=0;#1;
        if(q!==10'b1101010100 || dut.cnt!==0) $fatal(1,"asynchronous reset failed");
        #1;rst_n=1; model_count=0;checks=checks+1;
      end
   end
   $display("PASS tmds checks=%0d exhaustive_states=32 exhaustive_bytes=256 controls=128 continuous=100000 async_reset=14 one_pixel_latency=unchanged",checks);
   $finish;
 end
 initial begin #2000000; $fatal(1,"TMDS test timeout"); end
endmodule
