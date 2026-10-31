"""Finalize v111 UI fault categorization only. Never programs hardware or alters TF/Flash."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,shutil
root=Path(__file__).resolve().parents[1]
if '01_versions' in root.parts:raise SystemExit('Frozen archives are read-only')
ap=argparse.ArgumentParser();ap.add_argument('--synth-attempt',type=int,default=2);ap.add_argument('--physical-attempt',type=int,default=1);ap.add_argument('--bitgen-attempt',type=int,default=1);a=ap.parse_args()
version='v111_audio_fault_ui_20261027'
archive=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/version
assert not archive.exists(),'Never overwrite frozen archive'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def exact(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():assert sha(src)==sha(dst),str(dst)
 else:shutil.copy2(src,dst)
 assert sha(src)==sha(dst)
syp=root/f'05_td/v111_audio_visual_synth_attempt{a.synth_attempt}/attempt.json'
php=root/f'05_td/v111_audio_visual_physical_attempt{a.physical_attempt}/attempt.json'
bgp=root/f'05_td/v111_audio_fault_ui_bitgen_attempt{a.bitgen_attempt}/attempt.json'
sy,ph,bg=map(load,(syp,php,bgp))
assert all(x.get('completed') for x in (sy,ph,bg))
assert min(ph['slack_ns'].values())>=0
bit=root/'03_bitstreams/v111_audio_fault_ui_720p.bit'
assert sha(bit)==bg['bit_sha256'] and bit.stat().st_size==bg['bit_bytes']
for name,h in sy['source_sha256'].items():assert sha(root/name)==h,name
for item in bg['reviewed_reports'].values():assert sha(root/item['path'])==item['sha256'],item['path']
gate=syp.parent/'build/idx_video_Runs/syn_1'
preserve=root/'04_evidence/v111_final_synthesis_preserved'
kept=[]
for f in sorted(gate.iterdir()):
 if f.is_file():
  dest=preserve/f.name;exact(f,dest);kept.append(dict(file=f.name,sha256=sha(dest),bytes=dest.stat().st_size))
write(preserve/'preservation.json',dict(reason='Selected raw gate database preserved outside excluded build cache',files=kept))
prj=syp.parent/'td_project/idx_video.al';runprj=prj.parent/'idx_video_Runs/syn_1/idx_video.prj'
exact(syp.parent/'build/idx_video.al',prj);exact(gate/'idx_video.prj',runprj)
refs=[]
for f in (prj,runprj):
 for n in re.findall(r'<File Path="([^"]+)"',f.read_text(encoding='utf8')):
  q=(f.parent/n).resolve();assert q.is_file() and q.is_relative_to(root),str(q)
  refs.append(dict(project=f.relative_to(root).as_posix(),source=q.relative_to(root).as_posix(),sha256=sha(q)))
write(preserve/'td_project_relative_paths.json',dict(passed=True,references=refs))
area=php.parent/'physical/sdram_phy.area'
text=area.read_text(encoding='utf8')
routed={k:int(re.search(r'^#'+k+r'\s+(\d+)',text,re.M).group(1))for k in ('lut','reg','bram','bram32k','dsp','pll','gclk','pad')}
open_items=['Real-device A3 WAV FIFO underrun ROOT CAUSE IS NOT FIXED by this UI-only version',
 'No new board download, audible playback, Flash or cold-start acceptance',
 'RGB332 SDRAM cache (HDMI1280x720 output); not full24-bit image cache',
 'SDRAM macro relocation/internal abnormal delay/SiP/PVT/full-address real-device BIST remain open',
 'WAV48k16/24 mono/stereo only; no runtime FLAC/MP3 decoder or speech recognition']
status=dict(version=version,date=datetime.date.today().isoformat(),target='VF-E20NG88 / EG4S20NG88 /24MHz / HDMI1280x720',
 purpose='Separate image/audio UI fault categories and show accurate K0 action, not an A3 audio-path repair',
 source_version='v110_ui_pause_opt_20261026',source_hardware_feedback='A3 observed; browser K0 wrongly said retry; not accepted',
 simulation_passed=True,synthesis_completed=True,physical_numerical_check_passed=True,new_bit_generated=True,
 hardware_download=False,hardware_acceptance=False,formal_release_approved=False,flash_modified=False,tf_files_modified=False,
 resources_synthesis=sy['resources'],resources_routed=routed,slack_ns=ph['slack_ns'],
 bitstream=str(bit),bit_bytes=bit.stat().st_size,bit_sha256=sha(bit),archive_path=str(archive),known_open_items=open_items,
 reviewed_reports=bg['reviewed_reports'])
for name in ('README_先看这里.md','VERSION_STATUS.json','README_归档位置.md'):
 old=root/name
 if old.exists():exact(old,root/('INHERITED_v110_'+name))
write(root/'VERSION_STATUS.json',status)
(root/'README_归档位置.md').write_text('# 归档位置\n\n'+str(archive)+'\n\n旧版本保持冻结。只在 D 盘工作副本开发与测试。\n',encoding='utf8')
readme=f'''# v111：K0提示与音频A3分开显示\n\n**本版是临时SRAM测试候选，不是A3音频欠载修复/Flash验收版。**\n\n- 音频故障不会再伪装成图片读取失败。图片正常时，退出音频控制后K0显示“下一张”。\n- 音频行独立显示实际故障码，如“音频故障 A3”。A3仍会显示，不会隐藏。\n- 音频控制K0的暂停/继续提示按真实暂停状态显示。\n- 长K0只是退出控制，不停止音源、不清除A3；无需先重拷或格式化TF卡。\n\n## 当前推荐（只下载SRAM）\n\n位流：\n{bit}\n\n大小：{bit.stat().st_size}字节；SHA256：{sha(bit)}\n\n## 测试步骤\n\n见03_docs/v111_按键与上板步骤.md；先确认V111。重点看：A3在音频行，图片正常，浏览K0为“下一张”。\n\n## 本版实际证据\n\n707组独立UI文字状态和5幅720p栅格、按键/故障集成及顶层A3/E0注入、新生产综合/布局布线/ROM INIT/位流检查。未修改模块仅使用SHA256相同的旧回归，见VERSION_STATUS.json逐项执行标识；不冒称全套新实物通过。\n\n布局布线LUT {routed['lut']}/19600，BRAM {routed['bram']}/64，DSP {routed['dsp']}/29。SWNS {ph['slack_ns']['SWNS']:+.3f}ns，HWNS {ph['slack_ns']['HWNS']:+.3f}ns；这些是数值报告，不是PVT/SiP可靠性签核。\n\n原始照片见04_evidence/v111_v110_hardware_feedback。真实欠载的具体成因尚未定位，不能把延迟注入仿真当作实际板卡定位。没有改TF/Flash，没有硬件下载或听音验收。\n\n完整归档：{archive}\n\n用户独立完成，无需交接ZIP。所有旧版本保留。\n'''
(root/'README_先看这里.md').write_text(readme,encoding='utf8')
# A snapshot of all non-cache delivery artifacts; includes sources, scripts and reports.
files={}
for f in sorted(root.rglob('*')):
 if not f.is_file():continue
 rel=f.relative_to(root)
 if any(p in {'00_tmp','build','__pycache__','.git'}for p in rel.parts)or f.suffix.lower()in {'.vvp','.vcd','.pyc','.ppm'}:continue
 if rel.as_posix()=='04_evidence/v111_release_manifest.json':continue
 files[rel.as_posix()]=sha(f)
write(root/'04_evidence/v111_release_manifest.json',dict(version=version,files_sha256=files,checked_artifacts=len(files),scope='Local complete delivery consistency; not hardware acceptance'))
print(json.dumps(dict(version=version,bit=str(bit),bytes=bit.stat().st_size,sha256=sha(bit),routed=routed,slack_ns=ph['slack_ns'],manifest_entries=len(files)),ensure_ascii=False,indent=2))
