"""V130 surgical layer independence/UI volume and36px rounded caption layout."""
from pathlib import Path
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
p=r/'01_project/rtl/common/media_controls.v';s=p.read_text(encoding='utf-8')
s=s.replace('output reg [3:0] volume_level);','output reg [3:0] volume_level,output reg av_enabled);')
s=s.replace('osd_enabled<=1;volume_level<=10;','osd_enabled<=1;av_enabled<=1;volume_level<=10;')
s=s.replace('if(chord)osd_enabled<=!osd_enabled;','''// Short chord cycles independently composited visible layers, not playback.
   // 11 all ->10 base only ->01 audio-visual only ->00 clean picture ->11.
   if(chord){osd_enabled,av_enabled}<={osd_enabled,av_enabled}-2'd1;''')
s=s.replace("edit_field<=edit_field+1'b1;osd_enabled<=1;","edit_field<=edit_field+1'b1;")
p.write_text(s,encoding='utf-8')
p=r/'01_project/boards/idx_audio_visual_top.v';s=p.read_text(encoding='utf-8')
s=s.replace('wire ui_audio_select,ui_toggle,ui_audio_paused;','wire ui_av_enabled;wire ui_audio_select,ui_toggle,ui_audio_paused;')
s=s.replace('.keys_down(ui_keys_down),.volume_level(ui_volume)', '.keys_down(ui_keys_down),.av_enabled(ui_av_enabled),.volume_level(ui_volume)')
s=s.replace('reg active_osd_enabled;','reg active_osd_enabled,active_av_enabled;')
s=s.replace('active_osd_enabled<=1;end','active_osd_enabled<=1;active_av_enabled<=1;end')
s=s.replace('active_osd_enabled<=ui_osd_enabled;end','active_osd_enabled<=ui_osd_enabled;active_av_enabled<=ui_av_enabled;end')
s=s.replace('.picture_visible(op),.enable(active_osd_enabled)', '.picture_visible(op),.enable(active_av_enabled)')
s=s.replace('.enable(active_osd_enabled&&(ui_audio_choice==1||ui_audio_choice==3))', '.enable(active_av_enabled&&(ui_audio_choice==1||ui_audio_choice==3))')
s=s.replace('.overlays_enabled(ui_osd_enabled)', '.overlays_enabled(ui_osd_enabled),.av_enabled(ui_av_enabled)')
assert '.av_enabled(ui_av_enabled)'in s
p.write_text(s,encoding='utf-8')
p=r/'01_project/rtl/visual/subtitle_overlay.v';s=p.read_text(encoding='utf-8')
s=s.replace('// V129: shared exact-user-text subtitles for MUSIC and third audio.','// V130: independent AV layer; rounded source glyphs enlarged to36px (3x).')
s=s.replace('text_width<={text_length,5\'b0};',"text_width<=({6'd0,text_length}<<5)+({6'd0,text_length}<<4);")
s=s.replace("text_start<=(12'd1280-{2'd0,text_length,5'b0})>>1;","text_start<=(12'd1280-(({7'd0,text_length}<<5)+({7'd0,text_length}<<4)))>>1;")
s=s.replace('y>=662&&y<708','y>=648&&y<704').replace('y>=672&&y<696','y>=658&&y<694')
a=s.index(' wire [11:0] tx=');b=s.index('\n reg [23:0] base',a)
s=s[:a]+''' wire [11:0] tx=x-text_start;wire [5:0] ty=y-12'd658;
 //48px cells with centered36px glyphs; constants only, no extra DSP/BRAM.
 wire [4:0] col=tx/12'd48;
 wire [5:0] cell_x=tx-({7'd0,col}<<5)-({7'd0,col}<<4);
 wire [5:0] local_x=cell_x-6'd6;
'''+s[b:]
s=s.replace("tx[4:0]>=4&&tx[4:0]<28","cell_x>=6&&cell_x<42")
s=s.replace('font_y0<=ty[4:1]','font_y0<=ty/6\'d3').replace('font_x0<=local_x[4:1]','font_x0<=local_x/6\'d3')
p.write_text(s,encoding='utf-8')
p=r/'01_project/rtl/visual/media_ui_overlay.v';s=p.read_text(encoding='utf-8')
s=s.replace('input wire auto_mode,overlays_enabled,','input wire auto_mode,overlays_enabled,av_enabled,')
s=s.replace('reg previous_overlays,previous_auto;','reg previous_overlays,previous_auto,previous_av;reg shown_av;')
s=s.replace('wire action=volume_level!=previous_volume','wire action=av_enabled!=previous_av || volume_level!=previous_volume')
s=s.replace('previous_field<=0;previous_overlays<=1;previous_auto<=1;','previous_field<=0;previous_overlays<=1;previous_auto<=1;previous_av<=1;shown_av<=1;')
s=s.replace('previous_field<=edit_field;previous_overlays<=overlays_enabled;', 'previous_av<=av_enabled;previous_field<=edit_field;previous_overlays<=overlays_enabled;')
s=s.replace('shown_image<=image_index;shown_auto<=auto_mode;', 'shown_av<=av_enabled;shown_image<=image_index;shown_auto<=auto_mode;')
s=s.replace('6:label_message=(shown_field==3||shown_select)?59:19;', '6:label_message=19;')
s=s.replace('12:label_message=38;13:label_message=42;default:', '12:label_message=38;13:label_message=42;14:label_message=59;15:label_message=26;default:')
s=s.replace('6:state_message=(shown_field==3||shown_select)?60:20;', '6:state_message=20;')
s=s.replace('13:state_message=43;default:', '13:state_message=43;14:state_message=60;15:state_message=shown_av?24:25;default:')
s=s.replace('wire [13:0] row_decode;wire [3:0] font_row_decode[0:13];','wire [15:0] row_decode;wire [3:0] font_row_decode[0:15];')
s=s.replace('wire [13:0] glyph_row_decode;', 'wire [15:0] glyph_row_decode;')
s=s.replace('row_g<14','row_g<16').replace('LOW=80+40*row_g,HIGH=120+40*row_g,GLYPH_END=112+40*row_g','LOW=72+36*row_g,HIGH=108+36*row_g,GLYPH_END=104+36*row_g')
s=s.replace('row_i<14','row_i<16').replace('layout_row==13','layout_row==15')
s=s.replace('row_pre==1||row_pre==6','row_pre==1||row_pre==6||row_pre==14')
s=s.replace('6:if(shown_field==3||shown_select)begin','14:begin')
s=s.replace('end else case(value_col0)\n       0:begin override_now=1;override_glyph_now=shown_brightness', 'end\n    6:case(value_col0)\n       0:begin override_now=1;override_glyph_now=shown_brightness')
s=s.replace('x_pre>=576&&x_pre<578&&y_pre>=120&&y_pre<640','x_pre>=576&&x_pre<578&&y_pre>=108&&y_pre<644').replace('y_pre>=158&&y_pre<160','y_pre>=142&&y_pre<144')
s=s.replace('y_pre<112','y_pre<108')
s=s.replace('// Fourteen disjoint 40-pixel row ranges','// Sixteen disjoint36-pixel row ranges').replace('14-deep','16-deep')
p.write_text(s,encoding='utf-8')
print('V130 production surgical changes done')
