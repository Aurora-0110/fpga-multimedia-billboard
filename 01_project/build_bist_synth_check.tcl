# v044 synthesis-only diagnostic (or chained physical check).
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
if {[file exists sdram_bist.al]} {error "Existing output project: choose a fresh ADB_OUT; no overwrite."}
create_project sdram_bist $OUT -family eg4 -device EG4S20NG88 -speed 1

add_include_dir $ROOT/rtl
foreach f {ip/pll_sdram.v mem/sdram_ctrl.v mem/sdram_bist_seq.v common/reset_release.v common/bist_reset_ctrl.v common/key_debounce.v common/bist_status_595.v common/bist_led_encode.v common/bist_loop_ctrl.v common/bist_loop_led.v} {
    add_files $ROOT/rtl/$f
}
add_files $ROOT/boards/sdram_bist_top.v
add_files $ROOT/boards/sdram_bist.adc
add_files $ROOT/boards/sdram_bist.sdc
top_module sdram_bist_top

# v044 controlled comparison: retain logic FFs outside PADs so the router can
# repair actual min-delay paths. No timing exceptions, no protocol changes.
set_param -run syn_1 gate pack_seq_in_io off
# Confirm effective packing in syn_1/settings.cfg and synthesis log.
puts "@@@ LAUNCH SYN"
launch_runs syn_1
wait_run syn_1 900
# The run manager does not import the synthesized netlist here.
# See syn_1/sdram_bist_gate.area and run.log for real area/status.

set GATE $OUT/sdram_bist_Runs/syn_1
if {![file exists $GATE/sdram_bist_gate.db]} {error "SYNTHESIS_INCOMPLETE: gate database absent"}
puts "@@@ V044 SYNTHESIS CHECK END; NOT TIMING/HARDWARE ACCEPTANCE"
if {[info exists ::ADB_CHAIN_PHY] && $::ADB_CHAIN_PHY} {
    set ::env(ADB_GATE_DIR) $GATE
    if {![info exists ::env(ADB_PHY_OUT)]} {set ::env(ADB_PHY_OUT) $OUT/physical_check}
    source $ROOT/build_bist_physical_check.tcl
}
exit
