from pathlib import Path
r=Path(r'D:\FPGA_Billboard\work\v108_tf_wav_20261026')
def put(p,s):
 q=r/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(s,encoding='utf-8')
p=r/'01_project/rtl/audio/wav_pcm_decode.v';s=p.read_text();s=s.replace('HALT=8;', 'HALT=8,VALID_FMT=9;')
s=s.replace('state!=CHECK&&','state!=CHECK&&state!=VALID_FMT&&')
s=s.replace('  if(state==CHECK)begin','''  if(state==VALID_FMT)begin
   if(!pcm_format||align!=expected_align||byte_rate!=expected_rate)fail(3);
   else begin fmt_ok<=1;state<=odd?TAIL:CHUNK;ix<=0;end
  end
  if(state==CHECK)begin''')
s=s.replace('if(chunk_left==1)begin state<=PAD;end','if(chunk_left==1)begin state<=VALID_FMT;end')
p.write_text(s)
p=r/'01_project/rtl/tf/media_sd_arbiter.v';s=p.read_text().replace('reg bp,ap;', 'reg bp,ap,initialized;').replace('assign b_ready=bmp_reset_n', 'assign b_ready=initialized&&bmp_reset_n').replace('assign a_ready=aud_reset_n','assign a_ready=initialized&&aud_reset_n').replace('begin bp<=0;ap<=0;bl<=0;', 'begin initialized<=0;bp<=0;ap<=0;bl<=0;').replace('  h_req<=0;','  h_req<=0;if(h_ready)initialized<=1;');p.write_text(s)
put('01_project/rtl/audio/tf_wav_reader.v',r'''`timescale 1ns/1ps
// Reuses the BMP mount. Looks up MUSIC.WAV or ADVOICE.WAV in FAT32 root;
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
 reg [31:0] file_cluster,file_size;reg name_ok,attr_ok;reg [15:0] hi_cluster,lo_cluster;
 wire scan=state==DIR_START||state==DIR_SCAN;
 assign bus_reset_n=rst_n&&enable&&state!=RESET_FILE;
 wire bv,br,fs_done;wire [7:0] bd;wire [31:0] pos;wire [3:0] fe;
 wire decoder_done;wire [3:0] de;wire decoder_ready;
 wire [4:0] ei=pos[4:0];
 function [7:0] name_byte;input [4:0] i;begin
  if(choice==1)case(i)
   0:name_byte="M";1:name_byte="U";2:name_byte="S";3:name_byte="I";4:name_byte="C";
   5,6,7:name_byte=" ";8:name_byte="W";9:name_byte="A";10:name_byte="V";default:name_byte=0;
  endcase
  else case(i)
   0:name_byte="A";1:name_byte="D";2:name_byte="V";3:name_byte="O";4:name_byte="I";5:name_byte="C";6:name_byte="E";
   7:name_byte=" ";8:name_byte="W";9:name_byte="A";10:name_byte="V";default:name_byte=0;
  endcase
 end endfunction
 fat32_byte_stream stream(.clk(clk),.rst_n(bus_reset_n),.start(state==DIR_START||state==FILE_START),
 .directory_mode(scan),.start_cluster(scan?root_cluster:file_cluster),.file_size(scan?32'd65536:file_size),
 .data_base(data_base),.fat_base(fat_base),.cluster_max(cluster_max),.spc(spc),.shift(shift),
 .read_req(read_req),.read_lba(read_lba),.sd_ready(sd_ready),.sd_done(sd_done),.sd_error(sd_error),
 .data_valid(data_valid),.data_index(data_index),.data_byte(data_byte),.byte_valid(bv),.byte_ready(br),.byte_data(bd),.position(pos),.done(fs_done),.error_code(fe));
 assign br=scan?1'b1:(state==FILE_PLAY&&(decoder_done||decoder_ready));
 wav_pcm_decode decode(.clk(clk),.rst_n(rst_n&&(state==FILE_START||state==FILE_PLAY)),
 .byte_valid(bv&&state==FILE_PLAY),.byte_ready(decoder_ready),.byte_data(bd),.file_size(file_size),
 .left(left),.right(right),.pcm_valid(pcm_valid),.pcm_ready(pcm_ready),.header_ok(header_ok),.done(decoder_done),.error_code(de),.data_size(data_size));
 task fail;input [7:0] c;begin error_code<=c;state<=HALT;end endtask
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin state<=WAIT_MOUNT;reset_count<=0;file_cluster<=0;file_size<=0;name_ok<=0;attr_ok<=0;hi_cluster<=0;lo_cluster<=0;eof<=0;error_code<=0;end
 else if(enable)begin
  if(fe!=0&&state!=RESET_FILE&&state!=HALT)fail({4'h8,fe});
  else if(de!=0&&state==FILE_PLAY)fail({4'h9,de});
  else case(state)
   WAIT_MOUNT:if(mounted)state<=DIR_START;
   DIR_START:state<=DIR_SCAN;
   DIR_SCAN:begin
    if(fs_done)fail(8'ha1);
    if(bv&&br)begin
     if(ei==0)begin name_ok<=bd==name_byte(0);attr_ok<=0;if(bd==0)fail(8'ha1);end
     else if(ei<11&&bd!=name_byte(ei))name_ok<=0;
     case(ei)
      11:attr_ok<=((bd&8'h18)==0)&&bd!=8'h0f;
      20:hi_cluster[7:0]<=bd;21:hi_cluster[15:8]<=bd;
      26:lo_cluster[7:0]<=bd;27:lo_cluster[15:8]<=bd;
      28:file_size[7:0]<=bd;29:file_size[15:8]<=bd;30:file_size[23:16]<=bd;
      31:if(name_ok&&attr_ok)begin
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
''')
# A fully handshaken bundled-data mailbox, not separately synchronized choice bits.
put('01_project/rtl/audio/audio_choice_cdc.v',r'''`timescale 1ns/1ps
module audio_choice_cdc(input pclk,sclk,rst_n,input [1:0] choice,
 output reg [1:0] sd_choice,output reg changed);
 reg [1:0] payload;reg request,ack;
 (* ASYNC_REG="TRUE" *) reg [1:0] rq,ak;
 always @(posedge pclk or negedge rst_n)
 if(!rst_n)begin payload<=0;request<=0;ak<=0;end
 else begin ak<={ak[0],ack};if(ak[1]==request&&choice!=payload)begin payload<=choice;request<=~request;end end
 always @(posedge sclk or negedge rst_n)
 if(!rst_n)begin rq<=0;ack<=0;sd_choice<=0;changed<=0;end
 else begin rq<={rq[0],request};changed<=0;if(rq[1]!=ack)begin sd_choice<=payload;changed<=1;ack<=rq[1];end end
endmodule
''')
put('01_project/rtl/audio/tf_wav_playback.v',r'''`timescale 1ns/1ps
// SD-side decode -> 2048 stereo frame asynchronous BRAM FIFO -> exact48k
// pixel-domain cadence. Source reset is asserted to BOTH domains immediately
// on a selection change; each domain then synchronously releases after8 cycles.
// Selection never resets the physical SD host or the HDMI clock/packet engine.
// EOF drains cleanly and stops (not gapless looping in this first WAV release).
module tf_wav_playback #(parameter FIFO_AW=11,PREFILL=1024,LOW_WATER=1536,PIX_HZ=74250000,SAMPLE_HZ=48000)(
 input clk_sd,clk_pix,rst_n,input [1:0] choice,input mounted,
 input [31:0] root_cluster,data_base,fat_base,cluster_max,input [7:0] spc,input [3:0] shift,
 output bus_reset_n,output read_req,output [31:0] read_lba,output urgent,
 input sd_ready,sd_done,input [3:0] sd_error,input data_valid,input [8:0] data_index,input [7:0] data_byte,
 output reg signed [23:0] left,right,output reg valid,epoch,output reg playing,
 output reg underrun,output reg [7:0] error_pix,output reg finished);
 wire [1:0] cmd;wire changed;
 audio_choice_cdc command(.pclk(clk_pix),.sclk(clk_sd),.rst_n(rst_n),.choice(choice),.sd_choice(cmd),.changed(changed));
 reg [3:0] reset_count;
 always @(posedge clk_sd or negedge rst_n)
 if(!rst_n)reset_count<=0;else if(changed||cmd==0)reset_count<=0;else if(reset_count!=15)reset_count<=reset_count+1'b1;
 // Also assert on the pixel-side requested value changing, before mailbox ack.
 reg [1:0] seen_choice;
 always @(posedge clk_pix or negedge rst_n)if(!rst_n)seen_choice<=0;else seen_choice<=choice;
 wire fifo_async_n=rst_n&&(reset_count==15)&&(choice!=0)&&(seen_choice==choice);
 wire sr,pr;
 reset_release #(.RELEASE_FALLING_EDGE(0)) srst(.clk(clk_sd),.async_n(fifo_async_n),.rst_n(sr));
 reset_release #(.RELEASE_FALLING_EDGE(0)) prst(.clk(clk_pix),.async_n(fifo_async_n),.rst_n(pr));
 wire signed [23:0] sl,srr;wire sv,full,empty;wire [FIFO_AW:0] wu,ru;
 wire [47:0] rd;wire eof,header;wire [7:0] er;wire [31:0] data_size;
 tf_wav_reader reader(.clk(clk_sd),.rst_n(sr),.enable(cmd!=0),.choice(cmd),.mounted(mounted),
 .root_cluster(root_cluster),.data_base(data_base),.fat_base(fat_base),.cluster_max(cluster_max),.spc(spc),.shift(shift),
 .bus_reset_n(bus_reset_n),.read_req(read_req),.read_lba(read_lba),.sd_ready(sd_ready),.sd_done(sd_done),.sd_error(sd_error),
 .data_valid(data_valid),.data_index(data_index),.data_byte(data_byte),.left(sl),.right(srr),.pcm_valid(sv),.pcm_ready(!full),
 .eof(eof),.error_code(er),.header_ok(header),.data_size(data_size));
 assign urgent=cmd!=0&&wu<LOW_WATER&&!eof&&er==0;
 reg pop;reg pending,have;reg [47:0] held;
 async_fifo #(.WIDTH(48),.AW(FIFO_AW)) samples(.wclk(clk_sd),.wrst_n(sr),.wr_en(sv&&!full&&er==0),.wdata({sl,srr}),.wfull(full),.wused(wu),
 .rclk(clk_pix),.rrst_n(pr),.rd_en(pop),.rdata(rd),.rempty(empty),.rused(ru));
 (* ASYNC_REG="TRUE" *) reg [1:0] ep,hp;reg [7:0] e0,e1,elast;
 reg [26:0] acc;wire [27:0] sum={1'b0,acc}+SAMPLE_HZ;
 reg first_sample;reg pop_delay;
 always @(posedge clk_pix or negedge pr)
 if(!pr)begin ep<=0;hp<=0;e0<=0;e1<=0;elast<=0;error_pix<=0;end
 else begin ep<={ep[0],eof};hp<={hp[0],header};e0<=er;e1<=e0;elast<=e1;if(e1==elast)error_pix<=e1;end
 always @(posedge clk_pix or negedge pr)
 if(!pr)begin left<=0;right<=0;valid<=0;epoch<=0;playing<=0;underrun<=0;finished<=0;acc<=0;pop<=0;pending<=0;pop_delay<=0;have<=0;held<=0;first_sample<=1;end
 else begin
  valid<=0;epoch<=0;pop<=0;pop_delay<=pop;
  if(pop_delay)begin held<=rd;have<=1;pending<=0;end
  if(!have&&!pending&&!empty&&error_pix==0)begin pop<=1;pending<=1;end
  if(error_pix!=0)begin playing<=0;have<=0;end
  else if(!playing)begin
   acc<=0;
   if(!finished&&hp[1]&&(ru>=PREFILL||ep[1])&&(have||!empty))playing<=1;
   if(ep[1]&&empty&&!pending&&!have)finished<=1;
  end else if(sum>=PIX_HZ)begin
   acc<=sum-PIX_HZ;
   if(have)begin left<=held[47:24];right<=held[23:0];valid<=1;epoch<=first_sample;first_sample<=0;have<=0;end
   else begin
    playing<=0;left<=0;right<=0;
    if(ep[1]&&empty&&!pending)finished<=1;else underrun<=1;
   end
  end else acc<=sum[26:0];
 end
endmodule
''')
