# v042 unified DIAGNOSTIC entry: synthesis -> direct place/route -> reports.
# No bitgen/download. Do NOT interpret positive STA as board acceptance.
# Shares the mandatory pack_seq_in_io=off setting with synth-only entry.
if {[info exists ::env(ADB_ROOT)]} {
    set ROOT [file normalize $::env(ADB_ROOT)]
} elseif {[info script] ne ""} {
    set ROOT [file dirname [file normalize [info script]]]
} else {set ROOT [pwd]}
set ::ADB_CHAIN_PHY 1
source $ROOT/build_sdram_synth_check.tcl
