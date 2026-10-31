// Related clocks from ONE PLL: serial_clk = 5 * pixel_clk, phase locked.
// The parallel word remains stable for one pixel. Capture ~2 serial clocks
// after the pixel toggle, then emit 5 DDR pairs without gaps. Not an async FIFO.
`timescale 1ns/1ps
module tmds_serializer #(parameter SEPARATE_PIXEL_RESET=0)(input wire clk_pix,clk_5x,rst,
 input wire[9:0] din,output wire q,input wire rst_pix_n);
 wire pixel_clk=clk_pix,serial_clk=clk_5x,rst_n=~rst;
 wire marker_rst_n=SEPARATE_PIXEL_RESET?rst_pix_n:rst_n;
 wire [9:0] word=din;
 wire serial_out;
 assign q=serial_out;
 reg marker;reg[1:0] marker_sync;reg marker_seen;reg[9:0] shift;
 wire load=(marker_sync[1]!=marker_seen);
 always @(posedge pixel_clk or negedge marker_rst_n)
  if(!marker_rst_n)marker<=0;else marker<=~marker;
 always @(posedge serial_clk or negedge rst_n)begin
  if(!rst_n)begin marker_sync<=0;marker_seen<=0;shift<=0;end
  else begin
   marker_sync<={marker_sync[0],marker};marker_seen<=marker_sync[1];
   if(load)shift<=word;else shift<={2'b00,shift[9:2]};
  end
 end
 // Both inputs sampled on posedge; d1 appears on the following negedge.
 // ODDR itself is not asynchronously reset: upstream shift clears on reset,
 // and propagates zero through the pad on its next two edges. This avoids
 // routing high-fanout reset to four far-apart 371.25MHz pad reset pins.
 // No data/clock timing exception is used to conceal reset-recovery failure.
 EG_LOGIC_ODDR #(.ASYNCRST("DISABLE")) u_ddr(
 .q(serial_out),.clk(serial_clk),.d0(shift[0]),.d1(shift[1]),.rst(1'b0));
endmodule

// TMDS forwarded clock is the PIXEL clock, not the 5x serializer clock.
// Same serializer and reset as data lanes preserve word alignment.
module tmds_clock_lane #(parameter SEPARATE_PIXEL_RESET=0)(input wire clk_pix,clk_5x,rst,output wire q,input wire rst_pix_n);
 tmds_serializer #(.SEPARATE_PIXEL_RESET(SEPARATE_PIXEL_RESET)) u_clock(.clk_pix(clk_pix),.clk_5x(clk_5x),.rst(rst),
 .din(10'b1111100000),.q(q),.rst_pix_n(rst_pix_n));
endmodule
