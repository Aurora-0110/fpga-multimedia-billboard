"""Create V130-specific independent tests; keep historical TB files unchanged."""
from pathlib import Path
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
# UI text+pixel oracle:16 permanent rows, both layer states,11volumes in all contexts.
p=r/'02_tests/ui/run_v128_ui.py';s=p.read_text(encoding='utf-8').replace('v128','v130').replace('V128','V130')
s=s.replace('volume=10)','volume=10,av=True)')
s=s.replace('# Independent low-picture-gate fifth raster vector.', '''# Persistent volume row in browse/edit/audio and every independent layer combination.
for volume in range(11):
 for field in range(4):
  for select in [False,True]:
   c=base();c.update(volume=volume,field=field,select=select);cases.append(c)
for osd in [False,True]:
 for av in [False,True]:
  c=base();c.update(osd=osd,av=av);cases.append(c)
# Independent low-picture-gate fifth raster vector.''')
s=s.replace("'K1功能','双键操作']","'K1功能','双键操作','音量','音画图层']")
s=s.replace("'短按显隐 长按调参']","'短按切层 长按调参',f\"{c['volume']*10:03d}%\",'已开启' if c['av'] else '已隐藏']")
s=s.replace(" if c['field']==3 or c['select']:\n  case_labels[6]='音量';states[6]=f\"{c['volume']*10:03d}%\"\n",'')
s=s.replace("v |= c['volume']<<47","v |= (c['volume']<<47)|(c['av']<<51)")
(r/'02_tests/ui/run_v130_ui.py').write_text(s,encoding='utf-8')
p=r/'02_tests/ui/tb_v128_ui.sv';s=p.read_text(encoding='utf-8').replace('v128','v130')
s=s.replace('reg mode=1,osd=1,','reg avlayer=1;reg mode=1,osd=1,')
s=s.replace('.overlays_enabled(osd),','.overlays_enabled(osd),.av_enabled(avlayer),')
s=s.replace('reference_text[0:251]','reference_text[0:287]').replace('cycles(44)','cycles(60)')
s=s.replace('volume=v[50:47];','volume=v[50:47];avlayer=v[51];')
s=s.replace('row<14','row<16').replace('which*252','which*288').replace('y=80+row*40','y=72+row*36')
s=s.replace('y>=80&&y<640','y>=72&&y<648').replace('(y-80)/40','(y-72)/36').replace('y<112','y<108')
s=s.replace('rr<14','rr<16').replace('(y-80)%40','(y-72)%36')
s=s.replace('y>=120&&y<640','y>=108&&y<644').replace('y>=158&&y<160','y>=142&&y<144')
s=s.replace('i<252','i<288').replace('*252','*288')
(r/'02_tests/ui/tb_v130_ui.sv').write_text(s,encoding='utf-8')
# Original control regression retained with new layer-state truth table.
p=r/'02_tests/media_controls/tb_v126_controls.sv';s=p.read_text(encoding='utf-8').replace('v126','v130')
s=s.replace('wire nt,mt,osd,','wire avlayer;wire nt,mt,osd,').replace('pin,paused,volume);','pin,paused,volume,avlayer);')
s=s.replace('if(osd||field||sel||pin||nc!=1||mc!=1)', 'if(!osd||avlayer||field||sel||pin||nc!=1||mc!=1)')
s=s.replace('if(!osd||nc!=1||mc!=1)', 'if(osd||!avlayer||nc!=1||mc!=1)')
s=s.replace('release_all();if(osd)', 'release_all();if(osd||avlayer)')
s=s.replace('if(field!=1||!osd)', 'if(field!=1||osd||avlayer)')
s=s.replace('if(sel||pin||field||osd)', 'if(sel||pin||field||!osd||!avlayer)')
# Exercise full4-state cycle during active pause/selection with no choice/reset leakage.
s=s.replace('// Held chord at reset is never a new command.', '''long_key(0);short_key(0); // Enter audio control and pause.
  if(!sel||!paused)$fatal(1,"layer audio pause setup");
  for(i=0;i<4;i++)begin
   k0=0;k1=0;cycles(12);release_all();
   if({osd,avlayer}!==((2'd2-i)&2'b11)||!sel||!paused||choice!=2)$fatal(1,"layer4-state cycle leaked source/pause");
  end
  // Held chord at reset is never a new command.''')
(r/'02_tests/media_controls/tb_v130_controls.sv').write_text(s,encoding='utf-8')
p=r/'02_tests/media_controls/tb_v111_ui_pin.sv';s=p.read_text(encoding='utf-8').replace('v111','v130')
# Check actual syntax port names explicitly later.
s=s.replace('.overlays_enabled(osd)', '.overlays_enabled(osd),.av_enabled(1\'b1)')
(r/'02_tests/media_controls/tb_v130_ui_pin.sv').write_text(s,encoding='utf-8')
s=(r/'02_tests/media_controls/run_v128_media.py').read_text(encoding='utf-8').replace('v128_media_','v130_media_').replace('tb_v126_controls','tb_v130_controls').replace('tb_v111_ui_pin','tb_v130_ui_pin')
(r/'02_tests/media_controls/run_v130_media.py').write_text(s,encoding='utf-8')
# Caption bank/sample regressions retained. Independent pixels use36px rendered size.
s=(r/'02_tests/captions/run_v129_captions.py').read_text(encoding='utf-8').replace('v129','v130').replace('V129','V130')
s=s.replace("fontpath=r/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf'", "fontpath=r/spec['font_path']")
s=s.replace('fontpath),10','fontpath),11')
s=s.replace("assert spec['glyphs'][:197]==baseline['glyphs']", "assert spec['glyphs'][:197]==baseline['glyphs']")
(r/'02_tests/captions/run_v130_captions.py').write_text(s,encoding='utf-8')
for name in ['player','alignment']:
 p=r/f'02_tests/captions/tb_v129_caption_{name}.sv';(p.parent/p.name.replace('v129','v130')).write_text(p.read_text(encoding='utf-8').replace('v129','v130'),encoding='utf-8')
p=r/'02_tests/captions/tb_v129_caption_pixels.sv';s=p.read_text(encoding='utf-8').replace('v129','v130')
s=s.replace('y>=662&&y<708','y>=648&&y<704').replace('y>=672&&y<696','y>=658&&y<694')
s=s.replace('len*32','len*48').replace('(x-startx)%32-4','(x-startx)%48-6').replace('(y-672)/2','(y-658)/3').replace('(x-startx)/32','(x-startx)/48')
s=s.replace('lx<24','lx<36').replace('11-lx/2','11-lx/3').replace('length*32','length*48').replace('yy=672;yy<696','yy=658;yy<694')
s=s.replace('mode==5&&yy==660','mode==5&&yy==640')
s=s.replace('yy>=650','yy>=640')
(r/'02_tests/captions/tb_v130_caption_pixels.sv').write_text(s,encoding='utf-8')
# Actualtop tests independently force baseOSD and AV; no sample-position reset from either.
s=(r/'02_tests/captions/run_v129_caption_top.py').read_text(encoding='utf-8').replace('v129','v130').replace('V129','V130');(r/'02_tests/captions/run_v130_caption_top.py').write_text(s,encoding='utf-8')
s=(r/'02_tests/captions/tb_v129_caption_top.sv').read_text(encoding='utf-8').replace('v129','v130')
s=s.replace('reg picture=0,osd=1;', 'reg picture=0,osd=1,avlayer=1;')
s=s.replace('(osd&&(choice==1||choice==3))','(avlayer&&(choice==1||choice==3))')
s=s.replace('force dut.active_osd_enabled=osd;', 'force dut.active_osd_enabled=osd;force dut.active_av_enabled=avlayer;')
s=s.replace('if(n==36000)osd=0;if(n==44000)osd=1;', 'if(n==36000)avlayer=0;if(n==44000)avlayer=1;\n   if(n==18000)osd=0;if(n==50000)osd=1;')
s=s.replace('if(n==8000)osd=0;if(n==12000)osd=1;', 'if(n==8000)avlayer=0;if(n==12000)avlayer=1;\n   if(n==1000)osd=0;if(n==15000)osd=1;')
s=s.replace('checks=checks+1;', '''if(dut.spectrum.enable!==avlayer||dut.overlay.show_osd!==osd)$fatal(1,"AV/base enable coupling");
  if(dut.help_ui.av_enabled!==avlayer||dut.help_ui.overlays_enabled!==osd)$fatal(1,"UI layer status coupling");
  checks=checks+1;''')
(r/'02_tests/captions/tb_v130_caption_top.sv').write_text(s,encoding='utf-8')
for rel in ['02_tests/audio_visual/run_v129_synth.py','02_tests/audio_visual/run_v129_physical.py']:
 p=r/rel;(p.parent/p.name.replace('v129','v130')).write_text(p.read_text(encoding='utf-8').replace('v129','v130').replace('V129','V130'),encoding='utf-8')
print('V130 independent UI/media/captions/top tests and synth/route entrypoints created')
