`timescale 1ns / 1ps
`include "adboard_pkg.vh"
//--------------------------------------------------------------------------------
// bringup_top.v —— 板级第一步：只有 PLL + 彩条 + HDMI，不接 SD/SDRAM
//
// 目的：把"能不能出图"单独隔离出来验证。
//   出图  -> 说明 PLL 频率、TMDS 编码/串行化、引脚约束、显示器握手 全部正确
//   不出图 -> 逐个查：示波器量 P13 有没有 24MHz、量 HDMI CLK 差分有没有 126MHz
//
// 按键：KEY0 切图案（彩条/灰阶/棋盘/边框十字），KEY1 预留
// 595 ：把 {图案号, 帧计数} 打到移位寄存器上，顺便验证 SPI 式输出
//--------------------------------------------------------------------------------
module bringup_top (
    input  wire       clk24m,         // 板载 24MHz 晶振（P13）
    input  wire [1:0] key_n,          // KEY0/KEY1，低有效
    output wire       led_sclk,       // 595 时钟
    output wire       led_dout,       // 595 数据
    output wire       led_latch,      // 595 锁存
    output wire       hdmi_clk_p,     // HDMI 时钟差分（只用 P 侧）
    output wire [2:0] hdmi_d_p        // HDMI 数据差分（只用 P 侧）
);

`ifdef SIM_SMALL
    localparam integer KEY_CNT = 50;
    localparam integer LED_CNT = 8;
`else
    localparam integer KEY_CNT = 24000;    // 24MHz 下约 1ms
    localparam integer LED_CNT = 120;      // 595 时钟约 100kHz
`endif

    // ---- PLL ----
    wire clk_pix, clk_5x, clk_aux, locked;

    pll_wrap #(.FIN_MHZ(24)) u_pll (
        .clk_in  (clk24m),
        .rst_n   (1'b1),
        .clk_pix (clk_pix),
        .clk_5x  (clk_5x),
        .clk_aux (clk_aux),
        .locked  (locked)
    );

    // ---- 复位：等 PLL 锁定后释放，再同步几拍 ----
    reg [3:0] rst_sync;
    always @(posedge clk_pix) begin
        if (!locked) rst_sync <= 4'd0;
        else         rst_sync <= {rst_sync[2:0], 1'b1};
    end
    wire rst_n = rst_sync[3];

    // ---- 按键 ----
    wire key0_press, key1_press;

    key_debounce #(.CNT(KEY_CNT)) u_key0 (
        .clk (clk_pix), .rst_n (rst_n), .key_n (key_n[0]), .press (key0_press)
    );
    key_debounce #(.CNT(KEY_CNT)) u_key1 (
        .clk (clk_pix), .rst_n (rst_n), .key_n (key_n[1]), .press (key1_press)
    );

    reg [1:0] mode;
    always @(posedge clk_pix or negedge rst_n) begin
        if (!rst_n)         mode <= 2'd0;
        else if (key0_press) mode <= mode + 2'd1;
    end

    // ---- 图案 ----
    wire [7:0] r, g, b;
    wire de, hs, vs;

    tpg_bars #(.BAR_W(`H_ACTIVE/8)) u_tpg (
        .clk   (clk_pix),
        .rst_n (rst_n),
        .mode  (mode),
        .r     (r),
        .g     (g),
        .b     (b),
        .de    (de),
        .hs    (hs),
        .vs    (vs),
        .x     (),
        .y     ()
    );

    // ---- HDMI 输出 ----
    hdmi_tx_wrap u_hdmi (
        .clk_pix    (clk_pix),
        .clk_5x     (clk_5x),
        .rst_n      (rst_n),
        .r          (r),
        .g          (g),
        .b          (b),
        .de         (de),
        .hs         (hs),
        .vs         (vs),
        .tmds_clk_p (hdmi_clk_p),
        .tmds_clk_n (),
        .tmds_d_p   (hdmi_d_p),
        .tmds_d_n   ()
    );

    // ---- 帧计数（vs 上升沿）----
    reg vs_d;
    reg [7:0] fcnt;
    always @(posedge clk_pix or negedge rst_n) begin
        if (!rst_n) begin
            vs_d <= 1'b0;
            fcnt <= 8'd0;
        end else begin
            vs_d <= vs;
            if (vs & ~vs_d) fcnt <= fcnt + 8'd1;
        end
    end

    // ---- 595 ----
    wire unused_key1 = key1_press;

    led_595 #(.CNT(LED_CNT)) u_595 (
        .clk   (clk_pix),
        .rst_n (rst_n),
        .data  ({mode, fcnt, 4'h0, key_n[1], 1'b1}),
        .sclk  (led_sclk),
        .dout  (led_dout),
        .latch (led_latch)
    );

endmodule
