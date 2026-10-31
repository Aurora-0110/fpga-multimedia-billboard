"""Write a truthful final V127 release record after guarded bitgen. Never programs anything."""
from pathlib import Path
import datetime,json,hashlib,shutil,subprocess,sys
r=Path(__file__).resolve().parents[1];version='v127_sample_captions_20261030';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
archive=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/version
reqs=r/'05_td/v127_sample_caption_bitgen_attempt1/attempt.json';bg=read(reqs);assert bg['completed']
bit=r/'03_bitstreams/v127_sample_captions_720p.bit';assert sha(bit)==bg['bit_sha256']
respath=r/'04_evidence/v127_resource_review/summary.json';metrics=read(respath);assert metrics['passed']
# Preserve synthesis artifacts since the global archive intentionally skips directories named build.
syn=r/'05_td/v127_audio_visual_synth_attempt1/build/idx_video_Runs/syn_1';pres=r/'04_evidence/v127_synthesis_preserved/original_build/idx_video_Runs/syn_1'
assert not pres.exists();shutil.copytree(syn,pres);assert sha(pres/'idx_video_gate.db')==bg['synth_gate_sha256']
reports={}
for name,entry in bg['reviewed_reports'].items():
 p=r/entry['path'];assert sha(p)==entry['sha256'];reports[name]=entry
status=dict(version=version,date=datetime.datetime.now().astimezone().isoformat(),scope='Partial real MUSIC caption candidate + frame geometry/transaction-address timing optimization',baseline='v126_fifo_prefix_20261030',target='VF-E20NG88 / EG4S20NG88 / 24MHz / 1280x720 / RGB332',code_written=True,simulation_regressions_passed=True,synthesis_completed=True,physical_numerical_timing_passed=True,diagnostic_bit_generated=True,recommended_bit=bit.relative_to(r).as_posix(),bit_sha256=sha(bit),bit_bytes=bit.stat().st_size,hardware_downloaded=False,hardware_accepted=False,flash_modified=False,tf_modified=False,complete_lyrics=False,transcript_human_verified=False,subtitle_recognition_on_fpga=False,prepared_music_subtitles_enabled=True,enabled_cues=13,full_editable_draft_cues=55,old_demo_subtitles_and_progress_in_active_design=False,actual_sample_count_sync=True,pause_freeze=True,mute_continues=True,track_session_reset=True,metrics=metrics,reviewed_reports=reports,preserved_gate_db=(pres/'idx_video_gate.db').relative_to(r).as_posix(),known_open_review=metrics['known_open_review']+['Full720p dual-instance memory test and production SPI first runs timed out; failed reports retained; successful bounded retries recorded separately.','WAV MUSIC source hash must match caption spec; SRT is precompiled, not runtime TF SRT parser.','No new hardware listen/display/cold-start, sink-delay, Flash or stability acceptance.'],network_state='End-of-task disconnection request pending; see separate completion network log if executed.')
(r/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf8')
(r/'README_先看这里.md').write_text(f'''# V127 — 真实样本同步字幕候选与时序优化

## 结论

已生成新的 **SRAM临时测试候选**，不是可直接固化的已验收版本。

**歌词尚未完整准确完成**：原MUSIC.WAV《那天下雨了》已在本地离线转写两次；保留55句待校对稿，只启用两模型一致的13句候选。仍未逐句人工核实，其他时间为空。不是实时语音识别；广告/第三音频未添加歌词。

## 本次修改

- 从活动链路移除旧固定16秒进度条、模拟时间标记、DEMO字幕。
- 以真实已播放的WAV双声道采样帧计数，真实数字零样本计入；预缓冲和HDMI静音保活不计。暂停冻结、继续接续，音量为零仍随文件推进，切歌/会话/EOF/故障清空。
- 字幕与两级PCM增益延迟对齐，720p底部居中、逐帧提交；保留原音量、频谱、OSD、四图轮播和双按键交互。
- 将转场几何改为帧级寄存器，仲裁同拍锁存SDRAM事务地址，切断真实关键路径。没有降低时钟、放宽SDC或省略约束。

## 实际指标（路由后，同口径）

| 项目 | V126最后一次 | V127 |
|---|---:|---:|
| LUT | 18000 | 17659 / 19600（90.10%） |
| 寄存器 | 10546 | 10581 / 19600（53.98%） |
| BRAM9K | 60 | 60 / 64（93.75%） |
| DSP | 17 | 17 / 29（58.62%） |
| SWNS | −0.708ns | +0.193ns |
| STNS | −2.999ns | 0 |
| HWNS | +0.032ns | +0.021ns |

物理slice利用率97.09%，STA覆盖99.82%。数值setup/hold通过但裕量很小；**不是正式时序、SiP/PVT或稳定性签核**。原宏/内部异常延时、CDC及完整地址实物BIST边界保留。

## 测试证据

当前源码的受影响整机回归8组、字幕计数/720p像素/PCM对齐3组、实际top字幕接线、三WAV11组（包含真实数字零样本）、reader/packer18组及长程2组、SDRAM物理总线及显示双实例A/B、SPI音频/图像联合模型、多分辨率缩放+真实SDRAM总线、仲裁/故障记录单元，以及路由后12个ROM全部初始化位复核。详见位流生成guard中的每项报告和来源哈希。

FIFO、WAV解析、预取、全720p缩放及抖动的个别旧回归仅在**全部输入源码哈希完全相同**时明确继承；不伪称本轮重跑。超时/错误断言调试报告保留，最新成功报告与其分开。

## 你现在怎样测试

1. **不改TF、不固化Flash**；先临时下载`03_bitstreams/v127_sample_captions_720p.bit`。
2. 长K0进入音频控制，短K1选择音乐文件。原MUSIC时长223.333秒；前约32秒没有启用字幕，之后只有13句候选。
3. 听音核对底部字幕；显示某句时短K0暂停5秒再继续，检查不抢跑、不从头开始。
4. 调音量到0检查字幕仍随文件推进；切广告/第三音频时不得残留音乐字幕，切回音乐应重置。
5. 验证OSD/UI显隐、四图轮播和频谱不回退，无A3/L6或丢信号。先做临时测试并单独记录本版实测，再讨论固化。

详细步骤：`03_docs/v127_操作与测试步骤.md`。
字幕校对稿：`06_test_media/captions_music_prepared/MUSIC_双引擎待校对全稿.srt`。
准确性边界：`03_docs/v127_字幕准确性与实现边界.md`。

改SRT或换歌曲并不会自动更新本位流；字幕目前编译在FPGA ROM里，需要重新生成/综合。请先校对完整歌词再做最终字幕版本。

全部新文件在D盘；未删除电脑其他个人文件，未修改驱动/安全配置/许可证，无交接ZIP。
''',encoding='utf8')
(r/'README_归档位置.md').write_text(f'# 归档位置\n\n{archive}\n\n冻结工作树在01_project，实际RTL/TD工程在01_project/01_project。保留全部旧版本。无需交接ZIP。\n',encoding='utf8')
files=set()
for folder in ['01_project','02_tests']:
 files.update(p for p in (r/folder).rglob('*')if p.is_file()and not any(part in {'build','__pycache__','.git'}for part in p.relative_to(r).parts)and p.suffix not in {'.pyc','.vvp','.vcd'})
files.update(p for p in (r/'03_docs').glob('v127*')if p.is_file());files.update(p for p in (r/'06_test_media').glob('captions_music*/*')if p.is_file())
files.update(p for p in (r/'08_tools').glob('*v127*')if p.is_file());files.update([bit,reqs,respath,r/'VERSION_STATUS.json',r/'README_先看这里.md',r/'README_归档位置.md',r/'08_tools/verify_v127_release.py',r/'08_tools/finish_v127_candidate.py'])
for entry in reports.values():files.add(r/entry['path'])
for folder in ['05_td/v127_audio_visual_physical_attempt1','05_td/v127_sample_caption_bitgen_attempt1','04_evidence/v127_synthesis_preserved']:
 files.update(p for p in (r/folder).rglob('*')if p.is_file())
files.add(r/'05_td/v127_audio_visual_synth_attempt1/attempt.json')
manifest=dict(version=version,recommended_bit=bit.relative_to(r).as_posix(),slack_ns=bg['slack_ns'],hardware_accepted=False,formal_release_approved=False,complete_lyrics=False,transcript_human_verified=False,files={p.relative_to(r).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(files)})
(r/'V127_RELEASE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
subprocess.run([sys.executable,str(r/'08_tools/verify_v127_release.py')],check=True,cwd=r)
print(json.dumps(dict(version=version,bit=str(bit),bit_sha256=sha(bit),metrics=bg['slack_ns'],archive_next=str(archive)),ensure_ascii=False,indent=2))
