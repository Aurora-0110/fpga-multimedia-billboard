`ifndef ADBOARD_PKG_VH
`define ADBOARD_PKG_VH

// 640x480@60（VESA DMT，像素时钟 25.2MHz）
//   24MHz 晶振 -> PLL VCO 504MHz -> /20 = 25.2MHz 像素，/4 = 126MHz TMDS 5x
//   行：640 + 16(fp) + 96(sync) + 48(bp) = 800
//   场：480 + 10(fp) +  2(sync) + 33(bp) = 525
//   800 x 525 x 60Hz = 25.2MHz

`define H_ACTIVE 640
`define H_FP     16
`define H_SYNC   96
`define H_BP     48
`define V_ACTIVE 480
`define V_FP     10
`define V_SYNC   2
`define V_BP     33

`define H_TOTAL  (`H_ACTIVE + `H_FP + `H_SYNC + `H_BP)
`define V_TOTAL  (`V_ACTIVE + `V_FP + `V_SYNC + `V_BP)

`endif
