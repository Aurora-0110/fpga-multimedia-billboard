# 24MHz -> independent SDRAM and cascaded 74.25/371.25 video clocks.
create_clock -name clk24m -period 41.667 [get_ports {clk24m}]
derive_clocks
set_clock_groups -asynchronous -group [get_clocks {u_pll_sd/u_pll.clkc[0]}] -group [get_clocks {u_pll_vid/pll_video.clkc[0] u_pll_vid/pll_video.clkc[1]}]
set_false_path -from [get_ports {key0_n key1_n}]
# No blanket exceptions on native SDRAM, nor pixel/5x serializer paths.

# Individually synchronized LED diagnostics only. Metastability is confined
# to status_meta; stage2 and every functional data/reset path remain timed.
set_false_path -to [get_regs {status_meta*}]

# Diagnostic conservative 8ns external IO budgets relative to host clock.
# SPI SCK is a registered clock-enable output, not an internal fabric clock.
# v064 init ~200kHz, data ~990kHz; digital edge spacing is separately tested.
# The same 8ns budgets are diagnostic assumptions only, NOT measured SD-card tOD.
# These assumptions
# are NOT board-level IO/PVT signoff. No SPI paths are blanket false-pathed.
set_input_delay -clock [get_clocks {u_pll_sd/u_pll.clkc[0]}] -max 8.0 [get_ports {tf_miso}]
set_input_delay -clock [get_clocks {u_pll_sd/u_pll.clkc[0]}] -min 0.0 [get_ports {tf_miso}]
set_output_delay -clock [get_clocks {u_pll_sd/u_pll.clkc[0]}] -max 8.0 [get_ports {tf_cs_n tf_sck tf_mosi}]
set_output_delay -clock [get_clocks {u_pll_sd/u_pll.clkc[0]}] -min 0.0 [get_ports {tf_cs_n tf_sck tf_mosi}]
