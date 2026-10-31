`timescale 1ns/1ps
// Three-lane old RGB-register path vs retimed prepared-register path AND
// independent iterative DVI oracle. Input/control is sampled one clock before
// the encoder edge; no extra pixel latency is allowed.
module tb_v110_prepared_pipeline;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=1,de=0;reg [1:0] c=0;reg [23:0] rgb=0;
 reg [23:0] rgb_q;reg de_q;reg [1:0] c_q;
 wire [8:0] qm[0:2];wire [3:0] ones[0:2];
 reg [8:0] qm_q[0:2];reg [3:0] ones_q[0:2];
 wire [9:0] old_q[0:2],new_q[0:2];
 genvar k;
 generate for(k=0;k<3;k=k+1)begin:lane
  wire [1:0] ctl=k==0?c_q:2'b00;
  tmds_prepare pre(.din(rgb[8*k+:8]),.q_m(qm[k]),.n1q_m(ones[k]));
  always @(posedge clk or negedge rst_n)
  if(!rst_n)begin qm_q[k]<=9'h100;ones_q[k]<=0;end
  else begin qm_q[k]<=qm[k];ones_q[k]<=ones[k];end
  tmds_encoder oldenc(.clk(clk),.rst_n(rst_n),.din(rgb_q[8*k+:8]),.de(de_q),.c(ctl),.q(old_q[k]));
  tmds_encoder #(.PREPARED_INPUT(1)) newenc(.clk(clk),.rst_n(rst_n),.din(8'd0),.de(de_q),.c(ctl),.q(new_q[k]),.q_m_in(qm_q[k]),.ones_in(ones_q[k]));
 end endgenerate
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin rgb_q<=0;de_q<=0;c_q<=0;end
 else begin rgb_q<=rgb;de_q<=de;c_q<=c;end
 integer counts[0:2];reg [4:0] nextcount[0:2];reg [9:0] expected[0:2];
 integer i,j,checks=0,resets=0;reg [31:0] rng=32'h197053ce;
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

 initial begin
  for(i=0;i<3;i=i+1)counts[i]=0;
  #1;rst_n=0;#1;rst_n=1;
  for(j=0;j<120000;j=j+1)begin
   @(negedge clk);rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
   case((j/10000)%5)
    0:rgb={8'(j),8'(j+83),8'(j+171)};
    1:rgb=0;2:rgb=24'hffffff;3:rgb=j[0]?24'h55aa00:24'haa55ff;default:rgb=rng[23:0];
   endcase
   de=(j%1650<1280)&&(rng[27:25]!=0);c=rng[31:30];
   @(posedge clk);
   for(i=0;i<3;i=i+1)reference_step(rgb_q[8*i+:8],de_q,i==0?c_q:2'b00,counts[i],expected[i],nextcount[i]);
   #1;
   for(i=0;i<3;i=i+1)begin
    if(new_q[i]!==expected[i]||old_q[i]!==expected[i])
     $fatal(1,"retime symbol/latency mismatch cycle=%0d lane=%0d old=%h new=%h expected=%h",j,i,old_q[i],new_q[i],expected[i]);
    counts[i]=$signed(nextcount[i]);checks=checks+1;
   end
   if(j%8192==103)begin
    #1;rst_n=0;#1;
    for(i=0;i<3;i=i+1)begin
     if(old_q[i]!==10'b1101010100||new_q[i]!==10'b1101010100)$fatal(1,"retime async reset");counts[i]=0;
    end
    #1;rst_n=1;resets=resets+1;
   end
  end
  $display("PASS v110 three-lane prepared retiming checks=%0d cycles=120000 async_resets=%0d unchanged two-edge RGB/control latency, independent DVI oracle",checks,resets);$finish;
 end
 initial begin #2000000;$fatal(1,"prepared pipeline watchdog");end
endmodule
