"""Finalize source-bound v103 diagnostic candidate. Never programs hardware/TF/Flash."""
from pathlib import Path
import json,hashlib,shutil,argparse
r=Path(__file__).resolve().parents[1];a=Path(r'D:\FPGA_Billboard\99_archive\version_history')
ap=argparse.ArgumentParser();ap.add_argument('--synth-attempt',type=int,default=2);ap.add_argument('--physical-attempt',type=int,default=2);ap.add_argument('--bitgen-attempt',type=int,default=1);args=ap.parse_args()
vid='v103_acceptance_robustness_20261026';archive=a/'01_versions'/vid;assert not archive.exists(),'Archived versions are immutable'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
bit=r/'03_bitstreams/v103_acceptance_robustness_720p.bit';bg=r/f'05_td/v103_audio_spectrum_bitgen_attempt{args.bitgen_attempt}/attempt.json';synth=r/f'05_td/v103_audio_visual_synth_attempt{args.synth_attempt}/attempt.json';phy=r/f'05_td/v103_audio_visual_physical_attempt{args.physical_attempt}/attempt.json'
b=load(bg);sy=load(synth);ph=load(phy);assert b['completed'] and sy['completed'] and ph['completed'];assert sha(bit)==b['bit_sha256'];assert min(ph['slack_ns'].values())>=0
for rel,h in sy['source_sha256'].items():assert sha(r/rel)==h,rel
for item in b['reviewed_reports'].values():assert sha(r/item['path'])==item['sha256']
gate=synth.parent/'build/idx_video_Runs/syn_1';dest=r/'04_evidence/v103_final_synthesis_preserved';dest.mkdir(exist_ok=True);kept=[]
for src in sorted(gate.iterdir()):
 if src.is_file():
  dst=dest/src.name
  if dst.exists():assert sha(dst)==sha(src),'Refuse to overwrite different preserved synthesis evidence'
  else:shutil.copy2(src,dst)
  assert sha(src)==sha(dst);kept.append({'file':src.name,'bytes':src.stat().st_size,'sha256':sha(dst),'original':src.relative_to(r).as_posix()})
(dest/'preservation.json').write_text(json.dumps({'reason':'Preserve source-bound final synthesis DB/reports outside rebuildable build paths','files':kept},indent=2),encoding='utf8')
parent=a/'01_versions/v102_hidden_ui_20261026/01_project';changes=[]
for folder in ['01_project','02_tests','08_tools']:
 for p in sorted((r/folder).rglob('*')):
  if not p.is_file() or 'build' in p.relative_to(r).parts or p.suffix not in {'.v','.vh','.sv','.py','.tcl','.adc','.sdc'}:continue
  rel=p.relative_to(r);old=parent/rel
  if not old.is_file() or sha(old)!=sha(p):changes.append({'file':rel.as_posix(),'change':'modified' if old.is_file() else 'added','sha256':sha(p),'parent_sha256':sha(old) if old.is_file() else None})
(r/'03_docs/v103_SOURCE_CHANGES.json').write_text(json.dumps({'parent_archive':str(parent),'changes':changes},ensure_ascii=False,indent=2),encoding='utf8')
res=sy['resources'];sl=ph['slack_ns'];before=load(parent/'VERSION_STATUS.json')['resources'];delta={k:res[k]-before[k] for k in ['lut','reg','bram','dsp','pll']}
opens=['RGB332 SDRAM storage with stationary dither, not RGB888 full-frame storage','BMP24 BI_RGB source dimensions each 1..2048; stretch not aspect-fit; strong-minification aliasing and large-image SPI loading time remain bounded limitations','Audio is internal I2S24 demo; TF WAV/MP3 playback is not implemented; DFT has sixteen selected bins','Full720p real TF-SDRAM-HDMI joint end-to-end hardware/long-run/speaker and cold-start acceptance not performed for v103','PHY-7002 macro relocation and 33 abnormal input delays, two missing input-delay groups, seven missing output-delay groups and three dummy-node groups remain unwaived','Internal DQ, SiP voltage/speed, PVT and full-address real-device SDRAM BIST remain open','Watchdog covers FIRST/LOAD_NEXT inactivity only, not WAIT_DISPLAY/SLIDE/PLL loss; stream fault blocks auto retry, sticky display underflow may still need reconfiguration','Nonnegative STA numeric result is not a formal reliability or PVT signoff']
status={'version':vid,'date':'2026-10-26','parent':'v102_hidden_ui_20261026','target':'VF-E20NG88 / EG4S20NG88 / 24MHz','status':'SRAM_CANDIDATE_UNTESTED_ON_BOARD','features':['10s framebuffer-accepted-burst inactivity watchdog in TF loading only; continued progress permits long total load','Whitelisted transport fault retry: initial attempt plus at most two automatic attempts, one-second retry wait, manual retry grants budget','Old complete front retained on background failure; no partial frame commit; old-bank reuse still after transition drain','V103 diagnostic banner: hidden decorations cannot suppress current or historical fault evidence; no new audio gate assertion or HDMI reset','Unified nondestructive acceptance runner and four-category hardware checklist; full immutable version preservation'],'fresh_validation':{k:v for k,v in b['reviewed_reports'].items() if v['current_v103_execution']},'inherited_validation':{k:v for k,v in b['reviewed_reports'].items() if not v['current_v103_execution']},'module_results':{'playlist_scenarios':15,'playlist_checks':60,'diagnostic_sources':5,'diagnostic_checks':37,'nominal_pcm_samples':8192,'pcm_samples_with_atomic_collision':8197,'pcm_packets':2049,'legacy_groups':5,'system_groups':9,'native_phase_offsets_ps':[137,370,1111]},'resources':res,'delta_from_v102':delta,'slack_ns':sl,'check_timing_counts':b['check_timing_counts'],'numeric_timing_pass':True,'formal_release_approved':False,'new_hardware_acceptance':False,'programmed':False,'flash_modified':False,'tf_modified':False,'bitstream':str(bit),'bit_sha256':sha(bit),'bit_bytes':bit.stat().st_size,'selected_attempts':{'synthesis':args.synth_attempt,'physical':args.physical_attempt,'bitgen':args.bitgen_attempt},'archive_destination':str(archive),'known_open_review':opens,'storage':'All new code/output/temp on D; no handoff ZIP requested/created'}
(r/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf8')
resources='\n'.join(f'|{label}|{res[k]}/{cap}|{100*res[k]/cap:.2f}%|{delta[k]:+d}|' for k,label,cap in [('lut','LUT',19600),('reg','REG',19600),('bram','BRAM9K',64),('dsp','DSP',29),('pll','PLL',4)])
report=f'''# v103 四项优化：实现与验收矩阵

日期：2026-10-26。父版本v102，目标EG4S20NG88 / 24MHz；原ADC/SDC、视频/内存时钟、正常音频路径不变。

## 1. 一目了然

|方向|本版实际做了什么|当前证据|仍需用户实物确认|
|---|---|---|---|
|核心功能完整性|保留真实TF/FAT32/BMP24、双线性720p、双缓冲、四图、OSD/Logo、参数/模式、PCM/频谱；给文件装载补有限恢复|15保护场景60项检查；原5组单元和9组系统回归新运行通过；未改UI/多尺寸/scaler/存储证据源哈希逐项吻合|本版四图、大小图、按键及隐藏UI；不同尺寸不是无限尺寸|
|显示稳定性与鲁棒性|后台失败保留旧图，实际burst无进展10秒保护，传输错误最多两次自动重试；隐藏UI仍显示当前及历史错误|精确超时/优先级/流控/不提交半帧/银行回收；5类故障37项检查；真实top受控FIFO注入通过；最终STA数值通过|20～30分钟连续运行、供电/显示器兼容、异常后的真实表现；不等于宏/PVT已签核|
|基础音频输出|保留I2S24→PCM→HDMI复用与图像门控，新增长序列、左右声道/24位边界、IEC状态/奇偶校验、队列溢出/复位测试|8192标称样本+定向同时push/pop共8197样本、2049包；原独立I2S解码393样本/4音轨；原生HDMI/ODDR三相位通过|真实耳机/喇叭、破音/爆音、切图声音门控；当前无TF音乐文件播放|
|系统工程规范性|单一入口、要求-实现-证据表、错误码说明、上板结果表、源码哈希与最终报告/数据库保全、失败尝试不隐藏|新bit守门校验3专项+5legacy+9system+3native及继承证据/资源/最终STA；全新版本可追踪|填写真实验收结果，实物通过后再另立固化节点|

**状态：可临时上板的候选版，未本版下载、屏幕/听音、Flash或可靠性验收。不是四项已经全部实物闭环。**

## 2. 本轮测试与失败记录

- TF：首次前/后台超时、持续progress不误报、error>done>timeout、同周期progress优先、初次+2次重试且延迟准确、成功/手动重置预算、文件格式等不可重试、保留bank/front/index、stream_fault禁重试。
- 故障：UF/OF/AU/TF/内存曾释放后丢失五种；装饰关闭仍显示、恢复后历史不丢、默认旧接口行为兼容；诊断像素绝不抬高内容音频门控。
- 音频：48k/74.25M标称8192样本无溢出，再构造同时push/pop；左右独立24位、192帧状态回卷/奇偶校验、静音、空包无旧音；非法输入洪泛置sticky溢出，复位清队列不重播。
- 注意：8192样本仅约0.171秒仿真音频，不是长时间实物运行。原生三相位不是PCB信号完整性测试。top用替代PLL/受控FIFO，不能称完整真实TF-SDRAM-HDMI端到端实物。
- 未改UI、缩放、实际SPI和内存单元继承证据均由逐项源哈希核实，不当成本版全部重跑。
- 首轮playlist声明顺序编译失败、top临时force恢复问题、音频自然相位无同时读写导致覆盖门槛失败及后端局部布线冲突全部留证；重新完整通过才放行。后端改为手册支持的高布局强度/拥塞优化布线，不改引脚/频率或时序例外。

新执行/继承报告索引见`VERSION_STATUS.json`与`05_td/v103_audio_spectrum_bitgen_attempt{args.bitgen_attempt}/attempt.json`。

## 3. 最终整机资源（综合attempt{args.synth_attempt}）

|资源|使用/容量|占比|较v102|
|---|---:|---:|---:|
{resources}

没有新增BRAM、DSP或PLL。不要把独立缩放模块资源当整机资源。

## 4. 最终时序与边界（物理attempt{args.physical_attempt}，hold-fix之后）

SWNS {sl['SWNS']:+.3f}ns，STNS {sl['STNS']:.3f}ns，HWNS {sl['HWNS']:+.3f}ns，HTNS {sl['HTNS']:.3f}ns。以`sdram_pr.timing`和`sdram_phy.ts`为准，不用hold-fix前的中间报告替代最终结论。

check_timing计数：`{json.dumps(b['check_timing_counts'],ensure_ascii=False)}`。

保留PHY-7002/33异常输入延时等审查边界；SDRAM内部DQ/SiP/PVT/全地址BIST、板卡20～30分钟实物稳定性仍开放。只给SRAM候选，不据此自动写Flash。

## 5. 推荐位流

工作位流：`{bit}`

字节数：{bit.stat().st_size}；SHA256：`{sha(bit)}`。

完整归档目标：`{archive}`。

最终综合报告/数据库另存`04_evidence/v103_final_synthesis_preserved`，保留{len(kept)}份文件；布局布线与守门记录在`05_td`。

本版不改TF/Flash，不重装驱动。完整源码/记录保留，不生成交接ZIP。
'''
(r/'03_docs/v103_四项优化与验收矩阵.md').write_text(report,encoding='utf8')
readme=f'''# v103：四项收尾优化候选

**已完成代码、仿真、综合、布局布线与受保护位流生成；未本版实物验收。**

新增：10秒无实际帧缓存写入进展保护、传输类故障最多2次自动重试、后台失败保持旧图；装饰UI隐藏后故障历史仍可看见；连续PCM/队列异常验证和统一验收入口。

- 先看：`03_docs/v103_上板测试步骤.md`
- 四项矩阵/资源/最终时序：`03_docs/v103_四项优化与验收矩阵.md`
- 错误码/自动重试范围/脚本入口：`03_docs/v103_错误码与工程入口.md`
- 如实填写：`03_docs/v103_上板结果记录.md`
- 唯一新候选：`03_bitstreams/v103_acceptance_robustness_720p.bit`（{bit.stat().st_size}字节）
- SHA256：`{sha(bit)}`

LUT {res['lut']}/19600，REG {res['reg']}/19600，BRAM9K {res['bram']}/64，DSP {res['dsp']}/29，PLL {res['pll']}/4。
最终SWNS {sl['SWNS']:+.3f}ns / HWNS {sl['HWNS']:+.3f}ns；数值通过不是正式可靠性/PVT签核。

保持原TF四图及接线；TD只做JTAG/SRAM临时下载，不擦除/固化Flash。按键手势沿用v102。当前音源为内部I2S演示音，不是TF音乐播放器；缓存仍RGB332。

冻结位置：`{archive}`。继承旧位流只是历史留存，不作为本版已测或新候选。全部新增在D盘，无需交接包。
'''
(r/'README_先看这里.md').write_text(readme,encoding='utf8')
(r/'README_归档位置.md').write_text('冻结位置：`'+str(archive)+'`。工作区和快照均保持原相对路径；不要直接在冻结快照修改或编译。\n',encoding='utf8')
files=set()
for folder in ['01_project','02_tests','08_tools']:
 for p in (r/folder).rglob('*'):
  if p.is_file() and 'build' not in p.relative_to(r).parts and p.suffix.lower() in {'.v','.vh','.sv','.py','.tcl','.adc','.sdc','.prj','.ps1'}:files.add(p)
for name in ['VERSION_STATUS.json','README_先看这里.md','README_归档位置.md']:files.add(r/name)
files.add(bit)
for p in (r/'03_docs').glob('v103*'):
 if p.is_file():files.add(p)
for item in b['reviewed_reports'].values():
 for p in (r/item['path']).parent.rglob('*'):
  if p.is_file() and p.suffix not in {'.vvp','.vcd','.pyc'}:files.add(p)
for directory in [dest,bg.parent,synth.parent,phy.parent]:
 for p in directory.rglob('*'):
  if p.is_file() and 'build' not in p.relative_to(r).parts and p.suffix not in {'.vvp','.vcd','.pyc'}:files.add(p)
manifest={'version':vid,'scope':'Portable offline source/test/evidence/bit identity, not hardware acceptance','hardware_test':False,'files_sha256':{p.relative_to(r).as_posix():sha(p) for p in sorted(files)}}
(r/'04_evidence/v103_release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'version':vid,'resources':res,'delta_from_v102':delta,'slack_ns':sl,'preserved_synthesis_files':len(kept),'manifest_files':len(files),'bit_sha256':sha(bit),'archive':str(archive)},ensure_ascii=False,indent=2))
