"""Finalize v099 docs only after hash-bound simulations and guarded bitgen."""
from pathlib import Path
import json,hashlib
from PIL import Image
r=Path(__file__).resolve().parents[1]
parent=Path(r'D:\FPGA_Billboard\work\v098_audio_spectrum_resource_opt_20261025')
archive=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/r.name
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
syn=load(r/'05_td/v099_audio_visual_synth_attempt3/attempt.json')
phy=load(r/'05_td/v099_audio_visual_physical_attempt3/attempt.json')
bg=load(r/'05_td/v099_audio_spectrum_bitgen_attempt1/attempt.json')
assert syn['completed'] and phy['completed'] and bg['completed']
vp=r/bg['reviewed_reports']['visual']['path'];sim=load(vp)
assert sim['passed'] and len(sim['tests'])==8 and all(x['passed'] and x['sources_unchanged_during_run'] for x in sim['tests'])
bit=r/'03_bitstreams/v099_audio_spectrum_720p.bit';assert sha(bit)==bg['bit_sha256']
res=syn['resources'];base=load(parent/'VERSION_STATUS.json')
changes=[]
for branch in ['01_project','02_tests','08_tools']:
 for p in sorted((r/branch).rglob('*')):
  if not p.is_file() or p.suffix not in {'.v','.vh','.sv','.py','.tcl','.adc','.sdc'} or any(x in {'build','__pycache__'} for x in p.relative_to(r).parts):continue
  rel=p.relative_to(r).as_posix();old=parent/rel
  if not old.exists() or sha(old)!=sha(p):changes.append({'path':rel,'change':'modified' if old.exists() else 'added','parent_sha256':sha(old) if old.exists() else None,'sha256':sha(p)})
(r/'03_docs/v099_SOURCE_CHANGES.json').write_text(json.dumps({'parent':str(parent),'version':r.name,'changes':changes},ensure_ascii=False,indent=2),encoding='utf-8')
preview=r/'03_docs/v099_透明频谱_仿真预览.png'
im=Image.open(vp.parent/'v099_active_spectrum.ppm');im.load();assert im.size==(1280,720);im.save(preview)
status={'version':r.name,'parent':parent.name,'state':'SIMULATION_SYNTHESIS_PHYSICAL_TIMING_BITSTREAM_CANDIDATE_NOT_HARDWARE_TESTED','target':'VF-E20NG88 / EG4S20NG88 / 24MHz','storage':str(r),'archive_planned':str(archive),'simulation':vp.relative_to(r).as_posix(),'synthesis':'05_td/v099_audio_visual_synth_attempt3/attempt.json','physical':'05_td/v099_audio_visual_physical_attempt3/attempt.json','bitgen':'05_td/v099_audio_spectrum_bitgen_attempt1/attempt.json','bitstream':bit.relative_to(r).as_posix(),'bitstream_sha256':sha(bit),'bitstream_bytes':bit.stat().st_size,'resources':res,'slack_ns':phy['slack_ns'],'new_bitstream_generated':True,'new_hardware_test':False,'flash_changed':False,'formal_release_approved':False,'handoff_zip_generated':False,'audio_source':'FPGA generated 24-bit I2S demo, use_external=0; TF WAV/MP3 not implemented','visualization':'transparent16-bin DFT bars/peaks; 4-sample attack, 400ms quiet hold + ~200ms fade at60Hz, 100ms missing-sample watchdog','inherited_regressions':bg['reviewed_reports'],'known_open_review':base['open_items']+['v099 silence/display/audio have no new physical acceptance; continuous I2S demo has no automatic silent demo segment','Sparse16-bin rectangular-window DFT is not a full-band/calibrated FFT analyzer'],'storage_note':'All new code/reports/bit/temp in D; inherited raw evidence keeps original paths; old C work trees unchanged.'}
(r/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
rows=[]
for key,label,cap,bkey in [('lut','LUT',19600,'lut'),('reg','寄存器',19600,'reg'),('bram','BRAM9K',64,'bram9k'),('dsp','DSP',29,'dsp'),('pll','PLL',4,'pll')]:
 v=res[key];delta=v-base['resources'][bkey];rows.append(f'| {label} | {v:,} / {cap:,} | {v/cap*100:.2f}% | {delta:+,} |')
resource_table='\n'.join(rows)
checks='\n'.join('- **'+x['name']+'：PASS**；'+'；'.join(x['results']) for x in sim['tests'])
report=f'''# v099 透明频谱、声音触发和自动淡出记录

## 当前结论与来源

- VF-E20NG88 / EG4S20NG88，24MHz，HDMI 1280×720。
- 8组新仿真、整机综合、布局布线、四项时序数值和守卫位流生成完成。
- **本版未下载到板卡、未实屏/试听验收、未写Flash、未正式可靠性签核。**
- 来源：{parent}；所有旧版保留。
- 工作副本：{r}。
- 冻结归档：{archive}（以归档索引和verify为准）。
- 归档容器01_project保存整个版本，所以实际RTL位于快照的01_project/01_project/rtl。

## 设计变化

1. 去除旧频谱半透明底板及PCM DEMO标题，只绘制16柱与峰值；没有坐标轴或底线，柱间/区域外RGB24位逐位透传，不做黑色抠图。
2. 青—蓝—紫渐变，最高alpha=12/16，即75%柱体+25%原图；峰值使用相同透明度。
3. 分别检测实际送往HDMI的增益处理后24-bit PCM左右声道绝对值，避免反相抵消。连续4个有效样本达到4096触发，保持门限2048；不是valid/I2S时钟在跳就认为有声音。
4. 19200个低电平有效样本对应48kHz下400ms静音保持；7,425,000个74.25MHz时钟对应100ms无样本看门狗。
5. alpha帧首更新，每帧变化1/16，12帧约200ms；静音约400ms开始淡出，约600ms完全隐藏。短间隙不反复闪烁。
6. 轨道epoch帧间锁存，旧柱/峰值快速衰减，8帧保护期后新柱渐入；完全隐藏时清除旧高度和峰值，防止静音恢复时残影复活。
7. X=128～1151，每通道64像素、可见宽48；底Y=608，最大柱高144，峰值最高Y=462，避开上方Logo和Y≥640的OSD栏。
8. 保留三寄存器级RGB/坐标/DE/HS/VS/可见标志一致延迟；不改HDMI格式、TF/SDRAM引脚或时序例外。
9. 通道更新拆成读值/高度与衰减/峰值比较/写回四短级，每帧64时钟，仍串行复用运算；alpha使用移位/加法；未增加DSP或BRAM。代码独立实现，未复制GitHub源码/外部素材。

## 整机综合资源

| 资源 | 用量 / 容量 | 占比 | 相对v098 |
|---|---:|---:|---:|
{resource_table}

依据：{r / '05_td/v099_audio_visual_synth_attempt3/attempt.json'}。
原始面积报告：{r / '05_td/v099_audio_visual_synth_attempt3/build/idx_video_Runs/syn_1/idx_video_gate.area'}。

## 时序与开放项

- SWNS {phy['slack_ns']['SWNS']:+.3f}ns；STNS {phy['slack_ns']['STNS']:.3f}ns；HWNS {phy['slack_ns']['HWNS']:+.3f}ns；HTNS {phy['slack_ns']['HTNS']:.3f}ns。
- TD官方fix_hold；没有false path、放宽约束或豁免异常输入延时。四项非负不是正式签核。
- check_timing：{json.dumps(bg['check_timing_counts'],ensure_ascii=False)}。
- PHY-7002宏重放置、内部DQ/SiP/PVT、完整地址实物BIST仍按原边界开放。

## 仿真证据

最终完整新跑：{vp}。

{checks}

- RGB参考采用独立整数((16-a)*背景+a*前景)/16；覆盖12个渐入系数、整幅720p、16路不同高度、空白/隐藏/OSD旁路、同步和坐标。
- 400ms按默认19200个有效样本逐个计数测试；连续valid只用于加速仿真，不冒称实物48kHz验收。
- 顶层PCM线注入验证valid零样本不触发、非零触发、静音保持；其内存/FIFO为测试替身，不是TF到HDMI实物验收。
- 原生ODDR、SPI/FAT/BMP、缩放+SDRAM总线模型、双帧720p及旧按键等相关源未变，守卫逐文件SHA256核对后复用证据；不声称全部在本轮重跑。
- 开发中失败TB与旧attempt1/2日志保留；只有本节最终仿真和attempt3编译对应当前候选位流，不以旧PASS替代。

## 位流与使用边界

- SRAM临时候选：{bit}
- 字节数：{bit.stat().st_size}；SHA256：{sha(bit)}。
- 不自动下载、不写Flash、不修改TF卡，不生成默认队友ZIP。
- 当前仍是FPGA内部24-bit I2S演示音，外部接口use_external=0；TF WAV/MP3、真实音乐切换和ADC采集没有实现。
- 演示音连续发声时频谱持续显示是预期；零PCM/丢样本自动隐藏已仿真，尚无本版实物静音验收。
- 降低显示器/音箱音量不会改变FPGA PCM，不能据此测试输入静音。
- 当前为16个选定频点的稀疏矩形窗DFT，不是完整FFT/校准频谱仪；没有圆形/镜像/粒子效果。
- 图片SDRAM仍为RGB332；RGB888叠加输出不等于24-bit帧缓存。

## 仿真预览

v099_透明频谱_仿真预览.png来自RTL逐像素输出。彩色底图为测试合成图，16路为固定不同高度，只说明透明外观；**不是实屏截图，也不代表单音同时激励所有柱**。
'''
(r/'03_docs/v099_实现与资源时序记录.md').write_text(report,encoding='utf-8')
steps=f'''# v099 上板测试：只临时下载SRAM

1. 保持已经通过的板卡、HDMI屏幕、下载器、TF卡和供电连接；不用拔TF卡，不用新增图片或音频。改线前先断电。
2. TD Programmer沿用成功的SRAM临时下载方式，选：
   {bit}
   确认EG4S20NG88；不要选择Flash擦除/编程/固化。
3. 等画面与HDMI音频正常后看至少两轮四图轮播：原图、Logo、OSD、按键、亮度/对比度应正常，无新增黑屏/无信号/花屏。
4. 频谱旧黑底板和PCM DEMO标题应消失；只有半透明青/蓝/紫柱和峰值。柱间直接看到原图，不应整体变暗。单音只点亮少数频带正常，不是随机全柱跳动。
5. 切图/演示音轨时旧峰值应回落、新柱渐入，不应拖着不灭残影或让HDMI失锁。K0仍是切图/重试，K1仍是手动/自动。
6. 短按后释放K0+K1：OSD、Logo、频谱一起隐藏，图片和声音继续；再次短按恢复。不要长按，长按仍进入原参数编辑功能。
7. 如异常，不擦Flash；记录画面、L0～L7和有无声音，回退最后实物通过的旧位流。v098仍是未实测候选，不能冒充已验收回退基线。

## 自动静音隐藏的验收边界

- 连续静音约400ms后淡出，再约200ms全隐；有效声音回来后约200ms渐入。
- 当前演示音持续发声，没有人为加入“周期性自动静音段”，不用等待一个并未设计的静音演示周期。
- 调低显示器/音箱音量或拔音箱不会改变FPGA PCM，频谱继续动是预期。
- 真正零PCM、左右反相、右声道独立声音、样本中断和恢复残影已经TB验证；TF真实音频接入后还需实物验收。
- 本版没有TF WAV/MP3播放，不要往卡中随意加音频并期待它会播放。

## 请反馈

1. 四图、OSD/Logo和声音是否正常？
2. 是否无频谱黑底板，柱间原图是否不变暗？
3. 切图/演示音轨是否平滑，有无旧频谱残影？
4. K0+K1短按隐藏/恢复是否正常？

本版未上板验收、未写Flash，反馈后另行登记。
'''
(r/'03_docs/v099_上板测试步骤.md').write_text(steps,encoding='utf-8')
(r/'README_先看这里.md').write_text(f'''# v099 透明音频频谱候选版

- EG4S20NG88 / 24MHz / 1280×720。
- 无底板16柱渐变/峰值、PCM声音检测、静音淡出、切轨衰减、隐藏状态残影清除；保留原图片/音频/OSD/按键链路。
- 8组仿真、整机综合、布局布线/四项时序数值通过，已生成SRAM候选；**未下载、未实物验收、未写Flash**。
- 当前是FPGA内部I2S演示音；TF WAV/MP3未实现。静音功能已仿真，不冒称实物音乐播放。
- 位流：{bit}
- 测试步骤：{r / '03_docs/v099_上板测试步骤.md'}
- 资源：LUT {res['lut']}/19600，REG {res['reg']}/19600，BRAM9K {res['bram']}/64，DSP {res['dsp']}/29，PLL {res['pll']}/4。
- 详细记录：{r / '03_docs/v099_实现与资源时序记录.md'}
- 仿真预览：{preview}（非实屏）。
- 工作副本：{r}
- 冻结快照：{archive}
- 新生成物和临时文件均在D盘，旧版保留；无需交接ZIP。
''',encoding='utf-8')
(r/'README_归档位置待同步.md').write_text(f'# v099 路径说明\n\n工作副本：{r}\n冻结快照：{archive}\n以归档索引/verify结果为准，不在快照中编译或编辑。旧证据C盘路径保留原样，不表示本版新输出在C盘。\n',encoding='utf-8')
print(json.dumps({'bit':str(bit),'sha256':sha(bit),'resources':res,'slack_ns':phy['slack_ns'],'source_changes':len(changes),'new_hardware_test':False},ensure_ascii=False,indent=2))