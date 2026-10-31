`timescale 1ns/1ps
// Diagnostic-only, four-stage overlay (v130 coordinate/character timing cut). Its visibility NEVER depends on the
// framebuffer's picture_visible. Timing/coordinates and the real audio gate
// still advance together. A fault is exposed, NOT cleared or auto-retried.
module display_diagnostics_osd #(parameter FAULT_ONLY=1,VERSION_MAJOR=0,VERSION_TENS=8,VERSION_ONES=9,ALWAYS_SHOW_FAULTS=0,AUDIO_DEBUG=0)(
 input wire clk,rst_n,input wire [11:0] x,y,input wire [23:0] rgb,
 input wire de,hs,vs,picture_visible,input wire [1:0] image_index,
 // Pixel-domain snapshot: [0]front [1]running [2]visible [3]underflow
 // [4]overflow [5]audio fault [6]memory released [7]loader active.
 input wire [7:0] status,input wire [7:0] tf_error,input wire [12:0] fifo_used,
 input wire enable,
 input wire [12:0] audio_used,audio_minimum,audio_first_used,input wire [7:0] audio_first_flags,
 output reg [11:0] x_out,y_out,output reg [23:0] rgb_out,
 output reg de_out,hs_out,vs_out,picture_visible_out);
`include "video/osd_font.vh"
 function [7:0] hexchar;input [3:0] n;begin hexchar=n<10?("0"+n):("A"+n-10);end endfunction
 reg [15:0] frames;reg [7:0] shown,shown_error,first_error;reg [1:0] shown_index;
 reg [4:0] history,shown_history;reg memory_seen;
 reg [12:0] minimum,shown_minimum,shown_used;
 reg [12:0] aq,amin,afirst;reg [7:0] aflags;
 wire tick=de&&x==0&&y==0;
 wire [4:0] events={memory_seen&&!status[6],tf_error!=0,status[5:3]};
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  frames<=0;shown<=0;shown_error<=0;first_error<=0;shown_index<=0;
  history<=0;shown_history<=0;memory_seen<=0;minimum<=13'd4096;
  shown_minimum<=13'd4096;shown_used<=0;aq<=0;amin<=0;afirst<=0;aflags<=0;
 end else begin
  history<=history|events;
  if(status[6])memory_seen<=1;
  if(tf_error!=0&&first_error==0)first_error<=tf_error;
  if(status[1]&&de&&fifo_used<minimum)minimum<=fifo_used;
  // Capture FIRST audio underrun on a pixel clock, not only once per frame.
  // Keep it across source changes/UI exit. Only global reset clears it.
  if(AUDIO_DEBUG&&aflags==0&&audio_first_flags!=0)begin
   afirst<=audio_first_used;aflags<=audio_first_flags;
  end
  if(tick)begin
   frames<=frames+1'b1;shown<=status;shown_error<=tf_error;
   shown_index<=image_index;shown_history<=history|events;
   shown_minimum<=minimum;shown_used<=fifo_used;
   if(AUDIO_DEBUG)begin aq<=audio_used;amin<=audio_minimum;end
  end
 end
 function [7:0] header;input [5:0] c;begin
 header=" ";case(c)
 0:header="V";1:header="0"+VERSION_MAJOR;2:header="0"+VERSION_TENS;3:header="0"+VERSION_ONES;
 5:header="F";6:header="=";7:header=hexchar(frames[15:12]);8:header=hexchar(frames[11:8]);9:header=hexchar(frames[7:4]);10:header=hexchar(frames[3:0]);
 12:header="I";13:header="M";14:header="G";15:header="=";16:header="A"+shown_index;
 18:header="F";19:header="R";20:header="=";21:header="0"+shown[0];
 23:header="R";24:header="U";25:header="N";26:header="=";27:header="0"+shown[1];
 29:header="V";30:header="I";31:header="S";32:header="=";33:header="0"+shown[2];
 35:header="U";36:header="F";37:header="=";38:header="0"+shown[3];
 40:header="O";41:header="F";42:header="=";43:header="0"+shown[4];
 45:header="A";46:header="U";47:header="=";48:header="0"+shown[5];
 50:header="T";51:header="F";52:header="=";53:header=hexchar(shown_error[7:4]);54:header=hexchar(shown_error[3:0]);
 default:header=" ";endcase end endfunction
 function [7:0] footer;input [5:0] c;begin
 footer=" ";case(c)
 0:footer="H";1:footer="I";2:footer="S";3:footer="T";
 5:footer="U";6:footer="F";7:footer="=";8:footer="0"+shown_history[0];
 10:footer="O";11:footer="F";12:footer="=";13:footer="0"+shown_history[1];
 15:footer="A";16:footer="U";17:footer="=";18:footer="0"+shown_history[2];
 20:footer="T";21:footer="F";22:footer="=";23:footer=hexchar(first_error[7:4]);24:footer=hexchar(first_error[3:0]);
 26:footer="S";27:footer="D";28:footer="R";29:footer="=";30:footer="0"+shown_history[4];
 32:footer="Q";33:footer="=";34:footer=hexchar({3'b000,shown_used[12]});35:footer=hexchar(shown_used[11:8]);36:footer=hexchar(shown_used[7:4]);37:footer=hexchar(shown_used[3:0]);
 39:footer="M";40:footer="I";41:footer="N";42:footer="=";43:footer=hexchar({3'b000,shown_minimum[12]});44:footer=hexchar(shown_minimum[11:8]);45:footer=hexchar(shown_minimum[7:4]);46:footer=hexchar(shown_minimum[3:0]);
 default:footer=" ";endcase end endfunction
 function [7:0] audio_line;input [5:0] c;begin
 audio_line=" ";case(c)
 0:audio_line="A";1:audio_line="U";2:audio_line="D";
 4:audio_line="Q";5:audio_line="=";6:audio_line=hexchar({3'b0,aq[12]});7:audio_line=hexchar(aq[11:8]);8:audio_line=hexchar(aq[7:4]);9:audio_line=hexchar(aq[3:0]);
 11:audio_line="M";12:audio_line="I";13:audio_line="N";14:audio_line="=";15:audio_line=hexchar({3'b0,amin[12]});16:audio_line=hexchar(amin[11:8]);17:audio_line=hexchar(amin[7:4]);18:audio_line=hexchar(amin[3:0]);
 20:audio_line="A";21:audio_line="3";22:audio_line="Q";23:audio_line="=";24:audio_line=hexchar({3'b0,afirst[12]});25:audio_line=hexchar(afirst[11:8]);26:audio_line=hexchar(afirst[7:4]);27:audio_line=hexchar(afirst[3:0]);
 29:audio_line="S";30:audio_line="=";31:audio_line=hexchar(aflags[7:4]);32:audio_line=hexchar(aflags[3:0]);
 34:audio_line="B";35:audio_line="=";36:audio_line="3";
 default:audio_line=" ";endcase end endfunction
 // The inherited compact alphabet lacks Q and '='; keep the shared font
 // unchanged and provide only these diagnostic glyphs locally.
 function [4:0] diagfont;input [7:0] ch;input [2:0] row;reg [34:0] bits;
 begin
  if(ch=="Q"||ch=="=")begin
   bits=ch=="Q"?35'b01110_10001_10001_10001_10101_10010_01101:35'b00000_00000_11111_00000_11111_00000_00000;
   case(row)0:diagfont=bits[34:30];1:diagfont=bits[29:25];2:diagfont=bits[24:20];3:diagfont=bits[19:15];
    4:diagfont=bits[14:10];5:diagfont=bits[9:5];6:diagfont=bits[4:0];default:diagfont=0;endcase
  end else diagfont=fontrow(ch,row);
 end endfunction
 // Stage P registers geometry before the character mux. This removes the
 // x subtraction + 3-line character decode from a single pixel-clock path.
 // RGB, coordinates, timing and picture/audio gate receive the SAME cycle.
 reg [11:0] xp,yp,txp;reg [23:0] rgbp;reg [3:0] ctlp;
 reg panelp,glyphp,redp;reg [1:0] linep;reg [2:0] rowp;
 reg [11:0] xx0,yy0,xx1,yy1;reg [23:0] rgb0,rgb1;
 reg [3:0] ctl0,ctl1;reg panel0,panel1,glyph0,glyph1,red0,red1;
 reg [7:0] char0;reg [2:0] row0,col0,col1;reg [4:0] bits1;
 wire second=y>=30;wire third=AUDIO_DEBUG&&y>=48;
 wire [11:0] tx=x-12'd16;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  xp<=0;yp<=0;txp<=0;rgbp<=0;ctlp<=4'b0110;panelp<=0;glyphp<=0;redp<=0;linep<=0;rowp<=0;
  xx0<=0;yy0<=0;xx1<=0;yy1<=0;rgb0<=0;rgb1<=0;ctl0<=4'b0110;ctl1<=4'b0110;
  panel0<=0;panel1<=0;glyph0<=0;glyph1<=0;red0<=0;red1<=0;
  char0<=0;row0<=0;col0<=0;col1<=0;bits1<=0;
  x_out<=0;y_out<=0;rgb_out<=0;de_out<=0;hs_out<=1;vs_out<=1;picture_visible_out<=0;
 end else begin
  xp<=x;yp<=y;txp<=tx;rgbp<=rgb;ctlp<={de,hs,vs,picture_visible};
  panelp<=(enable||(ALWAYS_SHOW_FAULTS&&history!=0))&&(!FAULT_ONLY||!picture_visible||history!=0)&&de&&x>=8&&x<912&&y>=8&&y<(AUDIO_DEBUG?66:48);
  glyphp<=de&&x>=16&&x<896&&tx[3:0]<10&&((y>=12&&y<26)||(y>=30&&y<44)||(AUDIO_DEBUG&&y>=48&&y<62));
  linep<=third?2'd2:(second?2'd1:2'd0);
  rowp<=(y-(third?12'd48:(second?12'd30:12'd12)))>>1;redp<=history!=0;
  xx0<=xp;yy0<=yp;rgb0<=rgbp;ctl0<=ctlp;
  xx1<=xx0;yy1<=yy0;rgb1<=rgb0;ctl1<=ctl0;
  panel0<=panelp;glyph0<=glyphp;red0<=redp;
  char0<=linep==2?audio_line(txp[9:4]):(linep==1?footer(txp[9:4]):header(txp[9:4]));
  row0<=rowp;col0<=txp[3:1];
  panel1<=panel0;glyph1<=glyph0;red1<=red0;col1<=col0;bits1<=diagfont(char0,row0);
  x_out<=xx1;y_out<=yy1;{de_out,hs_out,vs_out,picture_visible_out}<=ctl1;
  rgb_out<=panel1?((glyph1&&bits1[4-col1])?24'hffffff:(red1?24'h601020:24'h102848)):rgb1;
 end
endmodule
