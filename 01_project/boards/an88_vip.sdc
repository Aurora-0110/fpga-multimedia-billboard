#---------------------------------------------------------------------------------
# an88_vip.sdc —— 时序约束（bringup）
#   只约束真实存在的时钟；PLL 出来的 25.2/126MHz 由 TD 从 PLL 参数自动派生。
#---------------------------------------------------------------------------------

create_clock -name clk24m -period 41.667 [get_ports clk24m]

# 按键是人手按的，与时钟无关
set_false_path -from [get_ports key_n*]

# 595 输出是慢速 GPIO，不需要按像素时钟收敛
set_false_path -to [get_ports led_*]
