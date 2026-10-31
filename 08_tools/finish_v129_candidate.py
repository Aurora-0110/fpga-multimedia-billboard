"""Finish guarded V129 candidate metadata only; no media, hardware or network changes."""
from pathlib import Path
import json,datetime,hashlib,shutil,subprocess,sys
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
version='v129_third_track_captions_20261030';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
archive=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/version
bgp=r/'05_td/v129_sample_caption_bitgen_attempt1/attempt.json';bg=read(bgp);assert bg['completed']and bg['full_user_text_covered']
bit=r/'03_bitstreams/v129_sample_captions_720p.bit';assert sha(bit)==bg['bit_sha256']
respath=r/'04_evidence/v129_resource_review/summary.json';metrics=read(respath);assert metrics['passed']
spec=read(r/'03_docs/v129_caption_spec.json');assert len(spec['cues'])==69 and [t['cue_count']for t in spec['tracks']]==[53,16]
syn=r/'05_td/v129_audio_visual_synth_attempt1/build/idx_video_Runs/syn_1';pres=r/'04_evidence/v129_synthesis_preserved/original_build/idx_video_Runs/syn_1';assert not pres.exists();shutil.copytree(syn,pres)
assert sha(pres/'idx_video_gate.db')==bg['synth_gate_sha256']
for name,entry in bg['reviewed_reports'].items():assert sha(r/entry['path'])==entry['sha256'],name
known=metrics['known_open_review']+['Automatic per-line timing is not human listening calibration or HDMI sink audio/video latency acceptance.','Third-track identity uses existing first-extra-WAV rule. It must be the only additional WAV; runtime FPGA does not hash-match songs.','Commentary before30.410s and after130.040s has no user-supplied captions and stays clear.','Identical TF/FAT32/WAV/FIFO/SDRAM/SPI core evidence is explicitly inherited after source proof; not rerun or falsely hardware accepted.','No programming,TF/Flash changes,physical10min testing,cold-start,endurance,complete-address BIST or PVT signoff.']
status=dict(version=version,date=datetime.datetime.now().astimezone().isoformat(),baseline='v128_lyrics_alignment_20261030',target='VF-E20NG88/EG4S20NG88/24MHz/1280x720/RGB332',scope='Two independent exact-user-text subtitle timelines; existing MUSIC preserved, third audio16new cues. Shared512x18 metadata,9bit text IDs and4+1 lossless font banks.',code_written=True,simulation_regressions_passed=True,synthesis_completed=True,physical_numerical_timing_passed=True,diagnostic_bit_generated=True,recommended_bit=bit.relative_to(r).as_posix(),bit_sha256=sha(bit),bit_bytes=bit.stat().st_size,source_lyric_lines=68,enabled_cues=69,caption_tracks=[1,3],track_cue_counts={'MUSIC':53,'THIRD':16},glyphs=286,full_user_text_covered=True,music_existing53_cues_retained_exactly=True,human_timing_verified=False,transcript_human_verified=False,subtitle_recognition_on_fpga=False,actual_sample_count_sync=True,pause_freeze=True,mute_continues=True,track_session_reset=True,old_demo_subtitles_and_progress_in_active_design=False,advertisement_subtitles=False,hardware_downloaded=False,hardware_accepted=False,flash_modified=False,tf_modified=False,network_settings_changed=False,automatic_disconnect_scheduled=False,formal_release_approved=False,metrics=metrics,reviewed_reports=bg['reviewed_reports'],unchanged_core_evidence_explicitly_inherited=True,preserved_gate_db=(pres/'idx_video_gate.db').relative_to(r).as_posix(),tracks=spec['tracks'],known_open_review=known)
(r/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
new=metrics['routed_resources'];old=metrics['baseline_v128_routed'];slack=bg['slack_ns']
readme=f'''# V129 两首音频独立字幕·SRAM测试候选

## 已完成

- MUSIC原有52行/53条字幕原文与时间轴逐项保留。
- 第三音源《突然的陀螺》16行完整用户原文接入独立时间轴，约30.41秒首句、130.04秒末句结束；前后解说不擅自补字幕。
- 实际消费WAV样本同步：暂停冻结、继续同步、静音继续、切歌/EOF/错误清空；广告不显示音乐字幕。
- 不是在线语音识别，不从TF动态读取SRT。自动强制对齐**仍需人工听校**。
- 共69条、286字，文本9bitID；字库144bit完整像素无损打包、显式4+1块BRAM，只新增一块BRAM，不复制整套播放器。

## 临时测试位流

{archive / '01_project/03_bitstreams/v129_sample_captions_720p.bit'}

SHA256：{sha(bit)}

大小：{bit.stat().st_size} bytes。只做SRAM临时测试，未替你下载或固化Flash。
TF保持原文件；第三音源沿用根目录首个额外WAV，除MUSIC.WAV与ADVOICE.WAV外请只保留本曲，避免字幕配错。

## 路由后同阶段对比

|资源|V128|V129|容量|
|---|---:|---:|---:|
'''+''.join(f'|{k.upper()}|{old[k]}|{new[k]}|{metrics["capacities"][k]}|\n'for k in ['lut','reg','bram','dsp'])+f'''

SWNS {slack['SWNS']:+.3f}ns，STNS {slack['STNS']:.3f}ns；HWNS {slack['HWNS']:+.3f}ns，HTNS {slack['HTNS']:.3f}ns；STA覆盖{metrics['coverage_percent']}%。
数值通过，但setup/hold余量小于V128，不宣称时序裕量全面改善或PVT签核。
不降低时钟、不改引脚/PLL/SDC、不扩大时序豁免；RGB332、SDRAM宏/SiP/内部延时/CDC/完整地址实物BIST等原边界保留。

## 本轮验证

69条两银行字幕端点与暂停/静音/切歌、3587262次独立像素对照、全部286字、实际top的事件/增益接线，以及8组受影响回归通过。路由后14块字幕/UI/Logo初始化ROM的全部INIT和INITP位独立核对通过。
一次综合、一次布局布线与受门控bitgen成功；未循环换种子碰运气。
不变底层的12份历史通过证据经哈希证明后明确继承，不冒称新实测或本轮重跑。

## 你下一步

1. 只临时下载以上V129位流，TF不需要重新写；暂不固化。
2. 长按K0进入音频控制，短按K1切到第三音源。约30.41秒开始字幕，前面无字幕属于预期。
3. 字幕出现后短按K0暂停5秒再继续；测试音乐→第三音源→广告→音乐无串词。
4. 长按K1显隐UI，再测试音量0→100%，字幕不能停走或重播；不应新增A3/L6。
5. 完整听两首并反馈具体句号的早/晚秒数。详细步骤见03_docs/v129_操作与听校步骤.md。

源码/TB/TD/约束/日志/位流全部保存；完整归档{archive}。无需交接ZIP。
保持联网；本轮不触碰网络设置、不安排断网，也未写TF或Flash。
'''
(r/'README_先看这里.md').write_text(readme,encoding='utf-8')
(r/'README_归档位置.md').write_text(f'# V129归档位置\n\n{archive}\n\n完整工作树在01_project，其内01_project为RTL/TD工程。快照冻结；不原地编译或改动。无需交接ZIP。\n',encoding='utf-8')
files=set()
for folder in ['01_project','02_tests']:
 files.update(p for p in (r/folder).rglob('*')if p.is_file()and not any(part in {'.git','build','__pycache__'}for part in p.relative_to(r).parts)and p.suffix not in ['.pyc','.vvp','.vcd'])
for folder,pattern in [('03_docs','v129*'),('08_tools','*v129*'),('06_test_media/captions_music_user','*'),('06_test_media/captions_third_user','*'),('07_acceptance','v129*')]:files.update(p for p in (r/folder).glob(pattern)if p.is_file())
for entry in bg['reviewed_reports'].values():
 p=r/entry['path'];files.add(p)
 files.update(f for f in p.parent.rglob('*')if f.is_file()and f.suffix not in ['.vvp','.vcd','.pyc'])
for folder in ['04_evidence/v129_synthesis_preserved','05_td/v129_audio_visual_physical_attempt1','05_td/v129_sample_caption_bitgen_attempt1']:
 files.update(p for p in (r/folder).rglob('*')if p.is_file())
for folder in (r/'04_evidence').glob('v129_*'):
 if folder.is_dir():files.update(p for p in folder.rglob('*')if p.is_file()and p.suffix not in ['.vvp','.vcd','.pyc'])
files.update([bit,bgp,respath,r/'VERSION_STATUS.json',r/'README_先看这里.md',r/'README_归档位置.md',r/'05_td/v129_audio_visual_synth_attempt1/attempt.json'])
m=dict(version=version,recommended_bit=bit.relative_to(r).as_posix(),bit_sha256=sha(bit),full_user_text_covered=True,human_timing_verified=False,hardware_accepted=False,formal_release_approved=False,files={p.relative_to(r).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(files)})
(r/'V129_RELEASE_MANIFEST.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
subprocess.run([sys.executable,str(r/'08_tools/verify_v129_release.py')],check=True,cwd=r)
print(json.dumps(dict(version=version,bit=str(bit),sha256=sha(bit),slack_ns=slack,archive_next=str(archive),release_files=len(files)),ensure_ascii=False,indent=2))
