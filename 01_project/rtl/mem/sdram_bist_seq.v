`timescale 1ns/1ps
// v043: destructive SDRAM BIST. ACK is registered acceptance, not completion.
// Default: all 524288 x 16-byte bursts, address pattern + complement.
// No requests during refresh hold. Does NOT claim March/physical fault coverage.
module sdram_bist_seq #(
    parameter [18:0] BASE_BURST=19'd0,
    parameter integer TEST_BURSTS=524288,
    parameter integer INIT_TIMEOUT=100000,
    parameter integer REQUEST_TIMEOUT=4096,
    parameter integer RESPONSE_TIMEOUT=4096,
    parameter integer DRAIN_TIMEOUT=4096,
    parameter integer HOLD_CLKS=3200000,
    parameter integer MIN_REFRESH=4096
)(
    input wire clk,rst_n,init_done,ctrl_idle,
    input wire [31:0] refresh_count,
    output reg req_valid,req_we,
    output reg [1:0] req_bank,
    output reg [10:0] req_row,
    output reg [5:0] req_col,
    output reg [127:0] req_wdata,
    input wire req_ready,rsp_valid,
    input wire [127:0] rsp_rdata,
    output reg done,passed,
    output reg [3:0] error_code,
    output reg [18:0] fail_burst,
    output reg fail_round,
    output reg [127:0] fail_expected,fail_actual,
    output reg [19:0] burst_cnt, // completed reads in CURRENT round, 0..524288
    output reg [20:0] writes_done,reads_done, // total across BOTH rounds
    output wire [3:0] phase,
    output wire test_round
);
    localparam INIT=0, WRITE=1, WACK=2, DRAIN=3, HOLD=4,
               READ=5, RACK=6, RESP=7, NEXT=8, FINISH=9, PASS=10, FAIL=11;
    reg [3:0] state;
    reg [18:0] bi;
    reg round_q;
    reg [31:0] ticks,refresh_start;
    localparam [18:0] LAST_BURST=BASE_BURST+TEST_BURSTS-1;
    assign phase=state;
    assign test_round=round_q;
    function [127:0] pattern;
        input [18:0] a; input inv;
        reg [19:0] b; reg [31:0] w0,w1,w2,w3;
        begin
            b={1'b0,a};
            w0={12'd0,b}^32'hA5A55A5A;
            w1={12'd0,b}^32'h5A5AA5A5;
            w2={b,12'd0}^32'h0F0F0F0F;
            w3={b,12'd0}^32'hF0F0F0F0;
            pattern=inv ? ~{w3,w2,w1,w0}:{w3,w2,w1,w0};
        end
    endfunction
    task fail;
        input [3:0] code;
        begin
            done<=1; passed<=0; error_code<=code;
            fail_burst<=bi; fail_round<=round_q;
            fail_expected<=pattern(bi,round_q);
            fail_actual<=(code==4)?rsp_rdata:128'd0;
            req_valid<=0; state<=FAIL;
        end
    endtask
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=INIT; bi<=BASE_BURST; round_q<=0; ticks<=0; refresh_start<=0;
            req_valid<=0;req_we<=0;req_bank<=0;req_row<=0;req_col<=0;req_wdata<=0;
            done<=0;passed<=0;error_code<=0;fail_burst<=0;fail_round<=0;
            fail_expected<=0;fail_actual<=0;burst_cnt<=0;writes_done<=0;reads_done<=0;
        end else if(state!=INIT && !done && !init_done) fail(7);
        else case(state)
            INIT: begin
                if(init_done) begin state<=WRITE;ticks<=0;end
                else if(ticks>=INIT_TIMEOUT-1) fail(1);
                else ticks<=ticks+1;
            end
            WRITE,READ: begin
                req_valid<=1;req_we<=(state==WRITE);
                req_bank<=bi[18:17];req_row<=bi[16:6];req_col<=bi[5:0];
                req_wdata<=pattern(bi,round_q);ticks<=0;
                state<=(state==WRITE)?WACK:RACK;
            end
            WACK: begin
                if(req_ready) begin
                    req_valid<=0;ticks<=0;writes_done<=writes_done+1;
                    if(bi==LAST_BURST) state<=DRAIN;
                    else begin bi<=bi+1;state<=WRITE;end
                end else if(ticks>=REQUEST_TIMEOUT-1) fail(2);
                else ticks<=ticks+1;
            end
            DRAIN: begin
                if(ctrl_idle) begin
                    refresh_start<=refresh_count;ticks<=0;state<=HOLD;
                end else if(ticks>=DRAIN_TIMEOUT-1) fail(5);
                else ticks<=ticks+1;
            end
            HOLD: begin
                // Unsigned modular subtraction handles refresh counter rollover.
                if(ticks>=HOLD_CLKS-1) begin
                    if((refresh_count-refresh_start)<MIN_REFRESH) fail(6);
                    else begin bi<=BASE_BURST;burst_cnt<=0;ticks<=0;state<=READ;end
                end else ticks<=ticks+1;
            end
            RACK: begin
                if(req_ready) begin
                    req_valid<=0;ticks<=0;
                    if(rsp_valid) begin
                        if(rsp_rdata!==pattern(bi,round_q)) fail(4);
                        else begin reads_done<=reads_done+1;burst_cnt<=burst_cnt+1;state<=NEXT;end
                    end else state<=RESP;
                end else if(ticks>=REQUEST_TIMEOUT-1) fail(2);
                else ticks<=ticks+1;
            end
            RESP: begin
                if(rsp_valid) begin
                    ticks<=0;
                    if(rsp_rdata!==pattern(bi,round_q)) fail(4);
                    else begin reads_done<=reads_done+1;burst_cnt<=burst_cnt+1;state<=NEXT;end
                end else if(ticks>=RESPONSE_TIMEOUT-1) fail(3);
                else ticks<=ticks+1;
            end
            NEXT: begin
                if(bi==LAST_BURST) state<=FINISH;
                else begin bi<=bi+1;state<=READ;end
                ticks<=0;
            end
            FINISH: begin
                if(ctrl_idle) begin
                    if(!round_q) begin round_q<=1;bi<=BASE_BURST;burst_cnt<=0;state<=WRITE;end
                    else begin done<=1;passed<=1;state<=PASS;end
                    ticks<=0;
                end else if(ticks>=DRAIN_TIMEOUT-1) fail(5);
                else ticks<=ticks+1;
            end
            PASS,FAIL: req_valid<=0;
            default: fail(8);
        endcase
    end
endmodule
