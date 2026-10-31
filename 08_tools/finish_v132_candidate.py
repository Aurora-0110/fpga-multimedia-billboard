"""Freeze V132 candidate documentation/manifest from actual new results. No programming."""
from pathlib import Path
import json,hashlib,re,shutil,ast,datetime
R=Path(__file__).resolve().parents[1];assert '01_versions'not in R.parts
B=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v130_av_layer_ui_20261030\01_project')
A=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/R.name
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
syn=R/'05_td/v132_audio_visual_synth_attempt1';phy=R/'05_td/v132_audio_visual_physical_attempt1'
sj=json.loads((syn/'attempt.json').read_text('utf8'));pj=json.loads((phy/'attempt.json').read_text('utf8'));assert sj['completed']and pj['completed']
assert sj['source_sha256']==pj['source_sha256']
for rel,h in sj['source_sha256'].items():assert(R/rel).is_file()and sha(R/rel)==h,rel
pres=R/'04_evidence/v132_synthesis_preserved_attempt1/idx_video_gate.db';assert sha(pres)==sj['gate_db_sha256']==pj['gate_db_sha256']
checks=[]
def latest(name,glob):
 paths=sorted((R/'04_evidence').glob(glob));assert paths,glob;p=paths[-1]/'summary.json';j=json.loads(p.read_text('utf8'));assert j['passed']and j.get('complete',True),(name,p)
 checks.append(dict(name=name,path=p.relative_to(R).as_posix(),sha256=sha(p),passed=True));return p,j
ui,uj=latest('UI_874cases_4608015pixels','v132_ui_[0-9]*');font,fj=latest('all_runtime_font_pixels_65536','v132_font_datapath_[0-9]*');affected,aj=latest('eight_affected_groups','v132_affected_[0-9]*');capt,cj=latest('69cues_4299516pixels','v130_captions_[0-9]*');ctop,ctj=latest('actual_top_caption_gain_events','v130_caption_top_[0-9]*');rom,rj=latest('all13routed_initialization_memories','v132_rom_init_[0-9]*');core,kj=latest('unchanged_datapath_inherited_source_recheck','v132_unchanged_core')
assert len(rj['mapped_roms'])==13 and rj['ui_logical_pixels_checked']==32768 and len(aj['cases'])==8
# Every source fingerprint in new test summaries must still match current files.
def verify(j):
 n=0
 if isinstance(j,dict):
  for key,v in j.items():
   if key in['source_sha256','sources']and isinstance(v,dict)and v and all(isinstance(h,str)and re.fullmatch('[0-9a-f]{64}',h)for h in v.values()):
    for rel,h in v.items():
     p=Path(rel);assert not p.is_absolute()and '..'not in p.parts;assert(R/p).is_file()and sha(R/p)==h,rel;n+=1
   elif isinstance(v,(dict,list)):n+=verify(v)
 elif isinstance(j,list):
  for v in j:n+=verify(v)
 return n
for file,j in[(ui,uj),(font,fj),(capt,cj),(ctop,ctj),(rom,rj)]:assert verify(j)>0
for ent in aj['cases']:
 for summary in ent['summary_paths']:
  p=Path(summary);assert p.is_file();j=json.loads(p.read_text('utf8'));assert j['passed'];assert verify(j)>0,(ent['case'],p)
 for rel,h in j.get('source_sha256',{}).items():assert sha(R/rel)==h
old=json.loads((B/'04_evidence/v130_resource_review/summary.json').read_text('utf8'));cap=old['capacities'];res=pj['resources'];assert all(res[k]<=cap[k]for k in cap)
text=(phy/'physical/sdram_pr.timing').read_text();coverage=float(re.search(r'STA coverage\s*:\s*([\d.]+)',text).group(1));counts={m.group(1):int(m.group(2))for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',(phy/'physical/sdram_check.rpt').read_text(),re.M)}
assert counts==old['check_timing_counts'],(counts,old['check_timing_counts']);assert coverage==old['coverage_percent']
slack=pj['slack_ns'];assert all(slack[k]>=0 for k in['SWNS','STNS','HWNS','HTNS'])
assert res['bram']==old['routed_resources']['bram']-1 and res['lut']==old['routed_resources']['lut']-10
review=R/'04_evidence/v132_resource_review';assert not review.exists();review.mkdir()
metric=dict(passed=True,scope='Measured same-stage V130/V132 resources and final numeric timing; no timing/PVT/SiP/hardware signoff.',baseline_v130_synthesis=old['synthesis_resources'],synthesis_resources=sj['resources'],synthesis_delta={k:sj['resources'][k]-old['synthesis_resources'][k]for k in cap},baseline_v130_routed=old['routed_resources'],routed_resources=res,routed_delta={k:res[k]-old['routed_resources'][k]for k in cap},capacities=cap,remaining={k:cap[k]-res[k]for k in cap},utilization_percent={k:round(100*res[k]/cap[k],2)for k in cap},baseline_slack_ns=old['slack_ns'],slack_ns=slack,coverage_percent=coverage,check_timing_counts=counts,source_sha256={p.relative_to(R).as_posix():sha(p)for p in[syn/'attempt.json',phy/'attempt.json',phy/'physical/sdram_phy.area',phy/'physical/sdram_phy.ts',phy/'physical/sdram_check.rpt',phy/'physical/sdram_pr.timing',pres]},not_all_metrics_improved=True,hold_margin_small_and_3ps_lower=True,formal_release_approved=False,hardware_accepted=False)
(review/'summary.json').write_text(json.dumps(metric,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
bit=R/'03_bitstreams/v132_ui_rom_compact_720p.bit';assert not bit.exists();shutil.copy2(phy/'physical/v119_audio_pingpong_720p.bit',bit);bitsha=sha(bit)
known=['RGB332 SDRAM storage and bilinear input/output semantics unchanged.','SDRAM macro/SiP/internal DQ delays,33abnormal input delays,3dummy,2missing input,7missing output constraints remain open.','Physical CDC skew/PVT/complete-address real-device SDRAM BIST not certified.','Human lyric listening/time calibration still required.','Hold margin +0.021ns remains small and is3ps below V130.','No hardware download,Flash/TF modification or network change in V132.']
status=dict(version=R.name,baseline='v130_av_layer_ui_20261030',scope='Optimization only: existing UI font lossless storage compaction; no new user feature or key rule.',target_device='EG4S20NG88',input_clock_mhz=24,video_output='1280x720p60',recommended_bit=bit.relative_to(R).as_posix(),bit_sha256=bitsha,bit_bytes=bit.stat().st_size,rtl_change_whitelist=['01_project/rtl/visual/media_ui_overlay.v','01_project/rtl/visual/media_ui_font_packed_v132.vh'],feature_set_unchanged=True,ui_pixel_and_control_latency_unchanged=True,ui_version_label_intentionally_kept='V130',supports_show_bin=False,new_external_configs_required=False,ui_cases=874,ui_pixel_comparisons=4608015,font_runtime_checks=65536,caption_pixel_comparisons=4299516,caption_cues=69,affected_groups=8,routed_initialized_rom_blocks_verified=13,selected_synthesis_attempt=1,selected_physical_attempt=1,metrics=metric,tests=checks,performance_claim='One lessBRAM9K,10less routed LUT,22more routed registers; setup25ps higher/hold3ps lower. No faster playback or lower latency claim.',diagnostic_bit_generated=True,sram_test_pending=True,hardware_downloaded=False,hardware_accepted=False,flash_modified=False,tf_modified=False,network_settings_changed=False,automatic_disconnect_scheduled=False,formal_release_approved=False,known_open_review=known)
(R/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
readme=f'''# V132 只优化现有版本：UI字库无损压缩候选

日期2026-10-31；VF-E20NG88 / EG4S20NG88 / 24MHz。

**不再实施V131扩展计划。现有功能、按键、UI布局/字号/全部像素和视频延迟不变；没有SHOW.BIN功能，也无需往TF放新文件。**

## 可临时测试位流

`{A / '01_project' / bit.relative_to(R)}`

SHA256：`{bitsha}`；{bit.stat().st_size} bytes。

只推荐先做**SRAM临时测试**；本轮未下载、未固化、未改TF或网络。旧V130完整保留作回退。屏幕UI标题仍显示V130是有意保留像素不变，版本以文件名/本状态和SHA256区分，不是下载错位流。

## 实际改动与收益（不是全面提速）

- 逐字证明16x16中文UI字库两侧全零列及底部全零行可省去，保留原字形每个像素，再无损打包到三个512x18原生9K ROM。
- UI字体从4块BRAM9K降至3块；整个工程62→61。原标签/文本ROM、字幕/Logo字库、音频/SDRAM/PLL/引脚/SDC不变。
- **路由后**LUT17749→17739，REG10654→10676，BRAM9K62→61，DSP17不变。综合LUT17510→17554，不能只拿路由结果冒称综合LUT也降低。
- setup SWNS +0.642→+0.667ns；hold HWNS +0.024→+0.021ns，STNS/HTNS0。hold小幅变差且余量仍小，不能宣传所有指标提升/正式时序签核。
- 不改变48k音频、720p刷新、读卡速度或播放延迟，不承诺本轮切图更快。

## 本轮新验证

- 全部128字槽：65536次实际ROM寻址/bit/bank/动态覆盖路径检查，独立字体源oracle；零边缘不是裁字。
- 874组UI状态、106917实际字格、4608015对齐像素、五个720p栅格；三个保存预览PNG与V130逐字节一致。
- 八组受影响回归：11档音量/前端、HDMI包/原生ODDR、整机接线、频谱/DFT/OSD、UI音频、媒体手势/UI。
- 69条字幕端点/暂停冻结及4299516字幕像素；真实top字幕/音量事件接线。
- 新综合、布局布线、四项slack非负及13块路由初始化ROM逐位检查通过；合成数据库单独保存在04_evidence，归档不依赖可重建build目录。
- 12份TF/SPI/FAT32/SDRAM/缩放核心历史报告及来源哈希重新核对，明确是继承证据，**不是本轮全链路重测/完整地址实物BIST**。

## 请这样实测（TF不动、Flash先不动）

1. 用TD下载上面V132 `.bit`到SRAM，确认四图轮播、720p持续稳定，无黑屏/花字。
2. 长K1独立显隐UI，观察中文、音量、亮度/对比度和错误状态不缺笔画、不变位置；双键短按四态图层正常。
3. 长K0进入音频控制，短K1轮流测试三WAV，短K0暂停/继续；保持声音/字幕位置、音量11档和UI显隐原行为。
4. 听音至少10分钟，并同时切图/显隐UI；L6/A3不能新增。字幕继续按真实样本计数，人工歌词听校是独立事项。
5. 把“屏幕/声音/按键是否与V130一致、是否出现A3或无信号”告诉我。通过前不要替换现有Flash。

## 维护与边界

- 工作副本内跑：`python -B 02_tests/ui/run_v132_ui.py`，再`02_tests/media_controls/run_v130_media.py`及`08_tools/run_v132_affected.py`；旧`tb_v130_ui`检查旧内部RAM名，保留为历史，不作为V132入口。
- `08_tools/generate_v132_ui_font.py`默认只读校验；`--write`仅允许工作副本。不要用旧字库生成器更改字体后绕过压缩前提。
- `02_tests/ui/check_v132_rom_init.py`检查的是本版真实路由网表；不是RTL空壳仿真。归档快照不直接跑会写报告的脚本。
- RGB332、SDRAM宏/SiP/内部DQ延时、CDC/PVT/全地址实物BIST、歌词听校仍是原边界。33abnormal/3dummy/2no-input/7no-output计数未被豁免。

归档：`{A}`。保留旧版；**无需交接ZIP**，不执行或安排断网。
'''
(R/'README_先看这里.md').write_text(readme,encoding='utf8')
(R/'README_归档位置.md').write_text(f'# V132归档位置\n\n{A}\n\n本版优化候选；源码/TB/约束/TD/位流/日志完整保存，无交接ZIP；快照冻结。\n',encoding='utf8')
doc='# V132同阶段资源、时序与真实收益\n\n只优化现有UI存储，未扩展功能、未改引脚/时钟/SDC。\n\n|资源|V130综合|V132综合|V130路由|V132路由|容量|\n|---|---:|---:|---:|---:|---:|\n'+''.join(f"|{k}|{old['synthesis_resources'][k]}|{sj['resources'][k]}|{old['routed_resources'][k]}|{res[k]}|{cap[k]}|\n"for k in cap)
doc+='\n'+f"最终setup{slack['SWNS']:+.3f}ns、hold{slack['HWNS']:+.3f}ns，STNS/HTNS0，覆盖{coverage}%。setup增加0.025ns、hold降低0.003ns；REG增加22，DSP不变。不能把本轮称为所有指标改善，也没有性能倍数或更快播放的实物数据。\n\n"
doc+='UI显式存储26880有效位，分配27648位（三512x18块），原逻辑32768位；被省46个全零像素/字槽仍以0解码。保持原16x16字形、2倍屏幕显示、五拍视频同步延迟；字体完整性32768像素和运行期65536检查通过。UI版本标题V130保留以保证逐像素不变。\n\n'
doc+='最终13路由ROM=UI4（文本1+字体3）+字幕6（文本1+字体5）+时间轴1+Logo2；内容和原生parity位全部核对。\n\n'
doc+='未关闭：33abnormal input delay、3dummy、2missing input、7missing output；RGB332缓存、宏/SiP/内部DQ、CDC/PVT及全地址实物BIST、人工歌词听校。新版本无硬件/Flash/TF验收；可先SRAM测试，不能直接替换固化版本。\n'
(R/'03_docs/v132_资源时序与优化边界.md').write_text(doc,encoding='utf8')
(R/'03_docs/v132_本轮操作记录.md').write_text('# V132实施记录\n\n- 2026-10-31：按用户要求取消扩展实施；以V130为功能基线。V131为历史方案包，不作新固件。\n- 发现另一个v131_flash_release工作目录，但检查生产文件与V130逐字节相同；未移动/删除/覆盖该目录。新工作副本独立建立。\n- 仅修改media_ui_overlay.v并新增packed初始化表；通过独立字体/像素oracle。\n- 真综合1次、布局布线1次，均保留完整日志、数据库与报告；没有降低时钟或改变ADC/SDC。\n- 路由数量/时序记录见资源说明；回归和路由初始化审查通过，不声称完整硬件可靠性验收。\n- 新输出均在D盘；不清理C盘、不改网络、不写TF/Flash、不新建交接ZIP。\n',encoding='utf8')
# Check all newly added scripts syntax without creating pycache.
news=[R/'08_tools'/n for n in['prepare_v132_ui_compact.py','build_v132_candidate.py','run_v132_affected.py','check_v132_unchanged_core.py','generate_v132_ui_font.py','finish_v132_candidate.py']]+[R/'02_tests/ui'/n for n in['run_v132_ui.py','check_v132_rom_init.py']]+[R/'02_tests/ui_compact/run_v132_font_datapath.py']
for p in news:ast.parse(p.read_text('utf-8-sig'))
(review/'new_scripts_syntax.json').write_text(json.dumps(dict(passed=True,scripts=len(news),source_sha256={p.relative_to(R).as_posix():sha(p)for p in news}),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
# Release subset: current sources/tests/scripts/status/docs/new reports+their independent inputs,
# and preserved synthesis database. Full archive separately includes all historical files.
files=set(p for p in(R/'01_project').rglob('*')if p.is_file())
files.update([bit,R/'VERSION_STATUS.json',R/'README_先看这里.md',R/'README_归档位置.md',R/'03_docs/v132_资源时序与优化边界.md',R/'03_docs/v132_本轮操作记录.md'])
newdirs=[p.parent for p in[ui,font,affected,capt,ctop,rom,core]]+[review,R/'04_evidence/v132_preparation',pres.parent,syn,phy]
for ent in aj['cases']:
 for summary in ent['summary_paths']:newdirs.append(Path(summary).parent)
for d in newdirs:
 files.update(p for p in d.rglob('*')if p.is_file()and'build'not in p.relative_to(R).parts and p.suffix not in{'.vvp','.vcd','.pyc'})
files.update(news);files.update([R/'02_tests/ui/tb_v132_ui.sv',R/'02_tests/ui_compact/tb_v132_font_datapath.sv'])
for p in[R/'03_docs/v130_caption_spec.json',R/'03_docs/v130_ui_font_spec.json',R/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf']:files.add(p)
assert all(p.is_relative_to(R)for p in files)
m=dict(version=R.name,baseline='v130_av_layer_ui_20261030',recommended_bit=bit.relative_to(R).as_posix(),bit_sha256=bitsha,preserved_gate_db=pres.relative_to(R).as_posix(),gate_db_sha256=sha(pres),hardware_accepted=False,formal_release_approved=False,files={p.relative_to(R).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(files)})
(R/'V132_RELEASE_MANIFEST.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(version=R.name,bit=str(bit),bit_sha256=bitsha,resources=res,slack=slack,coverage=coverage,release_files=len(files),archive=str(A),hardware_tested=False),ensure_ascii=False,indent=2))
