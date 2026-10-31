`timescale 1ns / 1ps
//--------------------------------------------------------------------------------
// video_timing.v —— 640x480@60 行/场时序发生器（负极性同步，VESA DMT）
//
//   一行 = H_ACTIVE(640) + H_FP(16) + H_SYNC(96) + H_BP(48) = 800 个像素时钟
//   一场 = V_ACTIVE(480) + V_FP(10) + V_SYNC(2)  + V_BP(33)  = 525 行
//   像素时钟 25.2MHz -> 25.2M/(800*525) = 60Hz
//
// frame_start：每帧第一个有效像素位置给一个单周期脉冲，供上层切帧/计帧用。
//   注意必须寄存一拍并做 rst_n 门控：复位或 PLL 未锁时 x/y 恒为 0，
//   组合式 (x==0 && y==0) 会一直为高，计数就会溢出。
//--------------------------------------------------------------------------------
module video_timing #(
    parameter integer H_ACTIVE = 640,
    parameter integer H_FP     = 16,
    parameter integer H_SYNC   = 96,
    parameter integer H_BP     = 48,
    parameter integer V_ACTIVE = 480,
    parameter integer V_FP     = 10,
    parameter integer V_SYNC   = 2,
    parameter integer V_BP     = 33
) (
    input  wire        clk,        // 像素时钟
    input  wire        rst_n,
    output reg  [11:0] x,          // 当前行内像素坐标 0..H_TOTAL-1
    output reg  [11:0] y,          // 当前帧内行坐标   0..V_TOTAL-1
    output wire        hs,         // 行同步（负极性）
    output wire        vs,         // 场同步（负极性）
    output wire        de,         // 数据有效
    output wire        frame_start // 每帧起点单脉冲
);

    localparam integer H_TOTAL = H_ACTIVE + H_FP + H_SYNC + H_BP;
    localparam integer V_TOTAL = V_ACTIVE + V_FP + V_SYNC + V_BP;

    // Do not drive long functional paths directly from a falling-edge reset
    // release. This local posedge guard restores a full-cycle timing budget.
    // Keep coordinates at origin for that guard cycle so pixel (0,0) and
    // frame_start still coincide; asynchronous assertion still blanks DE.
    reg timing_valid;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) timing_valid <= 1'b0;
        else        timing_valid <= 1'b1;

    // 计数
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            x <= 12'd0;
            y <= 12'd0;
        end else if (!timing_valid) begin
            x <= 12'd0;
            y <= 12'd0;
        end else if (x == H_TOTAL - 1) begin
            x <= 12'd0;
            y <= (y == V_TOTAL - 1) ? 12'd0 : (y + 12'd1);
        end else begin
            x <= x + 12'd1;
        end
    end

    // 同步信号：负极性，落在 FP/BP 段内
    assign hs = ~((x >= H_ACTIVE + H_FP) && (x < H_ACTIVE + H_FP + H_SYNC));
    assign vs = ~((y >= V_ACTIVE + V_FP) && (y < V_ACTIVE + V_FP + V_SYNC));

    assign de = timing_valid && (x < H_ACTIVE) && (y < V_ACTIVE);

    // 帧起点：寄存一拍，避免复位期间常高
    reg fs_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fs_r <= 1'b0;
        else        fs_r <= timing_valid && (x == 12'd0) && (y == 12'd0);
    end
    assign frame_start = timing_valid && ((x == 12'd0) && (y == 12'd0)) && ~fs_r;

endmodule
