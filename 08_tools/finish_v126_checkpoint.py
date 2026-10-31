"""Preserve a bounded build result honestly; never programs FPGA/Flash."""
from pathlib import Path
import json,hashlib,shutil,datetime,re,subprocess,sys
r=Path(__file__).resolve().parents[1]
version='v126_fifo_prefix_20261030'
arc=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/version
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def latest(pattern):
 p=sorted((r/'04_evidence').glob(pattern+'/summary.json'))[-1];return p,read(p)
reports={}
for name,pattern in [('affected','v126_affected_*'),('fifo','v126_fifo_equivalence_*'),('integrations','v126_fifo_integrations_*'),('three_wav','v126_three_wav_*'),('spi','v126_extra_spi_*')]:
 p,data=latest(pattern);assert data['passed'],str(p);reports[name]=(p,data)
assert len(reports['affected'][1]['cases'])==8 and len(reports['fifo'][1]['cases'])==21
assert reports['three_wav'][1]['complete'] and len(reports['three_wav'][1]['cases'])==11
assert reports['spi'][1]['production_parameters']
syn=r/'05_td/v126_audio_visual_synth_attempt1';sj=read(syn/'attempt.json');assert sj['completed']
gate=syn/'build/idx_video_Runs/syn_1';pres=r/'04_evidence/v126_synthesis_preserved/original_build/idx_video_Runs/syn_1'
if not pres.exists():shutil.copytree(gate,pres)
assert sha(gate/'idx_video_gate.db')==sha(pres/'idx_video_gate.db')
attempts=[read(r/f'05_td/v126_audio_visual_physical_attempt{i}/attempt.json')for i in [1,2,3]]
phy=attempts[-1];success=phy['completed'];bit=r/'03_bitstreams/v126_volume_720p.bit'
if success:
 bgpath=r/'05_td/v126_volume_bitgen_attempt1/attempt.json';bg=read(bgpath);assert bg['completed'] and bit.is_file()
 rp,metrics=latest('v126_resource_review');romp,rom=latest('v126_rom_init_*');assert metrics['passed'] and rom['passed'] and len(rom['mapped_roms'])==12
 slack=phy['slack_ns'];counts=bg['check_timing_counts']
else:
 assert not bit.exists(),'Unexpected unapproved bit in published directory'
 n,pj=[(i+1,a)for i,a in enumerate(attempts)if a.get('timing_reports_present')][-1]
 text=(r/f'05_td/v126_audio_visual_physical_attempt{n}/physical/sdram_phy.area').read_text(encoding='utf-8')
 metrics=dict(last_routed_attempt=n,routed_result_failed_timing=True,synthesis_resources=sj['resources'],routed_resources={k:int(v)for k,v in re.findall(r'^#(lut|reg|bram|bram32k|dsp|pll|gclk|pad)\s+(\d+)',text,re.M)})
 slack=pj['slack_ns'];counts={}
status=dict(version=version,created_local=datetime.datetime.now().isoformat(),target=dict(board='VF-E20NG88',device='EG4S20NG88',reference_clock_hz=24000000,video='1280x720',cache='RGB332'),work_directory=str(r),archive_directory=str(arc),simulation_passed=True,verification=dict(fresh_affected_jobs=8,fifo_prefix_exhaustive_cycle_ab=21,fresh_three_wav_cases=11,fresh_production_spi_cases=1,synthesis_passed=True,selected_physical_attempt=3,selected_physical_completed=success,programmed=False,cold_boot_tested=False,formal_release_approved=False),physical_attempts=attempts,metrics=metrics,slack_ns=slack,bit_generated=success,recommended_bit=bit.relative_to(r).as_posix()if success else None,hardware_test=False,flash_modified=False,subtitle_asr_implemented=False,external_wav_captions_enabled=False,prepared_transcript_alternative_approved=False,preserved_gate_db=(pres/'idx_video_gate.db').relative_to(r).as_posix(),known_open_review=['No V126 hardware/listening/Flash/cold-start acceptance. Earlier user feedback is not inherited.','ASR not implemented. Prepared transcript/sample-clock synchronized captions await user agreement.','RGB332 cache, SDRAM macro relocation/internal abnormal delays/SiP/PVT, CDC physical skew and actual full-address BIST remain open.','Individual LUT/register/BRAM/DSP capacities do not by themselves establish legal MSlice packing or timing closure.'])
(r/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
conclusion='当前约束下数值时序通过；已生成SRAM候选位流，尚未上板实测。'if success else '本轮未取得整机物理时序通过；没有生成或发布V126位流。'
text=f'''# V126 — 平滑音量与FIFO定向优化

## 当前结论

{conclusion}

- 音量11档，0～100%，每次10%；双声道一致、增益斜坡最长256个有效样本（48kHz约5.33ms）。100%保持旧版输出上限，不额外放大。
- 长按K0+K1约1秒并松开：浏览→亮度→对比度→音量→浏览。音量项中短K0减、短K1加。长K1显隐UI并沿用退出编辑到浏览规则，数值保留。长K0音频控制；音频控制中短K0暂停/继续、短K1选音源。
- 8组本版受影响回归、21组FIFO穷举与逐周期A/B、11组三WAV、1组生产深度SPI引脚模型并行图像/音频回归通过；不是硬件验收。其他组件仅精确源码哈希或明确声明的FIFO函数等价继承，不把旧失败聚合报告当通过。
- 没有音频转文字：外部WAV字幕仍关闭；现有DEMO提示不是歌词。真实预制字幕稿按样本同步方案等待用户确认。详见03_docs/v126_字幕请求_未实现项与可选方案.md。
- 详见VERSION_STATUS.json及05_td/v126_audio_visual_physical_attempt1~3。失败尝试完整保留，不覆盖、不豁免、不冒充通过。
- 全部新文件在D盘，无自动下载、TF写入、Flash、驱动或安全配置操作，无交接ZIP。
- 保留RGB332、SDRAM宏/SiP/PVT/内部延时、CDC与完整地址实物BIST边界。

## 用户下一步

'''
if success:
 text+='仅将03_bitstreams/v126_volume_720p.bit临时下载到SRAM，先不固化，不改TF。按03_docs/v126_操作与测试步骤.md验证100→50→0→100、静音持续播放、暂停/继续、三音频切换和UI显隐；检查没有新A3/L6和视频丢信号。建议连续播放至少10分钟，再单独记录本版实测。\n'
else:
 text+='保留板卡当前已实测通过的程序，不改TF、不重写Flash。本轮只有源码和测试证据，没有新增推荐位流。下一步应基于SD仲裁与TMDS具体关键路径修改，不放宽SDC或无限重复布局。操作步骤文档仅预先说明音量测试，不能视为已有对应bit。\n'
(r/'README_先看这里.md').write_text(text,encoding='utf-8')
(r/'README_归档位置.md').write_text(f'# 归档位置\n\n{arc}\n\n冻结工作树在01_project，实际RTL/TD工程在01_project/01_project。无需交接ZIP。\n',encoding='utf-8')
if success:
 files={p for p in (r/'01_project').rglob('*')if p.is_file() and 'build' not in p.parts}
 files.update([p for p,_ in reports.values()]);files.update(r/x['path']for x in bg['reviewed_reports'].values())
 files.update([r/'VERSION_STATUS.json',r/'README_先看这里.md',r/'README_归档位置.md',r/'08_tools/verify_v126_release.py',r/'08_tools/finish_v126_checkpoint.py',r/'02_tests/audio_visual/run_v126_bitgen.py',bit,bgpath,syn/'attempt.json',r/'05_td/v126_audio_visual_physical_attempt3/attempt.json',pres/'idx_video_gate.db',rp,romp])
 files.update(p for p in (r/'03_docs').glob('v126*')if p.is_file())
 manifest=dict(version=version,recommended_bit=bit.relative_to(r).as_posix(),slack_ns=slack,check_timing_counts=counts,fifo_equivalence_cases=21,files={p.relative_to(r).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(files)})
 (r/'V126_RELEASE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 subprocess.run([sys.executable,str(r/'08_tools/verify_v126_release.py')],check=True,cwd=r)
print(json.dumps(dict(version=version,bit_generated=success,slack_ns=slack,metrics=metrics,archive_next=str(arc)),ensure_ascii=False,indent=2))
