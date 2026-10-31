# Finalize once after successful bitgen; never edits a frozen archive.
from pathlib import Path
import datetime,hashlib,json,re,shutil
root=Path(__file__).resolve().parents[1]
version='v119_three_wav_20261027'
archive=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/version
assert root.name==version and not archive.exists(),'Do not finalize frozen snapshots'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads((root/p).read_text(encoding='utf8'))
write=lambda p,j:(root/p).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
synth_rel='05_td/v119_audio_visual_synth_attempt4';phy_rel='05_td/v119_audio_visual_physical_attempt1';bitgen_rel='05_td/v119_audio_refill_bitgen_attempt1'
syn=load(synth_rel+'/attempt.json');phy=load(phy_rel+'/attempt.json');bg=load(bitgen_rel+'/attempt.json')
assert syn['completed'] and phy['completed'] and bg['completed']
bit_rel='03_bitstreams/v119_three_wav_720p.bit';bit=root/bit_rel
assert sha(bit)==bg['bit_sha256'] and bit.stat().st_size==645936
assert sha(bit)!=sha(root/'03_bitstreams/v116_audio_refill_720p.bit')
for rel,h in syn['source_sha256'].items():assert sha(root/rel)==h,rel
for info in bg['reviewed_reports'].values():assert sha(root/info['path'])==info['sha256'],info['path']
# Same depth retains native PRJ ../../../../../01_project source paths.
preserved=root/'04_evidence/v119_final_synthesis_preserved/original_build'
assert not preserved.exists()
shutil.copytree(root/synth_rel/'build',preserved)
gate=preserved/'idx_video_Runs/syn_1/idx_video_gate.db';assert sha(gate)==bg['synth_gate_sha256']
for rel in (synth_rel+'/build/idx_video_Runs/syn_1/idx_video.prj','04_evidence/v119_final_synthesis_preserved/original_build/idx_video_Runs/syn_1/idx_video.prj'):
 p=root/rel;files=re.findall(r'<File Path="([^"]+)"',p.read_text(encoding='utf8'));assert files and all((p.parent/f).resolve().is_file() for f in files),rel
for n in (1,2,3):
 source=root/f'05_td/v119_audio_visual_synth_attempt{n}/build/idx_video_Runs/syn_1/run.log'
 if source.exists():shutil.copy2(source,root/f'04_evidence/v119_td_recovery/failed_child_synth_attempt{n}.log')
# Derived portable source lists; existence checks only, not a GUI-open claim.
s=(root/synth_rel/'build/idx_video.al').read_text(encoding='utf8')
s=re.sub(r'(<Project\b[^>]*\bPath=")[^"]+("[^>]*>)',r'\g<1>.\2',s,count=1).replace('../../../01_project/','')
(root/'01_project/v119_three_wav.al').write_text(s,encoding='utf8')
s=(preserved/'idx_video_Runs/syn_1/idx_video.prj').read_text(encoding='utf8').replace('../../../../../01_project/','')
(root/'01_project/v119_three_wav.prj').write_text(s,encoding='utf8')
for p in (root/'01_project/v119_three_wav.al',root/'01_project/v119_three_wav.prj'):
 paths=re.findall(r'<File Path="([^"]+)"',p.read_text(encoding='utf8'));assert paths and all((p.parent/f).is_file() for f in paths)
write('04_evidence/v119_portable_project_check.json',dict(passed=True,source_entries_checked=len(paths),scope='Relative source file existence from successful native project; not GUI-open or rebuild acceptance.'))
area_rel=phy_rel+'/physical/sdram_phy.area';text=(root/area_rel).read_text(encoding='utf8')
resources={k:int(re.search(r'^#'+k+r'\s+(\d+)',text,re.M).group(1)) for k in ('lut','reg','bram','dsp','pll','gclk','pad')}
capacities={'lut':19600,'reg':19600,'bram':64,'dsp':29,'pll':4,'gclk':16,'pad':66}
assert all(resources[k]<=n for k,n in capacities.items())
reg=load(bg['reviewed_reports']['fresh_regression']['path']);assert reg['passed'] and len(reg['cases'])==11
now=datetime.datetime.now().astimezone().isoformat()
status=dict(version=version,release_version='v119',design_version='v119',recorded_at=now,
 target=dict(board='VF-E20NG88',device='EG4S20NG88',reference_clock_hz=24000000,video='1280x720',cache='RGB332'),
 source_baseline='v118_bc_media_640x480_20261027 (v116 design plus v118 B/C media)',work_directory=str(root),archive_directory=str(archive),
 changes=['Preserve MUSIC/ADVOICE and select first additional ordinary root WAV using 8.3 alias extension',
 'Four-source cycle, Chinese extra-audio label and V119 diagnosis; fixed ROM sizes unchanged',
 'Reuse single decoder, three-sector transport and production4096-frame PCM FIFO',
 'Completed existing split TD installation on D by copying C bin; C originals/license unchanged'],
 verification=dict(third_wav_cases=11,third_wav_simulation_passed=True,regression_jobs=11,regression_passed=True,
 controls_and_subtitles_jobs=6,ui_jobs=3,native_hdmi_phase_cases=3,routed_rom_blocks=12,synthesis_passed=True,physical_numerical_checks_passed=True,diagnostic_bit_generated=True,
 programmed=False,listened_on_hardware=False,flash_written=False,cold_start_verified=False,formal_reliability_signoff=False),
 bitstream=dict(path=bit_rel,sha256=sha(bit),bytes=bit.stat().st_size,type='SRAM diagnostic test candidate; not hardware accepted'),
 physical_resources=resources,resource_capacities=capacities,resource_percent={k:round(100*resources[k]/n,2) for k,n in capacities.items()},
 previous_v116_routed_comparison=dict(lut=17653,reg=10418,bram=58,dsp=15,pll=3,lut_delta=resources['lut']-17653,reg_delta=resources['reg']-10418,note='Routed-to-routed, not synthesis estimates. Not an optimization release.'),
 slack_ns=phy['slack_ns'],check_timing_counts=bg['check_timing_counts'],td_runtime=r'D:\FPGA_Billboard\Anlogic\TD_6.2.1_Engineer_6.2.168.116',
 synthesis_attempt=synth_rel,physical_attempt=phy_rel,bitgen_attempt=bitgen_rel,preserved_gate_db=gate.relative_to(root).as_posix(),reviewed_reports=bg['reviewed_reports'],
 extra_wav_rule='First additional ordinary WAV in FAT32 root physical directory order;64KiB root scan cap; not recursive, sorted or unlimited',audio_media_record='04_evidence/v119_user_media_record.json',
 open_items=bg['known_open_review']+['dummy3/no-input-delay2/no-output-delay7 not waived','LUT90.26%, BRAM90.62%, hold24ps: tight, no PVT/electrical robustness claim',
 'No actual card enumeration/extra-file hash readback performed','Fixed DEMO captions are not transcription of the new song','No explicit new user acceptance of v116 actual-card A3 closure'],
 archive_policy='Append-only full version; no teammate ZIP requested; do not run inside snapshot')
write('VERSION_STATUS.json',status)
readme=f'''# v119：原音乐、广告与第三份WAV并存

新增“扩展音频”，保留MUSIC.WAV、ADVOICE.WAV，不覆盖原音乐。歌曲仍从TF读取，不在bit中。
已完成仿真、综合、布局布线、数值时序检查及新位流生成；**尚未下载、听音或写Flash，不是实物通过结论**。

## 推荐测试文件

工作位流：`{bit}`
归档位流：`{archive/'01_project'/bit_rel}`
SHA256：`{sha(bit)}`，645936字节。此文件不是旧v116改名。

## 你现在如何测试

1. 你已存入TURANDETUOLUO.WAV，无须因本次编译再拷贝。保留MUSIC.WAV、ADVOICE.WAV及A/B/C/D图片，额外WAV暂时只留这一份。
2. Program SRAM临时下载本版，先不要固化Flash。
3. 默认状态长按K0约1秒进入音频控制；短K1一次原音乐、两次广告、三次扩展音频、第四次回图片测试音。
4. 每份连续听至少30秒（短广告可完整播放）。确认第三份为新曲《突然的陀螺》，无A3/L6、卡顿或串音，四图继续轮播。
5. 短K0暂停/继续；长K1隐藏/显示UI；切回音乐再切回扩展，检查从头播放。
6. 出错先拍完整V119/AUD诊断，不要立即复位。A1未找到文件、9x解析错误、A3欠样分开记录。

不要带电取卡。只有要更改卡内容才断电取卡。不自动下载、不自动写卡、不自动改驱动。

## 文件识别限制

第三槽读取FAT32根目录除MUSIC/ADVOICE以外**存储顺序第一份普通WAV**，不是按字母排序，也不是无限播放列表。
使用长名的8.3短别名，不显示动态曲名；不递归子目录；沿用64KiB根目录扫描上限。
本次素材为48000Hz/24-bit/双声道PCM，不直接支持FLAC/MP3。此次未回读用户TF文件校验。
旧DEMO字幕不是新曲的自动识别歌词。

## 最终布局布线资源

| 资源 | 用量 | 占比 |
|---|---:|---:|
| LUT | {resources['lut']}/19600 | 90.26% |
| 寄存器 | {resources['reg']}/19600 | 53.21% |
| BRAM9K | 58/64 | 90.62% |
| DSP | 15/29 | 51.72% |
| PLL | 3/4 | 75.00% |

SWNS +0.663ns，HWNS +0.024ns，STNS/HTNS均0；相比v116最终布线LUT增加38，BRAM不变。
资源和保持裕量偏紧，不等于正式可靠性签核。SDRAM宏迁移、33项内部异常输入延时、dummy/外部延时、SiP/PVT、全地址实物BIST仍开放。

## TD目录已接好

使用 `D:\\FPGA_Billboard\\Anlogic\\TD_6.2.1_Engineer_6.2.168.116\\bin\\td.exe`。
C盘仅bin，D盘有其余器件/仿真库和用户许可证；本次只复制bin到D补齐。C原文件保留，未重装/改许可证/改驱动。
完整D目录已实际完成本版编译；安装器解压自带的过期许可证不是最终使用的用户许可证。

## 保存与证据

归档：`{archive}`。完整源码、TB、约束、相对路径TD源清单、报告和新bit保留。
操作详见`03_docs/v119_三份WAV与上板测试.md`；验证详见`03_docs/v119_验证资源与环境.md`。
`VERSION_STATUS.json`为状态，`04_evidence/v119_release_file_manifest.json`为SHA256清单。
`08_tools/verify_v119_release.py`仅只读验证，不编译或下载。不要在归档快照中运行编译/仿真。
旧版本全部保留。按你的要求，**无需交接压缩包**。
'''
(root/'README_先看这里.md').write_text(readme,encoding='utf8')
(root/'README_归档位置.md').write_text(f'# v119位置\n\n- 工作：`{root}`\n- 冻结归档：`{archive}`\n- 推荐bit：`{archive/"01_project"/bit_rel}`\n- 请在工作副本编辑，旧版保留，无需交接包。\n',encoding='utf8')
doc='''# v119验证、资源与环境

目标EG4S20NG88/24MHz/1280x720；RGB332缓存；48kHz/24bit双声道PCM。
未调整时钟/引脚/约束/SPI速率/缓存深度。

## 验证范围

新跑11个第三WAV用例、11项整机回归、6项控制/字幕、3项UI、3种HDMI ODDR相位、3个仲裁/首错用例、12块最终BRAM INIT核对；TD综合/布线/数值时序/新bit生成完成。
生产4096FIFO读卡使用虚拟扇区，额外WAV的针脚测试用512FIFO短协议场景；不替代实卡长期播放。
未变的解析器、预取、缩放、抖动报告在全部记录源哈希一致后继承，不冒称新跑。
首轮回归10项通过，top因仿真库移动无法启动；恢复D环境后只重跑top，合并11项通过。原失败和补跑记录都保留。
尚未下载、听音、回读卡内文件、写Flash、冷启动或电气/PVT验收。

## 综合输出保留

成功综合输出复制到04_evidence/v119_final_synthesis_preserved/original_build，避免归档排除build造成证据丢失；PRJ保留原相对路径。
01_project/v119_three_wav.al与.prj是成功工程的相对路径源清单导出，逐项存在性验证，不代表已在GUI重新打开验收。
归档仅只读；重建时复制到新工作目录并选未用attempt编号，使用完整D盘TD目录。

## 环境恢复

C盘bin50个文件复制到已有D目录后逐一核验哈希；C文件保留，用户许可证未修改；无重装/驱动/系统日期/签名策略变动。
失败1：分拆资源造成manager异常；失败2：C器件库不存在；失败3：安装器解压的默认许可证过期；尝试4：用户完整D目录成功。不能误称用户许可证过期。
恢复记录仅含文件哈希/日期等元数据。完整TD/安装器/许可证/驱动不纳入源码归档。

## 数值不等于全部问题关闭

最终资源/时序/约束检查如下。保持24ps、LUT与BRAM约90%偏紧，SDRAM宏迁移、33项内部异常延时、dummy/外部延时、SiP/PVT与全地址实物BIST仍开放。

'''
doc+=json.dumps(dict(resources=resources,slack_ns=phy['slack_ns'],checks=bg['check_timing_counts'],area=area_rel,bitgen=bitgen_rel+'/attempt.json'),ensure_ascii=False,indent=2)+'\n'
(root/'03_docs/v119_验证资源与环境.md').write_text(doc,encoding='utf8')
(root/'07_acceptance/v119_上板记录_待填写.md').write_text('''# v119上板记录（未验收，等待用户反馈）

- 日期/下载方式：待填
- V119位流确认：待测
- MUSIC连续播放30s：待测
- ADVOICE完整短广告或30s：待测
- 扩展音频为新曲且连续30s：待测
- 四源循环/暂停继续/长K1独立UI/退出音频控制：待测
- 四图轮播/OSD/频谱：待测
- A3/A1/9x/L6与完整AUD首错照片：待记录
- Flash/冷启动：未执行，不用SRAM测试替代
''',encoding='utf8')
skip_dirs={'build','__pycache__','.git','00_tmp'};skip_ext={'.vvp','.vcd','.pyc'}
manifest_rel='04_evidence/v119_release_file_manifest.json';files=[]
for p in sorted(root.rglob('*')):
 rel=p.relative_to(root)
 if not p.is_file() or rel.as_posix()==manifest_rel or any(x in skip_dirs for x in rel.parts) or p.suffix.lower() in skip_ext:continue
 assert p.suffix.lower() not in {'.lic','.exe','.dll'},'Do not bundle runtime/license: '+str(rel)
 files.append(dict(path=rel.as_posix(),sha256=sha(p),bytes=p.stat().st_size))
write(manifest_rel,dict(version=version,created=now,scope='File integrity only, NOT hardware acceptance',excluded_directories=sorted(skip_dirs),excluded_suffixes=sorted(skip_ext),files=files))
print(json.dumps(dict(version=version,bit_sha256=sha(bit),resources=resources,slack_ns=phy['slack_ns'],manifest_files=len(files),archive=str(archive)),ensure_ascii=False,indent=2))