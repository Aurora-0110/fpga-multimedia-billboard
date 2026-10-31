"""Finalize v112 double-sector audio / PCM FIFO / UI pipeline; never programs hardware."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,shutil
root=Path(__file__).resolve().parents[1]
if '01_versions' in root.parts:raise SystemExit('Frozen archives are read-only')
ap=argparse.ArgumentParser()
ap.add_argument('--synth-attempt',type=int,default=2)
ap.add_argument('--physical-attempt',type=int,default=2)
ap.add_argument('--bitgen-attempt',type=int,default=1)
a=ap.parse_args()
version='v112_audio_pingpong_20261027'
archive=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/version
assert not archive.exists(),'Never overwrite frozen archive'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def exact(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():assert sha(src)==sha(dst),str(dst)
 else:shutil.copy2(src,dst)
 assert sha(src)==sha(dst)
syp=root/f'05_td/v112_audio_visual_synth_attempt{a.synth_attempt}/attempt.json'
php=root/f'05_td/v112_audio_visual_physical_attempt{a.physical_attempt}/attempt.json'
bgp=root/f'05_td/v112_audio_pingpong_bitgen_attempt{a.bitgen_attempt}/attempt.json'
sy,ph,bg=map(load,(syp,php,bgp))
assert all(x.get('completed') for x in (sy,ph,bg))
assert min(ph['slack_ns'].values())>=0
assert bg['reloaded_slack_matches'] and bg['reloaded_timing_check_matches']
bit=root/'03_bitstreams/v112_audio_pingpong_720p.bit'
assert sha(bit)==bg['bit_sha256'] and bit.stat().st_size==bg['bit_bytes']
for name,h in sy['source_sha256'].items():assert sha(root/name)==h,name
for item in bg['reviewed_reports'].values():assert sha(root/item['path'])==item['sha256'],item['path']
# build is excluded by the archive utility. Preserve raw selected AND rejected
# TD synthesis artifacts outside directories named build; never change originals.
preserved=[]
for attempt in (1,a.synth_attempt):
 src=root/f'05_td/v112_audio_visual_synth_attempt{attempt}/build'
 dst=root/'04_evidence'/('v112_final_synthesis_preserved' if attempt==a.synth_attempt else f'v112_rejected_synthesis_attempt{attempt}_preserved')
 files=[]
 for f in sorted(src.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(src);q=dst/rel;exact(f,q)
  files.append(dict(path=rel.as_posix(),sha256=sha(q),bytes=q.stat().st_size))
 record=dict(selected=attempt==a.synth_attempt,original=str(src.relative_to(root)),preserved=str(dst.relative_to(root)),files=files)
 write(dst/'preservation.json',record);preserved.append(record)
# Keep usable relative-path TD .al/.prj at the same folder depth as raw build.
gate=syp.parent/'build/idx_video_Runs/syn_1'
prj=syp.parent/'td_project/idx_video.al'
runprj=prj.parent/'idx_video_Runs/syn_1/idx_video.prj'
exact(syp.parent/'build/idx_video.al',prj);exact(gate/'idx_video.prj',runprj)
refs=[]
for f in (prj,runprj):
 for n in re.findall(r'<File Path="([^"]+)"',f.read_text(encoding='utf8')):
  q=(f.parent/n).resolve();assert q.is_file() and q.is_relative_to(root),str(q)
  refs.append(dict(project=f.relative_to(root).as_posix(),source=q.relative_to(root).as_posix(),sha256=sha(q)))
write(root/'04_evidence/v112_td_project_relative_paths.json',dict(passed=True,references=refs))
area=php.parent/'physical/sdram_phy.area'
text=area.read_text(encoding='utf8')
routed={k:int(re.search(r'^#'+k+r'\s+(\d+)',text,re.M).group(1))for k in ('lut','reg','bram','bram32k','dsp','pll','gclk','pad')}
baseline_root=Path(load(root/'04_evidence/v112_origin.json')['source_frozen'])
baseline=load(root/'BASELINE_v111_VERSION_STATUS.json')
changes=[]
for f in sorted((root/'01_project').rglob('*')):
 if not f.is_file():continue
 rel=f.relative_to(root);old=baseline_root/rel
 if not old.exists() or sha(f)!=sha(old):
  changes.append(dict(path=rel.as_posix(),sha256=sha(f),previous_sha256=sha(old)if old.is_file() else None))
constraints={}
for f in sorted((root/'01_project/boards').glob('*')):
 if f.suffix.lower() not in {'.adc','.sdc'}:continue
 rel=f.relative_to(root);assert sha(f)==sha(baseline_root/rel),str(rel)
 constraints[rel.as_posix()]=sha(f)
write(root/'03_docs/v112_SOURCE_CHANGES.json',dict(baseline=str(baseline_root),changes=changes,constraints_unchanged=constraints,raw_synthesis_preservation=preserved))
open_items=[
 'Actual TF-card A3 root cause NOT proven fixed; controlled simulation is not real-card acceptance',
 'No new board download, audible playback, Flash or cold-start acceptance',
 'RGB332 SDRAM cache (HDMI1280x720 output); not full24-bit image cache',
 'SDRAM macro relocation /33 abnormal internal input annotations /dummy or external interface review /SiP/PVT/full-address real-device BIST remain open',
 'Only7 of64 BRAM9K remain; no triple image buffer implemented or assumed free',
 'WAV48k16/24 mono/stereo only; no runtime FLAC/MP3 decoder or speech recognition; EOF is not gapless looping']
status=dict(version=version,date=datetime.date.today().isoformat(),target='VF-E20NG88 / EG4S20NG88 /24MHz / HDMI1280x720',
 purpose='Dual512-byte audio prefetch +4096 PCM FIFO +aligned five-stage UI; retain original image double buffering',
 source_version='v111_audio_fault_ui_20261027',
 simulation_passed=True,synthesis_completed=True,physical_numerical_check_passed=True,new_bit_generated=True,
 hardware_download=False,hardware_acceptance=False,formal_release_approved=False,flash_modified=False,tf_files_modified=False,handoff_zip_generated=False,
 resources_synthesis=sy['resources'],resources_routed=routed,baseline_resources_routed=baseline['resources_routed'],
 slack_ns=ph['slack_ns'],baseline_slack_ns=baseline['slack_ns'],
 buffering=dict(image_frames='existing SDRAM front/back unchanged',audio_sector_banks=2,audio_bank_bytes=512,pcm_frames=4096,pcm_width_bits=48,prefill_frames=3072,low_water_frames=3584,sample_hz=48000,ui_stages=5),
 bitstream=str(bit),bitstream_relative=bit.relative_to(root).as_posix(),bit_bytes=bit.stat().st_size,bit_sha256=sha(bit),
 archive_path=str(archive),archive_bitstream=str(archive/'01_project/03_bitstreams'/bit.name),known_open_items=open_items,
 reviewed_reports=bg['reviewed_reports'],check_timing_counts=bg['check_timing_counts'],production_changes=changes,constraints_unchanged=constraints,
 selected_synthesis=str(syp.relative_to(root)),selected_physical=str(php.relative_to(root)),selected_bitgen=str(bgp.relative_to(root)))
write(root/'VERSION_STATUS.json',status)
(root/'README_归档位置.md').write_text('# v112归档位置\n\n'+str(archive)+'\n\n所有旧版本保持冻结。只在D盘工作副本开发与测试。无需交接ZIP。\n',encoding='utf8')
readme=f'''# v112：音频双扇区预取、加深PCM缓存与UI流水线

**临时SRAM测试候选；没有实物通过、没有Flash固化。真实TF卡A3根因仍待实测定位。**

## 本版做了什么

- 图像本来已采用SDRAM双帧缓存，本轮保留。
- 音频单扇区升级双512字节银行，CRC成功才提交，可与当前块解析重叠。
- PCM FIFO 2048→4096帧；预填3072、低水位3584。A3继续如实显示。
- UI长路径新增一级对齐流水线，不降频、不放宽约束；保留既有中文UI/按键、缩放、轮播、频谱、字幕和HDMI音频。

## 推荐位流（只临时下载SRAM）

{bit}

归档后同一位流：
{archive/'01_project/03_bitstreams'/bit.name}

{bit.stat().st_size}字节；SHA256：{sha(bit)}

不改TF文件、不重格式化、不写Flash。请按 `03_docs/v112_按键与SRAM测试步骤.md` 测试；确认UI为V112。

## 最终布局布线结果

LUT {routed['lut']}/19600，REG {routed['reg']}/19600，BRAM9K {routed['bram']}/64，DSP {routed['dsp']}/29，PLL {routed['pll']}/4。
SWNS {ph['slack_ns']['SWNS']:+.3f}ns，STNS0，HWNS {ph['slack_ns']['HWNS']:+.3f}ns，HTNS0。
与v111比LUT少94、BRAM多10。保持裕量仍小，SDRAM宏/内部延时/SiP/PVT边界未关闭。

## 已有证据与边界

新增36例预取、5例缓存/停顿/暂停/换源、2例旧版对照、8例播放、20例WAV解析、22例挂载；真实SPI数字模型5组合+生产深度1组合；中文UI五幅完整720p及顶层回归、新原生HDMI测试和12块ROM初始化一致性。

55ms/108.33ms是规定预填条件下5倍加速的虚拟供数停顿，不是实际卡响应时长保证。未改BMP/缩放/TMDS/抖动证据只继承SHA相同记录，不冒称新执行。发布选取明细见VERSION_STATUS.json。

最初路由SWNS-0.279ns被拒绝；改UI流水线后使用综合2/物理2。早期无效停顿试验保留并标记NOT_A_DURATION_PROOF，不用于55ms结论。

原始综合/路由DB和报告完整保留；TD相对路径工程见05_td/v112_audio_visual_synth_attempt2/td_project。
先读03_docs/v112_双缓冲设计与资源说明.md；运行08_tools/verify_v112.py仅做本地文件一致性检查，不会下载板卡。

所有后续新文件在D盘，旧版保留；无需交接ZIP。
'''
(root/'README_先看这里.md').write_text(readme,encoding='utf8')
files={}
for f in sorted(root.rglob('*')):
 if not f.is_file():continue
 rel=f.relative_to(root)
 if any(p in {'00_tmp','build','__pycache__','.git'}for p in rel.parts)or f.suffix.lower()in {'.vvp','.vcd','.pyc'}:continue
 if rel.as_posix()=='04_evidence/v112_release_manifest.json':continue
 files[rel.as_posix()]=sha(f)
write(root/'04_evidence/v112_release_manifest.json',dict(version=version,files_sha256=files,checked_artifacts=len(files),scope='Complete non-cache delivery consistency; not hardware acceptance'))
print(json.dumps(dict(version=version,bit=str(bit),bytes=bit.stat().st_size,sha256=sha(bit),routed=routed,slack_ns=ph['slack_ns'],manifest_entries=len(files)),ensure_ascii=False,indent=2))
