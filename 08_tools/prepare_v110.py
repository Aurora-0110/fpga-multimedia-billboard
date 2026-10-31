from pathlib import Path
r=Path(__file__).resolve().parents[1]
def edit(p,f):
 p=r/p;s=p.read_text('utf-8');p.write_text(f(s),encoding='utf-8')
# Long K1 is a toggle request, not a pin-level that forces the UI open.
for d in ['01_project','02_tests']:
 for p in (r/d).rglob('*'):
  if p.suffix not in {'.v','.sv'}:continue
  s=p.read_text('utf-8');n=s.replace('ui_pinned','ui_toggle')
  if n!=s:p.write_text(n,encoding='utf-8')
edit('01_project/rtl/common/media_controls.v',lambda s:s.replace('output reg ui_toggle);','output reg ui_toggle,output reg audio_paused);').replace('ui_toggle<=0;','ui_toggle<=0;audio_paused<=0;').replace('if(first_key)audio_choice<=audio_choice==2?0:audio_choice+1\'b1;\n    else audio_select<=0; // Short K0 safely exits; does NOT advance the image.',"if(first_key)begin audio_choice<=audio_choice==2?0:audio_choice+1'b1;audio_paused<=0;end\n    else audio_paused<=!audio_paused; // Long K0 exits; short K0 preserves the sample position."))
# Pause only stops sample consumption. The exact 48k HDMI cadence continues
# with zero PCM. A single prefetched frame may remain held across a pause.
edit('01_project/rtl/audio/tf_wav_playback.v',lambda s:s.replace('input [1:0] choice,input mounted,','input [1:0] choice,input mounted,input paused,').replace('wire [1:0] cmd;', '(* ASYNC_REG="TRUE" *) reg [1:0] pause_sd;\n always @(posedge clk_sd or negedge rst_n)\n if(!rst_n)pause_sd<=0;else pause_sd<={pause_sd[0],paused};\n wire [1:0] cmd;').replace('assign urgent=cmd!=0&&wu<LOW_WATER', 'assign urgent=!pause_sd[1]&&cmd!=0&&wu<LOW_WATER').replace('if(pr&&playing&&have&&error_pix==0)','if(pr&&!paused&&playing&&have&&error_pix==0)').replace('else if(sample_tick)begin','else if(sample_tick&&!paused)begin'))
edit('01_project/rtl/visual/audio_pcm_frontend.v',lambda s:s.replace('input clk_pix,rst_n,input [1:0]demo_track,','input clk_pix,rst_n,input paused,input [1:0]demo_track,').replace('.track(demo_track),','.track(demo_track),.paused(paused),').replace('wire signed [23:0]chosen_l=use_external?external_l:il;',"wire signed [23:0]chosen_l=paused?24'sd0:(use_external?external_l:il);").replace('wire signed [23:0]chosen_r=use_external?external_r:ir;',"wire signed [23:0]chosen_r=paused?24'sd0:(use_external?external_r:ir);").replace('pending_epoch,source_prev;','pending_epoch,source_prev,pause_prev;').replace('source_prev<=0;pcm_epoch','source_prev<=0;pause_prev<=0;pcm_epoch').replace('pcm_epoch<=0;source_prev<=use_external;','pcm_epoch<=0;source_prev<=use_external;pause_prev<=paused;').replace('if(use_external!=source_prev||external_epoch&&use_external)', 'if(paused!=pause_prev||use_external!=source_prev||external_epoch&&use_external)').replace('pcm_epoch<=pending_epoch||','pcm_epoch<=pending_epoch||(paused!=pause_prev)||').replace('(input clk_pix,rst_n,input [1:0]track,','(input clk_pix,rst_n,input paused,input [1:0]track,').replace('sample_track<=track;word<=fullword>>>(changing?2\'d3:atten);',"sample_track<=track;word<=paused?24'sd0:(fullword>>>(changing?2'd3:atten));").replace("phase<=changing?step:phase+step;", "if(!paused)phase<=changing?step:phase+step;").replace('if(changing)begin beat_count<=0;beat<=0;end','if(paused)begin end\n    else if(changing)begin beat_count<=0;beat<=0;end').replace('// Fixed 48k/24-bit stereo sample contract. EXTERNAL is the future TF PCM hook,\n// NOT an implemented WAV/MP3 reader.', '// Fixed 48k/24-bit stereo contract. External TF PCM and internal I2S demo\n// share pause silence, gain and DFT/HDMI samples. Pause never stops I2S clocks.'))
# UI toggle uses CURRENT visibility, including automatic entry/timeout. Manual
# hiding survives all key releases/source changes; only real faults override it.
p=r/'01_project/rtl/visual/media_ui_overlay.v';s=p.read_text('utf-8')
s=s.replace('input wire audio_select,ui_toggle,input wire [1:0] audio_choice,','input wire audio_select,ui_toggle,input wire [1:0] audio_choice,input wire [2:0] audio_status,')
s=s.replace('reg previous_pin,hide_pending,suppress_release;','reg previous_pin,manual_ui,manual_visible;\n reg previous_select;\n wire toggle_event=ui_toggle!=previous_pin;\n reg [2:0] shown_audio_status;')
s=s.replace('previous_pin<=0;hide_pending<=0;suppress_release<=0;', 'previous_pin<=0;manual_ui<=0;manual_visible<=0;previous_select<=0;shown_audio_status<=0;')
a=s.index('  if(previous_pin&&!ui_toggle)');b=s.index('  if(tick)begin',a)
s=s[:a]+'''  previous_select<=audio_select;
  if(toggle_event)begin manual_ui<=1;manual_visible<=!ui_visible;end
  if(key_change&&keys_down!=0&&(previous_keys==0||keys_down==3))last_key<=keys_down;
  if(action||audio_select!=previous_select)pending<=1;
'''+s[b:]
s=s.replace('shown_select<=audio_select;shown_pin<=ui_toggle;shown_choice<=audio_choice;','shown_select<=audio_select;shown_pin<=ui_toggle;shown_choice<=audio_choice;shown_audio_status<=audio_status;')
a=s.index('   if(load_failed||');b=s.index('   end else if(pending||action||keys_down!=0)',a)
s=s[:a]+'''   if(load_failed||tf_error!=0)begin
    remaining<=TIMEOUT_FRAMES;ui_visible<=1;
   end else if(toggle_event||manual_ui)begin
    remaining<=0;ui_visible<=toggle_event?!ui_visible:manual_visible;
   end else if(audio_select||edit_field!=0)begin
    remaining<=TIMEOUT_FRAMES;ui_visible<=1;
'''+s[b:]
s=s.replace('9:label_message=shown_select?46:26;', '9:label_message=shown_choice==0?47:(shown_choice==1?48:49);')
s=s.replace('9:state_message=shown_choice==0?47:(shown_choice==1?48:49);', '9:state_message=shown_audio_status==1?52:(shown_audio_status==2?53:(shown_audio_status==3?54:(shown_audio_status==4?55:(shown_choice!=0?56:(shown_audio?27:28)))));')
s=s.replace('11:state_message=shown_select?50:', '11:state_message=shown_select?(shown_audio_status==1?57:50):')
# Message lengths generated below, but explicit lengths for new strings.
s=s.replace("   6'd51:message_length=4'd4;", "   6'd51:message_length=4'd4;\n   6'd52:message_length=4'd3;\n   6'd53:message_length=4'd3;\n   6'd54:message_length=4'd3;\n   6'd55:message_length=4'd4;\n   6'd56:message_length=4'd3;\n   6'd57:message_length=4'd4;")
p.write_text(s,encoding='utf-8')
# Actual top wiring.
p=r/'01_project/boards/idx_audio_visual_top.v';s=p.read_text('utf-8')
s=s.replace('wire ui_audio_select,ui_toggle;', 'wire ui_audio_select,ui_toggle,ui_audio_paused;')
# Match actual declaration if differently grouped.
if 'wire ui_audio_select,ui_toggle,ui_audio_paused;' not in s:
 s=s.replace('wire ui_audio_select;', 'wire ui_audio_select,ui_audio_paused;')
s=s.replace('.ui_toggle(ui_toggle));','.ui_toggle(ui_toggle),.audio_paused(ui_audio_paused));')
s=s.replace('.choice(ui_audio_choice),.mounted(mount_valid),','.choice(ui_audio_choice),.mounted(mount_valid),.paused(ui_audio_paused),')
s=s.replace('.demo_track(selected_demo_track),','.demo_track(selected_demo_track),.paused(ui_audio_paused),')
s=s.replace('.audio_choice(ui_audio_choice),.ui_toggle(ui_toggle),', '.audio_choice(ui_audio_choice),.ui_toggle(ui_toggle),\n .audio_status(wav_error!=0||wav_under?3\'d4:(ui_audio_paused?3\'d1:(ui_audio_choice!=0?(wav_finished?3\'d3:(wav_playing?3\'d0:3\'d2)):3\'d0))),')
s=s.replace('.VERSION_TENS(0),.VERSION_ONES(9)', '.VERSION_TENS(1),.VERSION_ONES(0)')
# Demo subtitle time must freeze with paused audio, not follow silence cadence.
s=s.replace('.pcm_valid(pcm_valid),.pcm_epoch(pcm_epoch),.track', '.pcm_valid(pcm_valid&&!ui_audio_paused),.pcm_epoch(pcm_epoch),.track')
p.write_text(s,encoding='utf-8')
# Copy build/test helpers, changing only this version labels. Historical scripts
# remain for provenance, but new runners address the changed current sources.
for d in ['02_tests','08_tools']:
 for p in list((r/d).rglob('*v109*.py')):
  n=p.with_name(p.name.replace('v109','v110'));n.write_text(p.read_text('utf-8').replace('v109','v110').replace('V109','V110'),encoding='utf-8')
for p in (r/'01_project').glob('*.tcl'):
 s=p.read_text('utf-8');n=s.replace('v109','v110').replace('V109','V110').replace('v109_tf_wav_720p.bit','v110_ui_pause_720p.bit')
 n=n.replace('v110_tf_wav_720p.bit','v110_ui_pause_720p.bit');p.write_text(n,encoding='utf-8')
for p in [r/'02_tests/audio_visual/run_v110_bitgen.py',r/'02_tests/audio_visual/run_v110_physical.py']:
 s=p.read_text('utf-8').replace('v110_tf_wav_720p.bit','v110_ui_pause_720p.bit');p.write_text(s,encoding='utf-8')
p=r/'08_tools/generate_v110_ui_font.py';s=p.read_text('utf-8').replace("'退出选择', '切换音频'", "'暂停播放', '切换音频', '已暂停', '预缓冲', '已结束', '音频故障', '播放中', '继续播放'");p.write_text(s,encoding='utf-8')
print('v110 controls/UI/audio and build scaffolding written')
