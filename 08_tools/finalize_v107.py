"""Finalize source-bound v107 SRAM candidate; never programs JTAG/Flash or TF.
Run only in the mutable D: working copy, before archive save/verify.
"""
from pathlib import Path
import argparse, json, hashlib, shutil, re
from PIL import Image
r=Path(__file__).resolve().parents[1]
a=Path(r'D:\FPGA_Billboard\99_archive\version_history')
vid='v107_keys_subtitle_20261026'; archive=a/'01_versions'/vid
assert '01_versions' not in r.parts and not archive.exists(), 'Never edit frozen archives'
ap=argparse.ArgumentParser();ap.add_argument('--synth-attempt',type=int,default=1);ap.add_argument('--physical-attempt',type=int,default=1);ap.add_argument('--bitgen-attempt',type=int,default=1);args=ap.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():assert sha(src)==sha(dst),str(dst)
 else:shutil.copy2(src,dst)
 assert sha(src)==sha(dst)
parent=a/'01_versions/v105_center_glass_art_spectrum_20261026/01_project'
bit=r/'03_bitstreams/v107_keys_subtitle_720p.bit'
bg=r/f'05_td/v107_audio_spectrum_bitgen_attempt{args.bitgen_attempt}/attempt.json'
syn=r/f'05_td/v107_audio_visual_synth_attempt{args.synth_attempt}/attempt.json'
phy=r/f'05_td/v107_audio_visual_physical_attempt{args.physical_attempt}/attempt.json'
b,sy,ph=map(load,(bg,syn,phy))
assert b['completed'] and sy['completed'] and ph['completed']
assert sha(bit)==b['bit_sha256'] and min(ph['slack_ns'].values())>=0
for rel,h in sy['source_sha256'].items():assert sha(r/rel)==h,rel
for item in b['reviewed_reports'].values():assert sha(r/item['path'])==item['sha256'],item['path']
# Keep TD's real generated project AND the synthesis DB/reports outside excluded build.
# td_project is a sibling of build: all original source/include relative paths survive.
gate=syn.parent/'build/idx_video_Runs/syn_1';dest=r/'04_evidence/v107_final_synthesis_preserved';kept=[]
for src in sorted(gate.iterdir()):
 if not src.is_file():continue
 dst=dest/src.name;copy(src,dst)
 kept.append({'file':src.name,'bytes':src.stat().st_size,'sha256':sha(dst)})
write(dest/'preservation.json',{'reason':'Exact final synthesis DB/reports preserved outside excluded build cache','files':kept})
project_copy=syn.parent/'td_project/idx_video.al';copy(syn.parent/'build/idx_video.al',project_copy)
prj_copy=project_copy.parent/'idx_video_Runs/syn_1/idx_video.prj';copy(gate/'idx_video.prj',prj_copy)
references=[]
for project in (project_copy,prj_copy):
 # TD writes UsedInP&R without XML escaping; extract path attributes only.
 for rel in re.findall(r'<File Path=\x22([^\x22]+)\x22',project.read_text(encoding='utf8')):
  target=(project.parent/rel).resolve();assert target.is_file(),str(target)
  references.append({'project':project.relative_to(r).as_posix(),'source':target.relative_to(r).as_posix(),'sha256':sha(target)})
write(dest/'td_project_relative_paths.json',{'passed':True,'files_identical_to_generated_projects':True,'resolved_file_references':references,'note':'Raw TD projects retain their original absolute build header as evidence. File Path references remain valid at the same directory depth. Use the synthesis entry to create a fresh project in a work copy; no GUI-open/relocation or hardware claim.'})
res,sl=sy['resources'],ph['slack_ns'];before=load(parent/'VERSION_STATUS.json')['resources']
delta={k:res[k]-before[k] for k in ['lut','reg','bram','dsp','pll']}
ui_path=r/b['reviewed_reports']['hidden_ui']['path'];media_path=r/b['reviewed_reports']['media_controls_subtitle']['path'];visual_path=r/b['reviewed_reports']['visual']['path']
for src,name in [(ui_path.parent/'v107_ui_1.png','v107_UI_白底预览.png'),(ui_path.parent/'v107_ui_2.png','v107_UI_透底与编辑预览.png'),(media_path.parent/'caption_2.png','v107_字幕时间轴_RTL预览.png')]:copy(src,r/'03_docs'/name)
Image.open(visual_path.parent/'v107_active_spectrum.ppm').save(r/'03_docs/v107_艺术频谱_RTL预览.png')
for name in ['README_先看这里.md','VERSION_STATUS.json','README_归档位置.md']:
 p=r/name;backup=r/('INHERITED_v105_'+name)
 if p.is_file() and not backup.exists():shutil.copy2(p,backup)
opens=[
 'v107 has not been downloaded, viewed/heard on hardware, endurance tested, written to Flash or cold-start accepted',
 'Audio remains internal 24-bit I2S demo tones. MUSIC.WAV/ADVOICE.WAV are NOT read by this bitstream',
 'Subtitles are explicit DEMO ROM cues, NOT confirmed ad transcript, automatic speech recognition, or runtime TF SRT parsing',
 'Prototype subtitle capacity: 8 non-overlapping one-line cues, 24 glyphs each, a fixed 16-second progress axis; 6 demo cues compiled',
 'Accepted PCM samples define subtitle time; HDMI FIFO/output/sink delay remains uncalibrated, not external absolute A/V sync signoff',
 'RGB332+dither SDRAM framebuffer, despite 24-bit uncompressed BMP input; source dimensions 1..2048 each, bilinear stretch to 1280x720',
 '16 measured DFT bins interpolated into 64 DISPLAY bars, not 64 independently measured bins or a 1024-point FFT',
 'Small routed margins SWNS +0.062ns / HWNS +0.030ns do not establish PVT reliability',
 'SDRAM macro relocation, 33 abnormal input-delay annotations, 3 dummy nodes, external IO delay review, SiP/PVT and full-address real-device BIST remain open',
 'Fixed embedded glyph subsets, no arbitrary runtime Unicode; translucent glass tint is not optical blur/refraction'
]
fresh={'media_controls_subtitle','subtitle_import','rom_init','hidden_ui','robustness','native_hdmi','legacy_units','visual'}
status={'version':vid,'parent':'v105_center_glass_art_spectrum_20261026','precheck_archive':'v106_keys_subtitle_precheck_20261026','date':'2026-10-26','target':'VF-E20NG88 / EG4S20NG88 / 24MHz','scope':'Modal long-K0 demo-audio selection, independent long-K1 pinned Chinese UI, sample-clock Chinese DEMO subtitles/time/progress at 1280x720','new_hardware':False,'fresh_validation':{k:x for k,x in b['reviewed_reports'].items() if k in fresh},'inherited_validation':{k:x for k,x in b['reviewed_reports'].items() if k not in fresh},'resources':res,'delta_from_v105':delta,'slack_ns':sl,'numeric_timing_pass':True,'check_timing_counts':b['check_timing_counts'],'formal_release_approved':False,'new_hardware_acceptance':False,'programmed':False,'flash_modified':False,'tf_modified':False,'bitstream':str(bit),'archive_bitstream':str(archive/'01_project/03_bitstreams'/bit.name),'bit_sha256':sha(bit),'bit_bytes':bit.stat().st_size,'selected_attempts':{'synthesis':args.synth_attempt,'physical':args.physical_attempt,'bitgen':args.bitgen_attempt},'archive_destination':str(archive),'known_open_review':opens,'storage':'New sources/temp/evidence/output on D:; no handoff ZIP'}
write(r/'VERSION_STATUS.json',status)
keys='''|状态／操作|结果|
|---|---|
|浏览：短按 K0 后松手|下一张；发生读取错误时重试|
|浏览：短按 K1 后松手|自动／手动切换|
|长按 K0 约 1 秒后松手|进入／退出音频选择；进入后无需一直按住 K0|
|音频选择：短按 K1|跟随图片 → 测试音 A → 测试音 B → 跟随图片|
|音频选择：短按 K0|退出选择，保留音源，不切换图片|
|长按 K1 约 1 秒|控制 UI 常显／取消常显；不会顺带触发短按|
|双键同时短按再松手|图片 OSD、Logo、频谱、字幕／时间轴整体显隐；独立帮助 UI 不受此装饰开关控制|
|双键同时长按约 1 秒|浏览 → 亮度 → 对比度 → 浏览；退出音频选择|
|亮度编辑：短 K0／短 K1|减／加 16，范围 -64..+64|
|对比度编辑：短 K0／短 K1|减／加 25%，范围 50%..150%|
'''
steps='''1. 保持现有 TF 卡、HDMI、音箱与接线不变，不需要复制新文件到 TF。
2. 用本版 bit 做 **JTAG/SRAM 临时下载**，先不要固化或擦写 Flash。确认四张图、720p、Logo、音频、频谱仍正常。
3. 短按 K1 切到“手动切换”，使图片停留。每次操作前先松开两个键。
4. 长按 K0 约 1 秒并松手：UI 音频行应显示“音频选择”；短按 K1 选“测试音A”，再短按 K0 退出。图片不能因选择音源而换页，自动／手动状态不能误切。
5. 看底部中文字幕、MM:SS 和进度线约 16 秒：文字应按时间表出现，空档只保留时间／进度，16 秒后字幕消失、进度到尾，时间继续走。计时跟随有效播放采样；不可见暂停，非电脑墙上时钟。字幕需要装饰叠加开关开启。
6. 重复进入选择，改“测试音B”：听到音高变化、旧频谱收拢再出现新频谱，字幕时间重启；UI 能区分 A/B。“A/B”是真实内部测试音，不是 TF 里的音乐／广告。
7. 在已退出选择、退出参数编辑、无故障时：长按 K1 常显，等待超过 6 秒仍显示；再次长按 K1 收起，松手不应立即重开。下一次短按可临时唤醒，空闲约 6 秒收起。选择、编辑或故障会强制显示，不能用隐藏操作盖住错误。
8. 回归双键短按显隐、双键长按亮度／对比度、单键增减、回到浏览、K0 下一张、K1 自动／手动。长按不应同时触发单键短按；双键请尽量同时按下，不能在单键长按已触发后再拼组合。
9. 若需重看整段字幕，音源 A/B 互换触发新时间轴；不需要重新下载。选择“跟随图片”时切图／内部曲目改变也会重启，自动轮播可能看不到全部 16 秒。
10. 反馈图像稳定性、字幕是否错位、时间是否重启、A/B 是否可听切换、UI 是否能独立开关。出现无信号或 L6/L7 错误先记录现象；不要继续固化本版。
'''
(r/'README_先看这里.md').write_text(f'''# v107：新增按键、中文字幕与时间轴（待实物测试）

目标板 VF-E20NG88 / EG4S20NG88 / 24MHz，HDMI 1280×720。

**已经完成源码、仿真、TD 综合／布局布线／数值时序检查和位流生成；没有下载、实屏、听音或 Flash 验收。**

## 本次先测什么

- 长按 K0 进入音频选择，松手后短按 K1 切换；选择中短按 K0 安全退出。
- 长按 K1 独立常显／收起中文控制 UI，原调参和图像手势保留。
- 底部中文演示字幕、采样计时 MM:SS 和 16 秒进度条。不是语音识别。
- **音源仍是 FPGA 内部测试音，本版尚不能播放 MUSIC.WAV／ADVOICE.WAV，字幕不是已确认的广告词。**

## 位流

工作文件：`{bit}`

冻结归档文件：`{archive / '01_project/03_bitstreams' / bit.name}`

SHA256：`{sha(bit)}`；{bit.stat().st_size} 字节。仅推荐 SRAM 临时验证。

## 按键规则

{keys}
长按约 1 秒，只执行一次；短按在松手时执行。音频选择是锁存模式，不需要一直按 K0。

## 一步步测试

{steps}
## 工程与记录

- `03_docs/v107_实现与资源说明.md`：资源、验证范围与未闭环问题。
- `03_docs/v107_实物测试记录_待填写.md`：本版实测空表，不借用旧版通过结论。
- `06_test_media/subtitles/DEMO_ONLY.srt`：当前预编译演示字幕。
- `08_tools/run_acceptance.py`：默认仅做只读发布文件校验，不下载、不改 TF/Flash。
- 原始TD工程在 `05_td/v107_audio_visual_synth_attempt1/td_project/idx_video.al` 供查阅，文件相对路径已校验，但工程头保留原始构建绝对位置。重新构建请用验收入口的 synth 阶段创建新工程；不要直接在归档中运行 TD。

所有本次新增文件位于 D 盘，旧版本保留，无需交接压缩包。RGB332、SDRAM 宏／内部延迟／SiP/PVT 等边界保留。
''',encoding='utf8')
table='\n'.join(f'|{label}|{res[k]}/{cap}|{100*res[k]/cap:.2f}%|{delta[k]:+d}|' for k,label,cap in [('lut','LUT',19600),('reg','寄存器',19600),('bram','BRAM9K',64),('dsp','DSP',29),('pll','PLL',4)])
report_lines=[]
for key in sorted(fresh):
 d=load(r/b['reviewed_reports'][key]['path']);report_lines.append('- '+key+'：`'+b['reviewed_reports'][key]['path']+'`')
 for test in d.get('tests',[]):
  for line in test.get('results',[]):report_lines.append('  - '+line)
(r/'03_docs/v107_实现与资源说明.md').write_text(f'''# v107 实现、验证和资源

## 改动范围

新增 `media_controls.v`：同步／消抖、按住上电抑制、松手短按、一次长按、早组合接管／晚组合不二次触发。原 `picture_controls_osd.v` 留作历史兼容，没有偷偷改旧测试。
新增 `media_ui_overlay.v` 及独立中文字库：音频选择行、测试音A/B、长K1 pin/close 与松手抑制。UI 保留720p居中双列圆角浅色透底，114字形／52条消息；字库为固定 OFL Noto CJK 子集，不是任意Unicode。
顶层音源 mux 确实接入 `audio_pcm_frontend`，不是只改UI标签；跟随图片选择原四音色，固定A用内部track1、固定B用track3。24-bit PCM同源送HDMI、DFT和字幕时间基准。未加入TF WAV读取。
新增 `pcm_subtitle_timeline.v`、`subtitle_overlay.v` 及预编译cue/text/font ROM，位于频谱后、帮助UI前；四拍RGB／XY／DE／HS／VS／可见标记全对齐，按帧快照避免扫描中换字。
ADC／SDC、PLL、SDRAM、真实SPI/FAT32/BMP、双线性缩放、RGB332抖动、HDMI封包未改。源差异见 `v107_SOURCE_CHANGES.json`。

## 字幕原型边界

- 48kHz下48个已接收、播放使能的立体声PCM样本计1ms；数字静音也计时，播放不可见暂停。曲目epoch清零并优先丢弃边界样本，与DFT处理一致。不是ASR、电脑时间或按图帧数伪计时。
- MM:SS为十进制BCD；采样时间和输出HDMI／显示器／音箱还有队列与设备延迟，没有标定外部绝对同步。
- 固定16秒进度轴，最多8条、每条1行、24字，当前6条全部以“演示:”开头。底部区域[x64..1215,y664..715]；32px中文字幕、16px时间，1000px进度线。末条结束不再显示正文，时间可继续计数。
- `DEMO_ONLY.srt` 离线编译进ROM；运行时不读取TF的SRT，不自动识别音乐歌词／广告词，也未编译未经确认的广告转录。
- 官方媒体的字幕来源检查见 `04_evidence/v106_subtitle_source_review/result.json`，`transcript_confirmed=false`。
- 后续接入TF WAV播放器后必须共享valid/enable/epoch语义，再扩展时长／cue／字库及I/O队列，不能把当前16秒原型称为完整音乐／广告字幕播放器。
- 修改SRT须在新工作版本运行 `08_tools/generate_v107_subtitles.py --srt <确认文本的完整SRT路径>`，重新仿真、综合、物理检查、ROM检查和bitgen。当前生成器拒绝长于16秒的脚本；不要对已冻结版直接重编译。

## 资源（整机，不是独立字幕模块）

|资源|使用／容量|占比|较v105增量|
|---|---:|---:|---:|
{table}

没有新增DSP／PLL。主要增加字幕5块BRAM，以及按键／时间／UI逻辑。LUT余量仅{19600-res['lut']}，后续TF音频调度应继续控制查表、复用乘法器，不能假设无限资源。

最终综合attempt{args.synth_attempt}、物理attempt{args.physical_attempt}、bitgen attempt{args.bitgen_attempt}：SWNS {sl['SWNS']:+.3f}ns / STNS {sl['STNS']:.3f}ns / HWNS {sl['HWNS']:+.3f}ns / HTNS {sl['HTNS']:.3f}ns。
这只是当前工具／模型／约束的数值检查，裕量很小；未等价于温压／批次鲁棒性签核。

查看 `04_evidence/v107_final_synthesis_preserved/idx_video_gate.area` 中 Utilization Statistics；原始TD生成项目在 `05_td/v107_audio_visual_synth_attempt1/td_project/idx_video.al`，保留原相对文件路径与原构建绝对头，仅供证据查阅；重建用验收入口重新创建工程，不承诺GUI直接重定位。原始综合gate的{len(kept)}份报告与DB另行保全，不受build缓存排除影响。

## 新执行的通过证据

六项新增媒体测试、八项非法SRT拒绝、10块路由后ROM逐位核对；420独立UI状态／完整720p，9组顶层／HDMI／PCM／频谱回归，3项鲁棒性和5项旧单元重跑，3相位原生ODDR模型验证。
未改变的v101/v097 TF／缩放／SDRAM仿真只按源码哈希复用，不伪称本版全链新跑，更不是新实物通过。

{chr(10).join(report_lines)}

## 中途未通过记录保留

1. 首次UI runner 360秒超时，输出3张预览但没有完整PASS；未修改RTL，只把测试超时放宽到900秒重跑，第二次全部通过（UI实际464.25秒）。见 `04_evidence/v107_ui_20261026_194620/summary.json` 与最终UI报告。
2. 首次系统runner误指向不存在的新名overlay TB，未生成完整summary；补齐新名TB、真实新控件顶层断言并修正测试按压时长，第二次9组全部通过。首轮日志保存在 `04_evidence/v107_visual_20261026_194649`，没有把这次不完整运行标记通过。
以上是测试组织／超时问题，不是抹掉失败后冒认硬件功能；综合后active RTL／VH没有改动，最终源哈希与bit一致。

## 仍开放

{chr(10).join('- '+x for x in opens)}

本版从未下载／上屏／听音／写Flash，用户实测表为空。完整归档：`{archive}`。无交接ZIP。
''',encoding='utf8')
(r/'03_docs/v107_实物测试记录_待填写.md').write_text(f'''# v107 实物测试记录（待用户填写）

位流：`{bit}`
SHA256：`{sha(bit)}`

**本表尚无通过结论；不继承v105或更早版本的实物反馈。先临时下载，不写Flash。**

{steps}
|项目|预期|实际现象|结论|
|---|---|---|---|
|SRAM下载|工具成功且对应本版哈希|待填|未测|
|四图／720p|正常轮播与切图，不黑屏|待填|未测|
|短按与长按|长按不偷发短按，松手不连发|待填|未测|
|音频选择|进入／退出安全，A/B有真实音高变化|待填|未测|
|字幕／时间轴|16秒6条、空档、时间／进度、切音归零|待填|未测|
|长K1独立UI|常显／收起，松手不重开|待填|未测|
|原图像调参|亮度／对比度／显隐／自动手动保留|待填|未测|
|故障可见性|错误不被装饰隐藏盖住|待填|未测|
|长时间运行|记录持续时长、切图次数、音视频异常|待填|未测|
|Flash／冷启动|本轮不进行|未操作|未测|

若异常请记录所用bit、屏幕分辨率、按键顺序、L0..L7、重上电前后差异。本版不是TF音乐／广告播放器。
''',encoding='utf8')
(r/'README_归档位置.md').write_text(f'# v107 归档位置\n\n工作工程：`{r}`\n\n冻结归档：`{archive}`\n\n归档由archive_version.py save/verify完成。不要在快照中编辑或执行会写日志的TD/仿真。全部旧版本保留，无需交接压缩包。\n',encoding='utf8')
changes=[];unchanged=[]
for p in sorted((r/'01_project').rglob('*')):
 if not p.is_file() or 'build' in p.relative_to(r).parts:continue
 rel=p.relative_to(r);old=parent/rel
 if not old.is_file() or sha(old)!=sha(p):changes.append({'file':rel.as_posix(),'change':'modified' if old.is_file() else 'added','sha256':sha(p),'parent_sha256':sha(old) if old.is_file() else None})
 else:unchanged.append(rel.as_posix())
write(r/'03_docs/v107_SOURCE_CHANGES.json',{'parent_archive':str(parent),'changes':changes,'unchanged_files':unchanged})
write(r/'04_evidence/v107_validation_history.json',{'scope':'Test-harness history; failed/incomplete attempts retained, not hardware outcomes','incidents':[{'path':'04_evidence/v107_ui_20261026_194620','failure':'360-second UI test timeout, not PASS','resolution':'No active RTL change; final UI test timeout900 and all three groups passed','final_report':b['reviewed_reports']['hidden_ui']['path']},{'path':'04_evidence/v107_visual_20261026_194649','failure':'Runner referenced a not-yet-created v107 overlay TB; no complete summary','resolution':'Create dedicated renamed overlay and updated top TB, correct gesture-test durations, rerun full nine groups','final_report':b['reviewed_reports']['visual']['path']}],'bit_sha256':sha(bit),'new_hardware_test':False})
# Bind source, all current evidence (including imperfect attempts), docs, actual projects and bit.
# The full archive additionally retains all inherited history; build/vvp/vcd/pyc are rebuildable.
files=set()
for folder in [r/'01_project',r/'02_tests',r/'08_tools',r/'03_docs',r/'06_test_media',r/'07_reference/fonts/noto_cjk',dest,*[p for p in (r/'04_evidence').iterdir() if p.is_dir() and p.name.startswith(('v107_','v106_'))],*[p for p in (r/'05_td').iterdir() if p.is_dir() and p.name.startswith('v107_')],*[(r/x['path']).parent for x in b['reviewed_reports'].values()]]:
 for p in folder.rglob('*'):
  if p.is_file() and not {'build','__pycache__','.git'}.intersection(p.relative_to(r).parts) and p.suffix not in {'.vvp','.vcd','.pyc'}:files.add(p)
files.update([bit,r/'VERSION_STATUS.json',r/'README_先看这里.md',r/'README_归档位置.md',r/'04_evidence/v107_validation_history.json'])
manifest={'version':vid,'scope':'Offline source/evidence/project/report/bit identity only; NOT hardware acceptance','hardware_test':False,'files_sha256':{p.relative_to(r).as_posix():sha(p) for p in sorted(files)}}
write(r/'04_evidence/v107_release_manifest.json',manifest)
print(json.dumps({'version':vid,'resources':res,'delta_from_v105':delta,'slack_ns':sl,'preserved_synthesis_files':len(kept),'resolved_td_project_references':len(references),'manifest_files':len(files),'bit_sha256':sha(bit),'archive':str(archive)},ensure_ascii=False,indent=2))

