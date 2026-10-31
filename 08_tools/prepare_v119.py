"""v119: one additional WAV slot, reusing v116 transport/decoder/buffers."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
assert '01_versions' not in ROOT.parts

def edit(rel, old, new):
 p=ROOT/rel;s=p.read_text(encoding='utf8');assert old in s,(rel,old);p.write_text(s.replace(old,new),encoding='utf8')

reader='01_project/rtl/audio/tf_wav_reader.v'
edit(reader,'// Reuses the BMP mount. Looks up MUSIC.WAV or ADVOICE.WAV in FAT32 root;',
 '''// v119: choices1/2 preserve MUSIC.WAV and ADVOICE.WAV. Choice3 finds the
// first additional regular *.WAV in root directory order, excluding both names.
// VFAT long-name entries are ignored; the associated standard short alias is
// sufficient for the WAV extension. No long-name display/MP3/FLAC decoding.
// Reuses the BMP FAT32 mount and the same decoder/sector/sample buffers;''')
edit(reader,'reg [31:0] file_cluster,file_size;reg name_ok,attr_ok;',
 'reg [31:0] file_cluster,file_size;reg name_ok,attr_ok,music_name_ok,advoice_name_ok;')
edit(reader,'function [7:0] name_byte;input [4:0] i;begin\n  if(choice==1)case(i)',
 'function [7:0] name_byte;input [4:0] i;input use_ad;begin\n  if(!use_ad)case(i)')
edit(reader,'  end endfunction\n  fat32_audio_prefetch', '  end endfunction\n  fat32_audio_prefetch') if False else None
edit(reader,' end endfunction\n fat32_audio_prefetch', ''' end endfunction
 wire selected_name=choice==1?music_name_ok:
                    (choice==2?advoice_name_ok:(choice==3&&!music_name_ok&&!advoice_name_ok));
 fat32_audio_prefetch''')
edit(reader,'file_size<=0;name_ok<=0;attr_ok<=0;',
 'file_size<=0;name_ok<=0;music_name_ok<=0;advoice_name_ok<=0;attr_ok<=0;')
edit(reader,'''     if(ei==0)begin name_ok<=bd==name_byte(0);attr_ok<=0;if(bd==0)fail(8'ha1);end
     else if(ei<11&&bd!=name_byte(ei))name_ok<=0;''', '''     if(ei==0)begin
      name_ok<=bd!=8'he5&&bd!=0&&bd!=".";
      music_name_ok<=bd==name_byte(0,1'b0);advoice_name_ok<=bd==name_byte(0,1'b1);
      attr_ok<=0;if(bd==0)fail(8'ha1);
     end else if(ei<11)begin
      if(bd!=name_byte(ei,1'b0))music_name_ok<=0;
      if(bd!=name_byte(ei,1'b1))advoice_name_ok<=0;
      if((ei==8&&bd!="W")||(ei==9&&bd!="A")||(ei==10&&bd!="V"))name_ok<=0;
     end''')
edit(reader,'31:if(name_ok&&attr_ok)begin','31:if(name_ok&&attr_ok&&selected_name)begin')
edit('01_project/rtl/common/media_controls.v',
 'audio_choice<=audio_choice==2?0:audio_choice+1\'b1;',
 'audio_choice<=audio_choice+1\'b1; // 2-bit wrap: demo -> MUSIC -> ADVOICE -> extra WAV -> demo\n      ')
edit('01_project/rtl/visual/media_ui_overlay.v',
 '9:label_message=shown_choice==0?47:(shown_choice==1?48:49);',
 '9:label_message=shown_choice==0?47:(shown_choice==1?48:(shown_choice==2?49:58));')
edit('01_project/rtl/visual/media_ui_overlay.v',
 "6'd57:message_length=4'd4;", "6'd57:message_length=4'd4;\n   6'd58:message_length=4'd4;")
edit('01_project/boards/idx_audio_visual_top.v',
 'Existing demo choice0 retained;1 MUSIC,2 ADVOICE.',
 'Existing demo choice0 retained;1 MUSIC,2 ADVOICE,3 first extra WAV.')
edit('01_project/boards/idx_audio_visual_top.v','.VERSION_ONES(6)','.VERSION_ONES(9)')

font=(ROOT/'08_tools/generate_v114_ui_font.py').read_text(encoding='utf8')
font=font.replace('v114','v119').replace("'V114'","'V119'").replace("'继续播放'\n]", "'继续播放', '扩展音频'\n]")
assert "'扩展音频'" in font
(ROOT/'08_tools/generate_v119_ui_font.py').write_text(font,encoding='utf8')

# Preserve all historical tests; update only copies that encode the old 3-state cycle.
controls=(ROOT/'02_tests/media_controls/tb_v107_controls.sv').read_text(encoding='utf8')
controls=controls.replace('tb_v107_controls','tb_v119_controls').replace('PASS v110','PASS v119')
controls=controls.replace('short_key(1);if(choice!=0||mc!=1)$fatal(1,"selection wrap");',
 '''short_key(1);if(choice!=3||mc!=1)$fatal(1,"select extra WAV");
  short_key(1);if(choice!=0||mc!=1)$fatal(1,"four-source selection wrap");''')
(ROOT/'02_tests/media_controls/tb_v119_controls.sv').write_text(controls,encoding='utf8')
media=(ROOT/'02_tests/media_controls/run_v114_media.py').read_text(encoding='utf8').replace('v114_media_','v119_media_').replace('tb_v107_controls','tb_v119_controls')
(ROOT/'02_tests/media_controls/run_v119_media.py').write_text(media,encoding='utf8')
ui=(ROOT/'02_tests/ui/run_v114_ui.py').read_text(encoding='utf8').replace('v114_ui','v119_ui').replace('V114','V119')
ui=ui.replace('range(3):','range(4):').replace("['跟随图片','音乐文件','广告语音']","['跟随图片','音乐文件','广告语音','扩展音频']")
# run_v114_ui.py path replacement above also selects v119 spec and v119 TB.
(ROOT/'02_tests/ui/run_v119_ui.py').write_text(ui,encoding='utf8')
uitb=(ROOT/'02_tests/ui/tb_v114_ui.sv').read_text(encoding='utf8').replace('tb_v114_ui','tb_v119_ui')
(ROOT/'02_tests/ui/tb_v119_ui.sv').write_text(uitb,encoding='utf8')

for role in ('synth','physical'):
 p=ROOT/f'02_tests/audio_visual/run_v116_{role}.py'
 (ROOT/f'02_tests/audio_visual/run_v119_{role}.py').write_text(p.read_text(encoding='utf8').replace('v116','v119').replace('V116','V119'),encoding='utf8')
for rel in ('01_project/build_audio_visual_synth.tcl','01_project/build_audio_visual_physical_check.tcl'):
 p=ROOT/rel;p.write_text(p.read_text(encoding='utf8').replace('v116','v119').replace('V116','V119'),encoding='utf8')
print('v119 RTL, UI, and test/build entry copies prepared; no compile or hardware claim.')
