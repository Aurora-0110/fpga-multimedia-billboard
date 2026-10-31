# v055: diagnostic physical implementation; guarded opt-in bitgen, no download.
# Run after build_sdram_synth_check.tcl completes. Source this file in TD.
# ADB_GATE_DIR = directory holding idx_video.prj and idx_video_gate.db.
# ADB_PHY_OUT = a NEW output directory. Defaults refer to this project.
if {[info exists ::env(ADB_ROOT)]} {
    set ROOT [file normalize $::env(ADB_ROOT)]
} elseif {[info script] ne ""} {
    set ROOT [file dirname [file normalize [info script]]]
} else {
    set ROOT [pwd]
}
set GATE $ROOT/build/idx_video_Runs/syn_1
if {[info exists ::env(ADB_GATE_DIR)]} {set GATE [file normalize $::env(ADB_GATE_DIR)]}
set OUT $ROOT/build/physical_check
if {[info exists ::env(ADB_PHY_OUT)]} {set OUT [file normalize $::env(ADB_PHY_OUT)]}
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
# Hard macro placement is left to the device mapper; inspect the emitted PNL.
place
route
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
puts "@@@ PHYSICAL CHECK REPORTS GENERATED - NOT HARDWARE ACCEPTANCE"
puts $ts
if {[regexp {(S|H)WNS:\s*-} $ts]} {error "TIMING_NOT_MET: negative setup/hold slack; do not release a programming bitstream."}
puts "@@@ Nonnegative WNS alone is NOT signoff: review coverage, exceptions, SiP and CDC."
# v045 opt-in: diagnostic SRAM configuration only, not formal signoff.
if {[info exists ::ADB_DIAGNOSTIC_BIT] && $::ADB_DIAGNOSTIC_BIT} {
    commit_param -step bitgen
    bitgen -bit v081_picture_controls_720p.bit
    if {![file exists v081_picture_controls_720p.bit] || [file size v081_picture_controls_720p.bit] == 0} {
        error "BITGEN_INCOMPLETE"
    }
    export_bitgen_param -file diagnostic_bitgen_param.f
    puts "@@@ V056_DIAGNOSTIC_BIT_GENERATED; NOT HARDWARE ACCEPTANCE"
}
exit
