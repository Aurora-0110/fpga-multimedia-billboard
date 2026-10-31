`timescale 1ns/1ps
// VF-E20NG88 schematic p6: ONE U9 74HC595, Q0..Q7 -> LED0..7, active HIGH.
// MSB first. Data is snapshotted once per frame; changes never tear a frame.
module bist_status_595 #(parameter integer DIV=200, WIDTH=8)(
    input wire clk,rst_n,input wire [WIDTH-1:0] data,
    output reg sclk,dout,latch
);
    localparam integer TW=(DIV>1)?$clog2(DIV):1;
    localparam integer BW=(WIDTH>1)?$clog2(WIDTH):1;
    reg [WIDTH-1:0] snapshot;
    reg [TW-1:0] ticks;
    reg [BW-1:0] bit_index;
    reg [1:0] state;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin sclk<=0;dout<=0;latch<=0;snapshot<=0;ticks<=0;bit_index<=0;state<=0;end
        else case(state)
            0: begin snapshot<=data;dout<=data[WIDTH-1];sclk<=0;latch<=0;ticks<=0;bit_index<=0;state<=1;end
            1: if(ticks==DIV-1) begin sclk<=1;ticks<=0;state<=2;end else ticks<=ticks+1'b1;
            2: if(ticks==DIV-1) begin
                sclk<=0;ticks<=0;
                if(bit_index==WIDTH-1) state<=3;
                else begin bit_index<=bit_index+1'b1;dout<=snapshot[WIDTH-2-bit_index];state<=1;end
            end else ticks<=ticks+1'b1;
            3: if(ticks==DIV-1) begin latch<=1;ticks<=0;state<=0;end else ticks<=ticks+1'b1;
        endcase
    end
endmodule
