"""Create the separate scaled candidate; leave the accepted top/build intact."""
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'01_project'
target=root/'boards/idx_scaled_video_top.v'
assert not target.exists(), 'Never overwrite an existing candidate'
text=(root/'boards/idx_video_top.v').read_text(encoding='utf-8')
changes={
 'module idx_video_top #(':'module idx_scaled_video_top #(',
 '// v081 picture controls + double buffers':'// v087 variable BMP + bilinear full720p + paired transport; picture controls + double buffers',
 'wire window=de&&x>=320&&x<960&&y>=120&&y<600;':'wire window=de; // Entire effective 1280x720 picture, not a centered 640x480 window.',
 'tf_bmp_loader #(':'tf_scaled_loader #(',
 'idx_dual_pipeline pipe(':'idx_pair_pipeline pipe(',
}
for old,new in changes.items():
 assert text.count(old)==1,old
 text=text.replace(old,new)
target.write_text(text,encoding='utf-8')
synth=(root/'build_idx_synth.tcl').read_text(encoding='utf-8')
for old,new in {
 '# v044 synthesis-only diagnostic (or chained physical check).':'# v087 separate scaled candidate synthesis (or chained physical check).',
 'set OUT $ROOT/build':'set OUT $ROOT/build_scaled',
 'tf/tf_bmp_loader.v':'tf/tf_bmp_loader.v tf/tf_bmp_scaled_source.v tf/tf_scaled_loader.v scale/bmp_scale_bridge.v scale/bilinear_stream_scaler.v scale/bilinear_rgb888.v',
 'video/idx_dual_pipeline.v':'video/idx_dual_pipeline.v video/idx_pair_reader.v video/idx_pair_display.v video/idx_pair_pipeline.v',
 'add_files $ROOT/boards/idx_video_top.v':'add_files $ROOT/boards/idx_scaled_video_top.v',
 'top_module idx_video_top':'top_module idx_scaled_video_top',
 '@@@ V044 SYNTHESIS CHECK END; NOT TIMING/HARDWARE ACCEPTANCE':'@@@ V087 SCALED SYSTEM SYNTHESIS END; NOT TIMING/HARDWARE ACCEPTANCE',
 'source $ROOT/build_idx_physical_check.tcl':'source $ROOT/build_scaled_physical_check.tcl',
}.items():
 assert old in synth,old
 synth=synth.replace(old,new)
(root/'build_scaled_synth.tcl').write_text(synth,encoding='utf-8')
physical=(root/'build_idx_physical_check.tcl').read_text(encoding='utf-8')
physical=physical.replace('$ROOT/build/', '$ROOT/build_scaled/')
physical=physical.replace('v081_picture_controls_720p.bit','v087_bilinear_full720p.bit')
physical=physical.replace('V056_DIAGNOSTIC_BIT_GENERATED','V087_DIAGNOSTIC_BIT_GENERATED')
(root/'build_scaled_physical_check.tcl').write_text(physical,encoding='utf-8')
(root/'build_scaled_video.tcl').write_text('set ::ADB_CHAIN_PHY 1\nset ::ADB_DIAGNOSTIC_BIT 1\nsource [file join [file dirname [file normalize [info script]]] build_scaled_synth.tcl]\n',encoding='utf-8')
print(target)
