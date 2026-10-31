"""V129 shared caption datapath: 2x64 cue slots and 4+1 native BRAM font banks."""
from pathlib import Path
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
p=r/'01_project/rtl/visual/pcm_caption_player.v';s=p.read_text(encoding='utf-8')
assert 'metadata[0:255]'in s
s=s.replace('// V127: precompiled MUSIC captions driven ONLY by real accepted WAV stereo frames.','// V129: per-track precompiled captions driven ONLY by accepted WAV stereo frames.\n// MUSIC and third audio share one player; separate64-cue banks avoid an address adder.')
s=s.replace('metadata[0:255]','metadata[0:511]')
s=s.replace("wire good=(choice==2'd1)&&session_ready&&!finished&&(error_code==0);","wire caption_track=(choice==2'd1)||(choice==2'd3);\n wire good=caption_track&&session_ready&&!finished&&(error_code==0);\n wire [5:0] last_cue=(choice==2'd3)?THIRD_CUE_COUNT-1:MUSIC_CUE_COUNT-1;")
s=s.replace('assign cue_active=good&&started','assign cue_active=good&&(choice==previous_choice)&&started')
s=s.replace('metadata[{cue_index,load_step[1:0]}]',"metadata[{(choice==2'd3),cue_index,load_step[1:0]}]")
s=s.replace('// Four narrow words/cue fit a single9K ROM; no giant parallel cue mux.','// Two64-cue banks fit the existing single512x18 native9K ROM.')
s=s.replace('cue_index<MUSIC_CUE_COUNT-1','cue_index<last_cue');p.write_text(s,encoding='utf-8')
p=r/'01_project/rtl/visual/subtitle_overlay.v';s=p.read_text(encoding='utf-8')
s=s.replace('// V128: exact user-provided lyrics; no demo clock, time label or progress bar.','// V129: shared exact-user-text subtitles for MUSIC and third audio.')
s=s.replace('// 197glyphs fit2048x18 (four9K blocks), instead of4096x12 (six).','// Up to320 full glyphs:2048x18 +512x18 (five native9K blocks).\n// Explicit banks avoid rounding a286-glyph monolithic array to eight blocks.')
s=s.replace('reg [7:0] text_memory','reg [8:0] text_memory')
s=s.replace('(* rom_style="block" *) reg [17:0] font_memory[0:MUSIC_FONT_ROWS-1];','(* rom_style="block" *) reg [17:0] font_memory_lo[0:2047];\n (* rom_style="block" *) reg [17:0] font_memory_hi[0:511];')
s=s.replace('reg [7:0] text_glyph1;reg [17:0] bits2;','reg [8:0] text_glyph1;reg [17:0] bits2_lo,bits2_hi;reg font_bank2;\n wire [17:0] bits2=font_bank2?bits2_hi:bits2_lo;')
s=s.replace('bits2<=font_memory[{text_glyph1,font_word}];','bits2_lo<=font_memory_lo[{text_glyph1[7:0],font_word}];\n  bits2_hi<=font_memory_hi[{text_glyph1[5:0],font_word}];\n  font_bank2<=text_glyph1[8];');p.write_text(s,encoding='utf-8')
p=r/'01_project/boards/idx_audio_visual_top.v';s=p.read_text(encoding='utf-8');old='.enable(active_osd_enabled&&ui_audio_choice==1)';assert old in s
s=s.replace(old,'.enable(active_osd_enabled&&(ui_audio_choice==1||ui_audio_choice==3))');p.write_text(s,encoding='utf-8')
print('Updated player, shared banked overlay, top track enable; clocks/pins/PCM/TF unchanged')
