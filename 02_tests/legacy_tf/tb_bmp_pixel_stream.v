`timescale 1ns/1ps
module tb_bmp_pixel_stream;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0;
`ifdef FULL_IMAGE
 localparam W=640,H=480;
`else
 localparam W=4,H=3;
`endif
 reg [31:0] file_size,pixel_offset=54,file_cluster=3,data_base=1000000,fat_base=10,cluster_max=65526;
 reg [7:0] mounted_spc=1;reg [3:0] mounted_shift=0;reg top_down=0;
 reg sd_ready=0,sd_read_done=1;reg [3:0] sd_error=0;
 wire [15:0] source_width=W,source_height=H;
 reg data_valid=0;reg [8:0] data_index=0;reg [7:0] data_byte=0;
 wire read_req,pixel_valid,busy,done,ok;wire [31:0] read_lba,pixel_count,payload_crc32;
 reg pixel_ready=1;wire [23:0] pixel_rgb;wire [15:0] pixel_x,pixel_y;wire [3:0] error_code;
 bmp_pixel_stream #(.WIDTH(W),.HEIGHT(H),.READ_TIMEOUT_CYCLES(3000)) dut(.*);
 reg [7:0] ref_file[0:921653];
 string ref_path;integer mode=0,offset_arg=54,spc_arg=1,top_arg=0,expected_error=0;
 integer expected_crc,seen,cycle,server=0,request_count=0,byte_pos=0,logical_sector=0,cl_index=0,cl_sector=0;
 integer fat_requested=0,target_cluster=0,next_c=0,fatbyte=0,global_byte=0;
 integer crc_fail_read=0,saved_requests,saved_seen;
 reg [55:0] held_pixel;reg held=0;reg committed=0;
 function [7:0] payload_byte;input integer pos;
  begin
`ifdef FULL_IMAGE
   payload_byte=ref_file[pos+54];
`else
   payload_byte=(pos*17+11)&255;
`endif
  end
 endfunction
 function [7:0] sector_byte;input integer pos;
  integer t,entry_cluster,entry_index,link,which,fs;
  begin
   if(!fat_requested) begin
    fs=logical_sector*512+pos;
    sector_byte=(fs>=pixel_offset && fs<file_size)?payload_byte(fs-pixel_offset):8'hcc;
   end else begin
    t=(read_lba-fat_base)*128+(pos/4);which=pos%4;
    // File chain: 3 -> 140 -> 277 -> ... (deliberately fragmented FAT sectors).
    entry_cluster=t;
    entry_index=(entry_cluster-3)/137;
    if(entry_cluster>=3 && (entry_cluster-3)%137==0) begin
     if((entry_index+1)*mounted_spc*512>=file_size) link=32'h0fffffff;
     else link=entry_cluster+137;
     if(mode==5) link=0;
     if(mode==6) link=32'h0ffffff7;
     if(mode==7) link=32'h0fffffff;
     if(mode==8) link=3;
     if(mode==21) link=entry_cluster+137;
     if(mode==24) link=cluster_max+1;
     if(mode==25) link=32'h0ffffff0;
     sector_byte=(link>>(which*8))&255;
    end else sector_byte=0;
   end
  end
 endfunction
 always @(posedge clk) begin
  data_valid<=0;
  if(!rst_n) begin sd_ready<=0;sd_read_done<=1;sd_error<=0;server<=0;request_count<=0;committed<=0;end
  else case(server)
   0:if(mode!=13) begin sd_ready<=1;server<=1;end
   1:if(read_req) begin
    request_count<=request_count+1;committed<=0;
    if(mode==14) server<=9;
    else begin
     sd_ready<=0;sd_read_done<=0;byte_pos<=0;
     if(read_lba>=data_base) begin
      fat_requested=0;
      target_cluster=((read_lba-data_base)/mounted_spc)+2;
      cl_index=(target_cluster-3)/137;cl_sector=(read_lba-data_base)%mounted_spc;
      if(target_cluster<3 || (target_cluster-3)%137!=0) $fatal(1,"Invalid data LBA %0d",read_lba);
      logical_sector=cl_index*mounted_spc+cl_sector;
      if(logical_sector*512>=file_size) $fatal(1,"Read beyond logical file");
     end else fat_requested=1;
     if(mode==15) server<=9;else server<=2;
    end
   end
   2:begin
    data_valid<=1;data_index<=byte_pos;data_byte<=sector_byte(byte_pos);
    if(mode==9 && byte_pos==20) data_index<=19;
    if(mode==10 && byte_pos==0) data_index<=1;
    if(mode==11 && byte_pos==100) begin data_valid<=0;end
    if(byte_pos==511) server<=3;else byte_pos<=byte_pos+1;
   end
   3:begin // Wait beyond final provisional byte; no committed pixel should exist yet.
    if(!committed && request_count==1 && seen!=0) $fatal(1,"Pixel leaked before CRC commit");
    if((mode==12 && request_count==1)||(mode==23 && request_count==2)) begin sd_error<=10;server<=9;end
    else begin sd_ready<=1;sd_read_done<=1;committed<=1;server<=1;end
   end
   default:begin end
  endcase
 end
 always @(negedge clk) begin
  if(!rst_n) begin seen=0;cycle=0;held=0;pixel_ready=1;end
  else begin
   cycle=cycle+1;
   // Regular and multi-cycle backpressure, also at the last pixel.
   pixel_ready=(cycle%11>=4);
   if(held && (!pixel_valid || {pixel_rgb,pixel_x,pixel_y}!==held_pixel)) $fatal(1,"Unstable backpressured pixel");
   held=pixel_valid && !pixel_ready;held_pixel={pixel_rgb,pixel_x,pixel_y};
  end
 end
 always @(posedge clk) if(rst_n && pixel_valid && pixel_ready) begin
  if(seen>=W*H) $fatal(1,"Too many pixels");
  if(mode!=8 && pixel_rgb!=={payload_byte(seen*3+2),payload_byte(seen*3+1),payload_byte(seen*3)}) $fatal(1,"Wrong RGB pixel %0d",seen);
  if(mode!=8 && (pixel_x!==seen%W || pixel_y!==(top_down?seen/W:H-1-seen/W))) $fatal(1,"Wrong coordinates %0d (%0d,%0d)",seen,pixel_x,pixel_y);
  seen=seen+1;
 end
 initial begin
  if(!$value$plusargs("MODE=%d",mode)) mode=0;
  if(!$value$plusargs("OFFSET=%d",offset_arg)) offset_arg=54;
  if(!$value$plusargs("SPC=%d",spc_arg)) spc_arg=1;
  if(!$value$plusargs("TOP=%d",top_arg)) top_arg=0;
  if(!$value$plusargs("ERROR=%d",expected_error)) expected_error=0;
  if(!$value$plusargs("CRC=%h",expected_crc)) $fatal(1,"Missing expected CRC");
`ifdef FULL_IMAGE
  if(!$value$plusargs("REF=%s",ref_path)) $fatal(1,"Missing reference image");
  $readmemh(ref_path,ref_file);
`endif
  pixel_offset=offset_arg;file_size=offset_arg+W*H*3;mounted_spc=spc_arg;top_down=top_arg;
  case(spc_arg) 1:mounted_shift=0;2:mounted_shift=1;4:mounted_shift=2;8:mounted_shift=3;128:mounted_shift=7;default:mounted_shift=0;endcase
  if(mode==16) file_size=file_size-1;
  if(mode==17) data_base=32'hffffffff;
  if(mode==18) mounted_spc=3;
  if(mode==19) file_cluster=1;
  if(mode==20) pixel_offset=0;
  repeat(5) @(negedge clk);rst_n=1;repeat(3) @(negedge clk);start=1;
  wait(done);repeat(4) @(negedge clk);
  if(error_code!==expected_error || ok!==(expected_error==0) || busy || pixel_valid || read_req) $fatal(1,"Result err=%0d expected=%0d ok=%b",error_code,expected_error,ok);
  if(ok && (seen!=W*H || pixel_count!=W*H || payload_crc32!==expected_crc)) $fatal(1,"Count/CRC failure %0d %0d %08x expected %08x",seen,pixel_count,payload_crc32,expected_crc);
  if((mode==12 || mode==9 || mode==10 || mode==11) && seen!=0) $fatal(1,"Provisional data escaped");
  saved_seen=seen;saved_requests=request_count;
  repeat(80) @(negedge clk);
  if(!done || error_code!==expected_error || request_count!=saved_requests || seen!=saved_seen) $fatal(1,"Result not sticky");
  $display("PASS stream mode=%0d %0dx%0d offset=%0d spc=%0d err=%0d pixels=%0d CRC=%08x reads=%0d",mode,W,H,pixel_offset,mounted_spc,error_code,pixel_count,payload_crc32,request_count);$finish;
 end
 initial begin #100000000;$fatal(1,"Stream TB watchdog");end
endmodule

