`timescale 1ns/1ps
// Diagnostic-only, three-stage overlay. Its visibility NEVER depends on the
// framebuffer's picture_visible. Timing/coordinates and the real audio gate
// still advance together. A fault is exposed, NOT cleared or auto-retried.
module display_diagnostics(
 input wire clk,rst_n,input wire [11:0] x,y,input wire [23:0] rgb,
 input wire de,hs,vs,picture_visible,input wire [1:0] image_index,
 // Pixel-domain snapshot: [0]front [1]running [2]visible [3]underflow
 // [4]overflow [5]audio fault [6]memory released [7]loader active.
 input wire [7:0] status,input wire [7:0] tf_error,input wire [12:0] fifo_used,
 output reg [11:0] x_out,y_out,output reg [23:0] rgb_out,
 output reg de_out,hs_out,vs_out,picture_visible_out);
`include "video/osd_font.vh"
 function [7:0] hexchar;input [3:0] n;begin hexchar=n<10?("0"+n):("A"+n-10);end endfunction
 reg [15:0] frames;reg [7:0] shown,shown_error,first_error;reg [1:0] shown_index;
 reg [4:0] history,shown_history;reg memory_seen;
 reg [12:0] minimum,shown_minimum,shown_used;
 wire tick=de&&x==0&&y==0;
 wire [4:0] events={memory_seen&&!status[6],tf_error!=0,status[5:3]};
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  frames<=0;shown<=0;shown_error<=0;first_error<=0;shown_index<=0;
  history<=0;shown_history<=0;memory_seen<=0;minimum<=13'd4096;
  shown_minimum<=13'd4096;shown_used<=0;
 end else begin
  history<=history|events;
  if(status[6])memory_seen<=1;
  if(tf_error!=0&&first_error==0)first_error<=tf_error;
  if(status[1]&&de&&fifo_used<minimum)minimum<=fifo_used;
  if(tick)begin
   frames<=frames+1'b1;shown<=status;shown_error<=tf_error;
   shown_index<=image_index;shown_history<=history|events;
   shown_minimum<=minimum;shown_used<=fifo_used;
  end
 end
 function [7:0] header;input [5:0] c;begin
 header=" ";case(c)
 0:header="V";1:header="0";2:header="8";3:header="8";
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
 reg [11:0] xx0,yy0,xx1,yy1;reg [23:0] rgb0,rgb1;
 reg [3:0] ctl0,ctl1;reg panel0,panel1,glyph0,glyph1,red0,red1;
 reg [7:0] char0;reg [2:0] row0,col0,col1;reg [4:0] bits1;
 wire second=y>=30;
 wire [11:0] tx=x-12'd16;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  xx0<=0;yy0<=0;xx1<=0;yy1<=0;rgb0<=0;rgb1<=0;ctl0<=4'b0110;ctl1<=4'b0110;
  panel0<=0;panel1<=0;glyph0<=0;glyph1<=0;red0<=0;red1<=0;
  char0<=0;row0<=0;col0<=0;col1<=0;bits1<=0;
  x_out<=0;y_out<=0;rgb_out<=0;de_out<=0;hs_out<=1;vs_out<=1;picture_visible_out<=0;
 end else begin
  xx0<=x;yy0<=y;rgb0<=rgb;ctl0<={de,hs,vs,picture_visible};
  xx1<=xx0;yy1<=yy0;rgb1<=rgb0;ctl1<=ctl0;
  panel0<=de&&x>=8&&x<912&&y>=8&&y<48;
  glyph0<=de&&x>=16&&x<896&&tx[3:0]<10&&((y>=12&&y<26)||(y>=30&&y<44));
  char0<=second?footer(tx[9:4]):header(tx[9:4]);
  row0<=(y-(second?12'd30:12'd12))>>1;col0<=tx[3:1];red0<=history!=0;
  panel1<=panel0;glyph1<=glyph0;red1<=red0;col1<=col0;bits1<=fontrow(char0,row0);
  x_out<=xx1;y_out<=yy1;{de_out,hs_out,vs_out,picture_visible_out}<=ctl1;
  rgb_out<=panel1?((glyph1&&bits1[4-col1])?24'hffffff:(red1?24'h601020:24'h102848)):rgb1;
 end
endmodule
