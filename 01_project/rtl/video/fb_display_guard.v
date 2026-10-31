`timescale 1ns/1ps
// FIFO has registered synchronous read. pop at the SAME edge as frame pixel 0;
// valid_d accompanies rdata one cycle later. Underflow latches fault and stops
// consumption until a coordinated epoch reset, never resumes mid-frame.
module fb_display_guard #(parameter integer PREFILL_WORDS=512)(
    input wire clk, rst_n, enable, frame_start, de, hs, vs,
    input wire fifo_empty,
    input wire [10:0] fifo_used,
    input wire [31:0] fifo_data,
    output wire fifo_pop,
    output wire [23:0] rgb,
    output reg de_d, hs_d, vs_d,
    output reg running, fault,
    output reg [15:0] underrun_count
);
    wire start_now=frame_start && enable && !fault && fifo_used>=PREFILL_WORDS;
    wire active=enable && !fault && (running || start_now);
    reg valid_d;
    assign fifo_pop=rst_n && active && de && !fifo_empty;
    assign rgb=valid_d?fifo_data[23:0]:24'h000000;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            running<=0; fault<=0; underrun_count<=0;
            valid_d<=0; de_d<=0; hs_d<=1; vs_d<=1;
        end else begin
            de_d<=de; hs_d<=hs; vs_d<=vs;
            valid_d<=fifo_pop;
            if(!enable) running<=0;
            else if(start_now) running<=1;
            if(active && de && fifo_empty) begin
                fault<=1; running<=0;
                if(!(&underrun_count)) underrun_count<=underrun_count+1'b1;
            end
        end
    end
endmodule
