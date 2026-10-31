`timescale 1ns/1ps
// V130: independent AV layer; rounded source glyphs enlarged to36px (3x).
// Lossless144-bit glyphs in eight18-bit words, keeping full glyph pixels.
// Up to320 full glyphs:2048x18 +512x18 (five native9K blocks).
// Explicit banks avoid rounding a286-glyph monolithic array to eight blocks.
// Four-cycle RGB/XY/control latency is preserved; synchronous compact ROMs.
// Current line is snapshotted per video frame. Gaps/tracks without cues are clear.
module subtitle_overlay(
 input wire clk,rst_n,input wire [11:0] x,y,input wire [23:0] rgb,
 input wire de,hs,vs,picture_visible,enable,cue_active,
 input wire [10:0] text_offset,input wire [4:0] text_length,
 output reg [11:0] x_out,y_out,output reg [23:0] rgb_out,
 output reg de_out,hs_out,vs_out,picture_visible_out);
 `include "visual/music_caption_config.vh"
 (* rom_style="block" *) reg [8:0] text_memory[0:1023];
 (* rom_style="block" *) reg [17:0] font_memory_lo[0:2047];
 (* rom_style="block" *) reg [17:0] font_memory_hi[0:511];
 initial begin
  `include "visual/music_caption_text_init.vh"
 end
 initial begin
  `include "visual/music_caption_font_init.vh"
 end
 reg shown_enable;reg [10:0] shown_offset;
 reg [10:0] text_start,text_width;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin shown_enable<=0;shown_offset<=0;text_start<=640;text_width<=0;end
 else if(de&&x==0&&y==0)begin
  shown_enable<=enable&&cue_active;shown_offset<=text_offset;
  text_width<=({6'd0,text_length}<<5)+({6'd0,text_length}<<4);
  text_start<=(12'd1280-(({7'd0,text_length}<<5)+({7'd0,text_length}<<4)))>>1;
 end
 wire panel_now=shown_enable&&picture_visible&&de&&x>=64&&x<1216&&y>=648&&y<704;
 wire text_hit=x>=text_start&&x<text_start+text_width&&y>=658&&y<694;
 wire [11:0] tx=x-text_start;wire [5:0] ty=y-12'd658;
 //48px cells with centered36px glyphs; constants only, no extra DSP/BRAM.
 wire [4:0] col=tx/12'd48;
 wire [5:0] cell_x=tx-({7'd0,col}<<5)-({7'd0,col}<<4);
 wire [5:0] local_x=cell_x-6'd6;

 reg [23:0] base[0:2];reg [11:0] xx[0:2],yy[0:2];reg [3:0] ctl[0:2];
 reg [2:0] panel,glyph;reg [9:0] text_address0;
 reg [3:0] font_y0,font_y1,font_x0,font_x1;
 reg [4:0] font_bit2;reg [2:0] font_word;reg [4:0] font_bit;
 reg [8:0] text_glyph1;reg [17:0] bits2_lo,bits2_hi;reg font_bank2;
 wire [17:0] bits2=font_bank2?bits2_hi:bits2_lo;
 // Row-pair boundary selects a single word/bit; no general divider or multiplier.
 always @* begin
  font_word=0;font_bit=0;
  case(font_y1)
   0,3,6,9:begin
    case(font_y1)0:font_word=0;3:font_word=2;6:font_word=4;default:font_word=6;endcase
    font_bit=5'd11-{1'b0,font_x1};
   end
   1,4,7,10:begin
    case(font_y1)1:font_word=0;4:font_word=2;7:font_word=4;default:font_word=6;endcase
    if(font_x1<6)begin font_word=font_word+1'b1;font_bit=5'd5-{1'b0,font_x1};end
    else font_bit=5'd23-{1'b0,font_x1};
   end
   2,5,8,11:begin
    case(font_y1)2:font_word=1;5:font_word=3;8:font_word=5;default:font_word=7;endcase
    font_bit=5'd17-{1'b0,font_x1};
   end
   default:begin font_word=0;font_bit=0;end
  endcase
 end
 always @(posedge clk)begin
  text_glyph1<=text_memory[text_address0];
  bits2_lo<=font_memory_lo[{text_glyph1[7:0],font_word}];
  bits2_hi<=font_memory_hi[{text_glyph1[5:0],font_word}];
  font_bank2<=text_glyph1[8];
 end
 integer i;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  for(i=0;i<3;i=i+1)begin base[i]<=0;xx[i]<=0;yy[i]<=0;ctl[i]<=4'b0110;end
  panel<=0;glyph<=0;text_address0<=0;font_y0<=0;font_y1<=0;
  font_x0<=0;font_x1<=0;font_bit2<=0;
  x_out<=0;y_out<=0;rgb_out<=0;de_out<=0;hs_out<=1;vs_out<=1;picture_visible_out<=0;
 end else begin
  base[0]<=rgb;xx[0]<=x;yy[0]<=y;ctl[0]<={de,hs,vs,picture_visible};
  for(i=1;i<3;i=i+1)begin base[i]<=base[i-1];xx[i]<=xx[i-1];yy[i]<=yy[i-1];ctl[i]<=ctl[i-1];end
  panel<={panel[1:0],panel_now};glyph<={glyph[1:0],panel_now&&text_hit&&cell_x>=6&&cell_x<42};
  text_address0<=shown_offset[9:0]+col;
  font_y0<=ty/6'd3;font_y1<=font_y0;
  font_x0<=local_x/6'd3;font_x1<=font_x0;font_bit2<=font_bit;
  rgb_out<=(glyph[2]&&bits2[font_bit2])?24'hffffff:
            (panel[2]?{1'b0,base[2][23:17],1'b0,base[2][15:9],1'b0,base[2][7:1]}:base[2]);
  x_out<=xx[2];y_out<=yy[2];{de_out,hs_out,vs_out,picture_visible_out}<=ctl[2];
 end
endmodule
