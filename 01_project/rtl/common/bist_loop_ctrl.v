`timescale 1ns/1ps
// v050: restart ONLY the BIST client between successful passes.
// SDRAM controller/refresh is NOT reset at automatic loop boundaries.
// run_rst_n is still the shared user K0 / power / PLL-loss session reset.
module bist_loop_ctrl #(
    parameter integer GAP_CLKS=49500000,
    parameter integer COUNT_WIDTH=32
)(
    input wire clk,rst_n,
    input wire seq_done,seq_passed,
    input wire [3:0] seq_error,
    output reg seq_enable,
    output wire running,
    output reg [COUNT_WIDTH-1:0] completed,
    output reg failed,
    output reg [3:0] first_error
);
    localparam ARM=0,RUN=1,GAP=2,FAIL=3;
    reg [1:0] state;
    reg [31:0] gap_ticks;
    assign running=(state==RUN);
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=ARM;seq_enable<=0;completed<=0;failed<=0;first_error<=0;gap_ticks<=0;
        end else case(state)
            ARM: begin seq_enable<=1;state<=RUN;end
            RUN: if(seq_done) begin
                if(seq_passed && seq_error==0) begin
                    if(completed!={COUNT_WIDTH{1'b1}}) completed<=completed+1'b1;
                    seq_enable<=0;gap_ticks<=0;state<=GAP;
                end else begin
                    // Leave client terminal evidence intact; no automatic retry.
                    failed<=1;first_error<=(seq_error==0)?4'hf:seq_error;state<=FAIL;
                end
            end
            GAP: begin
                if(gap_ticks>=GAP_CLKS-1) begin seq_enable<=1;state<=RUN;end
                else gap_ticks<=gap_ticks+1'b1;
            end
            FAIL: begin seq_enable<=1;failed<=1;end
            default: begin failed<=1;first_error<=8;state<=FAIL;end
        endcase
    end
endmodule
