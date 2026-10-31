`timescale 1ns / 1ps
//--------------------------------------------------------------------------------
// pll_wrap.v —— EG4 内部 PLL 包装
//
//   输入 FIN = 24MHz（板载晶振 P13）
//   VCO   = FIN / REFCLK_DIV * FBCLK_DIV = 24 / 1 * 21 = 504MHz
//   clk_pix  = VCO / CLKC0_DIV = 504 / 20 = 25.2MHz  （像素时钟，800x525x25.2M = 59.99Hz）
//   clk_5x   = VCO / CLKC1_DIV = 504 /  4 = 126MHz   （TMDS 5x 串行时钟）
//   clk_aux  = VCO / CLKC2_DIV = 504 /  6 =  84MHz   （预留：SDRAM）
//
//   注：CPHASE 取 DIV/2 让占空比 ≈50%（TD 生成的 IP 习惯用 DIV-1，若上板波形不对改这里）
//--------------------------------------------------------------------------------
module pll_wrap #(
    parameter integer FIN_MHZ = 24
) (
    input  wire clk_in,
    input  wire rst_n,
    output wire clk_pix,
    output wire clk_5x,
    output wire clk_aux,
    output wire locked
);
`ifdef SIM_PLL_BEHAV
    // ---- 仿真模型：只做分频/自由跑，不模拟真实抖动 ----
    reg [2:0] div5;
    reg       c5;
    always @(posedge clk_in) begin
        if (div5 == 3'd2) begin
            div5 <= 3'd0;
            c5   <= ~c5;
        end else begin
            div5 <= div5 + 3'd1;
        end
    end

    reg [8:0] lcnt;
    reg       locked_r;
    always @(posedge clk_in) begin
        if (lcnt != 9'h1FF) begin
            lcnt     <= lcnt + 9'd1;
            locked_r <= 1'b0;
        end else begin
            locked_r <= 1'b1;
        end
    end

    assign clk_pix = clk_in;
    assign clk_5x  = c5;
    assign clk_aux = clk_in;
    assign locked  = locked_r;

    initial begin
        c5    = 1'b0;
        div5  = 3'd0;
        lcnt  = 9'd0;
    end
`else
    wire [4:0] clkc;

    EG_PHY_PLL #(
        .DYNCFG            ("DISABLE"),
        .IF_ESCLKSTSW      ("DISABLE"),
        .REFCLK_SEL        ("INTERNAL"),
        .FIN               ("24.000"),
        .REFCLK_DIV        (1),
        .FBCLK_DIV         (21),
        .CLKC0_DIV         (20),      // 25.2MHz
        .CLKC1_DIV         (4),       // 126MHz
        .CLKC2_DIV         (6),       // 84MHz
        .CLKC3_DIV         (40),      // 12.6MHz（预留音频）
        .CLKC4_DIV         (1),
        .CLKC0_ENABLE      ("ENABLE"),
        .CLKC1_ENABLE      ("ENABLE"),
        .CLKC2_ENABLE      ("ENABLE"),
        .CLKC3_ENABLE      ("DISABLE"),
        .CLKC4_ENABLE      ("DISABLE"),
        .CLKC0_DIV2_ENABLE ("DISABLE"),
        .CLKC1_DIV2_ENABLE ("DISABLE"),
        .CLKC2_DIV2_ENABLE ("DISABLE"),
        .CLKC3_DIV2_ENABLE ("DISABLE"),
        .CLKC4_DIV2_ENABLE ("DISABLE"),
        .FEEDBK_MODE       ("NORMAL"),
        .FEEDBK_PATH       ("VCO_PHASE_0"),
        .STDBY_ENABLE      ("DISABLE"),
        .CLKC0_CPHASE      (10),
        .CLKC1_CPHASE      (2),
        .CLKC2_CPHASE      (3),
        .CLKC3_CPHASE      (20),
        .GMC_GAIN          (2),
        .GMC_TEST          (14),
        .ICP_CURRENT       (9),
        .KVCO              (2),
        .LPF_CAPACITOR     (1),
        .LPF_RESISTOR      (8),
        .PLLRST_ENA        ("ENABLE"),
        .PLLMRST_ENA       ("DISABLE"),
        .PLLC2RST_ENA      ("DISABLE"),
        .PLLC34RST_ENA     ("DISABLE"),
        .PREDIV_MUXC0      ("VCO"),
        .PREDIV_MUXC1      ("VCO"),
        .PREDIV_MUXC2      ("VCO"),
        .PREDIV_MUXC3      ("VCO"),
        .PREDIV_MUXC4      ("VCO"),
        .ODIV_MUXC0        ("DIV"),
        .ODIV_MUXC1        ("DIV"),
        .ODIV_MUXC2        ("DIV"),
        .ODIV_MUXC3        ("DIV"),
        .ODIV_MUXC4        ("DIV"),
        .FREQ_LOCK_ACCURACY(2),
        .PLL_LOCK_MODE     (0),
        .INTFB_WAKE        ("DISABLE"),
        .DPHASE_SOURCE     ("DISABLE"),
        .VCO_NORESET       ("DISABLE"),
        .STDBY_VCO_ENA     ("DISABLE"),
        .NORESET           ("DISABLE"),
        .SYNC_ENABLE       ("DISABLE")
    ) u_pll (
        .clkc     (clkc),
        .extlock  (locked),
        .stdby    (1'b0),
        .refclk   (clk_in),
        .fbclk    (1'b0),
        .reset    (~rst_n),
        .load_reg (1'b0),
        .psdone   (),
        .psclk    (1'b0),
        .psdown   (1'b0),
        .psstep   (1'b0),
        .psclksel (3'b000),
        .do       (),
        .dclk     (1'b0),
        .dcs      (1'b0),
        .dwe      (1'b0),
        .di       (8'h00),
        .daddr    (6'h00)
    );

    // 全局时钟缓冲
    EG_PHY_GCLK u_gclk_pix  (.clki(clkc[0]), .clko(clk_pix));
    EG_PHY_GCLK u_gclk_5x   (.clki(clkc[1]), .clko(clk_5x));
    EG_PHY_GCLK u_gclk_aux  (.clki(clkc[2]), .clko(clk_aux));
`endif
endmodule
