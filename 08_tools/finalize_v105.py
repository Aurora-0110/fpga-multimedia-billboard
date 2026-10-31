"""Finalize v105 source-bound centered glass UI/rainbow spectrum diagnostic candidate.
No JTAG/Flash/TF changes. Run ONLY in working copy, never immutable archive.
"""
from pathlib import Path
import argparse,json,hashlib,shutil
r=Path(__file__).resolve().parents[1];a=Path(r'D:\FPGA_Billboard\99_archive\version_history')
ap=argparse.ArgumentParser();ap.add_argument('--synth-attempt',type=int,required=True);ap.add_argument('--physical-attempt',type=int,required=True);ap.add_argument('--bitgen-attempt',type=int,default=1);args=ap.parse_args()
vid='v105_center_glass_art_spectrum_20261026';archive=a/'01_versions'/vid
assert '01_versions' not in r.parts and not archive.exists(),'Never modify archived versions'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
parent=a/'01_versions/v104_chinese_two_column_ui_20261026/01_project'
bit=r/'03_bitstreams/v105_center_glass_art_spectrum_720p.bit'
bg=r/f'05_td/v105_audio_spectrum_bitgen_attempt{args.bitgen_attempt}/attempt.json'
synth=r/f'05_td/v105_audio_visual_synth_attempt{args.synth_attempt}/attempt.json'
phy=r/f'05_td/v105_audio_visual_physical_attempt{args.physical_attempt}/attempt.json'
b=load(bg);sy=load(synth);ph=load(phy)
assert b['completed'] and sy['completed'] and ph['completed'] and sha(bit)==b['bit_sha256'] and min(ph['slack_ns'].values())>=0
for rel,h in sy['source_sha256'].items():assert sha(r/rel)==h,rel
for item in b['reviewed_reports'].values():assert sha(r/item['path'])==item['sha256']
gate=synth.parent/'build/idx_video_Runs/syn_1';dest=r/'04_evidence/v105_final_synthesis_preserved';dest.mkdir(exist_ok=True);kept=[]
for src in sorted(gate.iterdir()):
 if src.is_file():
  dst=dest/src.name
  if dst.exists():assert sha(dst)==sha(src)
  else:shutil.copy2(src,dst)
  assert sha(src)==sha(dst);kept.append({'file':src.name,'bytes':src.stat().st_size,'sha256':sha(dst)})
(dest/'preservation.json').write_text(json.dumps({'reason':'Final source-bound synthesis DB and reports preserved outside excluded build cache','files':kept},indent=2),encoding='utf8')
res=sy['resources'];sl=ph['slack_ns'];before=load(parent/'VERSION_STATUS.json')['resources'];delta={k:res[k]-before[k] for k in ['lut','reg','bram','dsp','pll']}
uip=r/b['reviewed_reports']['hidden_ui']['path'];u=load(uip);assert u['complete'] and u['passed']
vp=r/b['reviewed_reports']['visual']['path'];v=load(vp);assert v['complete'] and v['passed']
from PIL import Image
for src,dst in [(uip.parent/'v105_ui_1.png',r/'03_docs/v105_UI_白底预览.png'),(uip.parent/'v105_ui_2.png',r/'03_docs/v105_UI_透底与编辑预览.png'),(uip.parent/'v105_ui_3.png',r/'03_docs/v105_UI_故障预览.png')]:shutil.copy2(src,dst)
Image.open(vp.parent/'v105_active_spectrum.ppm').save(r/'03_docs/v105_艺术频谱_白底预览.png')
opens=['No v105 JTAG download/display/speaker/endurance/Flash/cold-start acceptance','RGB332+dither SDRAM framebuffer; BMP24 input is not RGB888 frame storage','BMP source dimensions1..2048 each; bilinear stretch to1280x720, not unbounded resolution/aspect-fit','Internal24bit I2S demo tones, no TF WAV/MP3 music playback','16 selected real DFT bins interpolated to64 DISPLAY bars, not64 measured bins/1024-pointFFT','Only glass tint/transparency/rounded corners/highlight/drop-shadow; NO real-time blur or optical refraction','No new continuous waveform renderer in this revision','SDRAM macro initial relocation/internal DQ delays/SiP/PVT/full-address real-device BIST remain open','108 fixed Chinese/ASCII glyphs, not arbitrary Unicode runtime text']
for name in ['README_先看这里.md','VERSION_STATUS.json','README_归档位置.md']:
 p=r/name;dst=r/('INHERITED_v104_'+name)
 if p.is_file() and not dst.exists():shutil.copy2(p,dst)
fresh={'rom_init','hidden_ui','robustness','native_hdmi','legacy_units','visual'}
status={'version':vid,'parent':'v104_chinese_two_column_ui_20261026','date':'2026-10-26','target':'VF-E20NG88 / EG4S20NG88 /24MHz','scope':'centered rounded translucent two-column Chinese UI and64 rainbow thin display bars independently implemented from16 realDFT bands; white background previews only, TF images NOT replaced','new_hardware':False,'fresh_validation':{k:x for k,x in b['reviewed_reports'].items() if k in fresh},'inherited_validation':{k:x for k,x in b['reviewed_reports'].items() if k not in fresh},'resources':res,'delta_from_v104':delta,'slack_ns':sl,'numeric_timing_pass':True,'check_timing_counts':b['check_timing_counts'],'formal_release_approved':False,'new_hardware_acceptance':False,'programmed':False,'flash_modified':False,'tf_modified':False,'bitstream':str(bit),'archive_bitstream':str(archive/'01_project/03_bitstreams'/bit.name),'bit_sha256':sha(bit),'bit_bytes':bit.stat().st_size,'selected_attempts':{'synthesis':args.synth_attempt,'physical':args.physical_attempt,'bitgen':args.bitgen_attempt},'archive_destination':str(archive),'known_open_review':opens,'storage':'All new work/temp/output onD; NO handoffZIP'}
(r/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf8')
table='\n'.join(f'|{label}|{res[k]}/{cap}|{100*res[k]/cap:.2f}%|{delta[k]:+d}|' for k,label,cap in [('lut','LUT',19600),('reg','REG',19600),('bram','BRAM9K',64),('dsp','DSP',29),('pll','PLL',4)])
results='\n'.join('- '+line for report in [u,v] for test in report['tests'] for line in test['results'])
(r/'03_docs/v105_实现与资源说明.md').write_text(f'''# v105 居中玻璃UI与艺术频谱

## 本次效果

- 输出1280×720。UI圆角24px，面板[x288..991,y64..655]，几何中心(640,360)。左列中文功能/右列状态分别按实际字数居中。深色文字、浅蓝白半透明面板、细高光、轻量偏移阴影；编辑/按键高亮及错误红字保持。
- 文字16×16放大2倍、40px行距，14行。Noto CJK SIL OFL1.1，固定108字子集；原字体和许可证在07_reference/fonts/noto_cjk。独立从源字体重栅格化校验全部2048行，最终布线PNL逐位核对文字/字形ROM。
- 频谱x128..1151，64根16px间距/8px细柱及峰值、圆润端部、横向彩虹和轻量纵向高光。仍16真实DFT频带，经帧级四分之一线性插值得到64显示柱；不能宣传成64频带或1024点FFT。
- 静音/无有效新样本不造假律动，收拢淡出；曲目epoch收旧频谱后再淡入。只覆盖柱体/峰值，没有黑色面板、坐标轴或底线；其余RGB逐位透传。
- 白底是RTL演示预览背景，不改TF图片内容、不遮掉广告图。真机仍播放TF四张图片；要实屏白底应之后由用户决定是否替换其中一张BMP，本轮未写卡。
- 轻量仿玻璃，不是实时模糊/折射。不新增连续PCM波形，不移植XilinxIP，不引入CPU，不复制参考音乐/背景/RTL。

## 实现与资源控制

UI标签消息、文字长度、起止坐标采用帧首42拍预计算；数值覆盖和同步文字ROM并行流水，不增加原4拍RGB/坐标/DE/HS/VS/可见标志延迟。面板帧边界快照，空闲约6秒隐藏；编辑/按键/故障常显；自动轮播和音频活动不单独唤醒。原K0/K1手势不变。

频谱原16频带包络保留64拍更新，追加192拍生成64×16显示RAM，帧首共256拍完成，远早于y464首条频谱扫描。同步小BRAM读替代每像素多级大选择器，保持原3拍输出；shift/add alpha不新增像素乘法DSP。RAM不复位、draw_ready屏蔽未初始化内容。

没有更改ADC/SDC/PLL/SDRAM/SPI/BMP/双线性算法/音源/HDMI封包。top仅改版本标识/注释。

|资源|使用/容量|占比|较v104|
|---|---:|---:|---:|
{table}

最终综合attempt{args.synth_attempt}，布局布线attempt{args.physical_attempt}，SWNS {sl['SWNS']:+.3f}ns / STNS {sl['STNS']:.3f}ns / HWNS {sl['HWNS']:+.3f}ns / HTNS {sl['HTNS']:.3f}ns。未改约束掩盖失败。

首轮setup -6.304ns，原因是逐像素行解码->消息->长度->居中坐标->数值覆盖形成长组合链。报告、失败源码留在04_evidence/v105_failed_timing_attempt1_sources与05_td对应attempt。后续把布局提至帧首、覆盖移到同步ROM并行阶段，最终以本版受保护位流记录索引为准。

## 验证结果（不等于实物）

{results}

另新执行3专项鲁棒性、5旧单元、HDMI原生ODDR三相位；系统9组含实际top、注入/替代存储和PLL，不等于真实TF->屏幕整机电气仿真。未改存储/缩放证据逐项哈希复用，不冒称重新执行全部长时端到端仿真。

本次尚未JTAG下载、屏幕/喇叭观察、长稳或Flash验收。仍有RGB332、BMP尺寸1..2048、内部演示音、SDRAM宏/内部延迟/SiP/PVT/全地址实物BIST边界。数值STA通过不能代替正式可靠性签核。

唯一新候选：{bit.name}，{bit.stat().st_size}字节，SHA256 {sha(bit)}。本版只建议SRAM临时测试。
''',encoding='utf8')
(r/'03_docs/v105_上板测试步骤.md').write_text(f'''# v105 上板测试（尚未执行）

1. 保持现有TF四图、接线、HDMI和独立屏幕电源不变，无需买部件/改卡/装驱动。
2. TD下载器选择JTAG/SRAM临时配置，选{bit.name}；不要擦除或写Flash。
3. 开机检查720p画面、圆角面板居中、功能/状态两列各自居中，文字无遮挡/错字；若下方图片不是白色是正常的，本版保留TF内容。
4. 浏览模式约6秒不按键，面板应隐藏；K0短按松开下一张、K1短按切自动/手动，均唤醒UI；自动换图不反复弹面板。
5. 双键短按后全松显隐OSD/Logo/频谱；帮助面板可暂时显示、随后隐藏。双键长按约1秒进入亮度，再长按进入对比度，再长按回浏览；编辑K0减/K1加，参数/高亮/画面同步。
6. 面板隐藏后观察底部彩虹细柱：跟当前演示音变化，声音停止逐渐收拢/消失，切图/曲目旧能量不残留；不要把纯演示音当成已支持TF音乐。
7. 自动运行至少两轮四图，确认缩放、切图、Logo、声音均保持；建议连续20分钟观察黑屏、闪烁和报错，真实音箱试听。
8. 不带电拔TF造故障；如果失败记录位流名、图片/模式/按键顺序、LED和屏幕提示，可回退先前自己确认通过的SRAM位流；Flash旧内容本轮没有变。

请反馈：UI位置/文字/透明度；频谱配色/细柱/静音；轮播/声音稳定。所有结果填入v105_上板结果记录.md。
''',encoding='utf8')
(r/'03_docs/v105_上板结果记录.md').write_text('''# v105 实物结果（待填写，不能继承旧版通过）

- 日期/位流SHA256：
- JTAG/SRAM下载：未执行
- 720p画面与圆角UI/中文两列居中：未测
- 隐藏/唤醒/原K0/K1手势：未测
- 亮度/对比度数值、高亮与实际画面：未测
- 彩虹细柱/透明叠加/静音/切换淡出：未测
- 四图/缩放/转场/Logo/声音：未测
- 连续运行时间与异常：未测
- Flash/冷启动：本次未执行
''',encoding='utf8')
(r/'03_docs/v105_参考与独立实现.md').write_text('''# 艺术参考与独立实现边界

参考评估记录：D:/FPGA_Billboard/99_archive/version_history/03_reference_records/music_spectrum_style_review_20261026。
用户视频BV1FDfbYBEGQ与作者Music-Spectrum只作通用视觉参考；本版没有搬入作者RTL、音频、背景或XilinxFFT/CPU代码。自身16选频DFT/纯RTLTF/BMP/SDRAM链路保留，不宣称与原视频全部效果完全一致。
本版仅实现彩虹细柱、峰值、圆润端部、半透明叠加；连续PCM波形、TF音乐解码/播放仍是后续工作。
中文字形继续用本工程已固定的NotoCJK字体，原始OFL许可证必须保留。
''',encoding='utf8')
(r/'README_先看这里.md').write_text(f'''# v105 居中圆角玻璃UI + 艺术彩虹频谱

VF-E20NG88 / EG4S20NG88 /24MHz，父v104。1280×720中文两列居中、半透明圆角面板；16真实DFT频带插值为64根彩虹细柱，透明背景/静音淡出/切换收拢。白底仅预览，不替换TF广告图。

- 新候选：03_bitstreams/{bit.name}
- SHA256：{sha(bit)}
- 上板步骤/结果空表：03_docs/v105_上板测试步骤.md、v105_上板结果记录.md
- 实现/资源/边界：03_docs/v105_实现与资源说明.md
- RTL预览：03_docs/v105_UI_白底预览.png、v105_UI_透底与编辑预览.png、v105_艺术频谱_白底预览.png

本版仿真/综合/数值STA/受保护位流已通过，尚未实物验收；不把旧版通过冒称为本版。整机LUT {res['lut']}/19600，REG {res['reg']}/19600，BRAM9K {res['bram']}/64，DSP {res['dsp']}/29，PLL {res['pll']}/4。

统一验收入口08_tools/run_acceptance.py默认只读哈希检查；在工作副本可用--stage sim-all/synth/physical/rom-init/bitgen。冻结归档不可编译。仿玻璃无实时模糊/折射、64柱非64频带，音源仍内部I2S演示音、TF音乐和连续波形未做，RGB332/SDRAM可靠性边界保留。

只建议SRAM临时测试，不改TF/接线/Flash。所有新增源码/输出/临时文件在D盘；无需交接ZIP。
归档：{archive}。
''',encoding='utf8')
(r/'README_归档位置.md').write_text(f'冻结归档：`{archive}`。不要在快照中修改/仿真/编译；先复制到D盘工作目录。\n',encoding='utf8')
files=set();changes=[]
for folder in ['01_project','02_tests','08_tools']:
 for p in sorted((r/folder).rglob('*')):
  if not p.is_file() or 'build' in p.relative_to(r).parts or p.suffix not in {'.v','.vh','.sv','.py','.tcl','.adc','.sdc','.ps1','.prj'}:continue
  files.add(p);rel=p.relative_to(r);old=parent/rel
  if not old.is_file() or sha(old)!=sha(p):changes.append({'file':rel.as_posix(),'change':'modified' if old.is_file() else 'added','sha256':sha(p),'parent_sha256':sha(old) if old.is_file() else None})
(r/'03_docs/v105_SOURCE_CHANGES.json').write_text(json.dumps({'parent_archive':str(parent),'changes':changes},ensure_ascii=False,indent=2),encoding='utf8')
files.update([r/'VERSION_STATUS.json',r/'README_先看这里.md',r/'README_归档位置.md',bit])
folders=[r/'03_docs',r/'07_reference/fonts/noto_cjk',dest,bg.parent,synth.parent,phy.parent,uip.parent,*[(r/x['path']).parent for x in b['reviewed_reports'].values()]]
# Failed attempts are explicit evidence, not silently replaced.
folders+=list((r/'05_td').glob('v105_*'))+list((r/'04_evidence').glob('v105_failed*'))
for folder in folders:
 for p in folder.rglob('*'):
  if p.is_file() and 'build' not in p.relative_to(r).parts and p.suffix not in {'.vvp','.vcd','.pyc'}:files.add(p)
manifest={'version':vid,'scope':'Offline identity of sources/evidence/reports/bit only; no hardware acceptance','hardware_test':False,'files_sha256':{p.relative_to(r).as_posix():sha(p) for p in sorted(files)}}
(r/'04_evidence/v105_release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'version':vid,'resources':res,'delta_from_v104':delta,'slack_ns':sl,'preserved_synthesis_files':len(kept),'manifest_files':len(files),'bit_sha256':sha(bit),'archive':str(archive)},ensure_ascii=False,indent=2))
