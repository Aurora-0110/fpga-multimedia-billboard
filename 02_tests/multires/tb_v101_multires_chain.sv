`timescale 1ns/1ps
module tb_v101_multires_chain;
 parameter STAGE=2,OUT_WIDTH=32,OUT_HEIGHT=18;
 reg clk=0,rst_n=0;
 always #5 clk=~clk;
 reg sd_ready=0,sd_read_done=0,data_valid=0;
 reg [3:0] sd_error=0;
 reg [8:0] data_index=0;
 reg [7:0] data_byte=0;
 wire probe_req,probe_done,mounted,bmp_ok,top_down;
 wire [31:0] probe_lba,file_size,pixel_offset,file_cluster,data_base,fat_base,cluster_max,row_stride;
 wire [15:0] source_width,source_height;
 wire [7:0] mounted_spc;
 wire [3:0] mounted_shift,probe_error,stream_error;
 wire stream_req,stream_done,stream_ok,stream_valid,stream_ready;
 wire [31:0] stream_lba,raw_count,raw_crc;
 wire [23:0] stream_rgb;
 wire [15:0] stream_x,stream_y;
 wire use_pixels=probe_done&&bmp_ok&&STAGE!=0;
 wire read_req=use_pixels?stream_req:probe_req;
 wire [31:0] read_lba=use_pixels?stream_lba:probe_lba;
 wire [7:0] source_error=sd_error!=0?{4'h1,sd_error}:probe_error!=0?{4'h2,probe_error}:stream_error!=0?{4'h3,stream_error}:8'd0;
 wire source_done=source_error!=0||stream_done;
 wire source_ok=stream_done&&stream_ok&&source_error==0;
 fat32_bmp_probe #(.DYNAMIC_SIZE(1),.MAX_WIDTH(2048),.MAX_HEIGHT(2048),.READ_TIMEOUT_CYCLES(3000),.INIT_TIMEOUT_CYCLES(3000)) probe(
 .clk(clk),.rst_n(rst_n),.file_letter(8'h41),.sd_ready(sd_ready),.sd_read_done(sd_read_done),.sd_error(sd_error),
 .data_valid(data_valid),.data_index(data_index),.data_byte(data_byte),.read_req(probe_req),.read_lba(probe_lba),
 .mounted(mounted),.file_found(),.bmp_ok(bmp_ok),.done(probe_done),.top_down(top_down),.error_code(probe_error),
 .file_size(file_size),.pixel_offset(pixel_offset),.file_cluster(file_cluster),.sectors_scanned(),
 .data_base(data_base),.fat_base(fat_base),.cluster_max(cluster_max),.mounted_spc(mounted_spc),.mounted_shift(mounted_shift),
 .source_width(source_width),.source_height(source_height),.row_stride(row_stride));
 bmp_pixel_stream #(.DYNAMIC_SIZE(1),.MAX_WIDTH(2048),.MAX_HEIGHT(2048),.READ_TIMEOUT_CYCLES(3000)) stream(
 .clk(clk),.rst_n(rst_n),.start(use_pixels),.file_size(file_size),.pixel_offset(pixel_offset),.file_cluster(file_cluster),
 .data_base(data_base),.fat_base(fat_base),.cluster_max(cluster_max),.mounted_spc(mounted_spc),.mounted_shift(mounted_shift),
 .top_down(top_down),.source_width(source_width),.source_height(source_height),
 .sd_ready(sd_ready),.sd_read_done(sd_read_done),.sd_error(sd_error),.data_valid(data_valid),.data_index(data_index),.data_byte(data_byte),
 .read_req(stream_req),.read_lba(stream_lba),.pixel_valid(stream_valid),.pixel_ready(stream_ready),
 .pixel_rgb(stream_rgb),.pixel_x(stream_x),.pixel_y(stream_y),.busy(),.done(stream_done),.ok(stream_ok),.error_code(stream_error),
 .pixel_count(raw_count),.payload_crc32(raw_crc));
 reg raw_ready=0;
 wire bridge_ready,scaled_valid,scaled_done,scaled_ok;
 wire [23:0] scaled_rgb;
 wire [15:0] scaled_x,scaled_y;
 wire [7:0] scaled_error;
 wire packer_ready,packed_done,req_valid;
 wire [18:0] req_addr;
 wire [127:0] req_data;
 wire [7:0] packed_error;
 wire [31:0] packed_count,burst_count;
 reg req_ack=0;
 assign stream_ready=STAGE==1?raw_ready:bridge_ready;
 bmp_scale_bridge #(.OUT_WIDTH(OUT_WIDTH),.OUT_HEIGHT(OUT_HEIGHT),.MAX_WIDTH(2048),.MAX_HEIGHT(2048)) bridge(
 .clk(clk),.rst_n(rst_n),.metadata_valid(bmp_ok&&STAGE==2),.source_width(source_width),.source_height(source_height),.top_down(top_down),
 .source_valid(stream_valid&&STAGE==2),.source_ready(bridge_ready),.source_rgb(stream_rgb),
 .source_done(source_done),.source_ok(source_ok),.source_error(source_error),
 .pixel_valid(scaled_valid),.pixel_ready(packer_ready),.pixel_rgb(scaled_rgb),.pixel_x(scaled_x),.pixel_y(scaled_y),
 .done(scaled_done),.ok(scaled_ok),.error_code(scaled_error));
 bmp_pixel_packer #(.WIDTH(OUT_WIDTH),.HEIGHT(OUT_HEIGHT),.DITHER_ENABLE(1)) packer(
 .clk(clk),.rst_n(rst_n),.enable(STAGE==2),.pixel_valid(scaled_valid),.pixel_ready(packer_ready),
 .pixel_rgb(scaled_rgb),.pixel_x(scaled_x),.pixel_y(scaled_y),.source_done(scaled_done),.source_ok(scaled_ok),.source_error(scaled_error),
 .req_valid(req_valid),.req_addr(req_addr),.req_data(req_data),.req_ack(req_ack),.done(packed_done),.error_code(packed_error),
 .pixel_count(packed_count),.burst_count(burst_count));
 reg [7:0] fixture_bytes[0:131071];
 reg [31:0] fixture_lbas[0:255];
 reg [23:0] expected_raw[0:16383],expected_scaled[0:OUT_WIDTH*OUT_HEIGHT-1];
 reg [7:0] expected_indexed[0:OUT_WIDTH*OUT_HEIGHT-1];
 reg written[0:OUT_WIDTH*OUT_HEIGHT/16-1];
 string fixture;
 integer blocks,expected_width,expected_height,expected_stride,expected_top,expected_error,expected_crc;
 integer fault=0,fail_sector=0,retry=0,allow_partial=0,require_drain=0;
 integer server=0,position=0,selected=0,requests=0,cycles=0,seen=0,scaled_seen=0,writes=0;
 integer raw_sector=-1,committed_limit=0,request_is_pixels=0;
 integer pending=0,ack_delay=0,found,index,lane,raw_end,saved_reads,saved_seen,saved_scaled,saved_writes;
 reg drain_observed=0,held_raw=0,held_scaled=0;
 reg [55:0] saved_raw,saved_pixel;
 wire terminal=STAGE==0?probe_done:STAGE==1?source_done:(packed_done||packed_error!=0);
 always @(posedge clk)begin
  data_valid<=0;
  if(!rst_n)begin
   sd_ready<=0;sd_read_done<=0;sd_error<=0;server<=0;requests<=0;committed_limit<=0;
  end else case(server)
   0:begin sd_ready<=1;server<=1;end
   1:if(read_req)begin
    found=-1;
    for(index=0;index<blocks;index=index+1)if(fixture_lbas[index]==read_lba)found=index;
    if(found<0)$fatal(1,"Unexpected LBA %0d",read_lba);
    selected=found;requests<=requests+1;position<=0;sd_ready<=0;sd_read_done<=0;
    request_is_pixels=use_pixels&&read_lba>=data_base+mounted_spc;
    raw_sector=-1;
    if(request_is_pixels)begin
     raw_sector=(((read_lba-data_base)/mounted_spc+2-3)/137)*mounted_spc+(read_lba-data_base)%mounted_spc;
    end
    if(fault==4&&request_is_pixels)server<=9;else server<=2;
   end
   2:begin
    data_valid<=1;data_index<=position;data_byte<=fixture_bytes[selected*512+position];
    if(fault==3&&request_is_pixels&&position==17)data_index<=16;
    if(position==511)server<=3;else position<=position+1;
   end
   3:begin
    if((fault==1&&requests==3)||(fault==2&&request_is_pixels&&raw_sector==fail_sector))begin sd_error<=10;server<=9;end
    else begin
     sd_ready<=1;sd_read_done<=1;server<=1;
     if(request_is_pixels)committed_limit<=(raw_sector+1)*512;
    end
   end
   default:begin end
  endcase
 end
 always @(negedge clk)begin
  if(!rst_n)begin cycles=0;raw_ready=0;held_raw=0;held_scaled=0;end
  else begin
   cycles=cycles+1;raw_ready=(cycles%17>=6)&&(cycles%113<97);
   if(held_raw&&source_error==0&&(!stream_valid||{stream_rgb,stream_x,stream_y}!==saved_raw))$fatal(1,"Raw stall instability");
   if(held_scaled&&scaled_error==0&&(!scaled_valid||{scaled_rgb,scaled_x,scaled_y}!==saved_pixel))$fatal(1,"Scaled stall instability");
   held_raw=stream_valid&&!stream_ready;saved_raw={stream_rgb,stream_x,stream_y};
   held_scaled=scaled_valid&&!packer_ready;saved_pixel={scaled_rgb,scaled_x,scaled_y};
  end
 end
 always @(posedge clk)begin
  if(!rst_n)begin
   seen=0;scaled_seen=0;writes=0;pending=0;req_ack<=0;drain_observed=0;
   for(lane=0;lane<OUT_WIDTH*OUT_HEIGHT/16;lane=lane+1)written[lane]=0;
  end else begin
   if(stream_valid&&stream_ready)begin
    if(seen>=expected_width*expected_height)$fatal(1,"Too many raw pixels");
    if(stream_rgb!==expected_raw[seen])$fatal(1,"RGB mismatch raw pixel %0d",seen);
    if(stream_x!==seen%expected_width||stream_y!==(expected_top?seen/expected_width:expected_height-1-seen/expected_width))$fatal(1,"Raw coordinate mismatch %0d",seen);
    raw_end=pixel_offset+(seen/expected_width)*expected_stride+(seen%expected_width)*3+3;
    if(raw_end>committed_limit)$fatal(1,"Uncommitted sector escaped CRC quarantine");
    seen=seen+1;
   end
   if(scaled_valid&&packer_ready)begin
    if(scaled_seen>=OUT_WIDTH*OUT_HEIGHT)$fatal(1,"Too many scaled pixels");
    if(scaled_x!==scaled_seen%OUT_WIDTH||scaled_y!==(expected_top?scaled_seen/OUT_WIDTH:OUT_HEIGHT-1-scaled_seen/OUT_WIDTH))$fatal(1,"Scaled coordinates %0d",scaled_seen);
    if(scaled_rgb!==expected_scaled[scaled_seen])$fatal(1,"Scaled RGB mismatch %0d got=%h expected=%h",scaled_seen,scaled_rgb,expected_scaled[scaled_seen]);
    scaled_seen=scaled_seen+1;
   end
   if(source_done&&source_ok&&!scaled_done&&STAGE==2)begin
    drain_observed=1;
    if(packed_done)$fatal(1,"Published before scaler drained");
   end
   if(req_ack)begin req_ack<=0;pending=0;end
   else if(pending)begin
    if(ack_delay==0)req_ack<=1;else ack_delay=ack_delay-1;
   end else if(req_valid)begin
    if(req_addr>=OUT_WIDTH*OUT_HEIGHT/16||written[req_addr])$fatal(1,"Duplicate or invalid burst address %0d",req_addr);
    for(lane=0;lane<16;lane=lane+1)if(req_data[lane*8+:8]!==expected_indexed[req_addr*16+lane])$fatal(1,"Wrong indexed burst addr=%0d lane=%0d",req_addr,lane);
    written[req_addr]=1;writes=writes+1;pending=1;ack_delay=(writes%7)+1;
   end
  end
 end
 task run_once;
  integer actual_error;
  begin
   rst_n=0;repeat(6)@(negedge clk);rst_n=1;
   wait(terminal);repeat(15)@(negedge clk);
   actual_error=STAGE==0?source_error:STAGE==1?source_error:packed_error;
   if(actual_error!=expected_error)$fatal(1,"Error %02h expected %02h",actual_error,expected_error);
   if(expected_error==0)begin
    if(!bmp_ok||source_width!=expected_width||source_height!=expected_height||row_stride!=expected_stride||top_down!=expected_top)$fatal(1,"Committed metadata mismatch");
    if(STAGE!=0&&(!source_ok||raw_count!=expected_width*expected_height||seen!=raw_count||raw_crc!==expected_crc))$fatal(1,"Raw count/CRC mismatch %d %h vs %h",raw_count,raw_crc,expected_crc);
    if(STAGE==2&&(!packed_done||!scaled_ok||scaled_seen!=OUT_WIDTH*OUT_HEIGHT||writes!=OUT_WIDTH*OUT_HEIGHT/16||burst_count!=writes||packed_count!=OUT_WIDTH*OUT_HEIGHT))$fatal(1,"Incomplete scaled frame");
    if(require_drain&&!drain_observed)$fatal(1,"Missing explicit raw-done-before-scaled-done coverage");
   end else begin
    if(STAGE==2&&packed_done)$fatal(1,"Failed frame published");
    if(!allow_partial&&(seen!=0||scaled_seen!=0||writes!=0))$fatal(1,"Unexpected partial output");
    if(!bmp_ok&&(source_width!=0||source_height!=0||row_stride!=0))$fatal(1,"Rejected metadata was committed");
   end
   saved_reads=requests;saved_seen=seen;saved_scaled=scaled_seen;saved_writes=writes;
   repeat(70)@(negedge clk);
   if(!terminal||requests!=saved_reads||seen!=saved_seen||scaled_seen!=saved_scaled||writes!=saved_writes)$fatal(1,"Terminal state not sticky");
   $display("PASS dynamic stage=%0d src=%0dx%0d td=%0d err=%02h raw=%0d scaled=%0d bursts=%0d reads=%0d drained=%0d",STAGE,expected_width,expected_height,expected_top,actual_error,seen,scaled_seen,writes,requests,drain_observed);
  end
 endtask
 initial begin
  if(!$value$plusargs("FIXTURE=%s",fixture))$fatal(1,"Missing fixture");
  if(!$value$plusargs("BLOCKS=%d",blocks))$fatal(1,"Missing blocks");
  if(!$value$plusargs("WIDTH=%d",expected_width))$fatal(1,"Missing width");
  if(!$value$plusargs("HEIGHT=%d",expected_height))$fatal(1,"Missing height");
  if(!$value$plusargs("STRIDE=%d",expected_stride))$fatal(1,"Missing stride");
  if(!$value$plusargs("TOP=%d",expected_top))expected_top=0;
  if(!$value$plusargs("ERROR=%d",expected_error))expected_error=0;
  if(!$value$plusargs("CRC=%h",expected_crc))expected_crc=0;
  if(!$value$plusargs("FAULT=%d",fault))fault=0;
  if(!$value$plusargs("FAIL_SECTOR=%d",fail_sector))fail_sector=0;
  if(!$value$plusargs("RETRY=%d",retry))retry=0;
  if(!$value$plusargs("PARTIAL=%d",allow_partial))allow_partial=0;
  if(!$value$plusargs("DRAIN=%d",require_drain))require_drain=0;
  $readmemh({fixture,"/data.hex"},fixture_bytes,0,blocks*512-1);
  $readmemh({fixture,"/lbas.hex"},fixture_lbas,0,blocks-1);
  if(STAGE!=0)begin
   $readmemh({fixture,"/raw.hex"},expected_raw,0,expected_width*expected_height-1);
   $readmemh({fixture,"/scaled.hex"},expected_scaled,0,OUT_WIDTH*OUT_HEIGHT-1);
   $readmemh({fixture,"/indexed.hex"},expected_indexed,0,OUT_WIDTH*OUT_HEIGHT-1);
  end
  run_once;
  if(retry)run_once;
  $finish;
 end
 initial begin #100000000;$fatal(1,"Dynamic chain watchdog");end
endmodule
