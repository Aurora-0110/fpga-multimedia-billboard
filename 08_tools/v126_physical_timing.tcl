# V126 bounded attempt2: ALL-device options verified in TD_User_Guide_V6.2 printed pp281-283.
# v126: diagnostic physical implementation; guarded opt-in bitgen, no download.
# Run after build_sdram_synth_check.tcl completes. Source this file in TD.
# ADB_GATE_DIR = directory holding idx_video.prj and idx_video_gate.db.
# ADB_PHY_OUT = a NEW output directory. Defaults refer to this project.
if {[info exists ::env(ADB_ROOT)]} {
    set ROOT $::env(ADB_ROOT)
} elseif {[info script] ne ""} {
    set ROOT [file dirname [info script]]
} else {
    set ROOT [pwd]
}
if {[file pathtype $ROOT] ne "absolute"} {set ROOT [file join [pwd] $ROOT]}
set GATE $ROOT/build_audio_visual/idx_video_Runs/syn_1
if {[info exists ::env(ADB_GATE_DIR)]} {set GATE $::env(ADB_GATE_DIR)}
set OUT $ROOT/build_audio_visual/physical_check
if {[info exists ::env(ADB_PHY_OUT)]} {set OUT $::env(ADB_PHY_OUT)}
foreach name {idx_video.prj idx_video_gate.db} {
    if {![file exists $GATE/$name]} {error "Missing synthesized artifact: $GATE/$name"}
}
if {[file exists $OUT]} {error "Use a NEW ADB_PHY_OUT; no overwrite."}
file mkdir $OUT
# TD resolves relative include paths against cwd, NOT the supplied prj path.
cd $GATE
import_device eagle_s20.db -package EG4S20NG88
open_project idx_video.prj -noanalyze
import_db idx_video_gate.db
cd $OUT
# TD_User_Guide_V6.2 PDF pp281-283: placement effort=high and routing
# effort=routability are documented for ALL devices. No pin/frequency/exception changes.
# v126 attempt1 failed local routing in FAT32 probe, so choose congestion-aware flow.
set_param place effort high
set_param route effort routability
puts "@@@ V126 PLACE_EFFORT=high ROUTE_EFFORT=routability"
# Hard macro placement is left to the device mapper; inspect the emitted PNL.
# V126 comparison: documented ALL-device options, TD_User_Guide_V6.2 pp282-283.
# No source/pin/clock/exception changes, no increase in requested frequency.
set_param place post_place_opt ultra
set_param place hfn_opt_effort high
set_param route timing greedy
puts "@@@ V126 PHYSICAL_COMPARE POST_PLACE=ultra HFN=high TIMING=greedy"
place
# Use TD's physical hold-fix flow, not a timing exception or RTL identity buffer.
# The ordinary route is completed first; fix_hold may insert legal delay resources.
set_param route fix_hold off
route
fix_hold
set_param route fix_hold on
update_timing -mode final
report_area -io_info -file sdram_phy.area
# TD 6.2 report_clock_summary mutates timing-analysis state. Preserve evidence,
# then recompute BEFORE authoritative STA/check reports (v029 reproducer).
check_timing -file before_clock_summary.check -verbose
report_clock_summary -file sdram_clocks.rpt
check_timing -file after_clock_summary.check -verbose
update_timing -mode final
report_timing_summary -file sdram_pr.timing
report_timing_status -file sdram_phy.ts
report_timing_exception -file sdram_exception.timing
report_abnormal_timing_target -file abnormal_timing_targets.rpt
check_timing -file sdram_check.rpt -verbose
write_pnl sdram_netlist.pnl -v
export_ip_sdc -file macro_ip_export.sdc
export_db sdram_pr.db
set ch [open sdram_phy.ts r]
set ts [read $ch]
close $ch
puts "@@@ TD PHYSICAL HOLD-FIX APPLIED; REPORTS GENERATED - NOT HARDWARE ACCEPTANCE"
puts $ts
if {[regexp {(S|H)WNS:\s*-} $ts]} {error "TIMING_NOT_MET: negative setup/hold slack; do not release a programming bitstream."}
puts "@@@ Nonnegative WNS alone is NOT signoff: review coverage, exceptions, SiP and CDC."
# v045 opt-in: diagnostic SRAM configuration only, not formal signoff.
if {[info exists ::ADB_DIAGNOSTIC_BIT] && $::ADB_DIAGNOSTIC_BIT} {
    commit_param -step bitgen
    bitgen -bit v126_audio_pingpong_720p.bit
    if {![file exists v126_audio_pingpong_720p.bit] || [file size v126_audio_pingpong_720p.bit] == 0} {
        error "BITGEN_INCOMPLETE"
    }
    export_bitgen_param -file diagnostic_bitgen_param.f
    puts "@@@ V126_DIAGNOSTIC_BIT_GENERATED; NOT HARDWARE ACCEPTANCE"
}
exit
