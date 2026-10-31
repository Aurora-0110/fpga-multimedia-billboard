// SPI mode 0, MSB first. All logic uses clk; SCK is only a registered output.
`timescale 1ns/1ps
module spi_byte #(parameter integer HALF_DIV=60, DATA_HALF_DIV=HALF_DIV)(
 input wire clk,rst_n,start,fast_mode,input wire [7:0] tx,
 input wire miso,output reg sck,mosi,busy,done,output reg [7:0] rx);
 // Latch mode at byte start: changing fast_mode during a byte cannot truncate SCK.
 reg [15:0] divider;
 // Sample MISO one clk edge before the generated SCK rising edge. The card
 // changes data on SCK falling edges, so this preserves mode-0 protocol while
 // removing the direct pad-to-capture hold path seen after full-system place.
 reg miso_q;
 reg data_mode;
 wire [15:0] terminal_count=data_mode ? DATA_HALF_DIV-1 : HALF_DIV-1;
 reg [2:0] bit_index;
 reg [7:0] tx_shift,rx_shift;
always @(negedge clk or negedge rst_n)
 if(!rst_n) miso_q<=1'b1;
 else miso_q<=miso;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   divider<=0;data_mode<=0;bit_index<=0;tx_shift<=8'hff;rx_shift<=0;
   sck<=0;mosi<=1;busy<=0;done<=0;rx<=0;
  end else begin
   done<=0;
   if(!busy) begin
    sck<=0;mosi<=1;
    if(start) begin busy<=1;data_mode<=fast_mode;divider<=0;bit_index<=7;
     tx_shift<=tx;rx_shift<=0;mosi<=tx[7];end
   end else if(divider==terminal_count) begin
    divider<=0;
    if(!sck) begin sck<=1;rx_shift<={rx_shift[6:0],miso_q};end
    else begin
     sck<=0;
     if(bit_index==0) begin busy<=0;done<=1;rx<=rx_shift;mosi<=1;end
     else begin bit_index<=bit_index-1'b1;tx_shift<={tx_shift[6:0],1'b1};mosi<=tx_shift[6];end
    end
   end else divider<=divider+1'b1;
  end
 end
endmodule
