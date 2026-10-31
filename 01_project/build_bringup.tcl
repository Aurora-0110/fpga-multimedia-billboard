#---------------------------------------------------------------------------------
# build_bringup.tcl —— 纯彩条工程（不接 SD 卡、不接 SDRAM），用于验 HDMI 通路
#
#   用法（在 02_工程 目录下，路径不要有中文）：
#     C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin\run.exe < build_bringup.tcl
#   或：build.bat bringup
#
#   产物：<当前目录>\build\bringup_Runs\phy_1\bringup.bit
#---------------------------------------------------------------------------------
set ROOT [pwd]
if {[info exists ::env(ADB_OUT)]} {
    set OUT $::env(ADB_OUT)
} else {
    set OUT $ROOT/build
}
puts "@@@ ROOT = $ROOT"
puts "@@@ OUT  = $OUT"

create_project bringup $OUT -family eg4 -device EG4S20NG88 -speed 1

add_include_dir $ROOT/rtl

add_files $ROOT/rtl/video/video_timing.v
add_files $ROOT/rtl/video/tmds_encoder.v
add_files $ROOT/rtl/video/tmds_serializer.v
add_files $ROOT/rtl/video/tpg_bars.v
add_files $ROOT/rtl/ip/pll_wrap.v
add_files $ROOT/rtl/ip/hdmi_tx_wrap.v
add_files $ROOT/rtl/common/led_595.v
add_files $ROOT/rtl/common/key_debounce.v
add_files $ROOT/boards/bringup_top.v
add_files $ROOT/boards/bringup.adc
add_files $ROOT/boards/an88_vip.sdc

top_module bringup_top

puts "@@@ LAUNCH SYN"
launch_runs syn_1
wait_run syn_1 900
catch {report_area} ra
puts "AREA => $ra"

puts "@@@ LAUNCH PHY"
launch_runs phy_1
wait_run phy_1 1800
puts "@@@ DONE"

exit
