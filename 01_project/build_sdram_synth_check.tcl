# v042 synthesis-only diagnostic (or chained physical check).
# No bitgen/download. Fresh ADB_OUT required; inspect reports, not exit code alone.
if {[info exists ::env(ADB_ROOT)]} {
    set ROOT [file normalize $::env(ADB_ROOT)]
} elseif {[info script] ne ""} {
    set ROOT [file dirname [file normalize [info script]]]
} else {
    set ROOT [pwd]
}
if {[info exists ::env(ADB_OUT)]} {
    set OUT $::env(ADB_OUT)
} else {
    set OUT $ROOT/build
}
puts "@@@ ROOT = $ROOT"
puts "@@@ OUT  = $OUT"

file mkdir $OUT
cd $OUT
if {[file exists sdram_video.al]} {error "Existing output project: choose a fresh ADB_OUT; no overwrite."}
create_project sdram_video $OUT -family eg4 -device EG4S20NG88 -speed 1

add_include_dir $ROOT/rtl

# --- 时钟 ---
add_files $ROOT/rtl/ip/pll_sdram.v
add_files $ROOT/rtl/ip/pll_wrap.v
# --- SDRAM ---
add_files $ROOT/rtl/mem/sdram_ctrl.v
add_files $ROOT/rtl/mem/async_fifo.v
# --- 帧缓存读写 ---
add_files $ROOT/rtl/video/fb_writer.v
add_files $ROOT/rtl/video/fb_reader.v
add_files $ROOT/rtl/video/fb_session_ctrl.v
add_files $ROOT/rtl/video/fb_display_guard.v
add_files $ROOT/rtl/common/reset_release.v
# --- 视频 ---
add_files $ROOT/rtl/video/video_timing.v
add_files $ROOT/rtl/video/tmds_encoder.v
add_files $ROOT/rtl/video/tmds_serializer.v
add_files $ROOT/rtl/ip/hdmi_tx_wrap.v
# --- 板级 ---
add_files $ROOT/rtl/common/key_debounce.v
add_files $ROOT/rtl/common/led_595.v
add_files $ROOT/boards/sdram_video_top.v
add_files $ROOT/boards/sdram_video.adc
add_files $ROOT/boards/sdram_video.sdc

top_module sdram_video_top

# v042 controlled comparison: retain logic FFs outside PADs so the router can
# repair actual min-delay paths. No timing exceptions, no protocol changes.
set_param -run syn_1 gate pack_seq_in_io off
# Confirm effective packing in syn_1/settings.cfg and synthesis log.
puts "@@@ LAUNCH SYN"
launch_runs syn_1
wait_run syn_1 900
# The run manager does not import the synthesized netlist here.
# See syn_1/sdram_video_gate.area and run.log for real area/status.

set GATE $OUT/sdram_video_Runs/syn_1
if {![file exists $GATE/sdram_video_gate.db]} {error "SYNTHESIS_INCOMPLETE: gate database absent"}
puts "@@@ V042 SYNTHESIS CHECK END; NOT TIMING/HARDWARE ACCEPTANCE"
if {[info exists ::ADB_CHAIN_PHY] && $::ADB_CHAIN_PHY} {
    set ::env(ADB_GATE_DIR) $GATE
    if {![info exists ::env(ADB_PHY_OUT)]} {set ::env(ADB_PHY_OUT) $OUT/physical_check}
    source $ROOT/build_sdram_physical_check.tcl
}
exit
