# Finish a guarded V130 SRAM candidate. Never programs hardware/media/network.
from pathlib import Path
import datetime,hashlib,json,shutil,subprocess,sys
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
version='v130_av_layer_ui_20261030';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
archive=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/version
bgp=r/'05_td/v130_sample_caption_bitgen_attempt1/attempt.json';bg=read(bgp);assert bg['completed']and bg['full_user_text_covered']
bit=r/'03_bitstreams/v130_av_layers_rounded_720p.bit';assert sha(bit)==bg['bit_sha256']
metrics=read(r/'04_evidence/v130_resource_review/summary.json');assert metrics['passed']
for name,e in bg['reviewed_reports'].items():assert sha(r/e['path'])==e['sha256'],name
syn=r/'05_td/v130_audio_visual_synth_attempt2/build/idx_video_Runs/syn_1';pres=r/'04_evidence/v130_synthesis_preserved/original_build/idx_video_Runs/syn_1';assert not pres.exists();shutil.copytree(syn,pres)
assert sha(pres/'idx_video_gate.db')==bg['synth_gate_sha256']
spec=read(r/'03_docs/v130_caption_spec.json');assert len(spec['cues'])==69
known=metrics['known_open_review']+[
'Unchanged automatically aligned sample timelines require human listening; HDMI sink latency not verified.',
'ChillRoundM11px in12x12 bitmap enlarged3x to36px; not full36px anti-aliased vector rendering.',
'Third track follows original first-extra-WAV rule; no runtime song hash/ASR/SRT.',
'Spectrum and subtitles are ONE combined AV visibility group, separate from base OSD.',
'12inherited core reports hash-proven; diagnostic first_error excluded and freshly tested.',
'No download,cold-start,endurance,PVT,complete-address physical BIST or Flash acceptance.']
status=dict(version=version,date=datetime.datetime.now().astimezone().isoformat(),baseline='v129_third_track_captions_20261030',target='VF-E20NG88/EG4S20NG88/24MHz/1280x720/RGB332',code_written=True,simulation_regressions_passed=True,synthesis_completed=True,physical_numerical_timing_passed=True,diagnostic_bit_generated=True,recommended_bit=bit.relative_to(r).as_posix(),bit_sha256=sha(bit),bit_bytes=bit.stat().st_size,layers=dict(base='Logo/time/slogan OSD',av='spectrum+subtitles',short_chord_cycle=['11','10','01','00'],frame_committed=True,ui_visibility_independent=True,layer_change_restarts_audio=False),persistent_volume_row=True,subtitle_font='ChillRoundM v1.805 SIL OFL1.1;11px raster into12x12,3x36px display',subtitle_cell_px=36,subtitle_source_matrix_px=12,subtitle_monochrome=True,diagnostic_pipeline_cycles=4,enabled_cues=69,caption_tracks=[1,3],full_user_text_covered=True,caption_text_and_sample_times_unchanged=True,human_timing_verified=False,transcript_human_verified=False,actual_sample_count_sync=True,pause_freeze=True,mute_continues=True,hardware_downloaded=False,hardware_accepted=False,flash_modified=False,tf_modified=False,network_settings_changed=False,automatic_disconnect_scheduled=False,formal_release_approved=False,selected_synthesis_attempt=2,selected_physical_attempt=2,failed_physical_attempt1_preserved=True,metrics=metrics,reviewed_reports=bg['reviewed_reports'],unchanged_core_evidence_explicitly_inherited=True,preserved_gate_db=(pres/'idx_video_gate.db').relative_to(r).as_posix(),known_open_review=known)
(r/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
new=metrics['routed_resources'];old=metrics['baseline_v129_routed'];slack=bg['slack_ns']
readme=f'''# V130 独立音画图层·常驻音量·大号圆润字幕

## 三项改动

1. 原Logo/计时/标语OSD为基础图层；频谱+字幕为独立音画图层。双键短按四态循环，帧边界提交；不重启WAV或字幕计数，不改变图片与HDMI声音。
2. 原中文双列UI扩展至16行，仍保留亮度/对比度，常驻音量百分比与音画图层状态。长按K1独立显隐UI；真实故障诊断不允许隐藏。
3. 字幕采用ChillRoundM开源圆体，12×12单色点阵三倍显示为36px（原为24px），720p底部居中。受字库资源限制，并非36px抗锯齿矢量字。

## 本次唯一推荐SRAM临时位流

{archive / '01_project/03_bitstreams/v130_av_layers_rounded_720p.bit'}

SHA256：{sha(bit)}
大小：{bit.stat().st_size} bytes。

**只做SRAM临时测试；未自动下载/固化。TF文件不需要重写。目录旧版位流/Flash资料为历史参考，不是V130。**

## 按键

- 双键短按（约0.1~0.3秒并同时松开）：全部显示 → 仅原Logo/OSD → 仅频谱与字幕 → 两组均隐藏 → 全部显示。
- 单独长按K1（约1秒后松开）：独立UI显隐，不切歌、不暂停。
- 单独长按K0：进入/退出音频控制；该模式短按K1切音源，短按K0暂停/继续。
- 双键长按每次约1秒后松开：浏览 → 亮度 → 对比度 → 音量 → 浏览；退出音频控制页面，但不重启音乐。在音量项，短按K0减10%、K1加10%，0%静音、100%原幅度。
- 调参时单独长按K1会回到浏览并切换UI固定显示状态；短双键仍只切图层。
- 图层切换可唤醒UI；纯画面需再长按K1隐藏UI。故障条不能隐藏。

## 建议实测

1. 临时下载本版，等图片正常后进入MUSIC。双键短按循环四态：频谱/字幕成组显隐，原Logo/标语独立；声音持续、进度不重置。切换在对齐的视频帧生效。
2. 有歌词时暂停5秒再继续，字幕冻结/恢复；切图层不能引起暂停或A3/L6。广告无音乐歌词；第三音源约30.41秒才有第一句，沿用原时间轴。
3. 长K1显示UI，检查常驻音量/音画状态；调100→50→0→100应听到音量变化。静音仍继续走字幕，退出调参仍可独立显隐UI。
4. 检查字体更大、底部不截断、最长句不越界；Logo/缩放/亮度/对比度/自动手动轮播仍工作。人工听校反馈具体句号+早/晚秒数。
5. 至少10分钟连续音频并切音源/显隐UI，无新增A3、L6/L7或闪断，再考虑Flash版本；本轮不改Flash。

## 整机路由同阶段资源

|资源|V129|V130|容量|
|---|---:|---:|---:|
'''+''.join(f'|{k.upper()}|{old[k]}|{new[k]}|{metrics["capacities"][k]}|\n'for k in ['lut','reg','bram','dsp'])+f'''

Setup SWNS {slack['SWNS']:+.3f}ns，STNS {slack['STNS']:.3f}ns；Hold HWNS {slack['HWNS']:+.3f}ns，HTNS {slack['HTNS']:.3f}ns；覆盖率{metrics['coverage_percent']}%。数值通过不等于PVT/可靠性签核，余量仍有限。

## 本轮验证与修复

- 四态按键、实际top接线、69条歌词/286字、16行UI及音量检查通过；UI4608015次、字幕4299516次独立像素对照。
- 布局布线attempt1 setup -0.144ns，真实失败证据保留；定位原诊断层坐标减法+字符选择，新增一级几何寄存。诊断层3→4周期，RGB/XY/DE/HS/VS/音频可见门完整同步延迟。不降时钟、改引脚、放宽SDC或扩大例外。
- 新诊断层两模式双行179892次/音频行61269次像素、五类故障历史、单周期首次A3保存及实际top门控通过。位流来自attempt2。
- 14块路由ROM初始化含奇偶位逐位核对；合成DB另存，防止归档排除build后丢失。
- 不变TF/SPI/FAT/WAV/SDRAM证据明确哈希继承，不冒称本轮全地址实测。RGB332、宏/SiP、内部延时/CDC/PVT边界保留。
- 历史top短双键预期不再适用，另建V130四态TB；旧双行font oracle缺Q/=已补独立真值。失败记录保留，不改RTL迎合过时预期。
- 歌词原文与时间轴未改；人工听校、设备音画延迟及实物验收仍待完成。

归档：{archive}
源码/TB/约束/TD/位流/日志/字体许可证分层保存。无需交接ZIP；保持联网，不执行或安排断网。
'''
(r/'README_先看这里.md').write_text(readme.replace('|\\n','|\n'),encoding='utf-8')
(r/'README_归档位置.md').write_text(f'# V130归档位置\n\n{archive}\n\n完整工程在01_project；其内01_project为RTL/TD。快照冻结，不原地测试/编译，无ZIP。\n',encoding='utf-8')
files=set()
for folder in ['01_project','02_tests']:
 files.update(p for p in (r/folder).rglob('*')if p.is_file()and not any(q in {'.git','build','__pycache__'}for q in p.relative_to(r).parts)and p.suffix not in ['.pyc','.vvp','.vcd'])
for folder,pattern in [('03_docs','v130*'),('08_tools','*v130*'),('07_acceptance','v130*')]:files.update(p for p in (r/folder).glob(pattern)if p.is_file())
for prefix in ['04_evidence','05_td']:
 for folder in (r/prefix).glob('v130_*'):
  if folder.is_dir():files.update(p for p in folder.rglob('*')if p.is_file()and not any(q in {'build','__pycache__'}for q in p.relative_to(r).parts)and p.suffix not in ['.pyc','.vvp','.vcd'])
for e in bg['reviewed_reports'].values():files.add(r/e['path'])
files.update(p for p in (r/'07_reference/fonts/chill_round').rglob('*')if p.is_file())
files.update([bit,r/'VERSION_STATUS.json',r/'README_先看这里.md',r/'README_归档位置.md'])
m=dict(version=version,recommended_bit=bit.relative_to(r).as_posix(),bit_sha256=sha(bit),full_user_text_covered=True,human_timing_verified=False,hardware_accepted=False,formal_release_approved=False,files={p.relative_to(r).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(files)})
(r/'V130_RELEASE_MANIFEST.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
subprocess.run([sys.executable,str(r/'08_tools/verify_v130_release.py')],check=True,cwd=r)
print(json.dumps(dict(version=version,bit=str(bit),sha256=sha(bit),slack_ns=slack,archive_next=str(archive),release_files=len(files)),ensure_ascii=False,indent=2))
