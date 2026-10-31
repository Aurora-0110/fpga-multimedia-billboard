`timescale 1ns/1ps
// Read-only sequential FAT32 stream from an ALREADY validated mount. One
// synchronous BRAM quarantines the whole sector until transport CRC succeeds.
// File mode verifies the final FAT EOC. Directory mode accepts early EOC and
// has a hard 128-sector limit. No assumption that files/clusters are contiguous.
module fat32_byte_stream #(parameter TIMEOUT=48000000)(
 input clk,rst_n,start,directory_mode,
 input [31:0] start_cluster,file_size,data_base,fat_base,cluster_max,
 input [7:0] spc,input [3:0] shift,
 output read_req,output reg [31:0] read_lba,
 input sd_ready,sd_done,input [3:0] sd_error,
 input data_valid,input [8:0] data_index,input [7:0] data_byte,
 output byte_valid,input byte_ready,output [7:0] byte_data,output reg [31:0] position,
 output reg done,output reg [3:0] error_code);
 localparam IDLE=0,FETCH=1,ISSUE=2,ACCEPT=3,READ=4,DISPATCH=5,
 BYTE_REQ=6,BYTE_OUT=7,NEXT=8,FAT_FETCH=9,F0=10,F1=11,F2=12,F3=13,FCHECK=14,HALT=15,ADDR_SHIFT=16,ADDR_BASE=17,ADDR_SECTOR=18,ADDR_CHECK=19;
 reg [4:0] state;reg [31:0] cluster,timer;
 reg [7:0] sector;reg [8:0] index,fat_offset;reg [9:0] received;
 reg kind_fat,final_fat;
 reg [23:0] fat_lo;
 (* ram_style="block" *) reg [7:0] buffer[0:511];reg [7:0] q;
 reg [8:0] ra;
 always @*case(state)
 F0:ra=fat_offset;F1:ra=fat_offset+1'b1;F2:ra=fat_offset+2'd2;F3:ra=fat_offset+2'd3;
 default:ra=index;
 endcase
 always @(posedge clk)begin
  q<=buffer[ra];
  if(rst_n&&state==READ&&data_valid&&received<512&&data_index==received[8:0])buffer[data_index]<=data_byte;
 end
 // Valid clusters are < 2^28 and shift <= 7, so 36 bits include all
 // carries. At most seven fixed one-bit shifts replace a 40-bit barrel.
 reg [35:0] addr_work;reg [2:0] addr_shifts;
 wire [35:0] addr_operand=state==ADDR_BASE?{4'd0,data_base}:{28'd0,sector};
 wire [35:0] addr_sum=addr_work+addr_operand;
 wire [32:0] fat_calc={1'b0,fat_base}+{8'd0,cluster[31:7]};
 wire [27:0] next_cluster={q[3:0],fat_lo};
 assign read_req=state==ISSUE&&sd_ready;
 assign byte_valid=state==BYTE_OUT;assign byte_data=q;
 task fail;input [3:0] c;begin error_code<=c;done<=1;state<=HALT;end endtask
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin state<=IDLE;addr_work<=0;addr_shifts<=0;cluster<=0;timer<=0;sector<=0;index<=0;fat_offset<=0;received<=0;kind_fat<=0;final_fat<=0;fat_lo<=0;position<=0;read_lba<=0;done<=0;error_code<=0;end
 else if(sd_error!=0&&state!=IDLE&&state!=HALT)fail(1);
 else if(state==READ&&data_valid&&(received>=512||data_index!=received[8:0]))fail(3);
 else begin
  if(state==READ&&data_valid)received<=received+1'b1;
  case(state)
   IDLE:if(start)begin
    if(start_cluster<2||start_cluster>cluster_max||start_cluster>=32'h0ffffff0||file_size==0||shift>7||spc!=(8'd1<<shift))fail(2);
    else begin cluster<=start_cluster;position<=0;sector<=0;state<=FETCH;end
   end
   FETCH:begin addr_work<={4'd0,cluster}-36'd2;addr_shifts<=shift[2:0];state<=ADDR_SHIFT;end
   ADDR_SHIFT:if(addr_shifts==0)state<=ADDR_BASE;
    else begin addr_work<=addr_work<<1;addr_shifts<=addr_shifts-1'b1;end
   ADDR_BASE:begin addr_work<=addr_sum;state<=ADDR_SECTOR;end
   ADDR_SECTOR:begin addr_work<=addr_sum;state<=ADDR_CHECK;end
   ADDR_CHECK:if(addr_work[35:32]!=0)fail(4);
    else begin read_lba<=addr_work[31:0];kind_fat<=0;timer<=0;state<=ISSUE;end
   ISSUE:if(sd_ready)begin received<=0;timer<=0;state<=ACCEPT;end
    else if(timer==TIMEOUT-1)fail(5);else timer<=timer+1'b1;
   ACCEPT:if(!sd_ready)begin timer<=0;state<=READ;end
    else if(timer==TIMEOUT-1)fail(5);else timer<=timer+1'b1;
   READ:if(sd_ready&&sd_done)begin
    if(received!=512)fail(3);else begin index<=0;state<=DISPATCH;end
   end else if(timer==TIMEOUT-1)fail(5);else timer<=timer+1'b1;
   DISPATCH:state<=kind_fat?F0:BYTE_REQ;
   BYTE_REQ:state<=BYTE_OUT;
   BYTE_OUT:if(byte_ready)begin
    position<=position+1'b1;index<=index+1'b1;
    if(position==file_size-1'b1)begin
     if(directory_mode)fail(6);else begin final_fat<=1;state<=FAT_FETCH;end
    end else if(index==511)state<=NEXT;
    else state<=BYTE_REQ;
   end
   NEXT:if(sector==spc-1'b1)begin final_fat<=0;state<=FAT_FETCH;end
    else begin sector<=sector+1'b1;state<=FETCH;end
   FAT_FETCH:if(fat_calc[32])fail(4);else begin
    read_lba<=fat_calc[31:0];fat_offset<={cluster[6:0],2'b00};kind_fat<=1;timer<=0;state<=ISSUE;
   end
   F0:state<=F1;
   F1:begin fat_lo[7:0]<=q;state<=F2;end
   F2:begin fat_lo[15:8]<=q;state<=F3;end
   F3:begin fat_lo[23:16]<=q;state<=FCHECK;end
   FCHECK:if(next_cluster>=28'hffffff8)begin
    if(directory_mode||final_fat)begin done<=1;state<=HALT;end else fail(7);
   end else if(final_fat||next_cluster<2||next_cluster>=28'hffffff0||{4'd0,next_cluster}>cluster_max)fail(8);
   else begin cluster<={4'd0,next_cluster};sector<=0;state<=FETCH;end
   HALT:begin end
   default:fail(15);
  endcase
 end
endmodule
