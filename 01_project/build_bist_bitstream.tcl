# Explicit diagnostic bit generation; existing diagnostics still default to no bit.
set ::ADB_DIAGNOSTIC_BIT 1
source [file join [file dirname [file normalize [info script]]] build_bist_check.tcl]
