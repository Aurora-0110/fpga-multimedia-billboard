"""v108: independent Chinese text/pixel oracle, original key gestures and uptime.
No programming, Flash, TF writes or modifications to immutable archives.
"""
from pathlib import Path
import os,json,hashlib,datetime,subprocess,time
from PIL import Image,ImageDraw,ImageFont
r=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=r/'01_project/rtl'
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','');tmp=r/'00_tmp';tmp.mkdir(exist_ok=True);env.update(TEMP=str(tmp),TMP=str(tmp),TMPDIR=str(tmp),PYTHONDONTWRITEBYTECODE='1')
out=r/'04_evidence'/('v122_ui_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
spec=json.loads((r/'03_docs/v119_ui_font_spec.json').read_text(encoding='utf8'));ids=spec['glyph_ids']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
font_path=r/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf'
assert sha(font_path)==spec['font_sha256'];font=ImageFont.truetype(str(font_path),14)
# Re-render every font row from the pinned source font; do not parse RTL initializers.
font_rows=[]
for i in range(128):
 canvas=Image.new('L',(16,16));ch=spec['glyphs'][i] if i<len(spec['glyphs']) else ' '
 if ch!=' ':
  box=font.getbbox(ch);w=box[2]-box[0];h=box[3]-box[1]
  ImageDraw.Draw(canvas).text(((16-w)//2-box[0],(16-h)//2-box[1]),ch,font=font,fill=255)
 for y in range(16):font_rows.append(sum(2**(15-x) for x in range(16) if canvas.getpixel((x,y))>=112))
assert any(font_rows[ids['功']*16:ids['功']*16+16])
assert font_rows[ids['功']*16:ids['功']*16+16]!=font_rows[ids['状']*16:ids['状']*16+16]
(out/'font.hex').write_text(''.join(f'{v:04x}\n' for v in font_rows),encoding='ascii')
def base():return dict(br=0,gain=4,field=0,mode=True,osd=True,image=0,loading=False,failed=False,error=0,audio=True,pv=True,keys=0,select=False,choice=0,pin=False,status=0,aerror=0,paused=False)
cases=[]
for br in range(-64,65,16):
 for gain in range(2,7):
  for field in range(4):
   c=base();c.update(br=br,gain=gain,field=field,image=field);cases.append(c)
for error in range(256):
 c=base();c.update(failed=True,error=error,loading=bool(error&1));cases.append(c)
for values in [dict(keys=1),dict(keys=2),dict(keys=3),dict(loading=True,pv=False,audio=False),dict(pv=False,audio=False),dict(mode=False,osd=False),dict(image=3),dict(error=0xE0,failed=False),dict(field=3),dict(gain=0),dict(gain=1),dict(gain=7),dict(br=7)]:
 c=base();c.update(values);cases.append(c)
for choose in range(4):
 for select in [False,True]:
  for pin in [False,True]:
   c=base();c.update(choice=choose,select=select,pin=pin);cases.append(c)
for status in range(1,5):
 for choose in range(4):
  c=base();c.update(choice=choose,status=status,select=True,paused=status==1);cases.append(c)
# Audio faults must not poison the image row or K0 picture action.
for aerror in range(1,256):
 c=base();c.update(aerror=aerror,choice=1);cases.append(c)
for select in [False,True]:
 for status in [0,1,2,3,4]:
  for error in [0,0xE0]:
   c=base();c.update(aerror=0xA3,choice=2,select=select,status=status,error=error,paused=status==1);cases.append(c)
# Independent low-picture-gate fifth raster vector.
c=base();c.update(pv=False,keys=1);cases.append(c)
# Final three known cases form the actual RTL-rendered preview/reference rasters.
for values in [dict(),dict(br=32,gain=5,field=1,mode=False,osd=False,image=2,keys=1),dict(aerror=0xA3,choice=2,audio=False)]:
 c=base();c.update(values);cases.append(c)
assert len(cases)<=1024
labels=['系统控制','功能','播放模式','当前图片','资源读取','调节项目','亮度','对比度','画面叠加','音频输出','按键状态','K0功能','K1功能','双键操作']
text=[];vectors=[];descriptions=[]
for c in cases:
 failed=c['failed'] or c['error']!=0
 mag=abs(c['br']);br=f"{c['br']:+03d}" if mag in [0,16,32,48,64] else ('-' if c['br']<0 else '+')+'??'
 states=['V119','状态','自动轮播' if c['mode'] else '手动切换',f"第{c['image']+1}/4张",f"故障 {c['error']:02X}" if failed else ('读取中' if c['loading'] else ('已就绪' if c['pv'] else '等待中')),['浏览图片','调节亮度','调节对比度','参数异常'][c['field']],br,f"{c['gain']*25:03d}%" if 2<=c['gain']<=6 else '参数异常','已开启' if c['osd'] else '已隐藏',['跟随图片','音乐文件','广告语音','扩展音频'][c['choice']],['未按下','K0按下','K1按下','双键按下'][c['keys']],['错误重试' if failed else '下一张','亮度减','对比度减','参数异常'][c['field']],['自动或手动','亮度加','对比度加','参数异常'][c['field']],'短按显隐 长按调参']
 states[11]=('继续播放' if c['paused'] else '暂停播放') if c['select'] else states[11]
 states[12]='切换音频' if c['select'] else states[12]
 case_labels=list(labels);case_labels[9]=['跟随图片','音乐文件','广告语音','扩展音频'][c['choice']]
 states[9]=['播放中' if c['choice']!=0 else ('正在输出' if c['audio'] else '暂无声音'),'已暂停','预缓冲','已结束',f"音频故障 {c['aerror']:02X}"][4 if c['aerror'] else c['status']]
 rows=[]
 for label,state in zip(case_labels,states):
  assert len(label)<=6 and len(state)<=11
  line=label.ljust(7)+state.ljust(11);assert len(line)==18
  text.extend(ids[ch] for ch in line);rows.append(line)
 v=(c['br']&255)|(c['gain']<<8)|(c['field']<<11)|(c['mode']<<13)|(c['osd']<<14)|(c['image']<<15)|(c['loading']<<17)|(c['failed']<<18)|(c['error']<<19)|(c['audio']<<27)|(c['pv']<<28)|(c['keys']<<29)|(c['select']<<31)|(c['choice']<<32)|(c['pin']<<34)|(c['status']<<35)|(c['aerror']<<38)|(c['paused']<<46)
 vectors.append(v);descriptions.append({'parameters':c,'expected_rows':rows})
(out/'vectors.hex').write_text(''.join(f'{v:016x}\n' for v in vectors),encoding='ascii')
(out/'text.hex').write_text(''.join(f'{v:02x}\n' for v in text),encoding='ascii')
(out/'text_spec.json').write_text(json.dumps(descriptions,ensure_ascii=False,indent=2),encoding='utf8')
jobs=[('uptime','tb_v102_uptime',[t/'tb_v102_uptime.sv',rtl/'visual/osd_layers_visual.v',rtl/'visual/official_logo_compact_sync.v'],[]),('controls','tb_v089_controls',[r/'02_tests/scale_pipeline/tb_v089_controls.sv',rtl/'common/picture_controls_osd.v'],[]),('ui','tb_v119_ui',[t/'tb_v119_ui.sv',rtl/'visual/media_ui_overlay.v'],[f'+VECTORS={out}/vectors.hex',f'+TEXT={out}/text.hex',f'+FONT={out}/font.hex',f'+CASES={len(cases)}',f'+PREVIEW={out}/v119_ui'])]
records=[]
for name,top,src,plus in jobs:
 start=time.monotonic();exe=out/(name+'.vvp');cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s',top,'-o',str(exe),*map(str,src)]
 c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=60);log=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  try:
   v=subprocess.run([str(b/'vvp.exe'),str(exe),*plus],env=env,capture_output=True,text=True,timeout=900);log+=v.stdout+v.stderr;rc=v.returncode
  except subprocess.TimeoutExpired:log+='\nTIMEOUT\n'
 (out/(name+'.log')).write_text(log,encoding='utf8')
 inputs=src+[rtl/'video/osd_font.vh']
 if name=='ui':inputs += [rtl/'visual'/x for x in ['media_ui_zh_glyph_ids.vh','media_ui_zh_font_init.vh','media_ui_zh_text_init.vh']]+[font_path,r/'03_docs/v119_ui_font_spec.json',Path(__file__)]
 rec={'name':name,'passed':c.returncode==0 and rc==0 and 'PASS' in log and 'FATAL' not in log,'compile_returncode':c.returncode,'run_returncode':rc,'elapsed_seconds':round(time.monotonic()-start,3),'source_sha256':{p.relative_to(r).as_posix():sha(p) for p in inputs},'results':[x for x in log.splitlines() if x.startswith(('PASS','FATAL'))]};records.append(rec)
 summary={'passed':len(records)==len(jobs) and all(x['passed'] for x in records),'scope':f'{len(cases)} independent Chinese text vectors / full embedded font oracle / five full720p UI rasters including hidden and picture-gate-low / original gestures / uptime; simulation only, not hardware acceptance','complete':len(records)==len(jobs),'tests':records}
 (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in rec.items() if k!='source_sha256'},ensure_ascii=False),flush=True)
 if not rec['passed']:print(log[-6000:],flush=True);raise SystemExit(1)
for p in out.glob('*.ppm'):Image.open(p).save(p.with_suffix('.png'))
print(out,flush=True)
