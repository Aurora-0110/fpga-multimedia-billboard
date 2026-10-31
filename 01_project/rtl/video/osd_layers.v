`timescale 1ns/1ps
// RGB background -> translucent panels -> actual official logo -> dynamic text.
// Alpha range 0..16 (clamped), rounded per channel. Constant layer alphas permit
// shift/add synthesis; all video controls, coordinates and audio gate delay 6 clocks.
module osd_layers #(parameter PANEL_ALPHA=8,LOGO_ALPHA=12,TEXT_ALPHA=16,FRAMES_PER_SECOND=60,SHOW_PARAMS=0)(
 input wire clk,rst_n,input wire [11:0] x,y,input wire [23:0] rgb,
 input wire de,hs,vs,picture_visible,auto_mode,input wire [1:0] image_index,
 input wire signed [7:0] brightness,input wire [2:0] contrast_q2,input wire [1:0] edit_field,
 output reg [11:0] x_out,y_out,output reg [23:0] rgb_out,
 output reg de_out,hs_out,vs_out,picture_visible_out);
 function [7:0] channel;input [7:0] d,s;input integer a;integer v,aa;begin
 aa=a<0?0:(a>16?16:a);v=d*(16-aa)+s*aa+8;channel=v>>4;end endfunction
 function [23:0] blend;input [23:0] d,s;input integer a;begin
 blend={channel(d[23:16],s[23:16],a),channel(d[15:8],s[15:8],a),channel(d[7:0],s[7:0],a)};end endfunction
`include "video/osd_font.vh"
 wire tick=de&&x==0&&y==0;
 reg [5:0] frames;reg [3:0] s0,s1,m0,m1,h0,h1;
 reg [9:0] scroll;reg shown_mode;
 reg signed [7:0] shown_bright;reg [2:0] shown_contrast;reg [1:0] shown_field;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin frames<=0;s0<=0;s1<=0;m0<=0;m1<=0;h0<=0;h1<=0;scroll<=0;shown_mode<=0;shown_bright<=0;shown_contrast<=4;shown_field<=0;end
 else if(tick)begin
  shown_mode<=auto_mode;shown_bright<=brightness;shown_contrast<=contrast_q2;shown_field<=edit_field;
  scroll<=scroll==767?0:scroll+1'b1;
  if(frames==FRAMES_PER_SECOND-1)begin
   frames<=0;
   if(s0==9)begin s0<=0;
    if(s1==5)begin s1<=0;
     if(m0==9)begin m0<=0;
      if(m1==5)begin m1<=0;
       if(h0==9)begin h0<=0;if(h1==9)h1<=0;else h1<=h1+1'b1;end else h0<=h0+1'b1;
      end else m1<=m1+1'b1;
     end else m0<=m0+1'b1;
    end else s1<=s1+1'b1;
   end else s0<=s0+1'b1;
  end else frames<=frames+1'b1;
 end
 function [7:0] header;input [5:0] c;begin
 header=" ";case(c)
 0:header="U";1:header="P";3:header="0"+h1;4:header="0"+h0;5:header=":";
 6:header="0"+m1;7:header="0"+m0;8:header=":";9:header="0"+s1;10:header="0"+s0;
 13:header="I";14:header="M";15:header="G";17:header="A"+image_index;
 20:header=shown_mode?"A":"M";21:header=shown_mode?"U":"A";
 22:header=shown_mode?"T":"N";23:header=shown_mode?"O":"U";
 24:header=shown_mode?" ":"A";25:header=shown_mode?" ":"L";
 default:header=" ";endcase end endfunction
 // No general divider in the pixel path: only the supported control values.
 function [7:0] parameter_text;input [5:0] c;reg [6:0] mag;reg [7:0] tens,ones;begin
 mag=shown_bright[7]?-shown_bright:shown_bright;
 case(mag)0:begin tens="0";ones="0";end 16:begin tens="1";ones="6";end
 32:begin tens="3";ones="2";end 48:begin tens="4";ones="8";end
 64:begin tens="6";ones="4";end default:begin tens="?";ones="?";end endcase
 parameter_text=" ";case(c)
 0:parameter_text="B";1:parameter_text=":";2:parameter_text=shown_bright[7]?"-":"+";
 3:parameter_text=tens;4:parameter_text=ones;
 7:parameter_text="C";8:parameter_text=":";
 9:parameter_text=shown_contrast>=4?"1":"0";
 10:case(shown_contrast)2,6:parameter_text="5";3:parameter_text="7";5:parameter_text="2";default:parameter_text="0";endcase
 11:parameter_text=(shown_contrast==3||shown_contrast==5)?"5":"0";
 12:parameter_text="%";
 16:parameter_text=shown_field==0?"V":"E";17:parameter_text=shown_field==0?"I":"D";
 18:parameter_text=shown_field==0?"E":"I";19:parameter_text=shown_field==0?"W":"T";
 20:parameter_text=shown_field==0?" ":":";21:parameter_text=shown_field==1?"B":(shown_field==2?"C":" ");
 default:parameter_text=" ";endcase end endfunction
 function [7:0] slogan;input [5:0] c;begin
 case(c)
 0:slogan="A";1:slogan="N";2:slogan="L";3:slogan="O";4:slogan="G";5:slogan="I";6:slogan="C";
 8:slogan="F";9:slogan="P";10:slogan="G";11:slogan="A";
 13:slogan="M";14:slogan="U";15:slogan="L";16:slogan="T";17:slogan="I";
 18:slogan="M";19:slogan="E";20:slogan="D";21:slogan="I";22:slogan="A";
 24:slogan="B";25:slogan="I";26:slogan="L";27:slogan="L";28:slogan="B";
 29:slogan="O";30:slogan="A";31:slogan="R";32:slogan="D";
 default:slogan=" ";endcase end endfunction

 // Six balanced stages: local coordinates, character/ROM row, glyph row,
 // panel/bit mask, logo blend, text blend. All output controls delay six clocks.
 reg [23:0] base[0:2];reg [11:0] xx[0:4],yy[0:4];
 reg [3:0] ctl[0:4];reg pan[0:2],lz[0:2];
 reg [9:0] hx0;reg [10:0] sx0;reg [6:0] lx0;reg [5:0] ly0;
 reg param0;reg hz0,tz0;reg [7:0] hc1,sc1;reg [2:0] hr1,sr1,colh1,cols1;
 reg hv1,sv1,hv2,sv2;reg [2:0] colh2,cols2;reg [4:0] hb2,sb2;
 wire [10:0] sxraw=x-12'd328+scroll;
 wire [10:0] sxwrapped=sxraw>=768?sxraw-11'd768:sxraw;
 wire [1:0] lp1;reg [1:0] lp2;
 official_logo_sync logo(.clk(clk),.x(lx0),.y(ly0),.pixel(lp1));
 reg [23:0] r3,r4,lc3;reg logo3,text3,text4;
 integer i;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  for(i=0;i<3;i=i+1)begin base[i]<=0;pan[i]<=0;lz[i]<=0;end
  for(i=0;i<5;i=i+1)begin xx[i]<=0;yy[i]<=0;ctl[i]<=4'b0110;end
  hx0<=0;sx0<=0;lx0<=0;ly0<=0;hz0<=0;tz0<=0;param0<=0;
  hc1<=0;sc1<=0;hr1<=0;sr1<=0;colh1<=0;cols1<=0;hv1<=0;sv1<=0;
  hb2<=0;sb2<=0;colh2<=0;cols2<=0;hv2<=0;sv2<=0;lp2<=0;
  r3<=0;r4<=0;lc3<=0;logo3<=0;text3<=0;text4<=0;
  x_out<=0;y_out<=0;rgb_out<=0;de_out<=0;hs_out<=1;vs_out<=1;picture_visible_out<=0;
 end else begin
  base[0]<=rgb;for(i=1;i<3;i=i+1)base[i]<=base[i-1];
  xx[0]<=x;yy[0]<=y;ctl[0]<={de,hs,vs,picture_visible};
  for(i=1;i<5;i=i+1)begin xx[i]<=xx[i-1];yy[i]<=yy[i-1];ctl[i]<=ctl[i-1];end
  x_out<=xx[4];y_out<=yy[4];{de_out,hs_out,vs_out,picture_visible_out}<=ctl[4];
  pan[0]<=de&&picture_visible&&x>=320&&x<960&&((y>=120&&y<188)||(y>=564&&y<600));
  lz[0]<=de&&picture_visible&&x>=328&&x<440&&y>=126&&y<182;
  for(i=1;i<3;i=i+1)begin pan[i]<=pan[i-1];lz[i]<=lz[i-1];end
  hx0<=x-12'd456;sx0<=sxwrapped;lx0<=x-12'd328;ly0<=y-12'd126;
  param0<=SHOW_PARAMS&&y>=166&&y<180;
  hz0<=de&&picture_visible&&x>=456&&x<936&&((y>=144&&y<158)||(SHOW_PARAMS&&y>=166&&y<180));
  tz0<=de&&picture_visible&&x>=328&&x<952&&y>=576&&y<590;
  // 16px cells replace divide/modulo by 12; glyphs remain 10x14.
  hc1<=param0?parameter_text(hx0[9:4]):header(hx0[9:4]);sc1<=slogan(sx0[9:4]);
  hr1<=(yy[0]-(param0?12'd166:12'd144))>>1;sr1<=(yy[0]-12'd576)>>1;
  colh1<=hx0[3:1];cols1<=sx0[3:1];hv1<=hz0&&hx0[3:0]<10;sv1<=tz0&&sx0[3:0]<10;
  hb2<=fontrow(hc1,hr1);sb2<=fontrow(sc1,sr1);colh2<=colh1;cols2<=cols1;
  hv2<=hv1;sv2<=sv1;lp2<=lp1;
  r3<=pan[2]?blend(base[2],24'h102040,PANEL_ALPHA):base[2];
  logo3<=lz[2]&&lp2!=0;lc3<=lp2==2?24'hcf1830:24'h183858;
  text3<=(hv2&&hb2[4-colh2])||(sv2&&sb2[4-cols2]);
  r4<=logo3?blend(r3,lc3,LOGO_ALPHA):r3;text4<=text3;
  rgb_out<=text4?blend(r4,24'hffffff,TEXT_ALPHA):r4;
 end
endmodule
