"""Freeze V128 release metadata only after fresh guarded bitgen; no hardware."""
from pathlib import Path
import json,datetime,hashlib,shutil,subprocess,sys
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
version='v128_lyrics_alignment_20261030';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
archive=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/version
bgp=r/'05_td/v128_sample_caption_bitgen_attempt1/attempt.json';bg=read(bgp);assert bg['completed']and bg['full_user_text_covered']
bit=r/'03_bitstreams/v128_sample_captions_720p.bit';assert sha(bit)==bg['bit_sha256']
respath=r/'04_evidence/v128_resource_review/summary.json';metrics=read(respath);assert metrics['passed']
spec=read(r/'03_docs/v128_caption_spec.json');assert len(spec['cues'])==53 and spec['full_user_text_covered']
syn=r/'05_td/v128_audio_visual_synth_attempt1/build/idx_video_Runs/syn_1';pres=r/'04_evidence/v128_synthesis_preserved/original_build/idx_video_Runs/syn_1';assert not pres.exists();shutil.copytree(syn,pres)
assert sha(pres/'idx_video_gate.db')==bg['synth_gate_sha256']
for name,entry in bg['reviewed_reports'].items():assert sha(r/entry['path'])==entry['sha256'],name
spi=[]
for p in sorted((r/'04_evidence').glob('v128_extra_spi_*/summary.json')):
 j=read(p);spi.append(dict(path=p.relative_to(r).as_posix(),sha256=sha(p),passed=j['passed'],cases=j['cases']))
status=dict(version=version,date=datetime.datetime.now().astimezone().isoformat(),baseline='v127_sample_captions_20261030',target='VF-E20NG88/EG4S20NG88/24MHz/1280x720/RGB332',scope='Full exact user-provided lyrics, dual local forced alignment, actual consumed-WAV sample synchronization, lossless packed glyphs.',code_written=True,simulation_regressions_passed=True,synthesis_completed=True,physical_numerical_timing_passed=True,diagnostic_bit_generated=True,recommended_bit=bit.relative_to(r).as_posix(),bit_sha256=sha(bit),bit_bytes=bit.stat().st_size,source_lyric_lines=52,enabled_cues=53,source_text_received=True,full_user_text_covered=True,complete_lyrics=True,human_timing_verified=False,transcript_human_verified=False,timing_review_cue_count=len(spec['timing_review']),subtitle_recognition_on_fpga=False,actual_sample_count_sync=True,pause_freeze=True,mute_continues=True,track_session_reset=True,old_demo_subtitles_and_progress_in_active_design=False,hardware_downloaded=False,hardware_accepted=False,flash_modified=False,tf_modified=False,formal_release_approved=False,metrics=metrics,reviewed_reports=bg['reviewed_reports'],fresh_production_spi_attempts=spi,unchanged_core_evidence_explicitly_inherited=True,preserved_gate_db=(pres/'idx_video_gate.db').relative_to(r).as_posix(),known_open_review=metrics['known_open_review']+['Fresh600s production-SPI run timeout retained, not relabelled PASS or looped; V127 complete passing pin-level evidence inherited after core source equivalence proof.','Automatic timing preparation is not human listening calibration. Parenthetical adlib/chorus and sentence onsets still need listening.','No download/Flash/TF writes or new hardware display/listening/cold-start/endurance/sink-latency acceptance.'])
(r/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
new=metrics['routed_resources'];old=metrics['baseline_v127_routed'];slack=bg['slack_ns']
readme=f'''# V128 完整用户歌词·真实样本同步候选

## 结论

已生成新的SRAM临时测试候选。用户提供的52行歌词全部接入，形成53条字幕；不再是13句局部草稿。原ASR错字改用用户原文，结尾两句间保留约3.75秒停顿。没有旧演示字幕和固定时长进度条。

两套本地模型对原MUSIC.WAV强制对齐，**尚未逐句人工听校**；不是FPGA实时语音识别。和声、句首及“我胡了”等弱支持处仍需核实，不称为最终准确时间轴。

真实WAV消费样本驱动暂停冻结/继续同步/音量0继续/切歌与EOF清空。字库197字、12x12完整字形，144bit无损打包，保持4拍像素链路。

## 临时位流

{archive / '01_project/03_bitstreams/v128_sample_captions_720p.bit'}

SHA256：{sha(bit)}

TF原文件不改，不固化Flash；先做SRAM临时测试。

## 同阶段路由后资源

|资源|V127|V128|容量|
|---|---:|---:|---:|
'''+''.join(f'|{k.upper()}|{old[k]}|{new[k]}|{metrics["capacities"][k]}|\n'for k in ['lut','reg','bram','dsp'])+f'''

SWNS {slack['SWNS']:+.3f}ns，STNS {slack['STNS']:.3f}ns；HWNS {slack['HWNS']:+.3f}ns，HTNS {slack['HTNS']:.3f}ns。

不改时钟/引脚/SDC。数值通过不等于正式PVT/SiP/可靠性签核；原内部延时/CDC/RGB332/完整地址实物BIST边界保留。

## 验证与限制

新8组受影响回归、53条字幕端点、暂停/静音/切歌、3442014次像素对照、全197字、实际top事件接线及11组三WAV缓存/控制场景通过。路由后13块ROM逐位检查含INITP。

未改的TF/SDRAM/scaler/FIFO等核心经哈希证明，明确继承V127已通过证据，不冒称重跑。新的600秒SPI测试超时保留，没有循环重试或写成通过。

## 现在如何测试

1. 临时下载本版SRAM，TF和Flash不动。
2. 长K0进入音频控制，短K1选择音乐文件，从头播放；长K1收起UI。前约28.39秒是前奏无字幕。
3. 核对全曲字幕、暂停5秒再继续、音量0再恢复、切歌清空和切回重置。
4. 重点听校约116.42秒插话、约164.79秒句首与208.59至212.34秒停顿。
5. 本版未自动下载/实听/实看或固化。先反馈早晚偏差再做最终版。

03_docs中v128文档包含完整边界、资源与操作说明；06_test_media/captions_music_user保存用户原文、SRT、纠错对照及时间轴。改SRT/放TF不会动态更新ROM；更换录音或剪辑需重新对齐与编译。

全部新文件在D盘，旧版本保留，无需交接ZIP。
'''
(r/'README_先看这里.md').write_text(readme,encoding='utf-8')
(r/'README_归档位置.md').write_text(f'# V128归档位置\n\n{archive}\n\n完整工作树在01_project，其内01_project是RTL/TD工程。冻结后不原地运行。无需交接ZIP。\n',encoding='utf-8')
files=set()
for folder in ['01_project','02_tests']:
 files.update(p for p in (r/folder).rglob('*')if p.is_file()and not any(part in {'.git','build','__pycache__'}for part in p.relative_to(r).parts)and p.suffix not in ['.pyc','.vvp','.vcd'])
for folder,pattern in [('03_docs','v128*'),('08_tools','*v128*'),('06_test_media/captions_music_user','*'),('07_acceptance','v128*')]:files.update(p for p in (r/folder).glob(pattern)if p.is_file())
for entry in bg['reviewed_reports'].values():files.add(r/entry['path'])
for folder in ['04_evidence/v128_synthesis_preserved','05_td/v128_audio_visual_physical_attempt1','05_td/v128_sample_caption_bitgen_attempt1']:files.update(p for p in (r/folder).rglob('*')if p.is_file())
files.update([bit,bgp,respath,r/'VERSION_STATUS.json',r/'README_先看这里.md',r/'README_归档位置.md',r/'05_td/v128_audio_visual_synth_attempt1/attempt.json'])
files.update(r/x['path']for x in spi)
m=dict(version=version,recommended_bit=bit.relative_to(r).as_posix(),bit_sha256=sha(bit),full_user_text_covered=True,human_timing_verified=False,hardware_accepted=False,formal_release_approved=False,files={p.relative_to(r).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(files)})
(r/'V128_RELEASE_MANIFEST.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
subprocess.run([sys.executable,str(r/'08_tools/verify_v128_release.py')],check=True,cwd=r)
print(json.dumps(dict(version=version,bit=str(bit),sha256=sha(bit),slack_ns=slack,archive_next=str(archive)),ensure_ascii=False,indent=2))