// v062 controlled trial: NOCOMP + VCO_PHASE_0 feedback for both PLLs. Output dividers/phases unchanged; FBCLK_DIV scaled for VCO feedback.
// EG4S20NG88,24MHz. Two PLLs avoid out-of-spec 0.75MHz PFD of direct /32 *99.
// PLL_A: PFD=24MHz,VCO=24*33=792MHz; FB=/33, C0=/33=24MHz (unused), C1=/8=99MHz.
// PLL_B: PFD=99/4=24.75MHz; VCO=24.75*30=742.5MHz; internal FB=/30.
//        C0=/10=74.25MHz pixel,C1=/2=371.25MHz serial (5x).
// EG4 manual: PFD10..400,VCO300..1200,output<=400MHz. Actual lock/jitter
// and screen operation still REQUIRE physical verification. Unused SD/SDRAM=0.
`timescale 1ns/1fs
module pll_video720 #(parameter integer CLK_IN_HZ=24_000_000)(
 input wire clk_in,rst_n,output wire clk_pix,clk_5x,clk_sd,clk_sdram,locked);
 assign clk_sd=1'b0;assign clk_sdram=1'b0;
`ifdef SIM_PLL_BEHAV
 reg cp=0,cs=0;reg[7:0]lock_count=0;integer half_count=0;
 always #1.346801347 begin
  cs=~cs;
  if(half_count==4)begin half_count=0;cp=~cp;end
  else half_count=half_count+1;
 end
 always @(posedge clk_in or negedge rst_n)
  if(!rst_n)lock_count<=0;else if(!(&lock_count))lock_count<=lock_count+1'b1;
 assign clk_pix=cp;assign clk_5x=cs;assign locked=(&lock_count)&rst_n;
`else
 wire[4:0]ca,cb;wire ref99,lock_a,lock_b;
 EG_LOGIC_BUFG ga1(.i(ca[1]),.o(ref99));
 EG_LOGIC_BUFG gb0(.i(cb[0]),.o(clk_pix));
 EG_LOGIC_BUFG gb1(.i(cb[1]),.o(clk_5x));
 assign locked=lock_a & lock_b;
 EG_PHY_PLL #(.FIN("24.000"),.FEEDBK_MODE("NOCOMP"),.FEEDBK_PATH("VCO_PHASE_0"),
 .REFCLK_DIV(1),.FBCLK_DIV(33),
 .CLKC0_ENABLE("ENABLE"),.CLKC0_DIV(33),.CLKC0_CPHASE(32),.CLKC0_FPHASE(0),
 .CLKC1_ENABLE("ENABLE"),.CLKC1_DIV(8),.CLKC1_CPHASE(7),.CLKC1_FPHASE(0),
 .STDBY_ENABLE("DISABLE"),.PLLRST_ENA("ENABLE"),.SYNC_ENABLE("DISABLE"),
 .DPHASE_SOURCE("DISABLE"),.DYNCFG("DISABLE"),.DERIVE_PLL_CLOCKS("ENABLE"),.GEN_BASIC_CLOCK("DISABLE"),
 .GMC_GAIN(2),.ICP_CURRENT(9),.KVCO(2),.LPF_CAPACITOR(1),.LPF_RESISTOR(8)) pll_pre(
 .refclk(clk_in),.reset(~rst_n),.stdby(1'b0),.extlock(lock_a),.clkc(ca),.fbclk(),
 .load_reg(1'b0),.psclk(1'b0),.psdown(1'b0),.psstep(1'b0),.psclksel(3'b0),.psdone(),
 .dclk(1'b0),.dcs(1'b0),.dwe(1'b0),.di(8'd0),.daddr(6'd0),.do());
 EG_PHY_PLL #(.FIN("99.000"),.FEEDBK_MODE("NOCOMP"),.FEEDBK_PATH("VCO_PHASE_0"),
 .REFCLK_DIV(4),.FBCLK_DIV(30),
 .CLKC0_ENABLE("ENABLE"),.CLKC0_DIV(10),.CLKC0_CPHASE(9),.CLKC0_FPHASE(0),
 .CLKC1_ENABLE("ENABLE"),.CLKC1_DIV(2),.CLKC1_CPHASE(1),.CLKC1_FPHASE(0),
 .STDBY_ENABLE("DISABLE"),.PLLRST_ENA("ENABLE"),.SYNC_ENABLE("DISABLE"),
 .DPHASE_SOURCE("DISABLE"),.DYNCFG("DISABLE"),.DERIVE_PLL_CLOCKS("ENABLE"),.GEN_BASIC_CLOCK("DISABLE"),
 .GMC_GAIN(2),.ICP_CURRENT(9),.KVCO(2),.LPF_CAPACITOR(1),.LPF_RESISTOR(8)) pll_video(
 .refclk(ref99),.reset(~rst_n|~lock_a),.stdby(1'b0),.extlock(lock_b),.clkc(cb),.fbclk(),
 .load_reg(1'b0),.psclk(1'b0),.psdown(1'b0),.psstep(1'b0),.psclksel(3'b0),.psdone(),
 .dclk(1'b0),.dcs(1'b0),.dwe(1'b0),.di(8'd0),.daddr(6'd0),.do());
`endif
endmodule
