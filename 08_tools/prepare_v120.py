# Freeze the unchanged V119 design for user-approved Flash programming.
from pathlib import Path
import datetime,hashlib,json,re,shutil
root=Path(__file__).resolve().parents[1];version='v120_flash_release_20261027'
archive=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/version
assert root.name==version and not archive.exists(),'Do not edit frozen versions'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads((root/p).read_text(encoding='utf8'))
write=lambda p,j:(root/p).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
base=load('BASELINE_v119_VERSION_STATUS.json');expected=base['bitstream']['sha256'];original=root/base['bitstream']['path']
assert expected=='32971f15b0c7d9e0d937dcb905509aeeb45d8157a31765598127c3b4e9a01d07' and sha(original)==expected
# Retain the previous generic guides as explicitly historical references.
old=root/'06_flash/03_historical_evidence/v117_guides_before_v120';old.mkdir()
for p in (root/'06_flash/02_guides').glob('*'):
 if p.is_file():shutil.copy2(p,old/p.name)
bit_rel='06_flash/01_image/v119_three_wav_720p.bit';bit=root/bit_rel
assert not bit.exists();shutil.copy2(original,bit);assert sha(bit)==expected
manual_meta=load('06_flash/02_guides/官方手册依据.json')
manual=Path(r'D:\FPGA_Billboard\Anlogic\TD_6.2.1_Engineer_6.2.168.116\doc\SWUG\SWUG110_BitWizard_User_Guide.pdf')
assert manual.is_file() and sha(manual)==manual_meta['sha256']
manual_meta.update(path=str(manual),note='Same official manual bytes after user moved TD to D. Not a new Flash/programming result.')
write('06_flash/02_guides/官方手册依据.json',manual_meta)
now=datetime.datetime.now().astimezone().isoformat()
feedback=dict(recorded_at=now,user_message='这版可以最终固化了',applies_to_design='v119',interpretation='User approves V119 as the final Flash target. Do not invent individual 30-second listening, A3, Program/Verify or cold-boot measurements.',user_approved_for_flash=True,agent_observed_new_programming=False,program_flash_executed=False,verify_flash_executed=False,cold_boot_tested=False)
write('07_acceptance/v120_用户固化确认.json',feedback)
settings=load('06_flash/02_guides/固化设置.json')
settings.update(release_version='v120',design_version='v119',file_relative=bit_rel,sha256=expected,bytes=bit.stat().st_size,download_tool_path=r'D:\FPGA_Billboard\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin\bw.exe',user_approved_for_flash=True,program_executed=False,verify_executed=False,cold_boot_tested=False)
write('06_flash/02_guides/固化设置.json',settings)
# No RTL/constraints/build script changes. Hash-check all inherited source evidence.
syn=load(base['synthesis_attempt']+'/attempt.json')
for rel,h in syn['source_sha256'].items():assert sha(root/rel)==h,rel
for report in base['reviewed_reports'].values():assert sha(root/report['path'])==report['sha256'],report['path']
status=dict(version=version,release_version='v120',design_version='v119',recorded_at=now,type='User-approved V119 design freeze and Flash preparation; identical bit, no new RTL/build',target=base['target'],
 source_frozen=str(Path(base['archive_directory'])/'01_project'),work_directory=str(root),archive_directory=str(archive),
 new_rtl=False,new_simulation=False,new_td_build=False,new_bitstream=False,source_bound_inherited_checks_passed=True,user_approved_for_flash=True,
 user_confirmation='07_acceptance/v120_用户固化确认.json',bitstream=dict(path=bit_rel,sha256=expected,bytes=bit.stat().st_size,original_path=base['bitstream']['path'],on_screen_version='V119'),
 physical_resources=base['physical_resources'],resource_percent=base['resource_percent'],slack_ns=base['slack_ns'],check_timing_counts=base['check_timing_counts'],
 inherited_evidence=dict(scope='V119 reports rechecked by source/report SHA256; not rerun or new hardware results',baseline='BASELINE_v119_VERSION_STATUS.json',preflight='04_evidence/v120_preflight/baseline_checks.json',source_entries=len(syn['source_sha256']),reviewed_report_count=len(base['reviewed_reports'])),
 flash=dict(program_mode='PROGRAM_FLASH',verify_mode='VERIFY_FLASH',speed_mhz=5,memory_size_mbits=16,settings_basis='Same-board v074 historical Flash marking and settings; no fresh device probe',program_executed=False,verify_executed=False,cold_boot_tested=False,current_contents_known=False,original_flash_backup_available=False),
 tf_files_modified=False,drivers_modified=False,flash_modified=False,hardware_acceptance_observed_by_agent=False,formal_reliability_signoff=False,handoff_zip_generated=False,
 known_open_items=base['open_items']+['User approval does not supply separate itemized listening/A3 or cold-boot results. Record Program/Verify and cold-boot feedback separately.','V120 is packaging/acceptance-record version; actual hardware design/on-screen version remains V119.'])
write('VERSION_STATUS.json',status)
bit_path=archive/'01_project'/bit_rel
steps=f'''# v120固化步骤：最终设计仍为V119

## 冻结说明

你确认“这版可以最终固化了”，已记录为V120固化准备版。不再改RTL/时钟/约束/缓存，也不重新综合；采用V119原始同一份bit，屏幕仍显示V119，这是正常的。
只完成整理和校验；本次没有自动操作下载器，没有Program/Verify Flash或冷启动结果。

## 唯一推荐位流

工作文件：`{bit}`
归档文件：`{bit_path}`
SHA256：`{expected}`；{bit.stat().st_size}字节。
保留.bit，不改名.bin，不做截头转换。目录中保留的v116仅为历史回退文件，不要选错。
歌曲和图片仍保存在TF，固化不需要重新拷贝，也不把音乐写入配置Flash。

## 1 打开工具与确认参数

使用D盘TD的Tools → BitWriter，或：
`D:\\FPGA_Billboard\\Anlogic\\TD_6.2.1_Engineer_6.2.168.116\\bin\\bw.exe`

本板以往成功使用的设置：

| 项目 | 设置 |
|---|---|
| Device | EG4S20NG88 |
| Mode | PROGRAM_FLASH |
| Speed | 5 MHz |
| MemorySize | 16 Mbits（不是16MB） |
| File | v119_three_wav_720p.bit |

Flash型号/容量来自同一块板v074历史记录（U5 BoyaMicro 25Q16BSTIG），不是本次自动识别。若换板或界面/容量不一致，先停下核对，不盲写。
文件列表只保留这一条目标；只清工具列表，不删除磁盘旧版文件。Refresh读到FPGA ID不等于Flash已校验。

## 2 写入与校验

1. 保持稳定供电和JTAG连接。Program Flash会覆盖旧开机配置；本次没有做当前Flash备份。
2. 选择上面唯一位流和参数，Mode=PROGRAM_FLASH，Run。
3. 等日志明确PROGRAM_FLASH success !，保留截图或日志；过程中不断电/拔线。
4. 同一文件/容量，Mode改VERIFY_FLASH，Run，等VERIFY_FLASH success !，再保存本次结果。
5. 失败就停止，保留完整报错；不要为绕过失败反复整片擦除。

不额外点整片Erase Flash；不改MSEL、启动地址、OTP、安全/加密、QE；不使用PROGRAM_SPIBIN、DualBoot/MultiBoot。
如果仍没有完成同一V119 bit的实物测试，应先Program SRAM检查三份WAV/暂停/UI/四图。已测试者无需仅因打包又重复下载。

## 3 真实断电冷启动

1. 等工具完全结束，再断开板卡供电；排除下载器/JTAG或其他连接反供电，确认板卡指示灯确实熄灭。断电状态再整理连接，不带电拔TF/杜邦线。
2. 屏幕先供电并选择HDMI输入，再仅给板卡正常供电；此时不要点Program SRAM。
3. 等待自行出图，确认V119、四图轮播。长K0进入音频控制，短K1依次检查MUSIC、ADVOICE、扩展音频，再回测试音。
4. 短K0暂停/继续；长K1隐藏/显示UI；检查新曲和原两音频没有串音、A3/L6或卡顿。
5. 建议做3次完整断电重启，记录每次出图和播放，这是工程建议，不是额外官方条款。

默认音源为跟随图片测试音。新曲不会默认自动取代它，需要音频控制中短K1切到第三份。
如果Flash冷启动失败而同bit SRAM正常，先查启动/供电链路和本次Program/Verify证据；不要改动已冻结设计来碰运气。

## 记录边界

你的固化许可已记录，不代填各项实测。写入、校验、断电自启动分别保存，反馈后再建新验收版本；不回写冻结快照。
数值时序继承V119（SWNS+0.663ns/HWNS+0.024ns），不等于PVT/电气签核；资源约90%及SDRAM宏/33内部异常延时等既有项保留。
无需交接压缩包。
'''
(root/'06_flash/02_guides/固化步骤.md').write_text(steps,encoding='utf8')
(root/'07_acceptance/v120_固化与冷启动记录_待填写.md').write_text('''# V119最终固化记录（归档版本V120）

用户确认：这版可以最终固化了。
以下结果不得根据许可自动填通过：

- 本次文件确认V119及SHA256：待确认
- PROGRAM_FLASH结果/时间/截图：待操作
- VERIFY_FLASH结果/时间/截图：待操作
- 完全断电时指示灯熄灭且无反供电：待确认
- 不点Program SRAM，自主开机出图：待确认
- 四图轮播、音乐、广告、第三WAV：待确认
- 暂停继续、独立UI、A3与L6：待确认
- 冷启动第1/2/3次：待记录

后续反馈存新版本，不编辑冻结归档。屏幕版本应为V119，不会变V120。
''',encoding='utf8')
(root/'README_先看这里.md').write_text(f'''# v120：用户确认的V119最终固化版

- 用户反馈：“这版可以最终固化了”，许可已记录。
- 设计/屏幕仍为**V119**；V120只是冻结归档和固化准备编号。
- 源码/约束/位流未改，未新跑仿真或TD；继承证据已重新校验。
- **尚未执行本次Program Flash、Verify Flash或冷启动，不能提前记为固化成功。**

## 唯一推荐文件

`{bit_path}`

工作副本：`{bit}`
SHA256：`{expected}`（{bit.stat().st_size}字节）。与V119测试bit完全相同。

## 最短操作

1. 打开D盘TD BitWriter，选择EG4S20NG88、PROGRAM_FLASH、5MHz、16Mbits和上述bit（同板历史参数，不是新探测）。
2. Run，等待PROGRAM_FLASH success !。
3. 改VERIFY_FLASH，用同一文件Run，等待VERIFY_FLASH success !。
4. 工具结束后真正断电，排除下载器反供电；屏幕先上电，再给板卡供电。不要点Program SRAM，观察自行出图。
5. 检查四图与三份WAV/暂停/UI，反馈写入/校验/冷启动结果。

详细步骤：`{archive/'01_project/06_flash/02_guides/固化步骤.md'}`。
不重拷TF、不改名bin、不额外整片擦除、不改MSEL/安全项。本次未自动操作硬件；旧版本保留，无需交接包。

## 资源与边界

沿用V119最终LUT17691/19600、寄存器10429/19600、BRAM58/64、DSP15/29、PLL3/4，SWNS+0.663ns/HWNS+0.024ns。
用户确认是应用级固化许可，不取代宏/内部延时/SiP/PVT、全地址实物BIST或电气可靠性签核。

完整归档：`{archive}`。
只读核验：`{archive/'01_project/08_tools/verify_v120_release.py'}`；不要在归档快照内编译/仿真。
旧v119清单和报告原样保留作来源；本版以V120状态与清单为准。
''',encoding='utf8')
(root/'README_归档位置.md').write_text(f'# V120保存位置\n\n归档：`{archive}`\n\n推荐固化bit：`{bit_path}`\n\n设计为V119，不重编译，不自动写Flash；保留旧版本，无需ZIP。\n',encoding='utf8')
# Manifest consistent with append-only archiver exclusions.
manifest_rel='04_evidence/v120_release_file_manifest.json';files=[]
for p in sorted(root.rglob('*')):
 rel=p.relative_to(root)
 if not p.is_file() or rel.as_posix()==manifest_rel or any(x in {'build','__pycache__','.git','00_tmp'} for x in rel.parts) or p.suffix.lower() in {'.vvp','.vcd','.pyc'}:continue
 assert p.suffix.lower() not in {'.lic','.exe','.dll'},str(rel)
 files.append(dict(path=rel.as_posix(),sha256=sha(p),bytes=p.stat().st_size))
write(manifest_rel,dict(version=version,created=now,files=files,scope='Integrity/source freeze, not actual Flash/boot acceptance'))
print(json.dumps(dict(version=version,design='V119',bit_sha256=expected,files=len(files),archive=str(archive),user_approved=True,flash_executed=False),ensure_ascii=False,indent=2))