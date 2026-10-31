`timescale 1ns/1ps
module tb_v066_tmds;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,de=0;reg [7:0] din=8'h55;reg [1:0] c=0;
wire [9:0] q;tmds_encoder dut(.*);
reg [31:0] vectors[0:200000];string filename;
integer count,i,j,ones,rd=0,minrd=0,maxrd=0,mismatch=0,cntbad=0,decodebad=0;
reg [9:0] expected;reg [7:0] qm,decoded;
initial begin
 if(!$value$plusargs("VECTORS=%s",filename))$fatal(1,"vectors required");
 if(!$value$plusargs("COUNT=%d",count))$fatal(1,"count required");
 $readmemh(filename,vectors,0,count-1);
 if(^vectors[0]===1'bx || ^vectors[count-1]===1'bx)$fatal(1,"Fixture read failed");
 repeat(3)@(negedge clk);
 for(i=0;i<count;i=i+1)begin
  @(negedge clk);rst_n=vectors[i][27];de=vectors[i][10];c=vectors[i][9:8];din=vectors[i][7:0];expected=vectors[i][20:11];
  @(posedge clk);#1;
  if(q!==expected)begin mismatch=mismatch+1;if(mismatch<=3)$display("MISMATCH i=%0d din=%h actual=%b expected=%b",i,din,q,expected);end
  if(!rst_n||!de)rd=0;else begin
   ones=0;for(j=0;j<10;j=j+1)ones=ones+q[j];rd=rd+2*ones-10;
   if(rd<minrd)minrd=rd;if(rd>maxrd)maxrd=rd;
   qm=q[9]?~q[7:0]:q[7:0];decoded[0]=qm[0];
   for(j=1;j<8;j=j+1)decoded[j]=q[8]?(qm[j]^qm[j-1]):~(qm[j]^qm[j-1]);
   if(decoded!==din)decodebad=decodebad+1;
  end
  if($signed(dut.cnt)!==rd)cntbad=cntbad+1;
 end
 $display("RESULT vectors=%0d code_mismatch=%0d counter_mismatch=%0d decode_mismatch=%0d physical_RD_min=%0d max=%0d",count,mismatch,cntbad,decodebad,minrd,maxrd);
 if(mismatch||cntbad||decodebad||minrd< -8||maxrd>8)$fatal(1,"TMDS invariant failed");
 $display("PASS independent_TMDS_reference_and_disparity");$finish;
end
endmodule
