`timescale 1ns/1ps
// Read-only RIFF/WAVE PCM: 48 kHz, 16/24 bit, mono/stereo, little endian.
// v110: one rolling header window and exact format flags replace wide stored
// fields. One 16-bit PCM assembler serves both channels. Bounds are proved at
// each chunk entry; DATA no longer routes a 32-bit file comparator into PCM CE.
module wav_pcm_decode(
 input clk,rst_n,input byte_valid,output byte_ready,input [7:0] byte_data,
 input [31:0] file_size,
 output reg signed [23:0] left,right,output reg pcm_valid,input pcm_ready,
 output reg header_ok,done,output reg [3:0] error_code,
 output reg [31:0] data_size);
 localparam RIFF=0,CHUNK=1,FMT=2,SKIP=3,CHECK=5,DATA=6,TAIL=7,HALT=8,VALID_FMT=9;
 reg [3:0] state;reg [4:0] ix;
 reg [31:0] pos,riff_end,chunk_size,chunk_left;
 reg [23:0] header_shift;
 wire [31:0] header_word={byte_data,header_shift};
 wire [15:0] header_half=header_word[31:16];
 reg chunk_fmt,chunk_data,format_ok,channels_ok,rate_ok,bits_ok,stereo,is24;
 reg [2:0] align_code,rate_code;
 reg fmt_ok,odd;reg [2:0] phase;
 reg [15:0] pcm_shift;reg [23:0] left_hold;
 wire take=byte_valid&&byte_ready;
 assign byte_ready=state!=HALT&&state!=CHECK&&state!=VALID_FMT&&(!pcm_valid||pcm_ready);
 wire [32:0] chunk_end={1'b0,pos}+{1'b0,chunk_size}+{32'd0,chunk_size[0]};
 wire [2:0] format_code={1'b0,stereo,is24};
 wire [2:0] last_phase=stereo?(is24?3'd5:3'd3):(is24?3'd2:3'd1);
 wire [23:0] assembled={byte_data,pcm_shift};
 task fail;input [3:0] c;begin error_code<=c;done<=1;pcm_valid<=0;state<=HALT;end endtask
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  state<=RIFF;ix<=0;pos<=0;riff_end<=0;chunk_size<=0;chunk_left<=0;header_shift<=0;
  chunk_fmt<=0;chunk_data<=0;format_ok<=0;channels_ok<=0;rate_ok<=0;bits_ok<=0;stereo<=0;is24<=0;
  align_code<=7;rate_code<=7;fmt_ok<=0;odd<=0;phase<=0;pcm_shift<=0;left_hold<=0;
  left<=0;right<=0;pcm_valid<=0;header_ok<=0;done<=0;error_code<=0;data_size<=0;
 end else begin
  if(pcm_valid&&pcm_ready)pcm_valid<=0;
  if(state==VALID_FMT)begin
   if(!format_ok||!channels_ok||!rate_ok||!bits_ok||align_code!=format_code||rate_code!=format_code)fail(3);
   else begin fmt_ok<=1;state<=odd?TAIL:CHUNK;ix<=0;end
  end
  if(state==CHECK)begin
   if(chunk_end>{1'b0,riff_end}||chunk_end>{1'b0,file_size})fail(2);
   else if(chunk_fmt)begin
    if(fmt_ok||chunk_size<16)fail(3);
    else begin ix<=0;chunk_left<=chunk_size;odd<=chunk_size[0];state<=FMT;end
   end else if(chunk_data)begin
    if(!fmt_ok||chunk_size==0)fail(4);
    else begin chunk_left<=chunk_size;data_size<=chunk_size;phase<=0;header_ok<=1;state<=DATA;end
   end else begin chunk_left<=chunk_size;odd<=chunk_size[0];state<=chunk_size==0?CHUNK:SKIP;ix<=0;end
  end
  if(take)begin
   pos<=pos+1'b1;
   header_shift<={byte_data,header_shift[23:8]};
   if(state!=DATA&&pos>=file_size)fail(2);
   else case(state)
    RIFF:begin
     ix<=ix+1'b1;
     case(ix)
      0:if(byte_data!="R")fail(1);1:if(byte_data!="I")fail(1);2:if(byte_data!="F")fail(1);3:if(byte_data!="F")fail(1);
      7:riff_end<=header_word;
      8:begin if(byte_data!="W"||{1'b0,riff_end}+33'd8>{1'b0,file_size}||riff_end<36)fail(1);else riff_end<=riff_end+32'd8;end
      9:if(byte_data!="A")fail(1);10:if(byte_data!="V")fail(1);
      11:if(byte_data!="E")fail(1);else begin state<=CHUNK;ix<=0;end
     endcase
    end
    CHUNK:begin
     ix<=ix+1'b1;
     if(pos+32'd1>riff_end)fail(2);
     else case(ix)
      3:begin chunk_fmt<=header_word==32'h20746d66;chunk_data<=header_word==32'h61746164;end
      7:begin chunk_size<=header_word;state<=CHECK;ix<=0;end
     endcase
    end
    FMT:begin
     if(ix<16)ix<=ix+1'b1;chunk_left<=chunk_left-1'b1;
     case(ix)
      1:format_ok<=header_half==16'd1;
      3:begin channels_ok<=header_half==1||header_half==2;stereo<=header_half==2;end
      7:rate_ok<=header_word==32'd48000;
      11:case(header_word)
       96000:rate_code<=0;144000:rate_code<=1;192000:rate_code<=2;288000:rate_code<=3;default:rate_code<=7;
      endcase
      13:case(header_half)
       2:align_code<=0;3:align_code<=1;4:align_code<=2;6:align_code<=3;default:align_code<=7;
      endcase
      15:begin bits_ok<=header_half==16||header_half==24;is24<=header_half==24;end
     endcase
     if(chunk_left==1)state<=VALID_FMT;
    end
    SKIP:begin chunk_left<=chunk_left-1'b1;if(chunk_left==1)begin state<=odd?TAIL:CHUNK;ix<=0;end end
    TAIL:begin state<=CHUNK;ix<=0;end
    DATA:begin
     chunk_left<=chunk_left-1'b1;
     if(is24)pcm_shift<={byte_data,pcm_shift[15:8]};
     else if(!phase[0])pcm_shift<={byte_data,8'd0};
     if(phase==(is24?3'd2:3'd1))left_hold<=assembled;
     if(phase==last_phase)begin
      phase<=0;left<=stereo?left_hold:assembled;right<=assembled;pcm_valid<=1;
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
