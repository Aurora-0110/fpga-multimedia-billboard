# HISTORICAL development replay only; not the final build/rebuild entry.
# Use run_acceptance.py and generate_v105_ui_font.py instead.
import os
if os.environ.get('REPLAY_HISTORICAL_V105_EXPERIMENT')!='1':
 raise SystemExit('Historical experiment intentionally disabled; use final RTL and run_acceptance.py.')
from pathlib import Path
import shutil,json,hashlib
r=Path(r'D:\FPGA_Billboard\work\v105_center_glass_art_spectrum_20261026')
dest=r/'04_evidence/v105_failed_timing_attempt1_sources';dest.mkdir(exist_ok=False)
for rel in ['01_project/rtl/visual/ui_help_overlay.v','01_project/rtl/visual/spectrum_overlay.v','01_project/boards/idx_audio_visual_top.v','01_project/rtl/visual/ui_zh_glyph_ids.vh','01_project/rtl/visual/ui_zh_font_init.vh','01_project/rtl/visual/ui_zh_text_init.vh']:
 d=dest/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(r/rel,d)
(dest/'README.md').write_text('Attempt1 setup SWNS -6.304ns: y-row decoder -> variable message/length -> centered coordinate -> numeric override. Failed candidate, NO bit release. These are pre-fix RTL copies, never the active build. Constraints unchanged.\n',encoding='utf8')
p=r/'01_project/rtl/visual/ui_help_overlay.v';s=p.read_text(encoding='utf8')
a=s.index(' wire [5:0] label_now=');b=s.index(' reg override_now;',a)
s=s[:a]+''' // Frame-only three-step layout preparation: message -> length -> bounds.
 // Pixel path never computes a message length or derives centering from state.
 reg [5:0] state_msg_cache[0:15],state_start_cache[0:15],state_end_cache[0:15];
 reg layout_busy,layout_ready;reg [3:0] layout_row;reg [1:0] layout_phase;
 reg [5:0] layout_message;reg [3:0] layout_length;integer lr;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  layout_busy<=0;layout_ready<=0;layout_row<=0;layout_phase<=0;layout_message<=0;layout_length<=0;
  for(lr=0;lr<16;lr=lr+1)begin state_msg_cache[lr]<=0;state_start_cache[lr]<=0;state_end_cache[lr]<=0;end
 end else if(tick)begin
  layout_busy<=1;layout_ready<=0;layout_row<=0;layout_phase<=0;
 end else if(layout_busy)begin
  case(layout_phase)
   0:begin layout_message<=state_message(layout_row);layout_phase<=1;end
   1:begin layout_length<=message_length(layout_message);layout_phase<=2;end
   2:begin
    state_msg_cache[layout_row]<=layout_message;
    state_start_cache[layout_row]<=6'd48-{2'b0,layout_length};
    state_end_cache[layout_row]<=6'd48+{2'b0,layout_length};
    if(layout_row==13)begin layout_busy<=0;layout_ready<=1;end
    else begin layout_row<=layout_row+1'b1;layout_phase<=0;end
   end
  endcase
 end
 wire [5:0] label_now=label_message(row_now),state_now=state_msg_cache[row_now];
 wire [5:0] left_units=(row_now==1||row_now==6)?6'd26:(row_now==7?6'd25:6'd24);
 wire [5:0] left_end=(row_now==1||row_now==6)?6'd30:(row_now==7?6'd31:6'd32);
 wire is_right=x>=576;
 wire label_hit=x[11:4]>={2'b0,left_units}&&x[11:4]<{2'b0,left_end};
 wire state_hit=x[11:4]>={2'b0,state_start_cache[row_now]}&&x[11:4]<{2'b0,state_end_cache[row_now]};
 wire [5:0] start_units=is_right?state_start_cache[row_now]:left_units;
 wire [11:0] local_x=x-{2'b0,start_units,4'b0};
 wire [4:0] value_col_now={1'b0,local_x[8:5]};
 reg [3:0] row0;reg [4:0] value_col0;reg right0;
'''+s[b:]
# Retiming override into stage1, parallel with synchronous text ROM output.
a=s.index(' reg override_now;');b=s.index(' reg [23:0] base',a)
part=s[a:b].replace('if(state_hit)','if(right0)').replace('case(row_now)','case(row0)').replace('value_col_now','value_col0')
s=s[:a]+part+s[b:]
s=s.replace('reg override0,override1;reg [6:0] override_glyph0,override_glyph1,text_glyph1;','reg override1;reg [6:0] override_glyph1,text_glyph1;')
s=s.replace('override0<=0;override1<=0;override_glyph0<=0;override_glyph1<=0;','row0<=0;value_col0<=0;right0<=0;override1<=0;override_glyph1<=0;')
s=s.replace('glyph[0]<=ui_visible&&de&&glyph_y_now&&(label_hit||state_hit);','glyph[0]<=ui_visible&&layout_ready&&de&&glyph_y_now&&(label_hit||state_hit);')
s=s.replace("message0<=label_hit?label_now:(state_hit?state_now:6'd0);","message0<=is_right?state_now:label_now;")
s=s.replace('override0<=override_now;override1<=override0;override_glyph0<=override_glyph_now;override_glyph1<=override_glyph0;','row0<=row_now;value_col0<=value_col_now;right0<=is_right;\n  override1<=override_now;override_glyph1<=override_glyph_now;')
p.write_text(s,encoding='utf8')
p=r/'02_tests/ui/tb_v105_ui.sv';s=p.read_text(encoding='utf8').replace('x=1;de=0;cycles(2);end endtask','x=1;de=0;cycles(44);if(!d.layout_ready)$fatal(1,"frame layout deadline");end endtask');p.write_text(s,encoding='utf8')
p=r/'01_project/boards/idx_audio_visual_top.v';s=p.read_text(encoding='utf8').replace('.VERSION_ONES(4)','.VERSION_ONES(5)').replace('// v099 transparent sound-gated 16-band real PCM spectrum + compact logo;','// v105 centered rounded Chinese glass UI and64 rainbow display bars from16 real DFT bands;');p.write_text(s,encoding='utf8')
print('Preserved failed attempt1 sources; moved layout to42-cycle frame precompute and glyph overrides into parallel stage1; no extra video latency/SDC exception.')
