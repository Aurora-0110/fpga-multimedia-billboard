// v019: read-only FAT32 root A.BMP header probe, 512-byte sectors only.
// Stream fields are provisional until SD reader ready && read_done (CRC16 OK).
// No file data playback, writes, erase, directory recursion, exFAT or FAT16.
`timescale 1ns/1ps
module fat32_bmp_probe #(
 parameter integer RUNTIME_NAME=0, MAX_DIR_SECTORS=128,
 INIT_TIMEOUT_CYCLES=240000000,READ_TIMEOUT_CYCLES=48000000,
 DYNAMIC_SIZE=0,MAX_WIDTH=1280,MAX_HEIGHT=1024,MAX_OFFSET=65536
)(input wire clk,rst_n,
 input wire [7:0] file_letter,
 input wire sd_ready,sd_read_done,input wire [3:0] sd_error,
 input wire data_valid,input wire [8:0] data_index,input wire [7:0] data_byte,
 output reg read_req,output reg [31:0] read_lba,
 output reg mounted,file_found,bmp_ok,done,top_down,
 output reg [3:0] error_code,output reg [31:0] file_size,pixel_offset,
 output reg [31:0] file_cluster,output reg [15:0] sectors_scanned,
 output reg [31:0] data_base,fat_base,cluster_max,
 output reg [7:0] mounted_spc,output reg [3:0] mounted_shift,
 output reg [15:0] source_width,source_height,output reg [31:0] row_stride);
 localparam WAIT_INIT=0,ISSUE=1,ACCEPT=2,READ=3,DISPATCH=4,GEOMETRY=5,HALT=6,GEOM_OVERHEAD=7,GEOM_SUBTRACT=8,GEOM_SHIFT=9,GEOM_CHECK=10,GEOM_COMMIT=11;
 localparam BOOT0=0,VBR=1,ROOT=2,FAT=3,BMP=4;
 localparam BMP_STRIDE=12,BMP_PAYLOAD=13,BMP_COMMIT=14;
 reg [3:0] state;reg [2:0] kind;
 reg [31:0] timer,partition_start,partition_size,root_cluster;
 reg [7:0] root_sector;reg [8:0] fat_offset;reg [31:0] fat_value;
 reg partitioned;
 reg [7:0] jump,spc,nfats,mbr_type[0:3];
 reg [15:0] bps,reserved,root_entries,total16,fat16,ext_flags,fs_version,boot_signature;
 reg [31:0] total32,fatsz,root0,mbr_lba[0:3],mbr_size[0:3];
 reg [15:0] bmp_signature,planes,bpp;
 reg [31:0] bmp_size,bmp_offset,dib_size,width,height,compression,image_size;
 reg entry_name_ok,entry_attr_ok,sector_found,sector_end;
 reg [7:0] entry_first;
 reg [31:0] entry_cluster,entry_size,candidate_cluster,candidate_size;
 reg [7:0] locked_letter;
 reg name_locked;
 integer n;
 integer j;
 function [7:0] name_byte;input [3:0] pos;
  begin case(pos) 0:name_byte=locked_letter;8:name_byte="B";9:name_byte="M";10:name_byte="P";default:name_byte=" ";endcase end
 endfunction
 reg [3:0] spc_shift;reg spc_valid;
 always @* begin
  spc_valid=1;
  case(spc)
   1:spc_shift=0;2:spc_shift=1;4:spc_shift=2;8:spc_shift=3;
   16:spc_shift=4;32:spc_shift=5;64:spc_shift=6;128:spc_shift=7;
   default:begin spc_shift=0;spc_valid=0;end
  endcase
 end
 reg mbr_found;reg [31:0] selected_start,selected_size;
 always @* begin
  mbr_found=0;selected_start=0;selected_size=0;
  for(j=0;j<4;j=j+1) begin
   if(!mbr_found && (mbr_type[j]==8'h0b || mbr_type[j]==8'h0c)) begin
    mbr_found=1;selected_start=mbr_lba[j];selected_size=mbr_size[j];
   end
  end
 end
 // v057: bounded multi-cycle BPB geometry computation, not a timing exception.
 // All fields below are private until GEOM_COMMIT; CRC validation still precedes GEOMETRY.
 reg [32:0] fat_sectors,overhead,data_sectors,cluster_count,volume_end,partition_end;
 reg [39:0] fat_capacity,root_minus_two,root_offset,root_base,root_lba_calc;
 reg [31:0] fat_base_partial,fat_base_calc;
 reg geometry_bad;
 wire [27:0] next_cluster=fat_value[27:0];
 wire [32:0] bmp_required={1'b0,bmp_offset}+33'd921600;
 wire [32:0] dib_end={1'b0,dib_size}+33'd14;
 wire [31:0] absolute_height=height[31]?(32'd0-height):height;
 reg [15:0] parsed_width,parsed_height;
 reg [31:0] parsed_stride;
 reg [63:0] raster_bytes;
 wire [64:0] dynamic_required={33'd0,bmp_offset}+{1'b0,raster_bytes};
 task fail;input [3:0] code;
  begin error_code<=code;done<=1;state<=HALT;end
 endtask
 task fetch;input [31:0] lba;input [2:0] typ;
  begin read_lba<=lba;kind<=typ;timer<=0;state<=ISSUE;end
 endtask
 // Reset parsing registers each request, never the previously CRC-committed progress flags.
 task clear_sector;
  begin
   jump<=0;spc<=0;nfats<=0;bps<=0;reserved<=0;root_entries<=0;total16<=0;fat16<=0;
   ext_flags<=0;fs_version<=0;boot_signature<=0;total32<=0;fatsz<=0;root0<=0;
   // Mounted geometry uses dedicated registers, not these scratch fields.
   bmp_signature<=0;planes<=0;bpp<=0;bmp_size<=0;bmp_offset<=0;dib_size<=0;
   width<=0;height<=0;compression<=0;image_size<=0;fat_value<=0;
   sector_found<=0;sector_end<=0;entry_name_ok<=0;entry_attr_ok<=0;
   entry_first<=0;entry_cluster<=0;entry_size<=0;candidate_cluster<=0;candidate_size<=0;
   for(n=0;n<4;n=n+1) begin mbr_type[n]<=0;mbr_lba[n]<=0;mbr_size[n]<=0;end
  end
 endtask

 // Only mounted geometry is used after BPB validation, unaffected by scratch reset.
 wire [39:0] file_lba={8'b0,data_base}+(({8'b0,candidate_cluster}-40'd2)<<mounted_shift);
 wire [39:0] chained_root_lba={8'b0,data_base}+(({12'b0,next_cluster}-40'd2)<<mounted_shift);
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   locked_letter<="A";name_locked<=0;
   state<=WAIT_INIT;kind<=BOOT0;timer<=0;read_req<=0;read_lba<=0;
   mounted<=0;file_found<=0;bmp_ok<=0;done<=0;top_down<=0;error_code<=0;
   file_size<=0;pixel_offset<=0;file_cluster<=0;sectors_scanned<=0;
   source_width<=0;source_height<=0;row_stride<=0;
   parsed_width<=0;parsed_height<=0;parsed_stride<=0;raster_bytes<=0;
   partition_start<=0;partition_size<=0;partitioned<=0;data_base<=0;fat_base<=0;
   cluster_max<=0;root_cluster<=0;root_sector<=0;fat_offset<=0;mounted_spc<=0;mounted_shift<=0;
   fat_sectors<=0;overhead<=0;data_sectors<=0;cluster_count<=0;volume_end<=0;partition_end<=0;
   fat_capacity<=0;root_minus_two<=0;root_offset<=0;root_base<=0;root_lba_calc<=0;
   fat_base_partial<=0;fat_base_calc<=0;geometry_bad<=0;
   clear_sector;
  end else begin
   if(!name_locked) begin locked_letter<=RUNTIME_NAME?file_letter:8'h41;name_locked<=1;end
   read_req<=0;
   if(data_valid && state==READ) begin
    if(kind==BOOT0 || kind==VBR) begin
     case(data_index)
      0:jump<=data_byte;
      11:bps[7:0]<=data_byte;12:bps[15:8]<=data_byte;13:spc<=data_byte;
      14:reserved[7:0]<=data_byte;15:reserved[15:8]<=data_byte;16:nfats<=data_byte;
      17:root_entries[7:0]<=data_byte;18:root_entries[15:8]<=data_byte;
      19:total16[7:0]<=data_byte;20:total16[15:8]<=data_byte;
      22:fat16[7:0]<=data_byte;23:fat16[15:8]<=data_byte;
      32:total32[7:0]<=data_byte;33:total32[15:8]<=data_byte;
      34:total32[23:16]<=data_byte;35:total32[31:24]<=data_byte;
      36:fatsz[7:0]<=data_byte;37:fatsz[15:8]<=data_byte;
      38:fatsz[23:16]<=data_byte;39:fatsz[31:24]<=data_byte;
      40:ext_flags[7:0]<=data_byte;41:ext_flags[15:8]<=data_byte;
      42:fs_version[7:0]<=data_byte;43:fs_version[15:8]<=data_byte;
      44:root0[7:0]<=data_byte;45:root0[15:8]<=data_byte;
      46:root0[23:16]<=data_byte;47:root0[31:24]<=data_byte;
      510:boot_signature[7:0]<=data_byte;511:boot_signature[15:8]<=data_byte;
      default:begin end
     endcase
     for(n=0;n<4;n=n+1) begin
      if(data_index==450+n*16) mbr_type[n]<=data_byte;
      if(data_index==454+n*16) mbr_lba[n][7:0]<=data_byte;
      if(data_index==455+n*16) mbr_lba[n][15:8]<=data_byte;
      if(data_index==456+n*16) mbr_lba[n][23:16]<=data_byte;
      if(data_index==457+n*16) mbr_lba[n][31:24]<=data_byte;
      if(data_index==458+n*16) mbr_size[n][7:0]<=data_byte;
      if(data_index==459+n*16) mbr_size[n][15:8]<=data_byte;
      if(data_index==460+n*16) mbr_size[n][23:16]<=data_byte;
      if(data_index==461+n*16) mbr_size[n][31:24]<=data_byte;
     end
    end else if(kind==ROOT) begin
     if(data_index[4:0]==0) begin entry_first<=data_byte;entry_name_ok<=data_byte==name_byte(0);entry_cluster<=0;entry_size<=0;entry_attr_ok<=0;end
     else if(data_index[4:0]<=10) entry_name_ok<=entry_name_ok && data_byte==name_byte(data_index[3:0]);
     case(data_index[4:0])
      11:entry_attr_ok<=(data_byte & 8'h18)==0;
      20:entry_cluster[23:16]<=data_byte;21:entry_cluster[31:24]<=data_byte;
      26:entry_cluster[7:0]<=data_byte;27:entry_cluster[15:8]<=data_byte;
      28:entry_size[7:0]<=data_byte;29:entry_size[15:8]<=data_byte;30:entry_size[23:16]<=data_byte;
      31:begin
       if(entry_first==0) sector_end<=1;
       if(!sector_end && !sector_found && entry_first!=0 && entry_first!=8'he5 && entry_name_ok && entry_attr_ok) begin
        sector_found<=1;candidate_cluster<={4'b0,entry_cluster[27:0]};candidate_size<={data_byte,entry_size[23:0]};
       end
      end
      default:begin end
     endcase
    end else if(kind==FAT) begin
     if(data_index==fat_offset) fat_value[7:0]<=data_byte;
     if({1'b0,data_index}=={1'b0,fat_offset}+10'd1) fat_value[15:8]<=data_byte;
     if({1'b0,data_index}=={1'b0,fat_offset}+10'd2) fat_value[23:16]<=data_byte;
     if({1'b0,data_index}=={1'b0,fat_offset}+10'd3) fat_value[31:24]<=data_byte;
    end else if(kind==BMP) begin
     case(data_index)
      0:bmp_signature[7:0]<=data_byte;1:bmp_signature[15:8]<=data_byte;
      2:bmp_size[7:0]<=data_byte;3:bmp_size[15:8]<=data_byte;4:bmp_size[23:16]<=data_byte;5:bmp_size[31:24]<=data_byte;
      10:bmp_offset[7:0]<=data_byte;11:bmp_offset[15:8]<=data_byte;12:bmp_offset[23:16]<=data_byte;13:bmp_offset[31:24]<=data_byte;
      14:dib_size[7:0]<=data_byte;15:dib_size[15:8]<=data_byte;16:dib_size[23:16]<=data_byte;17:dib_size[31:24]<=data_byte;
      18:width[7:0]<=data_byte;19:width[15:8]<=data_byte;20:width[23:16]<=data_byte;21:width[31:24]<=data_byte;
      22:height[7:0]<=data_byte;23:height[15:8]<=data_byte;24:height[23:16]<=data_byte;25:height[31:24]<=data_byte;
      26:planes[7:0]<=data_byte;27:planes[15:8]<=data_byte;
      28:bpp[7:0]<=data_byte;29:bpp[15:8]<=data_byte;
      30:compression[7:0]<=data_byte;31:compression[15:8]<=data_byte;32:compression[23:16]<=data_byte;33:compression[31:24]<=data_byte;
      34:image_size[7:0]<=data_byte;35:image_size[15:8]<=data_byte;36:image_size[23:16]<=data_byte;37:image_size[31:24]<=data_byte;
      default:begin end
     endcase
    end
   end
   if(state!=HALT && sd_error!=0) fail(1);
   else case(state)
    WAIT_INIT:if(sd_ready) fetch(0,BOOT0);
      else if(timer==INIT_TIMEOUT_CYCLES-1) fail(13);else timer<=timer+1'b1;
    ISSUE:if(sd_ready) begin clear_sector;read_req<=1;timer<=0;state<=ACCEPT;end
      else if(timer==READ_TIMEOUT_CYCLES-1) fail(13);else timer<=timer+1'b1;
    ACCEPT:if(!sd_ready) begin timer<=0;state<=READ;end
      else if(timer==READ_TIMEOUT_CYCLES-1) fail(13);else timer<=timer+1'b1;
    READ:if(sd_ready && sd_read_done) begin timer<=0;state<=DISPATCH;end
      else if(timer==READ_TIMEOUT_CYCLES-1) fail(13);else timer<=timer+1'b1;
    DISPATCH:case(kind)
     BOOT0:begin
      if(boot_signature!=16'haa55) fail(2);
      else if((jump==8'heb || jump==8'he9) && bps==512) state<=GEOMETRY;
      else if(!mbr_found || selected_start==0 || selected_size==0 || ({1'b0,selected_start}+{1'b0,selected_size})>33'h100000000) fail(2);
      else begin partitioned<=1;partition_start<=selected_start;partition_size<=selected_size;fetch(selected_start,VBR);end
     end
     VBR:if(boot_signature!=16'haa55) fail(2);else state<=GEOMETRY;
     ROOT:begin
      sectors_scanned<=sectors_scanned+1'b1;
      if(sector_found) begin
       if(candidate_cluster<2 || candidate_cluster>cluster_max || candidate_size<54 || file_lba>40'hffffffff) fail(8);
       else begin file_found<=1;file_cluster<=candidate_cluster;file_size<=candidate_size;fetch(file_lba[31:0],BMP);end
      end else if(sector_end) fail(5);
      else if(sectors_scanned+1>=MAX_DIR_SECTORS) fail(7);
      else if(root_sector+9'd1<mounted_spc) begin root_sector<=root_sector+1'b1;fetch(read_lba+1'b1,ROOT);end
      else begin fat_offset<={root_cluster[6:0],2'b00};fetch(fat_base+(root_cluster>>7),FAT);end
     end
     FAT:if(next_cluster>=28'hffffff8) fail(5);
      else if(next_cluster<2 || next_cluster>cluster_max || next_cluster>=28'hffffff0 || chained_root_lba>40'hffffffff) fail(6);
      else begin root_cluster<={4'b0,next_cluster};root_sector<=0;fetch(chained_root_lba[31:0],ROOT);end
     BMP:begin
      if(bmp_signature!=16'h4d42) fail(9);
      else if(dib_size<40 || planes!=1 || bpp!=24 || compression!=0) fail(10);
      else if(DYNAMIC_SIZE) begin
       if(MAX_WIDTH<1 || MAX_WIDTH>65535 || MAX_HEIGHT<1 || MAX_HEIGHT>65535 ||
          width==0 || width[31] || width>MAX_WIDTH ||
          absolute_height==0 || height==32'h80000000 || absolute_height>MAX_HEIGHT) fail(11);
       else begin parsed_width<=width[15:0];parsed_height<=absolute_height[15:0];state<=BMP_STRIDE;end
      end else if(width!=640 || (height!=480 && height!=32'hfffffe20)) fail(11);
      else if(dib_end>{1'b0,bmp_offset} || bmp_required>{1'b0,file_size} ||
              bmp_required>{1'b0,bmp_size} || bmp_size>file_size ||
              (image_size!=0 && image_size!=921600)) fail(12);
      else begin
       bmp_ok<=1;pixel_offset<=bmp_offset;top_down<=height[31];done<=1;state<=HALT;
       source_width<=640;source_height<=480;row_stride<=1920;
      end
     end
     default:fail(15);
    endcase
    GEOMETRY:begin
     if((jump!=8'heb && jump!=8'he9) || bps!=512 || !spc_valid || reserved==0 ||
       (nfats!=1 && nfats!=2) || root_entries!=0 || total16!=0 || fat16!=0 ||
       fs_version!=0 || fatsz==0 || (ext_flags[7] && {4'b0,ext_flags[3:0]}>=nfats)) fail(3);
     else begin
      fat_sectors<={1'b0,fatsz} << ((nfats==2)?1:0);
      volume_end<={1'b0,partition_start}+{1'b0,total32};
      partition_end<={1'b0,partition_start}+{1'b0,partition_size};
      fat_capacity<={8'b0,fatsz}<<7;
      root_minus_two<={12'b0,root0[27:0]}-40'd2;
      fat_base_partial<=partition_start+reserved;
      state<=GEOM_OVERHEAD;
     end
    end
    GEOM_OVERHEAD:begin
     overhead<={17'b0,reserved}+fat_sectors;
     root_offset<=root_minus_two<<spc_shift;
     fat_base_calc<=fat_base_partial+((ext_flags[7] && ext_flags[3:0]==1)?fatsz:0);
     state<=GEOM_SUBTRACT;
    end
    GEOM_SUBTRACT:begin
     data_sectors<={1'b0,total32}-overhead;
     root_base<={8'b0,partition_start}+overhead;
     state<=GEOM_SHIFT;
    end
    GEOM_SHIFT:begin
     cluster_count<=data_sectors>>spc_shift;
     root_lba_calc<=root_base+root_offset;
     state<=GEOM_CHECK;
    end
    GEOM_CHECK:begin
     geometry_bad<=overhead>={1'b0,total32} || cluster_count<65525 || cluster_count>33'h0fffffee ||
       fat_capacity<cluster_count+2 || volume_end>33'h100000000 ||
       (partitioned && (total32>partition_size || volume_end>partition_end)) ||
       root0[31:28]!=0 || root0<2 || {1'b0,root0}>cluster_count+1 || root_lba_calc>40'hffffffff;
     state<=GEOM_COMMIT;
    end
    GEOM_COMMIT:begin
     if(geometry_bad) fail(4);
     else begin
      data_base<=root_base[31:0];fat_base<=fat_base_calc;
      cluster_max<=cluster_count[31:0]+1;
      root_cluster<=root0;mounted_spc<=spc;mounted_shift<=spc_shift;
      mounted<=1;root_sector<=0;fetch(root_lba_calc[31:0],ROOT);
     end
    end
    BMP_STRIDE:begin
     parsed_stride<=(({16'd0,parsed_width}<<1)+{16'd0,parsed_width}+32'd3)&32'hfffffffc;
     state<=BMP_PAYLOAD;
    end
    BMP_PAYLOAD:begin raster_bytes<={32'd0,parsed_stride}*{48'd0,parsed_height};state<=BMP_COMMIT;end
    BMP_COMMIT:begin
     if(bmp_offset<54 || bmp_offset>MAX_OFFSET || dib_end>{1'b0,bmp_offset} ||
        dynamic_required>65'hffffffff || dynamic_required!={33'd0,file_size} ||
        dynamic_required>{33'd0,bmp_size} || bmp_size>file_size ||
        (image_size!=0 && {32'd0,image_size}!=raster_bytes)) fail(12);
     else begin
      source_width<=parsed_width;source_height<=parsed_height;row_stride<=parsed_stride;
      pixel_offset<=bmp_offset;top_down<=height[31];bmp_ok<=1;done<=1;state<=HALT;
     end
    end
    HALT:begin end
    default:fail(15);
   endcase
  end
 end
endmodule
