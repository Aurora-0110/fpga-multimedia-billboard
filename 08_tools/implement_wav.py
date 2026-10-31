from pathlib import Path
r=Path(r'D:\FPGA_Billboard\work\v108_tf_wav_20261026')
def put(p,s):
 q=r/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(s,encoding='utf-8')
# Preserve old standalone storage interfaces and tests; factor a bus-facing copy.
p=r/'01_project/rtl/tf/fat32_bmp_probe.v'
s=p.read_text(encoding='utf-8').replace('module fat32_bmp_probe #(', 'module media_bmp_probe #(')
s=s.replace('output reg [31:0] data_base,fat_base,cluster_max,','output reg [31:0] data_base,fat_base,cluster_max, output reg [31:0] mounted_root,')
s=s.replace('root_cluster<=root0;mounted_spc<=spc;', 'root_cluster<=root0;mounted_root<=root0;mounted_spc<=spc;')
# initialize at the same reset as other persistent mount fields
s=s.replace('mounted<=0;', 'mounted_root<=0;mounted<=0;',1)
put('01_project/rtl/tf/media_bmp_probe.v',s)
s=(r/'01_project/rtl/tf/tf_bmp_source.v').read_text(encoding='utf-8')
s=s.replace('module tf_bmp_source #(', 'module tf_bus_bmp_source #(')
s=s.replace('input wire clk,rst_n,miso,output wire cs_n,sck,mosi,','input wire clk,rst_n,\n input wire ready,read_done,dv, input wire [3:0] se,input wire [8:0] di,input wire [7:0] db,\n output wire read_req,output wire [31:0] read_lba,\n output wire [31:0] mount_base,mount_fat,mount_max,mount_root, output wire [7:0] mount_spc,output wire [3:0] mount_shift,')
s=s.replace('output wire sd_init,mounted,bmp_ok,','output wire mounted,bmp_ok,')
s=s.replace(' wire ready,read_done,dv;wire [3:0] se,pe,xe;\n wire [8:0] di;wire [7:0] db;',' wire [3:0] pe,xe;')
a=s.index(' sd_spi_reader #(');b=s.index(' fat32_bmp_probe #(',a)
s=s[:a]+''' assign read_req=use_pixels?xr:pr;assign read_lba=use_pixels?xl:pl;
 assign mount_base=base;assign mount_fat=fat;assign mount_max=mx;assign mount_spc=spc;assign mount_shift=sh;
'''+s[b:]
s=s.replace('fat32_bmp_probe #(', 'media_bmp_probe #(').replace('.data_base(base),.fat_base(fat),.cluster_max(mx),','.data_base(base),.fat_base(fat),.cluster_max(mx),.mounted_root(mount_root),')
put('01_project/rtl/tf/tf_bus_bmp_source.v',s)
for old,new,child_old,child_new in [('tf_bmp_scaled_source','tf_bus_bmp_scaled_source','tf_bmp_source','tf_bus_bmp_source'),('tf_scaled_loader','tf_bus_scaled_loader','tf_bmp_scaled_source','tf_bus_bmp_scaled_source')]:
 s=(r/f'01_project/rtl/tf/{old}.v').read_text(encoding='utf-8').replace(f'module {old} #(',f'module {new} #(').replace(f'{child_old} #(',f'{child_new} #(')
 s=s.replace('input wire miso,','''input wire ready,read_done,dv,input wire [3:0] se,input wire [8:0] di,input wire [7:0] db,
 output wire read_req,output wire [31:0] read_lba,
 output wire [31:0] mount_base,mount_fat,mount_max,mount_root,output wire [7:0] mount_spc,output wire [3:0] mount_shift,''')
 s=s.replace('enable,miso,','''enable,
 input wire ready,read_done,dv,input wire [3:0] se,input wire [8:0] di,input wire [7:0] db,
 output wire read_req,output wire [31:0] read_lba,
 output wire [31:0] mount_base,mount_fat,mount_max,mount_root,output wire [7:0] mount_spc,output wire [3:0] mount_shift,''')
 s=s.replace(' output wire cs_n,sck,mosi,\n','').replace('output wire sd_init,mounted,bmp_ok','output wire mounted,bmp_ok')
 s=s.replace('.miso(miso),.cs_n(cs_n),.sck(sck),.mosi(mosi),', '''.ready(ready),.read_done(read_done),.dv(dv),.se(se),.di(di),.db(db),.read_req(read_req),.read_lba(read_lba),
 .mount_base(mount_base),.mount_fat(mount_fat),.mount_max(mount_max),.mount_root(mount_root),.mount_spc(mount_spc),.mount_shift(mount_shift),''')
 s=s.replace('.sd_init(sd_init),','')
 put(f'01_project/rtl/tf/{new}.v',s)
put('01_project/rtl/tf/media_sd_arbiter.v',r'''`timescale 1ns/1ps
// One persistent host, sector-atomic ownership. Each client has ONE queued slot.
// Ready drops immediately on request capture, even for a losing simultaneous
// request. Resetting a client cancels queued work and drains active work safely.
module media_sd_arbiter(
 input clk,rst_n, bmp_reset_n,aud_reset_n,audio_urgent,
 input b_req,input [31:0] b_lba,output b_ready,b_done,b_valid,
 input a_req,input [31:0] a_lba,output a_ready,a_done,a_valid,
 output [3:0] b_error,a_error,
 output reg h_req,output reg [31:0] h_lba,
 input h_ready,h_done,h_valid,input [3:0] h_error,
 output reg active,output reg owner_audio);
 reg bp,ap;reg [31:0] bl,al;reg issued,discard,br,ar;
 assign b_ready=bmp_reset_n&&!bp&&!(active&&!owner_audio);
 assign a_ready=aud_reset_n&&!ap&&!(active&&owner_audio);
 assign b_done=br;assign a_done=ar;
 assign b_valid=h_valid&&active&&!owner_audio&&!discard&&bmp_reset_n;
 assign a_valid=h_valid&&active&&owner_audio&&!discard&&aud_reset_n;
 assign b_error=bmp_reset_n?h_error:4'd0;
 assign a_error=aud_reset_n?h_error:4'd0;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin bp<=0;ap<=0;bl<=0;al<=0;active<=0;owner_audio<=0;issued<=0;discard<=0;h_req<=0;h_lba<=0;br<=0;ar<=0;end
 else begin
  h_req<=0;
  if(!bmp_reset_n)begin bp<=0;br<=0;end
  else if(b_req&&b_ready)begin bp<=1;bl<=b_lba;br<=0;end
  if(!aud_reset_n)begin ap<=0;ar<=0;end
  else if(a_req&&a_ready)begin ap<=1;al<=a_lba;ar<=0;end
  if(active)begin
   if(owner_audio?!aud_reset_n:!bmp_reset_n)discard<=1;
   // A host request is first seen one cycle later. Require its ready-fall
   // before accepting the sticky read_done left over from the previous sector.
   if(!h_ready)issued<=1;
   if(issued&&((h_ready&&h_done)||h_error!=0))begin
    active<=0;issued<=0;
    if(!discard)begin
     if(owner_audio&&aud_reset_n)ar<=1;
     if(!owner_audio&&bmp_reset_n)br<=1;
    end
   end
  end else if(h_ready&&h_error==0)begin
   if(ap&&aud_reset_n&&(audio_urgent||!bp||!bmp_reset_n))begin
    owner_audio<=1;ap<=0;h_lba<=al;h_req<=1;active<=1;discard<=0;issued<=0;
   end else if(bp&&bmp_reset_n)begin
    owner_audio<=0;bp<=0;h_lba<=bl;h_req<=1;active<=1;discard<=0;issued<=0;
   end else if(ap&&aud_reset_n)begin
    owner_audio<=1;ap<=0;h_lba<=al;h_req<=1;active<=1;discard<=0;issued<=0;
   end
  end
 end
endmodule
''')
put('01_project/rtl/tf/fat32_byte_stream.v',r'''`timescale 1ns/1ps
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
 BYTE_REQ=6,BYTE_OUT=7,NEXT=8,FAT_FETCH=9,F0=10,F1=11,F2=12,F3=13,FCHECK=14,HALT=15;
 reg [3:0] state;reg [31:0] cluster,timer;
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
 wire [39:0] calc={8'd0,data_base}+(({8'd0,cluster}-40'd2)<<shift)+{32'd0,sector};
 wire [32:0] fat_calc={1'b0,fat_base}+{8'd0,cluster[31:7]};
 wire [27:0] next_cluster={q[3:0],fat_lo};
 assign read_req=state==ISSUE&&sd_ready;
 assign byte_valid=state==BYTE_OUT;assign byte_data=q;
 task fail;input [3:0] c;begin error_code<=c;done<=1;state<=HALT;end endtask
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin state<=IDLE;cluster<=0;timer<=0;sector<=0;index<=0;fat_offset<=0;received<=0;kind_fat<=0;final_fat<=0;fat_lo<=0;position<=0;read_lba<=0;done<=0;error_code<=0;end
 else if(sd_error!=0&&state!=IDLE&&state!=HALT)fail(1);
 else if(state==READ&&data_valid&&(received>=512||data_index!=received[8:0]))fail(3);
 else begin
  if(state==READ&&data_valid)received<=received+1'b1;
  case(state)
   IDLE:if(start)begin
    if(start_cluster<2||start_cluster>cluster_max||start_cluster>=32'h0ffffff0||file_size==0||shift>7||spc!=(8'd1<<shift))fail(2);
    else begin cluster<=start_cluster;position<=0;sector<=0;state<=FETCH;end
   end
   FETCH:if(calc[39:32]!=0)fail(4);else begin read_lba<=calc[31:0];kind_fat<=0;timer<=0;state<=ISSUE;end
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
''')
put('01_project/rtl/audio/wav_pcm_decode.v',r'''`timescale 1ns/1ps
// RIFF/WAVE integer PCM only:48kHz,16/24-bit,mono/stereo, LE. Unknown chunks
// and odd pad bytes are skipped. No MP3/FLAC, float, or extensible codec.
// PCM is only released after validated fmt/data bounds. A late transport error
// can mute playback, not roll back samples that were already audibly played.
module wav_pcm_decode(
 input clk,rst_n,input byte_valid,output byte_ready,input [7:0] byte_data,
 input [31:0] file_size,
 output reg signed [23:0] left,right,output reg pcm_valid,input pcm_ready,
 output reg header_ok,done,output reg [3:0] error_code,
 output reg [31:0] data_size);
 localparam RIFF=0,CHUNK=1,FMT=2,SKIP=3,PAD=4,CHECK=5,DATA=6,TAIL=7,HALT=8;
 reg [3:0] state;reg [4:0] ix;
 reg [31:0] pos,riff_end,chunk_id,chunk_size,chunk_left;
 reg [31:0] sample_rate,byte_rate;reg [15:0] format_tag,channels,bits,align;
 reg fmt_ok,odd;reg [2:0] phase;reg [23:0] sample_l,sample_r;
 wire take=byte_valid&&byte_ready;
 assign byte_ready=state!=HALT&&state!=CHECK&&(!pcm_valid||pcm_ready);
 wire [32:0] chunk_end={1'b0,pos}+{1'b0,chunk_size}+{32'd0,chunk_size[0]};
 wire pcm_format= format_tag==1&&(channels==1||channels==2)&&sample_rate==48000&&(bits==16||bits==24);
 wire [15:0] expected_align=channels==1?(bits==16?16'd2:16'd3):(bits==16?16'd4:16'd6);
 wire [31:0] expected_rate=channels==1?(bits==16?32'd96000:32'd144000):(bits==16?32'd192000:32'd288000);
 wire [2:0] last_phase=channels==1?(bits==16?3'd1:3'd2):(bits==16?3'd3:3'd5);
 task fail;input [3:0] c;begin error_code<=c;done<=1;pcm_valid<=0;state<=HALT;end endtask
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin state<=RIFF;ix<=0;pos<=0;riff_end<=0;chunk_id<=0;chunk_size<=0;chunk_left<=0;sample_rate<=0;byte_rate<=0;format_tag<=0;channels<=0;bits<=0;align<=0;fmt_ok<=0;odd<=0;phase<=0;sample_l<=0;sample_r<=0;left<=0;right<=0;pcm_valid<=0;header_ok<=0;done<=0;error_code<=0;data_size<=0;end
 else begin
  if(pcm_valid&&pcm_ready)pcm_valid<=0;
  if(state==CHECK)begin
   if(chunk_end>{1'b0,riff_end}||chunk_end>{1'b0,file_size})fail(2);
   else if(chunk_id==32'h20746d66)begin
    if(fmt_ok||chunk_size<16)fail(3);
    else begin ix<=0;chunk_left<=chunk_size;odd<=chunk_size[0];state<=FMT;end
   end else if(chunk_id==32'h61746164)begin
    if(!fmt_ok||chunk_size==0)fail(4);
    else begin chunk_left<=chunk_size;data_size<=chunk_size;phase<=0;header_ok<=1;state<=DATA;end
   end else begin chunk_left<=chunk_size;odd<=chunk_size[0];state<=chunk_size==0?CHUNK:SKIP;ix<=0;end
  end
  if(take)begin
   pos<=pos+1'b1;
   if(pos>=file_size)fail(2);
   else case(state)
    RIFF:begin
     ix<=ix+1'b1;
     case(ix)
      0:if(byte_data!="R")fail(1);1:if(byte_data!="I")fail(1);2:if(byte_data!="F")fail(1);3:if(byte_data!="F")fail(1);
      4:riff_end[7:0]<=byte_data;5:riff_end[15:8]<=byte_data;6:riff_end[23:16]<=byte_data;7:riff_end[31:24]<=byte_data;
      8:begin if(byte_data!="W"||{1'b0,riff_end}+33'd8>{1'b0,file_size}||riff_end<36)fail(1);else riff_end<=riff_end+32'd8;end
      9:if(byte_data!="A")fail(1);10:if(byte_data!="V")fail(1);
      11:if(byte_data!="E")fail(1);else begin state<=CHUNK;ix<=0;end
     endcase
    end
    CHUNK:begin
     ix<=ix+1'b1;
     if(pos+32'd1>riff_end)fail(2);
     else case(ix)
      0:chunk_id[7:0]<=byte_data;1:chunk_id[15:8]<=byte_data;2:chunk_id[23:16]<=byte_data;3:chunk_id[31:24]<=byte_data;
      4:chunk_size[7:0]<=byte_data;5:chunk_size[15:8]<=byte_data;6:chunk_size[23:16]<=byte_data;
      7:begin chunk_size[31:24]<=byte_data;state<=CHECK;ix<=0;end
     endcase
    end
    FMT:begin
     if(ix<16)ix<=ix+1'b1;chunk_left<=chunk_left-1'b1;
     case(ix)
      0:format_tag[7:0]<=byte_data;1:format_tag[15:8]<=byte_data;
      2:channels[7:0]<=byte_data;3:channels[15:8]<=byte_data;
      4:sample_rate[7:0]<=byte_data;5:sample_rate[15:8]<=byte_data;6:sample_rate[23:16]<=byte_data;7:sample_rate[31:24]<=byte_data;
      8:byte_rate[7:0]<=byte_data;9:byte_rate[15:8]<=byte_data;10:byte_rate[23:16]<=byte_data;11:byte_rate[31:24]<=byte_data;
      12:align[7:0]<=byte_data;13:align[15:8]<=byte_data;14:bits[7:0]<=byte_data;15:bits[15:8]<=byte_data;
     endcase
     if(chunk_left==1)begin state<=PAD;end
    end
    PAD:begin // only entered with fmt complete or unknown odd padding
     if(!fmt_ok&&(!pcm_format||align!=expected_align||byte_rate!=expected_rate))fail(3);
     else begin fmt_ok<=1;state<=CHUNK;ix<=1;chunk_id[7:0]<=byte_data;end
    end
    SKIP:begin chunk_left<=chunk_left-1'b1;if(chunk_left==1)begin state<=CHUNK;ix<=0;if(odd)state<=TAIL;end end
    TAIL:begin state<=CHUNK;ix<=0;end
    DATA:begin
     chunk_left<=chunk_left-1'b1;
     if(bits==24)begin
      case(phase)
       0:sample_l[7:0]<=byte_data;1:sample_l[15:8]<=byte_data;2:sample_l[23:16]<=byte_data;
       3:sample_r[7:0]<=byte_data;4:sample_r[15:8]<=byte_data;5:sample_r[23:16]<=byte_data;
      endcase
     end else case(phase)
      0:begin sample_l[15:8]<=byte_data;sample_l[7:0]<=0;end
      1:sample_l[23:16]<=byte_data;
      2:begin sample_r[15:8]<=byte_data;sample_r[7:0]<=0;end
      3:sample_r[23:16]<=byte_data;
     endcase
     if(phase==last_phase)begin
      phase<=0;left<=channels==1?{byte_data,sample_l[15:0]}:sample_l;
      right<=channels==1?{byte_data,sample_l[15:0]}:{byte_data,sample_r[15:0]};pcm_valid<=1;
     end else phase<=phase+1'b1;
     if(chunk_left==1)begin
      if(phase!=last_phase)fail(4);else begin done<=1;state<=HALT;end
     end
    end
    default:begin end
   endcase
  end
 end
endmodule
''')
