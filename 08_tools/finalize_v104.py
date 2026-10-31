"""Finalize v104 Chinese two-column UI after source-bound simulation/STA/bitgen.
Does not program hardware, write Flash/TF, or modify any archived version.
"""
from pathlib import Path
import argparse,json,hashlib,shutil
r=Path(__file__).resolve().parents[1];a=Path(r'D:\FPGA_Billboard\99_archive\version_history')
ap=argparse.ArgumentParser();ap.add_argument('--synth-attempt',type=int,default=1);ap.add_argument('--physical-attempt',type=int,default=1);ap.add_argument('--bitgen-attempt',type=int,default=1);args=ap.parse_args()
vid='v104_chinese_two_column_ui_20261026';archive=a/'01_versions'/vid;assert not archive.exists(),'Immutable archive already exists'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
parent=a/'01_versions/v103_acceptance_robustness_20261026/01_project'
bit=r/'03_bitstreams/v104_chinese_two_column_ui_720p.bit'
bg=r/f'05_td/v104_audio_spectrum_bitgen_attempt{args.bitgen_attempt}/attempt.json'
synth=r/f'05_td/v104_audio_visual_synth_attempt{args.synth_attempt}/attempt.json';phy=r/f'05_td/v104_audio_visual_physical_attempt{args.physical_attempt}/attempt.json'
b=load(bg);sy=load(synth);ph=load(phy)
assert b['completed'] and sy['completed'] and ph['completed'] and sha(bit)==b['bit_sha256'] and min(ph['slack_ns'].values())>=0
for rel,h in sy['source_sha256'].items():assert sha(r/rel)==h,rel
for item in b['reviewed_reports'].values():assert sha(r/item['path'])==item['sha256']
gate=synth.parent/'build/idx_video_Runs/syn_1';dest=r/'04_evidence/v104_final_synthesis_preserved';dest.mkdir(exist_ok=True);kept=[]
for src in sorted(gate.iterdir()):
 if src.is_file():
  dst=dest/src.name
  if dst.exists():assert sha(dst)==sha(src)
  else:shutil.copy2(src,dst)
  assert sha(src)==sha(dst);kept.append({'file':src.name,'bytes':src.stat().st_size,'sha256':sha(dst)})
(dest/'preservation.json').write_text(json.dumps({'reason':'Final source-bound synthesis DB and reports outside rebuildable build directory','files':kept},indent=2),encoding='utf8')
res=sy['resources'];sl=ph['slack_ns'];before=load(parent/'VERSION_STATUS.json')['resources'];delta={k:res[k]-before[k] for k in ['lut','reg','bram','dsp','pll']}
ui=r/b['reviewed_reports']['hidden_ui']['path'];u=load(ui);assert u['complete'] and u['passed']
preview=r/'03_docs/v104_UI_中文两列_仿真预览.png';shutil.copy2(ui.parent/'v104_ui_1.png',preview)
opens=['No v104 JTAG download, display/speaker observation, cold-start or endurance result','RGB332+dither SDRAM framebuffer; BMP24 input is not RGB888 frame storage','Source dimensions 1..2048 each; bilinear stretch to1280x720, no unlimited-size/aspect-fit claim','Internal24bit I2S demo tone; no TF WAV/MP3 music playback','16 selected DFT bins; not a calibrated full-band FFT','SDRAM macro relocation/SiP/PVT/internal DQ delays/full-address real-device BIST remain open','UI has108 precompiled Chinese/ASCII glyphs and fixed text; not an arbitrary Unicode text loader']
for name in ['README_先看这里.md','VERSION_STATUS.json','README_归档位置.md']:
 old=r/name
 if old.is_file() and not (r/('INHERITED_v103_'+name)).exists():shutil.copy2(old,r/('INHERITED_v103_'+name))
status={'version':vid,'parent':'v103_acceptance_robustness_20261026','date':'2026-10-26','target':'VF-E20NG88 / EG4S20NG88 /24MHz','scope':'Chinese function/status two-column translucent UI only; embedded text/font block ROMs; original timing latency/controls/hide behavior preserved','new_hardware':False,'fresh_validation':{k:v for k,v in b['reviewed_reports'].items() if k in {'rom_init','hidden_ui','robustness','native_hdmi','legacy_units','visual'}},'inherited_validation':{k:v for k,v in b['reviewed_reports'].items() if k not in {'rom_init','hidden_ui','robustness','native_hdmi','legacy_units','visual'}},'resources':res,'delta_from_v103':delta,'slack_ns':sl,'numeric_timing_pass':True,'check_timing_counts':b['check_timing_counts'],'formal_release_approved':False,'new_hardware_acceptance':False,'programmed':False,'flash_modified':False,'tf_modified':False,'bitstream':str(bit),'bit_sha256':sha(bit),'bit_bytes':bit.stat().st_size,'selected_attempts':{'synthesis':args.synth_attempt,'physical':args.physical_attempt,'bitgen':args.bitgen_attempt},'archive_destination':str(archive),'known_open_review':opens,'storage':'New work/temp/output entirely on D; no handoff ZIP requested/created'}
(r/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf8')
resources='\n'.join(f'|{label}|{res[k]}/{cap}|{100*res[k]/cap:.2f}%|{delta[k]:+d}|' for k,label,cap in [('lut','LUT',19600),('reg','REG',19600),('bram','BRAM9K',64),('dsp','DSP',29),('pll','PLL',4)])
(r/'03_docs/v104_中文两列UI与资源.md').write_text(f'''# v104 中文两列 UI

## 1. 本次只改什么

左侧半透明面板：功能列 + 状态列，适配1280×720。面板范围x48..655/y64..647；16×16字形放大2倍，40px行距。标题及表头后依次显示：播放模式、当前图片、资源读取、调节项目、亮度、对比度、画面叠加、音频输出、按键状态、K0功能、K1功能、双键操作。

- 状态、标签中文；K0/K1/V104/数字/百分号/十六进制错误码保留原标识。
- 编辑亮度/对比度高亮对应行；按键按下行高亮；读取错误用暖红色。
- 默认空闲360视频帧约6秒隐藏；帧边界唤醒/提交状态。编辑中、按住按键、TF故障持续显示。自动轮播/音频活动不单独唤醒。
- 装饰OSD/Logo/频谱关闭不妨碍帮助面板再次唤醒；历史/当前故障诊断仍沿用v103不可隐藏保护。
- 音频状态表示数字PCM活动，不能当成外接喇叭实际发声的测量。
- 没有改变原K0/K1短按/组合长按功能，没有新增外接按键，没有更改ADC/SDC/PLL/SDRAM/SPI/HDMI或音频处理逻辑。
- 继续保持4级像素/坐标/DE/HS/VS/picture_visible延迟，面板不会把picture_visible从0抬成1。

## 2. 当前证据，不混同实物通过

{u['scope']}

UI测试结果：
{chr(10).join('- '+line for x in u['tests'] for line in x['results'])}

同时新执行TF重试/诊断/PCM长序列3组、legacy5组、系统/视觉/音频9组、原生HDMI三相位回归。继承v101/v097未改存储/缩放证据经过逐项源哈希核对，不称全部重新执行。真实top测试仍使用替代PLL/受控FIFO；原生HDMI验证不代表PCB电气测试。

字体准备曾发现15字号的“声”超出16px高度，已改14字号居中，全部108字形不裁切。初轮UI测试通过后复查第五幅参考图有局部DUT文本依赖，已保存初轮测试源并改成完全独立Python向量，整套重跑；最终以bitgen索引内最新UI报告为准。

## 3. 最终整机资源

|资源|使用/容量|占比|较v103|
|---|---:|---:|---:|
{resources}

增加5块BRAM9K：4块字形ROM、1块文字表ROM。已从最终布线PNL逐位核对：文字表1024字节和字形2048×16位初始化全部与独立参考一致；未因eram_init=off而丢失ROM常量。这不是位流回读或硬件验收。没有新增DSP/PLL；不是把中文字形映射成大规模寄存器阵列。

## 4. 最终数值时序

综合attempt{args.synth_attempt}；物理attempt{args.physical_attempt}。SWNS {sl['SWNS']:+.3f}ns / STNS {sl['STNS']:.3f}ns / HWNS {sl['HWNS']:+.3f}ns / HTNS {sl['HTNS']:.3f}ns。

数值STA通过，不等于正式可靠性签核。PHY-7002、内部延迟与SiP/PVT等开放项没有因为UI改版而消失。

## 5. 位流与测试

唯一新候选：`03_bitstreams/{bit.name}`，{bit.stat().st_size}字节，SHA256 `{sha(bit)}`。仅建议JTAG/SRAM临时下载，暂不固化Flash。保持原TF四图和接线。详见上板步骤和结果空表。

预览图是RTL仿真输出，背景是人为生成测试图，不是实屏拍照或TF图像端到端验收。
''',encoding='utf8')
(r/'03_docs/v104_上板测试步骤.md').write_text('''# v104 上板测试：中文功能/状态两列

状态：代码/仿真/综合/数值时序/位流已就绪，尚未进行本版实物验证。

1. 保持原TF四张图片、HDMI/音箱/下载器/供电及所有接线不变；无需新增按钮或复制文件到TF。
2. TD下载器只做JTAG/SRAM临时配置，选择03_bitstreams/v104_chinese_two_column_ui_720p.bit；不要擦除/写入Flash。
3. 显示后检查左侧中文面板：表头“功能｜状态”，播放模式、图片编号、读取状态、亮度/对比度等文字没有缺字、错行或出界。
4. VIEW无按键约6秒面板应隐藏，自动切图不应反复唤醒。单击K0（松开生效）应下一张并唤醒，K1应切换自动/手动。
5. 双键短按后全部松开，应继续显隐装饰OSD/Logo/频谱；帮助面板会暂时显示状态，约6秒后隐藏。这不是按短按后整个画面UI立即全消失。
6. 双键长按约1秒，看到进入亮度编辑后松开；“调节项目”显示“调节亮度”，亮度行高亮。K0减/K1加：-64..+64、步长16；数值和实际画面一致，编辑期间不自动隐藏。
7. 再长按双键并松开进入对比度；对应行高亮，K0减/K1加：50..150%、步长25%；再长按回浏览模式。不要误把亮度减键当成切图。
8. 检查“按键状态”单键/双键按下及松开显示；“K0功能/K1功能”随浏览/亮度/对比度模式变化。
9. 跑两轮四图，确认原转场、音画门控、频谱、Logo没有因UI出现/隐藏而错位或黑屏；建议连续AUTO运行20分钟，真实音箱试听。
10. 不要为了造错误带电拔TF；本版错误中文与历史故障不可隐藏已做仿真，但真实异常恢复仍需另立安全测试。
11. 如异常，记录图片/模式/按键步骤/LED/屏幕提示；必要时重新临时下载之前自己确认正常的位流。无需改动旧Flash内容。

请反馈：汉字清晰否、两列是否对齐、参数值/高亮正确否、隐藏/唤醒正常否、原轮播/声音是否保持。
''',encoding='utf8')
(r/'03_docs/v104_上板结果记录.md').write_text('''# v104 实物结果记录

当前状态：未上板。以下均待用户填写，不继承旧版本的通过结果。

- 日期/位流SHA256：
- 1280×720显示及中文两列布局：未测
- 汉字无缺字/裁切/重叠：未测
- 亮度/对比度数值和选中行：未测
- 单键/双键状态与模式对应：未测
- 空闲约6秒隐藏、按键唤醒：未测
- 原四图/缩放/转场/Logo/频谱/音频：未测
- 连续运行时长与问题：未测
- JTAG实际下载：未执行
- Flash固化/冷启动：未执行
''',encoding='utf8')
font_meta=load(r/'07_reference/fonts/noto_cjk/SOURCE.json')
(r/'03_docs/v104_字库来源与重建.md').write_text(f'''# 中文字库来源

Noto Sans CJK SC Medium，SIL Open Font License 1.1。源仓库：{font_meta['repository']}，固定提交：{font_meta['commit']}。

源字体、原始LICENSE、下载来源与SHA256保存在07_reference/fonts/noto_cjk。没有使用Windows系统字体，也不要求评委电脑安装字体。

运行08_tools/generate_v104_ui_font.py可用Pillow重新生成108个固定中英文字形、64×16文字表及ROM初始化头文件。16×16单色，14字号居中，112阈值，2倍显示；生成文件已嵌入Verilog，TD编译不必运行Python或访问网络。

需要新词语时应重新生成子集并跑UI测试/综合，不能声称支持任意Unicode字符。保留原字体版权与OFL声明；字体许可证不自动适用于整个工程。
''',encoding='utf8')
(r/'README_先看这里.md').write_text(f'''# v104 中文两列控制面板

目标VF-E20NG88 / EG4S20NG88 /24MHz。父版v103。功能列+状态列，全部功能标签中文，亮度/对比度编辑高亮、按键实时状态、空闲约6秒隐藏/唤醒，原按键手势不变。

- 上板步骤：03_docs/v104_上板测试步骤.md
- 详细实现/资源/边界：03_docs/v104_中文两列UI与资源.md
- 实物结果空表：03_docs/v104_上板结果记录.md
- 仿真布局：03_docs/v104_UI_中文两列_仿真预览.png
- 唯一新候选：03_bitstreams/{bit.name}
- SHA256：{sha(bit)}

仿真、综合、布局布线/数值STA与受保护位流生成通过；本版尚未实物下载/屏幕/听音/Flash/正式可靠性验收。旧bit仅历史留存，不是本版新候选。

整机LUT {res['lut']}/19600，REG {res['reg']}/19600，BRAM9K {res['bram']}/64，DSP {res['dsp']}/29，PLL {res['pll']}/4。相对v103 +{delta['lut']}LUT/+{delta['reg']}REG/+{delta['bram']}BRAM9K。

保持原TF与接线；只建议JTAG/SRAM临时下载，不改Flash。RGB332/内部I2S演示音/宏与PVT边界保留。完整记录在VERSION_STATUS.json，统一入口08_tools/run_acceptance.py默认只读核对，本版新增--stage ui及--stage rom-init，bitgen阶段会先核查ROM初始化。

归档：{archive}。所有新代码/输出/临时文件在D盘，不创建交接ZIP。
''',encoding='utf8')
(r/'README_归档位置.md').write_text(f'冻结归档：`{archive}`。不要在快照中修改或编译。\n',encoding='utf8')
changes=[];files=set()
for folder in ['01_project','02_tests','08_tools']:
 for p in sorted((r/folder).rglob('*')):
  if not p.is_file() or 'build' in p.relative_to(r).parts or p.suffix not in {'.v','.vh','.sv','.py','.tcl','.adc','.sdc','.ps1','.prj'}:continue
  files.add(p);rel=p.relative_to(r);old=parent/rel
  if not old.is_file() or sha(old)!=sha(p):changes.append({'file':rel.as_posix(),'change':'modified' if old.is_file() else 'added','sha256':sha(p),'parent_sha256':sha(old) if old.is_file() else None})
(r/'03_docs/v104_SOURCE_CHANGES.json').write_text(json.dumps({'parent_archive':str(parent),'changes':changes},ensure_ascii=False,indent=2),encoding='utf8')
for name in ['VERSION_STATUS.json','README_先看这里.md','README_归档位置.md']:files.add(r/name)
files.add(bit)
for folder in [r/'03_docs',r/'07_reference/fonts/noto_cjk',dest,bg.parent,synth.parent,phy.parent,ui.parent,*[(r/x['path']).parent for x in b['reviewed_reports'].values()]]:
 for p in folder.rglob('*'):
  if p.is_file() and 'build' not in p.relative_to(r).parts and p.suffix not in {'.vvp','.vcd','.pyc'}:files.add(p)
manifest={'version':vid,'scope':'Offline identity of sources/evidence/reports/bit only; no hardware acceptance','hardware_test':False,'files_sha256':{p.relative_to(r).as_posix():sha(p) for p in sorted(files)}}
(r/'04_evidence/v104_release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'version':vid,'resources':res,'delta_from_v103':delta,'slack_ns':sl,'preserved_synthesis_files':len(kept),'manifest_files':len(files),'bit_sha256':sha(bit),'archive':str(archive)},ensure_ascii=False,indent=2))
