`timescale 1ns/1ps
// v114 audio-only FAT32 stream: three CRC-committed 512-byte banks.
// BANKS=2 remains available for reproducible baseline/control tests.
// The producer reads/CRC-verifies bank N+1 while the consumer parses bank N.
// No speculative byte reaches PCM: a bank commits only after 512 ordered
// bytes AND transport success. FAT bytes are captured separately, then used
// only after the FAT sector CRC passes. Fragmentation and final EOC retained.
module fat32_audio_prefetch #(parameter TIMEOUT=48000000, BANKS=3)(
 input clk,rst_n,start,directory_mode,
 input [31:0] start_cluster,file_size,data_base,fat_base,cluster_max,
 input [7:0] spc,input [3:0] shift,
 output read_req,output reg [31:0] read_lba,
 input sd_ready,sd_done,input [3:0] sd_error,
 input data_valid,input [8:0] data_index,input [7:0] data_byte,
 output byte_valid,input byte_ready,output [7:0] byte_data,output reg [31:0] position,
 output reg done,output reg [3:0] error_code);
 localparam IDLE=0,FETCH=1,ADDR_SHIFT=2,ADDR_BASE=3,ADDR_SECTOR=4,ADDR_CHECK=5,
 ISSUE=6,ACCEPT=7,READ=8,NEXT=9,FAT_FETCH=10,FCHECK=11,END_STREAM=12,HALT=13;
 localparam TW=(TIMEOUT<2)?1:$clog2(TIMEOUT);
 reg [3:0] state;
 reg [31:0] cluster;
 reg [TW-1:0] timer;
 reg [7:0] sector;
 reg [23:0] blocks_left;
 reg [9:0] received;
 reg kind_fat,final_fat,producer_end,limit_hit;
 reg [27:0] next_cluster;
 reg [8:0] fat_offset,index;
 localparam BW=(BANKS<=2)?1:$clog2(BANKS);
 localparam CW=$clog2(BANKS+1);
 reg [BW-1:0] write_bank,read_bank;
 reg [CW-1:0] queued;
 function [BW-1:0] next_bank;input [BW-1:0] bank;begin next_bank=bank==BANKS-1?0:bank+1'b1;end endfunction
 reg rx_valid,rx_finished;
 (* ram_style="block" *) reg [7:0] buffer[0:BANKS*512-1];
 reg [7:0] q;
 wire verified=state==READ&&sd_ready&&sd_done&&received==512&&sd_error==0;
 wire enqueue=verified&&!kind_fat;
 wire dequeue=byte_valid&&byte_ready&&(index==511||position==file_size-1'b1);
 always @(posedge clk)begin
  q<=buffer[{read_bank,index}];
  if(rst_n&&state==READ&&!kind_fat&&data_valid&&received<512&&data_index==received[8:0])
   buffer[{write_bank,data_index}]<=data_byte;
 end
 reg [35:0] addr_work;
 reg [2:0] addr_shifts;
 // Same multi-cycle address adder is reused for data_base and sector offset.
 wire [35:0] addr_operand=state==ADDR_BASE?{4'd0,data_base}:{28'd0,sector};
 wire [35:0] addr_sum=addr_work+addr_operand;
 wire [32:0] fat_calc={1'b0,fat_base}+{8'd0,cluster[31:7]};
 assign read_req=state==ISSUE&&sd_ready;
 assign byte_valid=rx_valid&&!done&&error_code==0;
 assign byte_data=q;
 task fail;input [3:0] c;begin error_code<=c;done<=1;state<=HALT;rx_valid<=0;end endtask
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  state<=IDLE;cluster<=0;timer<=0;sector<=0;blocks_left<=0;received<=0;
  kind_fat<=0;final_fat<=0;producer_end<=0;limit_hit<=0;next_cluster<=0;
  fat_offset<=0;index<=0;write_bank<=0;read_bank<=0;queued<=0;
  rx_valid<=0;rx_finished<=0;position<=0;read_lba<=0;done<=0;error_code<=0;
  addr_work<=0;addr_shifts<=0;
 end else if(sd_error!=0&&state!=IDLE&&state!=HALT)fail(1);
 else if(state==READ&&data_valid&&(received>=512||data_index!=received[8:0]))fail(3);
 else if(state!=HALT)begin
  // Committed-bank count; simultaneous producer/consumer completion
  // leaves it unchanged. A producer never writes either queued bank.
  case({enqueue,dequeue})
   2'b10:queued<=queued+1'b1;
   2'b01:queued<=queued-1'b1;
   default:begin end
  endcase
  if(enqueue)begin write_bank<=next_bank(write_bank);blocks_left<=blocks_left-1'b1;end
  if(byte_valid&&byte_ready)begin
   position<=position+1'b1;rx_valid<=0;
   if(dequeue)begin index<=0;read_bank<=next_bank(read_bank);end
   else index<=index+1'b1;
   if(position==file_size-1'b1)rx_finished<=1;
  end else if(!rx_valid&&queued!=0&&!rx_finished)rx_valid<=1;
  if(state==READ&&data_valid)begin
   received<=received+1'b1;
   if(kind_fat&&data_index[8:2]==fat_offset[8:2])case(data_index[1:0])
    0:next_cluster[7:0]<=data_byte;
    1:next_cluster[15:8]<=data_byte;
    2:next_cluster[23:16]<=data_byte;
    3:next_cluster[27:24]<=data_byte[3:0];
   endcase
  end
  case(state)
   IDLE:if(start)begin
    if(start_cluster<2||start_cluster>cluster_max||start_cluster>=32'h0ffffff0||file_size==0||shift>7||spc!=(8'd1<<shift))fail(2);
    else begin cluster<=start_cluster;blocks_left<={1'b0,file_size[31:9]}+(|file_size[8:0]);state<=FETCH;end
   end
   FETCH:if(queued<BANKS)begin addr_work<={4'd0,cluster}-36'd2;addr_shifts<=shift[2:0];state<=ADDR_SHIFT;end
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
    if(received!=512)fail(3);else state<=kind_fat?FCHECK:NEXT;
   end else if(timer==TIMEOUT-1)fail(5);else timer<=timer+1'b1;
   NEXT:if(blocks_left==0)begin
    if(directory_mode)begin producer_end<=1;limit_hit<=1;state<=END_STREAM;end
    else begin final_fat<=1;state<=FAT_FETCH;end
   end else if(sector==spc-1'b1)begin final_fat<=0;state<=FAT_FETCH;end
    else begin sector<=sector+1'b1;state<=FETCH;end
   FAT_FETCH:if(fat_calc[32])fail(4);else begin
    read_lba<=fat_calc[31:0];fat_offset<={cluster[6:0],2'b00};kind_fat<=1;timer<=0;state<=ISSUE;
   end
   FCHECK:if(next_cluster>=28'hffffff8)begin
    if(directory_mode||final_fat)begin producer_end<=1;state<=END_STREAM;end else fail(7);
   end else if(final_fat||next_cluster<2||next_cluster>=28'hffffff0||{4'd0,next_cluster}>cluster_max)fail(8);
   else begin cluster<={4'd0,next_cluster};sector<=0;state<=FETCH;end
   END_STREAM:if(producer_end&&queued==0&&!rx_valid)begin
    if(limit_hit)fail(6);else begin done<=1;state<=HALT;end
   end
   default:fail(15);
  endcase
 end
endmodule