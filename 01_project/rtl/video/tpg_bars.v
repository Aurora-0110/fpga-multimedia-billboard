`timescale 1ns / 1ps
`include "adboard_pkg.vh"
//--------------------------------------------------------------------------------
// tpg_bars.v —— 测试图案发生器（验证链路用）
//   mode 0：8 级 75% 彩条（白 黄 青 绿 品 红 蓝 黑）—— 用来判断 R/G/B 通道接反
//   mode 1：8 级灰阶
//   mode 2：32x32 黑白棋盘 —— 判断像素时钟/分辨率是否正确
//   mode 3：黑底 + 白边框 + 十字线 —— 判断画面是否居中、有没有裁边
//--------------------------------------------------------------------------------
module tpg_bars #(
    parameter integer BAR_W = 80          // H_ACTIVE / 8
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [1:0]  mode,
    output reg  [7:0]  r,
    output reg  [7:0]  g,
    output reg  [7:0]  b,
    output wire        de,
    output wire        hs,
    output wire        vs,
    output wire [11:0] x,
    output wire [11:0] y
);

    wire [11:0] px, py;

    video_timing #(
        .H_ACTIVE (`H_ACTIVE), .H_FP (`H_FP), .H_SYNC (`H_SYNC), .H_BP (`H_BP),
        .V_ACTIVE (`V_ACTIVE), .V_FP (`V_FP), .V_SYNC (`V_SYNC), .V_BP (`V_BP)
    ) u_vt (
        .clk         (clk),
        .rst_n       (rst_n),
        .x           (px),
        .y           (py),
        .hs          (hs),
        .vs          (vs),
        .de          (de),
        .frame_start ()
    );

    assign x = px;
    assign y = py;

    // 8 段分界（不用除法器）
    function [2:0] bar_index;
        input [11:0] xx;
        begin
            if      (xx >= BAR_W*7) bar_index = 3'd7;
            else if (xx >= BAR_W*6) bar_index = 3'd6;
            else if (xx >= BAR_W*5) bar_index = 3'd5;
            else if (xx >= BAR_W*4) bar_index = 3'd4;
            else if (xx >= BAR_W*3) bar_index = 3'd3;
            else if (xx >= BAR_W*2) bar_index = 3'd2;
            else if (xx >= BAR_W*1) bar_index = 3'd1;
            else                    bar_index = 3'd0;
        end
    endfunction

    function [23:0] bar_color;
        input [2:0] idx;
        begin
            case (idx)
                3'd0: bar_color = 24'hBFBFBF;  // 白 75%
                3'd1: bar_color = 24'hBFBF00;  // 黄
                3'd2: bar_color = 24'h00BFBF;  // 青
                3'd3: bar_color = 24'h00BF00;  // 绿
                3'd4: bar_color = 24'hBF00BF;  // 品红
                3'd5: bar_color = 24'hBF0000;  // 红
                3'd6: bar_color = 24'h0000BF;  // 蓝
                default: bar_color = 24'h000000; // 黑
            endcase
        end
    endfunction

    wire [2:0]  bi    = bar_index(px);
    wire [23:0] bc    = bar_color(bi);
    wire [7:0]  gray  = {bi, 5'b00000};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r <= 8'd0;
            g <= 8'd0;
            b <= 8'd0;
        end else if (!de) begin
            r <= 8'd0;
            g <= 8'd0;
            b <= 8'd0;
        end else begin
            case (mode)
                2'd0: begin              // 彩条
                    r <= bc[23:16];
                    g <= bc[15:8];
                    b <= bc[7:0];
                end
                2'd1: begin              // 灰阶
                    r <= gray;
                    g <= gray;
                    b <= gray;
                end
                2'd2: begin              // 棋盘
                    if (px[5] ^ py[5]) begin
                        r <= 8'hFF; g <= 8'hFF; b <= 8'hFF;
                    end else begin
                        r <= 8'h00; g <= 8'h00; b <= 8'h00;
                    end
                end
                default: begin           // 边框 + 十字
                    if ((px < 12'd4) || (px >= `H_ACTIVE - 4) ||
                        (py < 12'd4) || (py >= `V_ACTIVE - 4))
                    begin
                        r <= 8'hFF; g <= 8'hFF; b <= 8'hFF;
                    end else if ((px > `H_ACTIVE/2 - 2 && px < `H_ACTIVE/2 + 2) ||
                                 (py > `V_ACTIVE/2 - 2 && py < `V_ACTIVE/2 + 2))
                    begin
                        r <= 8'hFF; g <= 8'h00; b <= 8'h00;
                    end else begin
                        r <= 8'h00; g <= 8'h00; b <= 8'h00;
                    end
                end
            endcase
        end
    end

endmodule
