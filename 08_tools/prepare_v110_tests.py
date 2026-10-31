from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=r/'02_tests/media_controls/tb_v107_controls.sv';s=p.read_text('utf-8')
a=s.index('  short_key(1);short_key(0);');b=s.index('  long_key(1);',a)
s=s[:a]+'''  short_key(1);short_key(0);if(!sel||!paused||choice!=1||nc!=1)$fatal(1,"short K0 pause");
  short_key(0);if(paused||!sel||nc!=1)$fatal(1,"short K0 resume");
  short_key(0);short_key(1);if(paused||choice!=2||mc!=1)$fatal(1,"source selection must start new source");
  short_key(0);long_key(0);if(sel||!paused||choice!=2||nc!=1)$fatal(1,"long K0 exit must retain paused position");
  long_key(0);short_key(0);if(!sel||paused)$fatal(1,"reenter resume");
  long_key(0);if(sel||choice!=2||nc!=1)$fatal(1,"long K0 exit/repeated hold");
'''+s[b:]
s=s.replace('if(nt||mt||sel||pin||field||choice||br||gain!=4||!osd)', 'if(nt||mt||sel||pin||field||choice||paused||br||gain!=4||!osd)').replace('PASS v107','PASS v110')
p.write_text(s,encoding='utf-8')
# Playback sequence tests, with exact random stereo frames as the oracle.
p=r/'02_tests/wav/tb_wav_playback.sv';s=p.read_text('utf-8').replace('reg rst=0;','reg paused=0;reg rst=0;').replace(".paused(1'b0)",'.paused(paused)')
s=s.replace('if(mode==1)begin','''if(mode==4)begin
   wait(n>=125);@(negedge pix);paused=1;repeat(400000)@(negedge pix);
   if(!dut.full)$fatal(1,"pause did not exercise FIFO backpressure");
   paused=0;wait(n>=1500);@(negedge pix);paused=1;repeat(4000)@(negedge pix);paused=0;
  end
  if(mode==5)begin
   wait(n>=1);@(negedge pix);paused=1;repeat(400000)@(negedge pix);paused=0;
  end
  if(mode==7)begin
   wait(n>=nm-1);@(negedge pix);paused=1;repeat(40000)@(negedge pix);paused=0;
  end
  if(mode==1||mode==6)begin''')
s=s.replace('wait(n>=700);@(negedge pix);choice=2;', 'wait(n>=700);@(negedge pix);if(mode==6)begin paused=1;repeat(40000)@(negedge pix);end\n   choice=2;paused=0;')
s=s.replace('if(mode>=2&&err!=0)', 'if((mode==2||mode==3)&&err!=0)').replace('if(mode>=2)$fatal', 'if(mode==2||mode==3)$fatal').replace('(mode==1?2:1)','((mode==1||mode==6)?2:1)')
s=s.replace('integer n=0,epochs=0,','integer pause_samples=0,pause_n=-1;\n integer n=0,epochs=0,')
s=s.replace('   // Accumulator runs', '''   if(paused)begin
    if({l,rr}!==48'd0)$fatal(1,"nonzero PCM during pause");
    if(pause_n>=0&&n!=pause_n)$fatal(1,"pause consumed sample index");
    pause_n=n;pause_samples=pause_samples+1;
   end else pause_n=-1;
   // Accumulator runs''')
s=s.replace('   $display("PASS playback mode=', '''   if(mode>=4&&pause_samples<20)$fatal(1,"missing pause evidence");
   $display("PASS playback mode=''')
p.write_text(s,encoding='utf-8')
p=r/'02_tests/wav/run_v110_playback_tests.py';s=p.read_text('utf-8').replace('else range(4)','else range(8)');s=s.replace("'scope':'virtual sector", "'scope':'eight cases including midstream/FIFO-full, first sample, switch-while-paused and near-EOF pause; virtual sector");p.write_text(s,encoding='utf-8')
# UI oracle now checks SOURCE in the left column and real playback STATUS in
# the right one. It is independent of message IDs in the synthesizable RTL.
p=r/'02_tests/ui/run_v110_ui.py';s=p.read_text('utf-8').replace('pin=False)', 'pin=False,status=0)')
s=s.replace('# Independent low-picture-gate fifth raster vector.', '''for status in range(1,5):
 for choose in range(3):
  c=base();c.update(choice=choose,status=status,select=True);cases.append(c)
# Independent low-picture-gate fifth raster vector.''')
s=s.replace("states[11]='退出选择' if c['select'] else states[11]", "states[11]=('继续播放' if c['status']==1 else '暂停播放') if c['select'] else states[11]")
s=s.replace("case_labels=list(labels);case_labels[9]='音频选择' if c['select'] else case_labels[9]", "case_labels=list(labels);case_labels[9]=['跟随图片','音乐文件','广告语音'][c['choice']]\n states[9]=['播放中' if c['choice']!=0 else ('正在输出' if c['audio'] else '暂无声音'),'已暂停','预缓冲','已结束','音频故障'][c['status']]")
s=s.replace("|(c['pin']<<34)", "|(c['pin']<<34)|(c['status']<<35)")
p.write_text(s,encoding='utf-8')
p=r/'02_tests/ui/tb_v108_ui.sv';s=p.read_text('utf-8').replace('reg select_audio=0,pin=0;', 'reg [2:0] status=0;reg select_audio=0,pin=0;').replace(".audio_status(3'd0)",'.audio_status(status)').replace('pin=v[34];','pin=v[34];status=v[37:35];')
# Every text-vector load is an independent render, not a UI gesture sequence.
s=s.replace('@(negedge clk);keys=0;cycles(3);v=vectors[which];', '@(negedge clk);rst=0;keys=0;cycles(3);rst=1;v=vectors[which];')
s=s.replace('@(negedge clk);br=v[7:0];', '@(negedge clk);br=v[7:0];')
# Do not fire manual toggle tokens as part of static text vectors.
s=s.replace('pin=v[34];status=v[37:35];','pin=0;status=v[37:35];')
# Dynamic visibility tests are separately verified with the actual controls.
a=s.index('  // UI is temporarily visible');b=s.find('  $display(',a) if a!=-1 else -1
if a!=-1 and b!=-1:s=s[:a]+s[b:]
p.write_text(s,encoding='utf-8')
print('v110 UI oracle + pause/control regressions updated')
