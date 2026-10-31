#---------------------------------------------------------------------------------
# sdram_video.sdc —— 时序约束
#
#   唯一输入时钟：24MHz 晶振（P13）。
#   时钟域（TD derive_clocks 实际派生出来的名字）：
#     clk24m                      41.667ns   （按键/595 控制）
#     u_pll_sd/u_pll.clkc[0]      20.202ns   （49.5MHz，SDRAM 侧）
#     u_pll_vid/u_pll.clkc[0]      39.683ns  （25.2MHz，像素）
#     u_pll_vid/u_pll.clkc[1]      7.937ns   （126MHz，TMDS 5x）
#
#   两个 PLL 同参考但 VCO 不同（792MHz / 504MHz），工具无法可靠地对互相之间的路径
#   做时序分析；跨域数据只经异步 FIFO 的格雷码指针，所以按异步时钟组切开。
#   像素时钟与 5x 时钟来自同一个 PLL，必须留在同一组里，否则串行化路径会被切掉。
#---------------------------------------------------------------------------------
create_clock -name clk24m -period 41.667 -waveform {0.000 20.833} [get_ports {clk24m}]

derive_clocks

set_clock_groups -asynchronous \
    -group [get_clocks {clk24m}] \
    -group [get_clocks {u_pll_sd/u_pll.clkc[0]}] \
    -group [get_clocks {u_pll_vid/u_pll.clkc[0] u_pll_vid/u_pll.clkc[1]}]

set_false_path -from [get_ports {key_n[*]}]

# v041: removed inherited blanket SiP false-path exception. The old claim
# that these paths need not be analyzed is unverified. Actual SiP setup/hold,
# clock-object matching, CDC constraints and resource fit require TD signoff.
# Do NOT restore a broad false_path merely to hide negative slack.
