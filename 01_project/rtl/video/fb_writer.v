`timescale 1ns/1ps
// v040: accepted-request interface (registered ACK, NOT combinational ready).
// frame_ready means all writes ACCEPTED, not committed. Owner must also wait
// for sdram_ctrl.idle before reading. restart is deferred to a request boundary.
// ENABLE_SWEEP=0 is required by the static single-owner diagnostic top.
module fb_writer #(
    parameter integer LINE_BURSTS=160,
    parameter integer TOTAL_LINES=480,
    parameter integer WAIT_CYC=2475000,
    parameter integer ENABLE_SWEEP=1
)(
    input wire clk, rst_n, init_done, restart,
    output wire req_valid,
    output wire [1:0] req_bank,
    output wire [10:0] req_row,
    output wire [5:0] req_col,
    output wire [127:0] req_wdata,
    input wire req_ready,
    output reg frame_ready,
    output reg [11:0] sweep_y
);
    function [23:0] rgb_of;
        input [9:0]  x;
        input [9:0]  yy;
        input [11:0] hl;
        reg   [23:0] c;
        begin
            if      (x < 10'd80)  c = 24'hBFBFBF;   // 白
            else if (x < 10'd160) c = 24'hBFBF00;   // 黄
            else if (x < 10'd240) c = 24'h00BFBF;   // 青
            else if (x < 10'd320) c = 24'h00BF00;   // 绿
            else if (x < 10'd400) c = 24'hBF00BF;   // 品红
            else if (x < 10'd480) c = 24'hBF0000;   // 红
            else if (x < 10'd560) c = 24'h0000BF;   // 蓝
            else                  c = 24'h000000;   // 黑

            if (x[5:0] == 6'd0 || yy[5:0] == 6'd0)
                c = 24'hFFFFFF;                     // 网格

            if ({2'b00, yy} == hl)
                c = 24'h00FF00;                     // 扫描线

            rgb_of = c;
        end
    endfunction


    localparam ST_IDLE=0, ST_ISSUE=1, ST_NEXT=2, ST_WAIT=3;
    localparam PH_FILL=0, PH_ERASE=1, PH_DRAW=2;
    reg [1:0] st, phase;
    reg [9:0] ly;
    reg [7:0] xb;
    reg [11:0] hl;
    reg [31:0] wcnt;
    reg have_line, restart_pending;
    wire [9:0] x0={xb,2'b00};
    wire [18:0] burst_addr=ly*LINE_BURSTS+xb;
    wire [11:0] next_line=(sweep_y==TOTAL_LINES-1)?12'd0:sweep_y+12'd1;
    assign req_valid=(st==ST_ISSUE) && init_done;
    assign {req_bank,req_row,req_col}=burst_addr;
    assign req_wdata={
        {8'h00,rgb_of(x0+10'd3,ly,hl)},
        {8'h00,rgb_of(x0+10'd2,ly,hl)},
        {8'h00,rgb_of(x0+10'd1,ly,hl)},
        {8'h00,rgb_of(x0,ly,hl)}};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st<=ST_IDLE; phase<=PH_FILL; ly<=0; xb<=0; hl<=12'hfff;
            wcnt<=0; frame_ready<=0; sweep_y<=0;
            have_line<=0; restart_pending<=0;
        end else begin
            if (restart) restart_pending<=1;
            // Never retract/change a stalled request. An ACK must first retire it.
            if ((restart_pending || restart) && st!=ST_ISSUE) begin
                st<=ST_IDLE; phase<=PH_FILL; ly<=0; xb<=0; hl<=12'hfff;
                wcnt<=0; frame_ready<=0; sweep_y<=0;
                have_line<=0; restart_pending<=0;
            end else case(st)
                ST_IDLE: if(init_done) st<=ST_ISSUE;
                ST_ISSUE: if(req_ready) st<=ST_NEXT;
                ST_NEXT: begin
                    if (xb!=LINE_BURSTS-1) begin
                        xb<=xb+1'b1; st<=ST_ISSUE;
                    end else begin
                        xb<=0;
                        case(phase)
                            PH_FILL: if(ly!=TOTAL_LINES-1) begin
                                ly<=ly+1'b1; st<=ST_ISSUE;
                            end else begin
                                frame_ready<=1; wcnt<=0; st<=ST_WAIT;
                            end
                            PH_ERASE: begin
                                phase<=PH_DRAW; sweep_y<=next_line;
                                ly<=next_line[9:0]; hl<=next_line; st<=ST_ISSUE;
                            end
                            default: begin
                                have_line<=1; wcnt<=0; st<=ST_WAIT;
                            end
                        endcase
                    end
                end
                ST_WAIT: if(ENABLE_SWEEP) begin
                    if(wcnt>=WAIT_CYC) begin
                        wcnt<=0; ly<=sweep_y[9:0]; xb<=0;
                        phase<=have_line?PH_ERASE:PH_DRAW;
                        hl<=have_line?12'hfff:sweep_y;
                        st<=ST_ISSUE;
                    end else wcnt<=wcnt+1'b1;
                end
                default: st<=ST_IDLE;
            endcase
        end
    end
endmodule
