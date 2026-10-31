create_clock -name clk24m -period 41.667 [get_ports {clk24m}]
derive_clocks
# Asynchronous mechanical key: only its entry to the 2-FF synchronizer is excepted.
# External 595 source-synchronous board timing not signed off by this constraint.
set_false_path -from [get_ports {key0_n}]
