`timescale 1ns / 1ps
//--------------------------------------------------------------------------------
// pll_sdram.v —— SDRAM BIST 用 PLL
//   FIN = 24MHz（P13）
//   VCO = 24 / 1 × 33 = 792MHz
//   clk_sd = 792 / 16 = 49.5MHz   （SDR SDRAM 控制器时钟，周期 20.202ns）
//   clk_24 = 792 / 33 = 24MHz     （保留：以后接视频/串口）
//--------------------------------------------------------------------------------
module pll_sdram #(
    parameter integer FIN_MHZ = 24
) (
    input  wire clk_in,
    input  wire rst_n,
    output wire clk_sd,
    output wire clk_24,
    output wire locked
);
    wire [4:0] clkc;

    // v044: NOCOMP uses INTERNAL feedback (TD manual PLL section).
    // fbclk is unused in this mode and deliberately unconnected, not tied low.
    // No assumption of input/output phase compensation is made.
    EG_PHY_PLL #(
        .DYNCFG            ("DISABLE"),
        .IF_ESCLKSTSW      ("DISABLE"),
        .REFCLK_SEL        ("INTERNAL"),
        .FIN               ("24.000"),
        .REFCLK_DIV        (1),
        .FBCLK_DIV         (33),      // VCO = 792MHz
        .CLKC0_DIV         (16),      // 49.5MHz
        .CLKC1_DIV         (33),      // 24MHz
        .CLKC2_DIV         (11),      // 72MHz（预留）
        .CLKC3_DIV         (44),      // 18MHz（预留）
        .CLKC4_DIV         (1),
        .CLKC0_ENABLE      ("ENABLE"),
        .CLKC1_ENABLE      ("ENABLE"),
        .CLKC2_ENABLE      ("DISABLE"),
        .CLKC3_ENABLE      ("DISABLE"),
        .CLKC4_ENABLE      ("DISABLE"),
        .CLKC0_DIV2_ENABLE ("DISABLE"),
        .CLKC1_DIV2_ENABLE ("DISABLE"),
        .CLKC2_DIV2_ENABLE ("DISABLE"),
        .CLKC3_DIV2_ENABLE ("DISABLE"),
        .CLKC4_DIV2_ENABLE ("DISABLE"),
        .FEEDBK_MODE       ("NOCOMP"),
        .FEEDBK_PATH       ("VCO_PHASE_0"),
        .STDBY_ENABLE      ("DISABLE"),
        .CLKC0_CPHASE      (8),
        .CLKC1_CPHASE      (16),
        .CLKC2_CPHASE      (5),
        .CLKC3_CPHASE      (22),
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
        .fbclk    (),
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

    EG_PHY_GCLK u_gclk_sd  (.clki(clkc[0]), .clko(clk_sd));
    EG_PHY_GCLK u_gclk_24  (.clki(clkc[1]), .clko(clk_24));
endmodule
