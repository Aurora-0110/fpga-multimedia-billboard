import os
if os.environ.get('REPLAY_HISTORICAL_V107_EXPERIMENT')!='1':
 raise SystemExit('Historical development rewrite disabled. Use final RTL and run_acceptance.py.')
from pathlib import Path
r=Path(r'D:\FPGA_Billboard\work\v107_keys_subtitle_20261026')
rtl=r/'01_project/rtl'
control=r'''`timescale 1ns/1ps
// Pixel-domain gestures. A stable release is required after boot/each session.
// Short actions run on RELEASE; each long action fires once while held.
// A chord observed before a single-long threshold owns the whole gesture.
// A chord added AFTER a fired single-long cannot trigger a second action.
module media_controls #(parameter DEBOUNCE_CYCLES=742500,HOLD_CYCLES=74250000)(
 input wire clk,rst_n,key0_n,key1_n,
 output reg next_toggle,mode_toggle,
 output reg signed [7:0] brightness,
 output reg [2:0] contrast_q2,output reg [1:0] edit_field,
 output reg osd_enabled,output wire [1:0] keys_down,
 output reg audio_select,output reg [1:0] audio_choice,output reg ui_pinned);
 localparam DBW=DEBOUNCE_CYCLES>1?$clog2(DEBOUNCE_CYCLES):1;
 localparam HW=HOLD_CYCLES>1?$clog2(HOLD_CYCLES):1;
 localparam AW=$clog2(DEBOUNCE_CYCLES+4);
 (* ASYNC_REG="TRUE" *) reg [1:0] k0sync,k1sync;
 reg down0,down1;reg [DBW-1:0] db0,db1;
 assign keys_down={down1,down0};
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin k0sync<=3;k1sync<=3;down0<=0;down1<=0;db0<=0;db1<=0;end
 else begin
  k0sync<={k0sync[0],key0_n};k1sync<={k1sync[0],key1_n};
  if((!k0sync[1])==down0)db0<=0;
  else if(db0==DEBOUNCE_CYCLES-1)begin down0<=!k0sync[1];db0<=0;end
  else db0<=db0+1'b1;
  if((!k1sync[1])==down1)db1<=0;
  else if(db1==DEBOUNCE_CYCLES-1)begin down1<=!k1sync[1];db1<=0;end
  else db1<=db1+1'b1;
 end
 reg [AW-1:0] arm_count;reg [HW-1:0] hold_count;
 reg ready,session,chord,held,first_key;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  ready<=0;arm_count<=0;session<=0;chord<=0;held<=0;first_key<=0;hold_count<=0;
  next_toggle<=0;mode_toggle<=0;brightness<=0;contrast_q2<=4;edit_field<=0;
  osd_enabled<=1;audio_select<=0;audio_choice<=0;ui_pinned<=0;
 end else if(!ready)begin
  // Unsynchronized pads inhibit boot arming ONLY; never cause an action.
  if(key0_n&&key1_n&&(&k0sync)&&(&k1sync)&&!down0&&!down1)begin
   if(arm_count==DEBOUNCE_CYCLES+2)ready<=1;else arm_count<=arm_count+1'b1;
  end else arm_count<=0;
 end else if(!session)begin
  hold_count<=0;held<=0;chord<=0;
  if(down0||down1)begin session<=1;first_key<=down1;chord<=down0&&down1;end
 end else if(!down0&&!down1)begin
  session<=0;hold_count<=0;
  if(!held)begin
   if(chord)osd_enabled<=!osd_enabled;
   else if(audio_select)begin
    if(first_key)audio_choice<=audio_choice==2?0:audio_choice+1'b1;
    else audio_select<=0; // Short K0 safely exits; does NOT advance the image.
   end else case(edit_field)
    0:if(first_key)mode_toggle<=!mode_toggle;else next_toggle<=!next_toggle;
    1:if(first_key)begin if(brightness<64)brightness<=brightness+8'sd16;end
      else if(brightness> -64)brightness<=brightness-8'sd16;
    2:if(first_key)begin if(contrast_q2<6)contrast_q2<=contrast_q2+1'b1;end
      else if(contrast_q2>2)contrast_q2<=contrast_q2-1'b1;
    default:edit_field<=0;
   endcase
  end
 end else if(down0&&down1)begin
  chord<=1;
  // The first cycle of a newly observed chord starts a NEW hold interval.
  if(!chord)hold_count<=0;
  else if(!held)begin
   if(hold_count==HOLD_CYCLES-1)begin
    held<=1;hold_count<=0;audio_select<=0;
    edit_field<=edit_field==2?0:edit_field+1'b1;osd_enabled<=1;
   end else hold_count<=hold_count+1'b1;
  end
 end else if(!chord&&!held)begin
  if(hold_count==HOLD_CYCLES-1)begin
   held<=1;hold_count<=0;edit_field<=0;
   if(first_key)ui_pinned<=!ui_pinned;
   else audio_select<=!audio_select;
  end else hold_count<=hold_count+1'b1;
 end else hold_count<=0;
endmodule
'''
(rtl/'common/media_controls.v').write_text(control,encoding='utf8')
ui=(rtl/'visual/ui_help_overlay.v').read_text(encoding='utf8').replace('module ui_help_overlay','module media_ui_overlay').replace('visual/ui_zh_','visual/media_ui_zh_')
ui=ui.replace('input wire [7:0] tf_error,input wire audio_active,','input wire [7:0] tf_error,input wire audio_active,\n input wire audio_select,ui_pinned,input wire [1:0] audio_choice,')
ui=ui.replace('reg previous_overlays,previous_auto;','reg previous_overlays,previous_auto;\n reg previous_pin,hide_pending,suppress_release;\n reg shown_select,shown_pin;reg [1:0] shown_choice;')
ui=ui.replace('remaining<=TIMEOUT_FRAMES;pending<=0;ui_visible<=1;','remaining<=TIMEOUT_FRAMES;pending<=0;ui_visible<=1;\n  previous_pin<=0;hide_pending<=0;suppress_release<=0;shown_select<=0;shown_pin<=0;shown_choice<=0;',1)
ui=ui.replace('previous_field<=edit_field;previous_overlays<=overlays_enabled;previous_auto<=auto_mode;','previous_field<=edit_field;previous_overlays<=overlays_enabled;previous_auto<=auto_mode;\n  previous_pin<=ui_pinned;\n  if(previous_pin&&!ui_pinned)begin hide_pending<=1;suppress_release<=1;pending<=0;end\n  if(suppress_release&&keys_down==0)suppress_release<=0;')
ui=ui.replace('if(action)pending<=1;','if(action&&!suppress_release&&!(previous_pin&&!ui_pinned))pending<=1;')
ui=ui.replace('shown_video<=picture_visible;shown_audio<=audio_active;','shown_video<=picture_visible;shown_audio<=audio_active;\n   shown_select<=audio_select;shown_pin<=ui_pinned;shown_choice<=audio_choice;')
old='''if(pending||action||keys_down!=0||edit_field!=0||load_failed||tf_error!=0)begin
    remaining<=TIMEOUT_FRAMES;ui_visible<=1;
   end else if(remaining>1)begin remaining<=remaining-1'b1;ui_visible<=1;end'''
new='''if(load_failed||tf_error!=0||audio_select||edit_field!=0||ui_pinned)begin
    remaining<=TIMEOUT_FRAMES;ui_visible<=1;hide_pending<=0;
   end else if(hide_pending||(previous_pin&&!ui_pinned)||suppress_release)begin
    remaining<=0;ui_visible<=0;hide_pending<=0;
   end else if(pending||action||keys_down!=0)begin
    remaining<=TIMEOUT_FRAMES;ui_visible<=1;
   end else if(remaining>1)begin remaining<=remaining-1'b1;ui_visible<=1;end'''
assert old in ui;ui=ui.replace(old,new)
ui=ui.replace('9:label_message=26;','9:label_message=shown_select?46:26;')
ui=ui.replace('9:state_message=shown_audio?27:28;','9:state_message=shown_choice==0?47:(shown_choice==1?48:49);')
ui=ui.replace('11:state_message=shown_field==0?', '11:state_message=shown_select?50:(shown_field==0?')
ui=ui.replace('(shown_field==2?37:45));','(shown_field==2?37:45)));')
ui=ui.replace('12:state_message=shown_field==0?39:', '12:state_message=shown_select?51:(shown_field==0?39:')
ui=ui.replace('(shown_field==2?41:45));','(shown_field==2?41:45)));')
# Length cases are regenerated after font generation.
(rtl/'visual/media_ui_overlay.v').write_text(ui,encoding='utf8')
# Keep the inherited font generation tool; generate new named assets only.
g=(r/'08_tools/generate_v105_ui_font.py').read_text(encoding='utf8').replace('v105','v107').replace('ui_zh_', 'media_ui_zh_')
g=g.replace("'系统控制', 'V105'", "'系统控制', 'V107'")
g=g.replace("'参数异常'", "'参数异常', '音频选择', '跟随图片', '测试音A', '测试音B', '退出选择', '切换音频'")
(r/'08_tools/generate_v107_ui_font.py').write_text(g,encoding='utf8')
# Active top only; historical scaled top and existing control tests remain valid.
top=r/'01_project/boards/idx_audio_visual_top.v';s=top.read_text(encoding='utf8')
s=s.replace('picture_controls_osd #(', 'media_controls #(')
s=s.replace('wire [1:0] ui_keys_down;', 'wire ui_audio_select,ui_pinned;wire [1:0] ui_audio_choice;wire [1:0] ui_keys_down;')
s=s.replace('.keys_down(ui_keys_down));','.keys_down(ui_keys_down),.audio_select(ui_audio_select),.audio_choice(ui_audio_choice),.ui_pinned(ui_pinned));',1)
s=s.replace('wire signed[23:0]pcm_left,pcm_right;', 'wire [1:0] selected_demo_track=ui_audio_choice==0?demo_track:(ui_audio_choice==1?2\'d1:2\'d3);\n wire signed[23:0]pcm_left,pcm_right;')
s=s.replace('.demo_track(demo_track),.use_external', '.demo_track(selected_demo_track),.use_external')
s=s.replace('ui_help_overlay #(', 'media_ui_overlay #(')
s=s.replace('.audio_active(pcm_sound_active),', '.audio_active(pcm_sound_active),.audio_select(ui_audio_select),.audio_choice(ui_audio_choice),.ui_pinned(ui_pinned),')
s=s.replace('.VERSION_ONES(5)', '.VERSION_ONES(7)')
s=s.replace('// v103 bounded','// v107: long single-key media/UI gestures and sample-clock demo subtitles; no TF WAV reader yet.\n// v103 bounded',1)
top.write_text(s,encoding='utf8')
b=r/'01_project/build_audio_visual_synth.tcl';s=b.read_text(encoding='utf8').replace('V105','V107').replace('v105','v107')
s=s.replace('common/picture_controls_osd.v','common/picture_controls_osd.v common/media_controls.v visual/media_ui_overlay.v visual/pcm_subtitle_timeline.v visual/subtitle_overlay.v')
b.write_text(s,encoding='utf8')
print('New media controls/UI scaffold and active top written; subtitle modules follow.')
