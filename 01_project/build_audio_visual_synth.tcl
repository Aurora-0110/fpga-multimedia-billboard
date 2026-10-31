# v119 resource-optimized audio visual candidate synthesis (or chained physical check).
# No bitgen/download. Fresh ADB_OUT required; inspect reports, not exit code alone.
if {[info exists ::env(ADB_ROOT)]} {
    set ROOT $::env(ADB_ROOT)
} elseif {[info script] ne ""} {
    set ROOT [file dirname [info script]]
} else {
    set ROOT [pwd]
}
# TD 6.2.168116 under this sandbox account drops Documents from file normalize.
# Keep existing absolute paths verbatim; do not canonicalize through TD's VFS.
if {[file pathtype $ROOT] ne "absolute"} {set ROOT [file join [pwd] $ROOT]}
if {![file isdirectory $ROOT/rtl]} {error "Invalid project source root: $ROOT"}
if {[info exists ::env(ADB_OUT)]} {
    set OUT $::env(ADB_OUT)
} else {
    set OUT $ROOT/build_audio_visual
}
puts "@@@ ROOT = $ROOT"
puts "@@@ OUT  = $OUT"

file mkdir $OUT
cd $OUT
if {[file exists idx_video.al]} {error "Existing output project: choose a fresh ADB_OUT; no overwrite."}
create_project idx_video $OUT -family eg4 -device EG4S20NG88 -speed 1

add_include_dir $ROOT/rtl
foreach f {audio/i2s_test_tone.v audio/hdmi_audio_packets.v ip/pll_sdram.v ip/pll_video720.v ip/hdmi_tx_wrap.v ip/hdmi_visual_wrap.v visual/audio_pcm_frontend.v visual/pcm_activity_gate.v visual/pcm_spectrum_dft.v visual/spectrum_power_level.v visual/spectrum_overlay.v visual/official_logo_compact_sync.v visual/osd_layers_visual.v visual/ui_help_overlay.v mem/sdram_ctrl.v mem/async_fifo.v tf/media_bmp_probe.v tf/tf_bus_bmp_source.v tf/tf_bus_bmp_scaled_source.v tf/tf_bus_scaled_loader.v tf/media_sd_arbiter.v tf/fat32_byte_stream.v tf/fat32_audio_prefetch.v audio/wav_pcm_decode.v audio/tf_wav_reader.v audio/audio_choice_cdc.v audio/tf_wav_playback.v tf/spi_byte.v tf/sd_spi_reader.v tf/fat32_bmp_probe.v tf/bmp_pixel_stream.v tf/bmp_pixel_packer.v tf/tf_bmp_source.v tf/tf_bmp_loader.v tf/tf_bmp_scaled_source.v tf/tf_scaled_loader.v scale/bmp_scale_bridge.v scale/bilinear_stream_scaler.v scale/bilinear_rgb888.v tf/tf_playlist_ctrl.v tf/tf_double_playlist.v video/idx_writer.v video/idx_reader.v video/idx_slide_reader.v video/idx_dual_pipeline.v video/idx_pair_reader.v video/idx_pair_display.v video/display_diagnostics.v video/display_diagnostics_osd.v video/idx_pair_pipeline.v video/official_logo.v video/osd_layers.v video/osd_layers_full720.v video/picture_adjust.v common/picture_controls.v common/picture_controls_osd.v common/media_controls.v visual/media_ui_overlay.v visual/pcm_caption_player.v visual/subtitle_overlay.v video/idx_display.v video/idx_pipeline.v video/fb_session_ctrl.v video/video_timing.v video/tmds_encoder.v video/tmds_serializer.v common/reset_release.v common/key_debounce.v common/bist_status_595.v} {
    add_files $ROOT/rtl/$f
}
add_files $ROOT/boards/idx_audio_visual_top.v
add_files $ROOT/boards/idx_video.adc
add_files $ROOT/boards/idx_video.sdc
top_module idx_audio_visual_top

# v044 controlled comparison: retain logic FFs outside PADs so the router can
# repair actual min-delay paths. No timing exceptions, no protocol changes.
set_param -run syn_1 gate pack_seq_in_io off
# TD_User_Guide_V6.2 pp278-280: ALL-device options; no frequency/IO waiver.
# High packing can reduce required slices; control sets of >=2 retain native
# enable/reset rather than spending LUTs. Review subsequent route congestion.
set_param -run syn_1 rtl min_control_set 2
set_param -run syn_1 gate pack_effort high
# Confirm effective packing in syn_1/settings.cfg and synthesis log.
puts "@@@ LAUNCH SYN"
launch_runs syn_1
wait_run syn_1 900
# The run manager does not import the synthesized netlist here.
# See syn_1/idx_video_gate.area and run.log for real area/status.

set GATE $OUT/idx_video_Runs/syn_1
if {![file exists $GATE/idx_video_gate.db]} {error "SYNTHESIS_INCOMPLETE: gate database absent"}
puts "@@@ V119 RESOURCE-OPTIMIZED AUDIO VISUAL SYNTHESIS END; NOT TIMING/HARDWARE ACCEPTANCE"
if {[info exists ::ADB_CHAIN_PHY] && $::ADB_CHAIN_PHY} {
    set ::env(ADB_GATE_DIR) $GATE
    if {![info exists ::env(ADB_PHY_OUT)]} {set ::env(ADB_PHY_OUT) $OUT/physical_check}
    source $ROOT/build_audio_visual_physical_check.tcl
}
exit
