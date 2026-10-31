"""Finalize v102 after source-bound regression and guarded bitgen pass."""
from pathlib import Path
import json,hashlib,shutil
r=Path(__file__).resolve().parents[1];a=Path(r'D:\FPGA_Billboard\99_archive\version_history');vid='v102_hidden_ui_20261026';archive=a/'01_versions'/vid
assert not archive.exists(),'Archive is immutable'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def latest(pattern):
    paths=sorted((r/'04_evidence').glob(pattern+'/summary.json'));assert paths,pattern
    return paths[-1]
bit=r/'03_bitstreams/v102_hidden_ui_720p.bit';bg=r/'05_td/v102_audio_spectrum_bitgen_attempt1/attempt.json';synth=r/'05_td/v102_audio_visual_synth_attempt1/attempt.json';phy=r/'05_td/v102_audio_visual_physical_attempt1/attempt.json'
b=load(bg);sy=load(synth);ph=load(phy);assert b['completed'] and sy['completed'] and ph['completed'];assert sha(bit)==b['bit_sha256']
ui=latest('v102_ui_*');ui_data=load(ui);assert ui_data['passed'] and {x['name'] for x in ui_data['tests']}=={'ui','uptime','controls'}
visuals=[p for p in sorted((r/'04_evidence').glob('v102_visual_*/summary.json')) if '_native_' not in p.parent.name];vis=visuals[-1];assert load(vis)['passed']
# Preserve final synthesis evidence outside archive-excluded build paths.
gate=r/'05_td/v102_audio_visual_synth_attempt1/build/idx_video_Runs/syn_1';dest=r/'04_evidence/v102_final_synthesis_preserved';dest.mkdir(exist_ok=True);kept=[]
for src in sorted(gate.iterdir()):
    if not src.is_file():continue
    dst=dest/src.name;shutil.copy2(src,dst);assert sha(src)==sha(dst)
    kept.append({'file':src.name,'bytes':src.stat().st_size,'sha256':sha(dst),'original':str(src.relative_to(r))})
(dest/'preservation.json').write_text(json.dumps({'reason':'Archive excludes rebuildable build directories; keep final synthesis reports and DB','files':kept},indent=2),encoding='utf-8')
base=a/'01_versions/v101_multires_dither_20261026/01_project';changes=[]
for folder in ['01_project','02_tests','08_tools']:
    for p in sorted((r/folder).rglob('*')):
        if not p.is_file() or 'build' in p.relative_to(r).parts or p.suffix not in {'.v','.vh','.sv','.py','.tcl','.adc','.sdc'}:continue
        rel=p.relative_to(r);old=base/rel;h=sha(p)
        if not old.is_file() or sha(old)!=h:changes.append({'file':rel.as_posix(),'change':'modified' if old.is_file() else 'added','sha256':h,'v101_sha256':sha(old) if old.is_file() else None})
(r/'03_docs/v102_SOURCE_CHANGES.json').write_text(json.dumps({'parent_archive':str(base),'changes':changes},ensure_ascii=False,indent=2),encoding='utf-8')
preview=ui.parent/'v102_ui_actual.png'
if preview.exists():shutil.copy2(preview,r/'03_docs/v102_UI_仿真预览.png')
status={'version':vid,'date':'2026-10-26','parent':'v101_multires_dither_20261026','target':'VF-E20NG88 / EG4S20NG88 / 24MHz','status':'SRAM_CANDIDATE_UNTESTED_ON_BOARD','features':['Expose debounced key levels; retain existing release/chord/long-hold gestures','Transient 720p parameter/key/function-status UI: six-second VIEW timeout, persistent while editing/holding/error','Pressed-key highlight and LAST K0/K1/BOTH; edit-dependent hints and load/video/PCM activity status','Help recovers when decorative OSD/Logo/spectrum hidden; per-frame snapshot and four aligned pixel/control stages','Registered second pulse before OSD BCD carry; RGB pipeline latency unchanged'],'fresh_validation':{'ui_report':str(ui.relative_to(r)),'character_vectors':143,'character_comparisons':36864,'complete_active_ui_rasters':3,'ui_scope':'UI module, not TF-to-HDMI end to end','uptime_boundaries':6,'visual_report':str(vis.relative_to(r)),'native_hdmi':str(latest('v102_visual_native_*').relative_to(r))},'inherited_evidence':'Unchanged storage/scaler/dither/paired memory tests reused from v101/v097; every recorded RTL/TB source hash checked against v102, not claimed freshly rerun or hardware PASS','resources':sy['resources'],'delta_from_v101':{'lut':586,'reg':291,'bram':0,'dsp':0,'pll':0},'slack_ns':ph['slack_ns'],'numeric_timing_pass':True,'formal_release_approved':False,'new_hardware_acceptance':False,'programmed':False,'flash_modified':False,'tf_modified':False,'bitstream':str(bit),'bit_sha256':sha(bit),'bit_bytes':bit.stat().st_size,'archive_destination':str(archive),'known_open_review':['RGB332 SDRAM storage; 24-bit BMP reading is not RGB888 framebuffer storage','Source width/height remain 1..2048 each; stretch to 1280x720; big-image SPI loading time not guaranteed five seconds','Full720p TF-SDRAM-HDMI joint end-to-end simulation and this version physical display/audio/cold-start testing not done','PHY-7002 macro relocation, 33 abnormal input delays, two missing input-delay groups, seven missing output-delay groups and three dummy-node groups not waived','Internal DQ, SiP voltage/speed, PVT and full-address real-device SDRAM BIST open','Audio still internal I2S24 demo, no TF WAV/MP3 playback; AUDIO UI indicates PCM activity, not verified speaker output','Final hold slack +0.024ns: numeric STA not formal reliability signoff'],'storage':'All new work/output/temp in D:, no handoff ZIP requested or created'}
(r/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
step=r'''# v102 上板测试：可隐藏的按键/参数/状态提示窗

目标板：VF-E20NG88 / EG4S20NG88，24MHz。此版尚未上板验收。
**不换TF卡、不格式化、不改驱动、不写Flash。先SRAM临时下载。**

## 1. 下载文件

`D:\FPGA_Billboard\work\v102_hidden_ui_20261026\03_bitstreams\v102_hidden_ui_720p.bit`

在TD Programmer沿用之前成功的SRAM下载方式，选择EG4S20NG88。不要勾选Flash擦除/写入/固化。
若要重新接线或取TF卡，先断电；屏幕保持独立稳定供电。

## 2. 看提示窗自动隐藏

1. 下载完成并等待原图加载。画面上部偏中的半透明框显示亮度、对比度、编辑状态、自动/手动、当前图片和叠加层状态。
2. 第二行显示K0/K1的UP（松开）/DN（按下）以及对应功能；按下的键会高亮。LAST记录最近K0/K1/BOTH。
3. 第三行是双键操作提示。第四行TF:LOAD/READY/WAIT/ERRxx、VIDEO、AUDIO和UI状态。
4. VIEW浏览模式不操作约6秒，**新增帮助框**自动消失；原OSD/Logo/频谱保持原开关，不随它自动消失。
5. 自动轮播换图不反复弹出帮助框。按一下按键，下一帧恢复显示。按键原动作仍会正常执行，并非只唤醒不操作。

## 3. 按键操作表

| 所在模式 | 操作 | 作用 |
|---|---|---|
| VIEW浏览 | K0单击并松开 | 下一张；失败时按原逻辑重试，忙时不强行中断读取 |
| VIEW浏览 | K1单击并松开 | 自动/手动切换 |
| 任意模式 | K0+K1短按，然后两键都松开 | 开/关原OSD、Logo和频谱；不关图片/声音；帮助框显示约6秒（编辑时不隐藏） |
| 任意模式 | K0+K1同时按住约1秒，看到编辑状态改变后松开 | VIEW → BRI亮度 → CONT对比度 → VIEW；每次只走一步，需两键松开再按 |
| BRI亮度 | K0 / K1单击 | 减少 / 增加亮度，每次16，范围-64..+64 |
| CONT对比度 | K0 / K1单击 | 减少 / 增加对比度，每次25%，范围50%..150% |

长按双键会恢复原装饰叠加层，便于找到编辑入口。亮度、对比度沿用原算法和每帧提交机制，不改图片文件。

## 4. 建议按这个顺序验收

1. 原四图轮播、OSD/Logo、演示音、频谱正常；没有闪一下就消失、黑屏或无信号。
2. VIEW等待6秒看新提示框消失；K1切到手动，检查MAN及按键功能提示。
3. 双键长按一次进入BRI；K0减、K1加，观察画面和BR:+/-数值同步变化。停留8秒，编辑提示框不应消失。
4. 双键长按一次进入CONT；K0/K1调节50/75/100/125/150%，画面及CT数值对应；编辑时不应误切图。
5. 调回亮度0、对比度100%后退出VIEW；在CONT可长按回VIEW，再按上述循环进入对应字段恢复参数。
6. VIEW短按双键隐藏原OSD/Logo/频谱；等6秒新提示框也隐藏。再按K1，应重新看到帮助框和OSD:OFF；图像和声音不应因隐藏UI而停止。
7. 短按双键恢复装饰叠加层，K1回自动，观察至少两轮。较短按压若未在一帧内捕捉到高亮，LAST仍应记录最近操作。

异常请记录：位流、发生在哪一步、是否无信号、L0..L7、显示的TF:ERR码。不要先改Flash。
AUDIO:ON指FPGA检测到PCM音频活动，不能代替耳机/喇叭试听；当前仍为内部演示音，不是TF音乐播放器。

## 5. 时序与回退

数值STA：SWNS +0.369ns / STNS 0 / HWNS +0.024ns / HTNS 0。保持时间余量仍小，SDRAM宏/内部延时/SiP/PVT等未签核，先只临时测试。
原Flash内容和TF素材未动。若不稳定，回到最近你实物确认通过的旧版，不把v101或v100仿真版自动当成已验收回退版。

完整保存位置：
`D:\FPGA_Billboard\99_archive\version_history\01_versions\v102_hidden_ui_20261026`

本次无需交接ZIP。
'''
(r/'03_docs/v102_上板测试步骤.md').write_text(step,encoding='utf-8')
record=f'''# v102 实现、资源、时序及证据边界

日期：2026-10-26。父版本：v101冻结快照。目标：EG4S20NG88 / 24MHz，约束不变。

## 实现

- 保留亮度/对比度计算与K0/K1 release/chord/hold手势，仅导出已去抖按键状态。
- 新ui_help_overlay：720p半透明四行提示、按键高亮、LAST单/双键、当前编辑字段操作帮助。
- VIEW约360帧无操作隐藏；按键/参数/模式操作唤醒；编辑/按住/错误时常显；自动换图不唤醒。
- 原装饰OSD关闭后帮助窗仍能恢复，两个开关有意分开，避免隐藏后找不到入口。
- TF busy/failed经双触发器同步，错误码沿用两次相等样本发布；像素域编辑值按帧快照。显示层增加4周期匹配RGB/坐标/DE/HS/VS/picture_visible流水，绝不提高音频门控。
- 原OSD秒脉冲寄存后进入六位BCD进位链；计时状态晚1像素周期，RGB延迟未改，不增加时序例外。字库补X，无新DSP/BRAM/外接处理器。

## 验证（不是实物）

1. 新UI：143独立字符串向量，36,864字符比较；3完整720p有效光栅2,764,800像素，含随机/排空共2,766,825次带时序比较。覆盖隐藏、编辑常显、帧边界、双键错位松开、原OSD关闭、无图像不抬高音频门控、精确旁路。
2. 原按键去抖/开机按住/短组合键/长按/限幅/无误切图回归通过。
3. 6个初始化BCD边界通过（59秒/59分/99小时回卷）；不是100小时实物耐久测试。
4. 当前视觉/PCM/DFT/频谱/OSD/TMDS共9组回归通过；原生HDMI/厂商ODDR三相位通过。Top回归使用替代PLL及受控FIFO注入，不是真实TF/板卡测试。
5. 原v101多分辨率/抖动/全720p独立缩放和v097 SPI/存储回归未重复执行，但每项RTL/TB记录哈希与v102一致，门控逐项核实后复用，不称作本版新运行。
6. 完整720p TF→SDRAM→HDMI联合端到端仿真、本版下载/屏幕试听/冷启动/Flash均未执行。

UI报告：`{ui.relative_to(r).as_posix()}`。
视觉报告：`{vis.relative_to(r).as_posix()}`。
本目录UI预览为实际DUT仿真输出，背景是合成渐变，不是板卡照片。

## 整机资源（最终综合attempt1）

|资源|使用/容量|占比|较v101|
|---|---:|---:|---:|
|LUT|15011/19600|76.59%|+586|
|REG|8417/19600|42.94%|+291|
|BRAM9K|23/64|35.94%|不变|
|DSP|14/29|48.28%|不变|
|PLL|3/4|75.00%|不变|

最终综合报告/DB共{len(kept)}份逐项复制校验到04_evidence/v102_final_synthesis_preserved，避免归档排除build后遗失。

## 最终物理时序（attempt1）

SWNS +0.369ns / STNS 0 / HWNS +0.024ns / HTNS 0；setup较v101的+0.001ns改善。无路由ERROR，但保持时间仅24ps，不能作为可靠性签核。
权威报告：05_td/v102_audio_visual_physical_attempt1/physical/sdram_pr.timing、sdram_phy.ts、sdram_check.rpt。
仍有dummy node 3组、缺input delay 2组、缺output delay 7组、异常input delay 33组；PHY-7002宏重定位、内部DQ、SiP电压速度级、PVT、完整地址实物BIST均开放。

## 位流与边界

位流：`{bit}`。
SHA256：`{sha(bit)}`；{bit.stat().st_size}字节。
门控脚本核对当前专项/完整回归、继承证据源码哈希、综合/路由数据库、四项slack及重新加载check_timing一致性才发布。没有自动下载/改TF/Flash。
RGB332、宽高各1..2048、拉伸/强缩小混叠、大图SPI耗时及内部I2S演示音/无TF音乐等边界保留。

## 失败记录

专项TB早期两处参考设置错误（相同亮度测试“变化”；无图像帧参考未将READY/ON改成WAIT）保留失败日志，修正参考后完整重跑，未删测试或改RTL绕过。最终RTL与综合/布线/仿真源哈希一致。

仅写D盘，旧版全部保留，无需交接ZIP。
'''
(r/'03_docs/v102_实现与资源时序记录.md').write_text(record,encoding='utf-8')
(r/'README_先看这里.md').write_text('# v102：可隐藏的按键/参数/功能状态提示窗\n\n未上板的SRAM候选版，先读：\n`'+str(r/'03_docs/v102_上板测试步骤.md')+'`\n\n临时位流：\n`'+str(bit)+'`\n\n不换TF，不写Flash。新增提示约6秒隐藏，编辑时常显。原装饰叠加层开关保留，帮助窗独立唤醒。\n\n完整状态见VERSION_STATUS.json，资源/时序/仿真见03_docs/v102_实现与资源时序记录.md。\n\n冻结归档目标：`'+str(archive)+'`。保留旧版，无需交接ZIP。\n',encoding='utf-8')
(r/'README_归档位置待同步.md').write_text('# 本版保存位置\n\n工作副本：`'+str(r)+'`\n\n快照目标：`'+str(archive)+'`\n\n归档后以索引、versions.json和SHA256清单为准，不在快照内编译/测试。\n',encoding='utf-8')
print(json.dumps({'version':vid,'bit':str(bit),'sha256':sha(bit),'source_changes':len(changes),'synthesis_preserved_files':len(kept)},ensure_ascii=False,indent=2))
