`timescale 1ns/1ps
// v119: choices1/2 preserve MUSIC.WAV and ADVOICE.WAV. Choice3 finds the
// first additional regular *.WAV in root directory order, excluding both names.
// VFAT long-name entries are ignored; the associated standard short alias is
// sufficient for the WAV extension. No long-name display/MP3/FLAC decoding.
// Reuses the BMP FAT32 mount and the same decoder/sector/sample buffers;
// never silently substitutes a test tone for a missing/corrupt audio file.
module tf_wav_reader(
 input clk,rst_n,enable,input [1:0] choice,input mounted,
 input [31:0] root_cluster,data_base,fat_base,cluster_max,
 input [7:0] spc,input [3:0] shift,
 output bus_reset_n,output read_req,output [31:0] read_lba,
 input sd_ready,sd_done,input [3:0] sd_error,
 input data_valid,input [8:0] data_index,input [7:0] data_byte,
 output signed [23:0] left,right,output pcm_valid,input pcm_ready,
 output reg eof,output reg [7:0] error_code,output header_ok,output [31:0] data_size);
 localparam WAIT_MOUNT=0,DIR_START=1,DIR_SCAN=2,RESET_FILE=3,FILE_START=4,FILE_PLAY=5,HALT=6;
 reg [2:0] state,reset_count;
 reg [31:0] file_cluster,file_size;reg name_ok,attr_ok,music_name_ok,advoice_name_ok;reg [15:0] hi_cluster,lo_cluster;
 wire scan=state==DIR_START||state==DIR_SCAN;
 assign bus_reset_n=rst_n&&enable&&state!=RESET_FILE;
 wire bv,br,fs_done;wire [7:0] bd;wire [31:0] pos;wire [3:0] fe;
 wire decoder_done;wire [3:0] de;wire decoder_ready;
 wire [4:0] ei=pos[4:0];
 function [7:0] name_byte;input [4:0] i;input use_ad;begin
  if(!use_ad)case(i)
   0:name_byte="M";1:name_byte="U";2:name_byte="S";3:name_byte="I";4:name_byte="C";
   5,6,7:name_byte=" ";8:name_byte="W";9:name_byte="A";10:name_byte="V";default:name_byte=0;
  endcase
  else case(i)
   0:name_byte="A";1:name_byte="D";2:name_byte="V";3:name_byte="O";4:name_byte="I";5:name_byte="C";6:name_byte="E";
   7:name_byte=" ";8:name_byte="W";9:name_byte="A";10:name_byte="V";default:name_byte=0;
  endcase
 end endfunction
 wire selected_name=choice==1?music_name_ok:
                    (choice==2?advoice_name_ok:(choice==3&&!music_name_ok&&!advoice_name_ok));
 fat32_audio_prefetch stream(.clk(clk),.rst_n(bus_reset_n),.start(state==DIR_START||state==FILE_START),
 .directory_mode(scan),.start_cluster(scan?root_cluster:file_cluster),.file_size(scan?32'd65536:file_size),
 .data_base(data_base),.fat_base(fat_base),.cluster_max(cluster_max),.spc(spc),.shift(shift),
 .read_req(read_req),.read_lba(read_lba),.sd_ready(sd_ready),.sd_done(sd_done),.sd_error(sd_error),
 .data_valid(data_valid),.data_index(data_index),.data_byte(data_byte),.byte_valid(bv),.byte_ready(br),.byte_data(bd),.position(pos),.done(fs_done),.error_code(fe));
 assign br=scan?1'b1:(state==FILE_PLAY&&(decoder_done||decoder_ready));
 wav_pcm_decode decode(.clk(clk),.rst_n(rst_n&&(state==FILE_START||state==FILE_PLAY||(state==HALT&&eof))),
 .byte_valid(bv&&state==FILE_PLAY),.byte_ready(decoder_ready),.byte_data(bd),.file_size(file_size),
 .left(left),.right(right),.pcm_valid(pcm_valid),.pcm_ready(pcm_ready),.header_ok(header_ok),.done(decoder_done),.error_code(de),.data_size(data_size));
 task fail;input [7:0] c;begin error_code<=c;state<=HALT;end endtask
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin state<=WAIT_MOUNT;reset_count<=0;file_cluster<=0;file_size<=0;name_ok<=0;music_name_ok<=0;advoice_name_ok<=0;attr_ok<=0;hi_cluster<=0;lo_cluster<=0;eof<=0;error_code<=0;end
 else if(enable)begin
  if(fe!=0&&state!=RESET_FILE&&state!=HALT)fail({4'h8,fe});
  else if(de!=0&&state==FILE_PLAY)fail({4'h9,de});
  else case(state)
   WAIT_MOUNT:if(mounted)state<=DIR_START;
   DIR_START:state<=DIR_SCAN;
   DIR_SCAN:begin
    if(fs_done)fail(8'ha1);
    if(bv&&br)begin
     if(ei==0)begin
      name_ok<=bd!=8'he5&&bd!=0&&bd!=".";
      music_name_ok<=bd==name_byte(0,1'b0);advoice_name_ok<=bd==name_byte(0,1'b1);
      attr_ok<=0;if(bd==0)fail(8'ha1);
     end else if(ei<11)begin
      if(bd!=name_byte(ei,1'b0))music_name_ok<=0;
      if(bd!=name_byte(ei,1'b1))advoice_name_ok<=0;
      if((ei==8&&bd!="W")||(ei==9&&bd!="A")||(ei==10&&bd!="V"))name_ok<=0;
     end
     case(ei)
      11:attr_ok<=((bd&8'h18)==0)&&bd!=8'h0f;
      20:hi_cluster[7:0]<=bd;21:hi_cluster[15:8]<=bd;
      26:lo_cluster[7:0]<=bd;27:lo_cluster[15:8]<=bd;
      28:file_size[7:0]<=bd;29:file_size[15:8]<=bd;30:file_size[23:16]<=bd;
      31:if(name_ok&&attr_ok&&selected_name)begin
       file_size[31:24]<=bd;file_cluster<={4'd0,hi_cluster[11:0],lo_cluster};reset_count<=0;state<=RESET_FILE;
      end
     endcase
    end
   end
   RESET_FILE:if(reset_count==3)state<=FILE_START;else reset_count<=reset_count+1'b1;
   FILE_START:state<=FILE_PLAY;
   FILE_PLAY:if(fs_done)begin
    if(!decoder_done)fail(8'ha2);else if(!pcm_valid)begin eof<=1;state<=HALT;end
   end
   HALT:begin end
   default:fail(8'haf);
  endcase
 end
endmodule
