`timescale 1ns/1ps
// Load-side, sequential RGB888 scaler. This is NOT a live HDMI pixel-clock
// scaler. It deliberately backpressures the source while calculating pixels.
// Input rows arrive in BMP FILE order (padding already removed). At most two
// source rows are stored. Output y is logical display y, even for bottom-up BMP.
// Align-corners mapping, Q0.8 weights, round once after both axes. No divider.
module bilinear_stream_scaler #(
 parameter OUT_WIDTH=1280, OUT_HEIGHT=720,
 parameter MAX_WIDTH=1280, MAX_HEIGHT=1024
)(
 input wire clk,rst_n,start,
 input wire [15:0] src_width,src_height,input wire top_down,
 output reg busy,done,error,output reg [3:0] error_code,
 input wire in_valid,output wire in_ready,input wire [23:0] in_rgb,
 output wire out_valid,input wire out_ready,output wire [23:0] out_rgb,
 output wire [15:0] out_x,out_y
);
 localparam IDLE=0,LOAD=1,READ0=2,WAIT0=3,TAKE0=4,
            READ1=5,WAIT1=6,TAKE1=7,FRAC=8,SEND=9,RESULT=10,
            XSTEP=11,YSTEP=12;
 reg [3:0] state;
 // Range-proven widths: dimensions validated BEFORE capture; source row
 // count includes h as a sentinel, but indices never exceed max-1.
 localparam WW=MAX_WIDTH<2?1:$clog2(MAX_WIDTH+1),HH=MAX_HEIGHT<2?1:$clog2(MAX_HEIGHT+1);
 localparam SXW=MAX_WIDTH<2?1:$clog2(MAX_WIDTH),SYW=MAX_HEIGHT<2?1:$clog2(MAX_HEIGHT);
 localparam DXW=OUT_WIDTH<2?1:$clog2(OUT_WIDTH),DYW=OUT_HEIGHT<2?1:$clog2(OUT_HEIGHT);
 localparam RXW=OUT_WIDTH+MAX_WIDTH<4?1:$clog2(OUT_WIDTH+MAX_WIDTH-2);
 localparam RYW=OUT_HEIGHT+MAX_HEIGHT<4?1:$clog2(OUT_HEIGHT+MAX_HEIGHT-2);
 localparam FXW=OUT_WIDTH<3?1:$clog2(OUT_WIDTH-1),FYW=OUT_HEIGHT<3?1:$clog2(OUT_HEIGHT-1);
 reg [WW-1:0] w;reg [HH-1:0] h,loaded;
 reg [SXW-1:0] wx,sx;reg [SYW-1:0] sy;
 reg [DXW-1:0] dx;reg [DYW-1:0] dy;
 reg td;
 reg [RXW-1:0] rx;reg [RYW-1:0] ry;
 reg [FXW-1:0] fxrem;reg [FYW-1:0] fyrem;
 reg [7:0] fx,fy;reg [3:0] frac_bit;
 localparam ROW_AW=(MAX_WIDTH<=1)?1:$clog2(MAX_WIDTH);
 localparam ROW_DEPTH=(1<<ROW_AW);
 // Physical RAM uses power-of-two depth and bounded addresses.
 (* ram_style = "bram" *) reg [23:0] row0[0:ROW_DEPTH-1];
 (* ram_style = "bram" *) reg [23:0] row1[0:ROW_DEPTH-1];
 reg [ROW_AW-1:0] rd_addr;
 reg [23:0] q0,q1,p00,p10,p01,p11;
 wire [SXW:0] sx_plus={1'b0,sx}+1'b1;
 wire [SXW-1:0] xnext=sx_plus<w?sx_plus[SXW-1:0]:sx;
 wire [SYW:0] sy_plus={1'b0,sy}+1'b1;
 wire [SYW-1:0] ynext=sy_plus<h?sy_plus[SYW-1:0]:sy;
 wire [FXW:0] next_fxrem={fxrem,1'b0};
 wire [FYW:0] next_fyrem={fyrem,1'b0};
 wire kernel_ready,kernel_valid;
 wire [31:0] kernel_tag;
 assign in_ready=busy&&(state==LOAD)&&(loaded<=ynext);
 assign out_valid=kernel_valid&&(state==RESULT)&&busy;
 assign out_x=kernel_tag[15:0];assign out_y=kernel_tag[31:16];
 wire [15:0] logical_y=td?dy:OUT_HEIGHT-1-dy;
 wire [15:0] logical_x=dx;
 bilinear_rgb888 #(.TAG_BITS(32)) interp(
  .clk(clk),.rst_n(rst_n),.in_valid(busy&&(state==SEND)),.in_ready(kernel_ready),
  .p00(p00),.p10(p10),.p01(p01),.p11(p11),.fx(fx),.fy(fy),
  .in_tag({logical_y,logical_x}),.out_valid(kernel_valid),
  .out_ready(out_ready&&(state==RESULT)&&busy),.out_rgb(out_rgb),.out_tag(kernel_tag));
 // Synchronous RAM reads. The two row banks share one read address; data is
 // selected by the source row parity. RAM contents need not be reset.
 always @(posedge clk)begin
  q0<=row0[rd_addr];q1<=row1[rd_addr];
  if(in_valid&&in_ready)begin
   if(loaded[0])row1[wx[ROW_AW-1:0]]<=in_rgb;else row0[wx[ROW_AW-1:0]]<=in_rgb;
  end
 end
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  state<=IDLE;busy<=0;done<=0;error<=0;error_code<=0;
  w<=0;h<=0;td<=0;loaded<=0;wx<=0;dx<=0;dy<=0;sx<=0;sy<=0;
  rx<=0;ry<=0;fxrem<=0;fyrem<=0;fx<=0;fy<=0;frac_bit<=0;
  rd_addr<=0;p00<=0;p10<=0;p01<=0;p11<=0;
 end else if(start&&!busy)begin
  done<=0;error<=0;error_code<=0;
  if(src_width==0||src_height==0||src_width>MAX_WIDTH||src_height>MAX_HEIGHT||
     OUT_WIDTH<2||OUT_HEIGHT<2||OUT_WIDTH>65535||OUT_HEIGHT>65535||
     MAX_WIDTH>65535||MAX_HEIGHT>65535)begin
   busy<=0;error<=1;error_code<=1;state<=IDLE;
  end else begin
   busy<=1;w<=src_width;h<=src_height;td<=top_down;
   loaded<=0;wx<=0;dx<=0;dy<=0;sx<=0;sy<=0;rx<=0;ry<=0;
   state<=LOAD;
  end
 end else if(busy)case(state)
  LOAD:begin
   if(loaded>ynext)state<=READ0;
   else if(in_valid&&in_ready)begin
    if(wx==w-1)begin wx<=0;loaded<=loaded+1'b1;end
    else wx<=wx+1'b1;
   end
  end
  READ0:begin rd_addr<=sx;state<=WAIT0;end
  WAIT0:state<=TAKE0;
  TAKE0:begin
   p00<=sy[0]?q1:q0;p01<=ynext[0]?q1:q0;state<=READ1;
  end
  READ1:begin rd_addr<=xnext;state<=WAIT1;end
  WAIT1:state<=TAKE1;
  TAKE1:begin
   p10<=sy[0]?q1:q0;p11<=ynext[0]?q1:q0;
   fx<=0;fy<=0;fxrem<=rx;fyrem<=ry;frac_bit<=0;state<=FRAC;
  end
  FRAC:begin
   // Eight restoring fractional divide iterations. Denominators are output
   // dimensions minus one and hence constants, not costly variable dividers.
   if(next_fxrem>=OUT_WIDTH-1)begin fxrem<=next_fxrem-(OUT_WIDTH-1);fx<={fx[6:0],1'b1};end
   else begin fxrem<=next_fxrem;fx<={fx[6:0],1'b0};end
   if(next_fyrem>=OUT_HEIGHT-1)begin fyrem<=next_fyrem-(OUT_HEIGHT-1);fy<={fy[6:0],1'b1};end
   else begin fyrem<=next_fyrem;fy<={fy[6:0],1'b0};end
   if(frac_bit==7)state<=SEND;else frac_bit<=frac_bit+1'b1;
  end
  SEND:if(kernel_ready)state<=RESULT;
  RESULT:if(out_valid&&out_ready)begin
   if(dx==OUT_WIDTH-1)begin
    if(dy==OUT_HEIGHT-1)begin busy<=0;done<=1;state<=IDLE;end
    else begin dy<=dy+1'b1;dx<=0;sx<=0;rx<=0;ry<=ry+h-1'b1;state<=YSTEP;end
   end else begin dx<=dx+1'b1;rx<=rx+w-1'b1;state<=XSTEP;end
  end
  XSTEP:begin
   if(rx>=OUT_WIDTH-1)begin rx<=rx-(OUT_WIDTH-1);sx<=sx+1'b1;end
   else state<=READ0;
  end
  YSTEP:begin
   if(ry>=OUT_HEIGHT-1)begin ry<=ry-(OUT_HEIGHT-1);sy<=sy+1'b1;end
   else state<=LOAD;
  end
  default:begin busy<=0;error<=1;error_code<=2;state<=IDLE;end
 endcase
endmodule
