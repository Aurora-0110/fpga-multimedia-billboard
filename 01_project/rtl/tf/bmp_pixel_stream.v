`timescale 1ns/1ps
// v022. Read-only BMP payload -> RGB888 ready/valid stream.
// One 512-byte quarantine buffer: no byte released before SD CRC16 commits.
// RGB888 file rows; dynamic mode discards DWORD row padding after CRC commit.
// Bounded first implementation: exact file end, offset<=65536, final FAT EOC.
module bmp_pixel_stream #(
 parameter integer WIDTH=640, HEIGHT=480, READ_TIMEOUT_CYCLES=48000000,
 parameter integer MAX_OFFSET=65536,DYNAMIC_SIZE=0,MAX_WIDTH=1280,MAX_HEIGHT=1024
)(
 input wire clk,rst_n,start,
 input wire [31:0] file_size,pixel_offset,file_cluster,data_base,fat_base,cluster_max,
 input wire [7:0] mounted_spc,input wire [3:0] mounted_shift,input wire top_down,
 input wire [15:0] source_width,source_height,
 input wire sd_ready,sd_read_done,input wire [3:0] sd_error,
 input wire data_valid,input wire [8:0] data_index,input wire [7:0] data_byte,
 output reg read_req,output reg [31:0] read_lba,
 output reg pixel_valid,input wire pixel_ready,
 output reg [23:0] pixel_rgb,output reg [15:0] pixel_x,pixel_y,
 output reg busy,done,ok,output reg [3:0] error_code,
 output reg [31:0] pixel_count,payload_crc32
);
 localparam IDLE=0,DATA_FETCH=1,ISSUE=2,ACCEPT=3,READ=4,DISPATCH=5,
 DRAIN=6,EMIT=7,NEXT_SECTOR=8,FAT_FETCH=9,FAT_CHECK=10,HALT=11,META=12,VALIDATE=13,
            FAT_READ0=14,FAT_READ1=15,FAT_READ2=16,FAT_READ3=17,ADDR_SHIFT=18,ADDR_BASE=19,ADDR_SECTOR=20,ADDR_CHECK=21;
 reg [4:0] state;
 (* ram_style="block" *) reg [7:0] buffer[0:511];
 reg [9:0] received;
 reg [8:0] buffer_index;
 reg [31:0] current_cluster,position,timer,crc;
 reg [7:0] sector_in_cluster;
 reg [1:0] phase;
 reg [7:0] blue,green;
 localparam BOUND_W=DYNAMIC_SIZE?MAX_WIDTH:WIDTH,BOUND_H=DYNAMIC_SIZE?MAX_HEIGHT:HEIGHT;
 localparam WW=BOUND_W<2?1:$clog2(BOUND_W+1),HH=BOUND_H<2?1:$clog2(BOUND_H+1);
 localparam STRIDE_MAX=((BOUND_W*3+3)/4)*4;
 localparam STRIDE_W=STRIDE_MAX<2?1:$clog2(STRIDE_MAX+1);
 // Force 64-bit constant math so generic large parameter values cannot wrap.
 localparam RASTER_MAX=64'd1*STRIDE_MAX*BOUND_H;
 localparam RASTER_W=RASTER_MAX<2?1:$clog2(RASTER_MAX+1);
 localparam COUNT_MAX=64'd1*BOUND_W*BOUND_H;
 localparam COUNT_W=COUNT_MAX<2?1:$clog2(COUNT_MAX+1);
 reg [WW-1:0] x;reg [HH-1:0] y;
 reg [WW-1:0] locked_width;reg [HH-1:0] locked_height;
 reg locked_top_down;
 reg [STRIDE_W-1:0] locked_stride;reg [COUNT_W-1:0] expected_pixels;
 reg [RASTER_W-1:0] raster_bytes;
 reg [1:0] padding_left,row_padding;
 wire [31:0] selected_width=DYNAMIC_SIZE?{16'd0,source_width}:WIDTH;
 wire [31:0] selected_height=DYNAMIC_SIZE?{16'd0,source_height}:HEIGHT;
 wire [31:0] selected_stride=((selected_width<<1)+selected_width+32'd3)&32'hfffffffc;
 reg kind_fat,final_fat;
 reg [8:0] fat_offset;
 reg [7:0] buffer_q;
 reg [23:0] fat_value_lo;
 reg [8:0] buffer_rd_addr;
  reg [35:0] addr_work;reg [2:0] addr_shifts;
 wire [35:0] addr_operand=state==ADDR_BASE?{4'd0,data_base}:{28'd0,sector_in_cluster};
 wire [35:0] addr_sum=addr_work+addr_operand;
 wire [32:0] fat_calc={1'b0,fat_base}+{8'b0,current_cluster[31:7]};
 wire [64:0] required={33'd0,pixel_offset}+raster_bytes;
 wire [7:0] value=buffer_q;
 wire [31:0] fat_value={buffer_q,fat_value_lo};
 wire [27:0] next_cluster=fat_value[27:0];
 always @* begin
  buffer_rd_addr=buffer_index;
  case(state)
   DRAIN:buffer_rd_addr=buffer_index+9'd1;
   FAT_READ0:buffer_rd_addr=fat_offset;
   FAT_READ1:buffer_rd_addr=fat_offset+9'd1;
   FAT_READ2:buffer_rd_addr=fat_offset+9'd2;
   FAT_READ3:buffer_rd_addr=fat_offset+9'd3;
   default:buffer_rd_addr=buffer_index;
  endcase
 end
 // Synchronous simple-dual-port RAM: one byte written during the CRC
 // quarantine phase and one byte read per cycle during payload drain.
 always @(posedge clk) begin
  buffer_q<=buffer[buffer_rd_addr];
  if(rst_n&&state==READ&&data_valid&&received<512&&data_index==received[8:0])
   buffer[data_index]<=data_byte;
 end
 function [31:0] crc_byte;
  input [31:0] prior;input [7:0] byte_in;reg [31:0] c;integer k;
  begin c=prior^{24'b0,byte_in};for(k=0;k<8;k=k+1) c=c[0] ? (c>>1)^32'hedb88320 : c>>1;crc_byte=c;end
 endfunction
 task fail;input [3:0] code;
  begin error_code<=code;busy<=0;done<=1;ok<=0;pixel_valid<=0;read_req<=0;state<=HALT;end
 endtask
 task after_byte;
  begin
   position<=position+1'b1;buffer_index<=buffer_index+1'b1;
   if(buffer_index==511) state<=NEXT_SECTOR;
  end
 endtask
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=IDLE;addr_work<=0;addr_shifts<=0;read_req<=0;read_lba<=0;pixel_valid<=0;pixel_rgb<=0;pixel_x<=0;pixel_y<=0;
   busy<=0;done<=0;ok<=0;error_code<=0;pixel_count<=0;payload_crc32<=0;
   received<=0;buffer_index<=0;current_cluster<=0;position<=0;timer<=0;crc<=32'hffffffff;
   sector_in_cluster<=0;phase<=0;blue<=0;green<=0;x<=0;y<=0;kind_fat<=0;final_fat<=0;fat_offset<=0;
   locked_width<=0;locked_height<=0;locked_top_down<=0;locked_stride<=0;
   expected_pixels<=0;raster_bytes<=0;padding_left<=0;row_padding<=0;
  end else begin
   read_req<=0;
   if(busy && sd_error!=0) fail(1);
   else begin
    // Single ordered sector capture. Metadata is held stable by the probe.
    if(state==READ && data_valid) begin
     if(received>=512 || data_index!=received[8:0]) fail(3);
     else received<=received+1'b1;
    end
    // Index failure has priority over simultaneous completion.
    if(!(state==READ && data_valid && (received>=512 || data_index!=received[8:0]))) begin
     case(state)
      IDLE:if(start) begin
       if(selected_width==0 || selected_height==0 || selected_width>65535 || selected_height>65535 ||
          (DYNAMIC_SIZE && (MAX_WIDTH<1 || MAX_WIDTH>65535 || MAX_HEIGHT<1 || MAX_HEIGHT>65535 ||
                           selected_width>MAX_WIDTH || selected_height>MAX_HEIGHT)) ||
          (!DYNAMIC_SIZE && (WIDTH<4 || WIDTH%4!=0)) ||
          pixel_offset<54 || pixel_offset>MAX_OFFSET ||
          file_cluster<2 || file_cluster>cluster_max || file_cluster>=32'h0ffffff0 ||
          mounted_shift>7 || mounted_spc!=(8'd1<<mounted_shift)) fail(2);
       else begin
        busy<=1;current_cluster<=file_cluster;y<=top_down?0:selected_height-1'b1;
        locked_width<=selected_width[15:0];locked_height<=selected_height[15:0];locked_top_down<=top_down;
        locked_stride<=selected_stride;row_padding<=selected_stride-selected_width*3;state<=META;
       end
      end
      META:begin
       raster_bytes<=locked_stride*locked_height;
       expected_pixels<=locked_width*locked_height;state<=VALIDATE;
      end
      VALIDATE:if(required>65'hffffffff || required!={33'd0,file_size}) fail(2);else state<=DATA_FETCH;
      DATA_FETCH:begin
       addr_work<={4'd0,current_cluster}-36'd2;addr_shifts<=mounted_shift[2:0];state<=ADDR_SHIFT;
      end
      ADDR_SHIFT:if(addr_shifts==0)state<=ADDR_BASE;
       else begin addr_work<=addr_work<<1;addr_shifts<=addr_shifts-1'b1;end
      ADDR_BASE:begin addr_work<=addr_sum;state<=ADDR_SECTOR;end
      ADDR_SECTOR:begin addr_work<=addr_sum;state<=ADDR_CHECK;end
      ADDR_CHECK:if(addr_work[35:32]!=0)fail(4);
       else begin read_lba<=addr_work[31:0];kind_fat<=0;timer<=0;state<=ISSUE;end
      ISSUE:begin
       if(sd_ready) begin read_req<=1;timer<=0;received<=0;state<=ACCEPT;end
       else if(timer==READ_TIMEOUT_CYCLES-1) fail(5);else timer<=timer+1'b1;
      end
      ACCEPT:begin
       if(!sd_ready) begin timer<=0;state<=READ;end
       else if(timer==READ_TIMEOUT_CYCLES-1) fail(5);else timer<=timer+1'b1;
      end
      READ:begin
       if(sd_ready && sd_read_done) begin
        if(received!=512) fail(3);else begin buffer_index<=0;state<=DISPATCH;end
       end else if(timer==READ_TIMEOUT_CYCLES-1) fail(5);else timer<=timer+1'b1;
      end
      DISPATCH:if(kind_fat) state<=FAT_READ0;else state<=DRAIN;
      FAT_READ0:state<=FAT_READ1;
      FAT_READ1:begin fat_value_lo[7:0]<=buffer_q;state<=FAT_READ2;end
      FAT_READ2:begin fat_value_lo[15:8]<=buffer_q;state<=FAT_READ3;end
      FAT_READ3:begin fat_value_lo[23:16]<=buffer_q;state<=FAT_CHECK;end
      DRAIN:begin
       after_byte;
       if(position>=pixel_offset) begin
        crc<=crc_byte(crc,value);
        if(padding_left!=0) begin
         padding_left<=padding_left-1'b1;
         if(position+33'd1=={1'b0,file_size}) begin
          payload_crc32<=~crc_byte(crc,value);final_fat<=1;state<=FAT_FETCH;
         end
        end else case(phase)
         0:begin blue<=value;phase<=1;end
         1:begin green<=value;phase<=2;end
         2:begin
          pixel_rgb<={value,green,blue};pixel_x<=x;pixel_y<=y;pixel_valid<=1;phase<=0;state<=EMIT;
         end
         default:fail(15);
        endcase
       end
      end
      EMIT:if(pixel_ready) begin
       pixel_valid<=0;pixel_count<={{(32-COUNT_W){1'b0}},(pixel_count[COUNT_W-1:0]+1'b1)};
       if(x==locked_width-1) begin
        x<=0;y<=locked_top_down?y+1'b1:y-1'b1;padding_left<=row_padding;
       end else x<=x+1'b1;
       if(position==file_size) begin
        payload_crc32<=~crc;final_fat<=1;state<=FAT_FETCH;
       end else if(buffer_index==0) state<=NEXT_SECTOR;else state<=DRAIN;
      end
      NEXT_SECTOR:begin
       if(sector_in_cluster+9'd1<{1'b0,mounted_spc}) begin sector_in_cluster<=sector_in_cluster+1'b1;state<=DATA_FETCH;end
       else begin final_fat<=0;state<=FAT_FETCH;end
      end
      FAT_FETCH:begin
       if(fat_calc[32]) fail(4);
       else begin
        read_lba<=fat_calc[31:0];kind_fat<=1;fat_offset<={current_cluster[6:0],2'b00};timer<=0;state<=ISSUE;
       end
      end
      FAT_CHECK:begin
       if(final_fat) begin
        if(next_cluster<28'hffffff8) fail(7); // Includes over-allocation/cycles: intentionally unsupported.
        else if(pixel_count!=expected_pixels) fail(8);
        else begin busy<=0;done<=1;ok<=1;state<=HALT;end
       end else if(next_cluster<2 || next_cluster>=28'hffffff0 || {4'b0,next_cluster}>cluster_max) fail(6);
       else begin current_cluster<={4'b0,next_cluster};sector_in_cluster<=0;state<=DATA_FETCH;end
      end
      HALT:begin end
      default:fail(15);
     endcase
    end
   end
  end
 end
endmodule
