"""Finalize v100 source-bound evidence, preview, notes, and preserved synthesis.
Only works in the D: working copy; never downloads, changes TF, or writes Flash.
"""
from pathlib import Path
import argparse, hashlib, json, re, shutil
from PIL import Image

root = Path(__file__).resolve().parents[1]
parent = Path(r'D:\FPGA_Billboard\work\v099_transparent_spectrum_20261026')
archive = Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions') / root.name
ap = argparse.ArgumentParser()
ap.add_argument('--synth-attempt', type=int, default=1)
ap.add_argument('--physical-attempt', type=int, default=1)
ap.add_argument('--bitgen-attempt', type=int, default=1)
args = ap.parse_args()

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1024*1024), b''):
            h.update(data)
    return h.hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def require(test, message):
    if not test:
        raise RuntimeError(message)

require(root.drive.upper() == 'D:', 'Final outputs must stay on D:')
synpath = root / f'05_td/v100_audio_visual_synth_attempt{args.synth_attempt}/attempt.json'
phypath = root / f'05_td/v100_audio_visual_physical_attempt{args.physical_attempt}/attempt.json'
bgpath = root / f'05_td/v100_audio_spectrum_bitgen_attempt{args.bitgen_attempt}/attempt.json'
syn, phy, bg = load(synpath), load(phypath), load(bgpath)
require(syn['completed'] and syn['within_capacities'], 'Synthesis incomplete')
require(phy['completed'] and phy['nonnegative_slack'], 'Physical timing not passed')
require(bg['completed'] and bg['reloaded_timing_check_matches'], 'Guarded bitgen incomplete')
require(sha(synpath) == bg['synthesis_attempt_sha256'], 'Synthesis evidence changed')
require(sha(phypath) == bg['physical_attempt_sha256'], 'Physical evidence changed')
require(all(v >= 0 for v in phy['slack_ns'].values()), 'Negative slack')
for rel, expected in syn['source_sha256'].items():
    require(sha(root / rel) == expected, 'Changed synthesized source: '+rel)
for evidence in bg['reviewed_reports'].values():
    require(sha(root / evidence['path']) == evidence['sha256'], 'Changed regression evidence')
vp = root / bg['reviewed_reports']['visual']['path']
sim = load(vp)
expected_tests = {'activity','power_level','logo','dft','overlay','osd','top','audio_pcm','tmds'}
require(sim['passed'] and sim['complete'], 'Full suite incomplete')
require({t['name'] for t in sim['tests']} == expected_tests, 'Nine tests required')
require(all(t['passed'] and t['sources_unchanged_during_run'] for t in sim['tests']), 'Simulation failed/source changed')
bit = root / '03_bitstreams/v100_audio_spectrum_720p.bit'
require(bit.is_file() and sha(bit) == bg['bit_sha256'], 'Missing/mismatched v100 bit')
res = syn['resources']
base = load(parent / 'VERSION_STATUS.json')

# The archiver excludes every directory named build. Preserve the exact final
# synthesis reports AND databases outside build, with their origin and hashes.
gate = synpath.parent / 'build/idx_video_Runs/syn_1'
preserved = root / '04_evidence/v100_final_synthesis_preserved'
preserved.mkdir(parents=True, exist_ok=True)
records = []
for source in sorted(gate.iterdir()):
    if not source.is_file():
        continue
    target = preserved / source.name
    if target.exists():
        require(sha(target) == sha(source), 'Refusing to overwrite preserved evidence')
    else:
        shutil.copy2(source, target)
    require(sha(target) == sha(source), 'Preservation copy mismatch')
    records.append({'source': source.relative_to(root).as_posix(),
                    'preserved': target.relative_to(root).as_posix(),
                    'bytes': target.stat().st_size, 'sha256': sha(target)})
require(any(x['preserved'].endswith('idx_video_gate.db') for x in records), 'Gate DB not preserved')
require(any(x['preserved'].endswith('idx_video_gate.area') for x in records), 'Area report not preserved')
write_json(preserved / 'preservation.json', records)

preview = root / '03_docs/v100_透明频谱_仿真预览.png'
with Image.open(vp.parent / 'v100_active_spectrum.ppm') as im:
    im.load()
    require(im.size == (1280,720), 'Wrong preview dimensions')
    im.save(preview)

# Keep the inherited entry-page/status contents explicitly labeled.
for name in ['VERSION_STATUS.json','README_先看这里.md','README_归档位置待同步.md']:
    saved = root / ('INHERITED_v099_'+name)
    if not saved.exists():
        shutil.copy2(parent / name, saved)

open_review = [
    'No v100 download, screen/audio acceptance, cold-start test or Flash write has occurred.',
    'PHY-7002 SDRAM hard-macro initial relocation persists; no unsupported placement forced.',
    '33 abnormal input-delay entries, 2 missing input-delay groups, 7 missing output-delay groups and 3 dummy-node groups remain for documented review; not waived.',
    'SiP voltage/speed, internal DQ timing, PVT robustness and full-address real-device SDRAM BIST remain open.',
    'RGB332 SDRAM frame cache remains; RGB888 overlay output is not a 24-bit frame cache.',
    'Audio is FPGA internal 24-bit I2S demo; TF WAV/MP3 music playback and external ADC capture are NOT implemented.',
    '16 selected-frequency rectangular-window DFT is not a full-band FFT or calibrated analyzer.',
    'Current zero-PCM/missing-sample/silence fade behavior is simulation-verified, not yet hardware accepted.',
    'Full combined TF + scaler + physical SDRAM-model + HDMI 1280x720 end-to-end simulation is not complete; separate scopes are recorded below.'
]
status = {
    'version':'v100', 'directory':root.name, 'parent':'v099',
    'target':'VF-E20NG88 / EG4S20NG88 / 24MHz / 1280x720',
    'status':'Nine-group simulation PASS; synthesis PASS; routed STA numerical PASS; guarded diagnostic SRAM bit generated; NO new hardware/Flash/formal signoff',
    'storage':str(root), 'archive':str(archive),
    'resource':{'LUT':res['lut'],'REG':res['reg'],'BRAM9K':res['bram'],
                'BRAM32K':res['bram32k'],'DSP':res['dsp'],'PLL':res['pll'],
                'GCLK':res['gclk'],'PAD':res['pad']},
    'resource_delta_vs_v099':{'LUT':res['lut']-base['resource']['LUT'],
                            'REG':res['reg']-base['resource']['REG'],
                            'BRAM9K':res['bram']-base['resource']['BRAM9K'],
                            'DSP':res['dsp']-base['resource']['DSP']},
    'timing_ns':phy['slack_ns'], 'check_timing_counts':bg['check_timing_counts'],
    'simulation':vp.relative_to(root).as_posix(),
    'synthesis':synpath.relative_to(root).as_posix(),
    'final_physical':phypath.relative_to(root).as_posix(),
    'bitgen':bgpath.relative_to(root).as_posix(),
    'bitstream':bit.relative_to(root).as_posix(),
    'bitstream_sha256':sha(bit), 'bitstream_bytes':bit.stat().st_size,
    'bit_generated':True, 'hardware_tested':False, 'flash_changed':False,
    'formal_release_approved':False, 'handoff_zip_generated':False,
    'tmds_latency':'one pixel clock, unchanged; exhaustive equivalence 108333 checks',
    'audio_source':'FPGA internal 24-bit I2S demo; use_external=0',
    'activity':'post-gain stereo absolute magnitudes; attack 4 samples; 400ms quiet hold at48k; approx200ms frame fade; missing-sample watchdog100ms',
    'reviewed_regressions':bg['reviewed_reports'], 'open':open_review,
    'last_user_hardware_feedback':'v089, recorded in v090; v098/v099/v100 are not inherited physical acceptances',
    'storage_note':'All new files/temp/compilation on D:. Inherited evidence may retain historical C: paths; existing C: work trees untouched.'
}
write_json(root / 'VERSION_STATUS.json', status)

changes = []
for branch in ['01_project','02_tests','08_tools']:
    for path in sorted((root / branch).rglob('*')):
        if not path.is_file() or path.suffix not in {'.v','.vh','.sv','.py','.tcl','.adc','.sdc'}:
            continue
        if any(x in {'build','__pycache__'} for x in path.relative_to(root).parts):
            continue
        rel = path.relative_to(root).as_posix()
        old = parent / rel
        if not old.exists() or sha(old) != sha(path):
            changes.append({'path':rel,'change':'modified' if old.exists() else 'added',
                            'parent_sha256':sha(old) if old.exists() else None,'sha256':sha(path)})
write_json(root / '03_docs/v100_SOURCE_CHANGES.json',
           {'parent':str(parent),'version':root.name,'changes':changes})
rows = []
for key,label,capacity in [('lut','LUT',19600),('reg','REG',19600),('bram','BRAM9K',64),
                           ('dsp','DSP',29),('pll','PLL',4)]:
    rows.append(f'| {label} | {res[key]:,} / {capacity:,} | {res[key]/capacity*100:.2f}% |')
resource_table = '\n'.join(rows)
checks = '\n'.join('- **'+t['name']+'：PASS**；'+'；'.join(t['results']) for t in sim['tests'])
review_counts = '\n'.join(f'- {k}: {v}' for k,v in bg['check_timing_counts'].items())
report = f'''# v100 透明艺术频谱与 HDMI 编码优化记录

## 结论

- 目标：VF-E20NG88 / EG4S20NG88 / 24 MHz / HDMI 1280×720。
- 9 组本轮功能仿真通过，原生 ODDR/HDMI 三相位验证通过；整机综合、布局布线及四项 STA 数值通过，已生成对应的 SRAM 临时测试位流。
- **未下载、未进行本版实屏/试听/冷启动验收、未写 Flash；数字裕量通过不等于正式时序、电气或可靠性签核。**
- 来源：{parent}。v099 最终建立时序未过且没有新位流，本版不继承其早期 attempt 的通过结论。
- 归档：{archive}。归档容器的 01_project 保存整个版本，故实际 RTL 位于其 01_project/01_project/rtl 下。

## 实现

1. 无黑色背景板、标题、坐标轴或底线，16 个柱与峰值之外的 RGB888 逐位透传；青蓝紫渐变，最高 Alpha 12/16。
2. 以实际送 HDMI 的增益后 24-bit 双声道 PCM 检测声音，各自取绝对值，避免反相抵消。连续 4 个样本达到 4096 触发，保持门限 2048。
3. 48 kHz 下 19200 个安静样本保持约 400ms，再以帧为单位渐隐；约 200ms 淡入/淡出，丢样本 100ms 看门狗，轨道 epoch 清理与衰减。
4. 16 路稀疏 DFT，柱高/峰值和渐变均由 RTL 实时绘制，不使用预录制动画。坐标 X128～1151，底部 Y608，最大柱高 144，避开现有 OSD/Logo。
5. 保留 TF/BMP、双线性缩放、SDRAM、四图轮播、HDMI 音频、亮度/对比度和按键；短按并释放 K0+K1 继续整体隐藏/恢复 OSD、Logo 与频谱。
6. v100 将 TMDS popcount 改为平衡树、串行 XOR/XNOR 改并行前缀，并简化 DC disparity 更新。仍为一个像素时钟延迟，不增加流水级，不改音频数据岛/保护带对齐。
7. 频谱混合用移位加法，无新增 DSP/RAM；整机 LUT 相对 v099 减少 {base['resource']['LUT']-res['lut']}，其余主要资源不变。未降低分辨率或放宽时序来换取通过。

## 整机综合资源（不是独立模块）

| 资源 | 使用 / 容量 | 占比 |
|---|---:|---:|
{resource_table}

- v099 LUT {base['resource']['LUT']} → v100 {res['lut']}。
- v097 LUT 16392 → v100 {res['lut']}，累计减少 {16392-res['lut']}（{(16392-res['lut'])/16392*100:.2f}%）；此处比较不同功能候选版本，不代表本轮单项收益。
- 查看 `{preserved / 'idx_video_gate.area'}` 中 `Utilization Statistics`，不要把 PAD 占用当 LUT。
- 保留记录：`{preserved / 'preservation.json'}`，共 {len(records)} 个最终综合文件；原相对路径与文件哈希保留。归档工具排除 build，但这些报告与数据库不会丢失。

## 本轮测试

{checks}

- 原生 ODDR/HDMI 三个相位 137/370/1111 ps 均通过；使用本机安装 TD 的模型，来源摘录/哈希有记录。
- 精确 TMDS 参考使用原始迭代算法，256 字节×32 个计数状态穷举，另含控制字、100000 连续符号及异步复位；不复用优化公式充当参考。
- 第一次 TMDS TB 在首时钟前检查初始复位失败；改为显式复位脉冲后独立验证和完整 9 组均通过。失败日志保留，不冒称首轮全过。
- 完整 720p 透明混合/OSD 是逐像素验证，顶层控制测试注入内存模型。实际 SPI/SD 卡/FAT/BMP/缩放+SDRAM 模型组合回归为 32×18；另有全宽 720p 合成写入器+SDRAM/显示测试。**不把这些拼成一次完整 TF→物理 SDRAM 模型→HDMI 的 720p 端到端仿真。**
- 未变的 TF/缓存/双帧等继承回归经逐文件 SHA256 核对后复用，不声称本轮全量重跑。具体 scope 见 VERSION_STATUS.json 的 reviewed_regressions。

## 最终物理检查

- 综合 attempt {args.synth_attempt}、布局布线 attempt {args.physical_attempt}、位流 attempt {args.bitgen_attempt}，均对应当前源码。
- SWNS {phy['slack_ns']['SWNS']:+.3f}ns；STNS {phy['slack_ns']['STNS']:.3f}ns；HWNS {phy['slack_ns']['HWNS']:+.3f}ns；HTNS {phy['slack_ns']['HTNS']:.3f}ns。
- 使用 TD 原生 hold-fix；无路由 ERROR。PHY-7002 SDRAM 初始位置重放置仍保留。
- check_timing（非零项目没有被豁免）：
{review_counts}

## 位流与边界

- 当前工作候选：{bit}
- 冻结归档位流：{archive / '01_project/03_bitstreams/v100_audio_spectrum_720p.bit'}
- {bit.stat().st_size} 字节；SHA256：{sha(bit)}。
- 当前仍为 FPGA 内部 24-bit I2S 测试音，use_external=0；TF WAV/MP3、真实音乐切换、外接 ADC 尚未实现，只预留实际 PCM/epoch 接入位置。
- 内部连续测试音会让频谱持续显示，不存在人为加入的周期静音。调低外部音箱音量不改变 FPGA 内部 PCM，不能用来验收自动隐藏。
- 稀疏 16 频点矩形窗 DFT 不是全频 FFT；单音集中少数柱正常，不会伪造全部柱随机跳动。
- SDRAM 仍为 RGB332；宏重定位、内部 DQ/SiP/PVT、完整地址实物 BIST、输入输出约束审查保持开放。
- 不自动下载、不改 TF、不写 Flash，不生成默认交接 ZIP。最近实物功能反馈为 v089（记录于 v090）；v098/v099 不是已实测回退版。

## 预览说明

v100_透明频谱_仿真预览.png 来自 RTL 逐像素输出。彩色背景是 TB 合成图，16 路设定不同高度以检查外观；**不是实屏截图，不代表单音同时激励所有柱**。
'''
(root / '03_docs/v100_实现与资源时序记录.md').write_text(report,encoding='utf-8')
steps = f'''# v100 上板：仅临时下载 SRAM

## 现在只做这些

1. 沿用已通过的供电、TF、HDMI 屏幕、下载器连接；不用增加文件，不用取出 TF。若要改线先断电。
2. TD Programmer 选择 EG4S20NG88，沿用此前成功的 **SRAM 临时下载**方式，文件：
   {bit}
   **不要执行 Flash 擦除、编程或固化。**
3. 等画面/HDMI 音频正常后看至少两轮四图轮播。图片、OSD、Logo、声音、原有亮度对比度操作不应回归成黑屏/无信号/花屏。
4. 看频谱：只有半透明青蓝紫柱和峰值，无黑色底板/标题/坐标轴。柱间原图应完整保留，不应整片变暗；单音只激励少数柱是正常。
5. 切图/内部演示音轨时看旧柱/峰值回落、新柱渐入，无长期残影，也不应造成 HDMI 失锁。
6. K0 仍切图/重试，K1 仍切手动/自动；**短按并释放 K0+K1**，OSD、Logo、频谱应整体隐藏，再次短按恢复，图像与音频继续。不要长按，长按保留原参数编辑功能。
7. 只临时测试，不固化。本版未实物验收；出现异常记录画面、声音和 L0～L7，保留现有 Flash，不反复擦写。

## 静音功能说明

- 实际零 PCM 连续约 400ms 后开始淡出，再约 200ms 隐藏；有效声音回来后约 200ms 渐入。
- 当前源是持续内部测试音，没有额外设计自动静音演示段，频谱持续出现正常。
- 调音箱音量、关音箱或拔音箱不会改变 FPGA PCM，不能用这些办法测试自动隐藏。
- 零 PCM、左右反相、仅右声道、噪声门限、样本中断及 epoch 已仿真。TF 真音乐接入后还须做对应实物验收。
- 不要往 TF 随意加 WAV/MP3 后期待自动播放，本版尚未实现 TF 音频读取。

## 请反馈四点

1. 四图、OSD/Logo 和声音是否仍正常？
2. 频谱是否无底板、柱间能看到原图？
3. 切图/音轨是否有长期残影或无信号？
4. K0+K1 短按隐藏/恢复是否正常？

本版完成仿真/编译/数值时序/位流生成，**下载和实屏验收尚未发生**；本次无需交接包。
'''
(root / '03_docs/v100_上板测试步骤.md').write_text(steps,encoding='utf-8')
(root / 'README_先看这里.md').write_text(f'''# v100 透明艺术频谱候选版

- VF-E20NG88 / EG4S20NG88 / 24MHz / 1280×720。
- 无背景板的青蓝紫 16 柱/峰值，实际 PCM 触发，静音淡出，切轨衰减；保留图片、OSD、Logo、音频、按键链路。
- TMDS 等价优化，不增加像素延迟；9 组仿真 + 原生 HDMI/ODDR 验证 + 综合/布局布线/四项 STA 数值通过，已生成 SRAM 候选。
- **未下载、未进行本版实物验收、未写 Flash；不是正式可靠性签核。**
- 当前内部 I2S 测试音；TF 音乐播放尚未实现。
- 工作位流：{bit}
- 测试说明：{root / '03_docs/v100_上板测试步骤.md'}
- 完整记录：{root / '03_docs/v100_实现与资源时序记录.md'}
- 资源：LUT {res['lut']}/19600，REG {res['reg']}/19600，BRAM9K {res['bram']}/64，DSP {res['dsp']}/29，PLL {res['pll']}/4。
- 数值时序：SWNS +0.454ns，STNS 0，HWNS +0.024ns，HTNS 0。
- 仿真预览：{preview}（不是实屏截图）。
- 工作目录：{root}
- 冻结快照：{archive}（归档结果以索引与 verify 为准）。
- 全部新增文件/临时目录/编译输出在 D 盘，旧版本保留；不改 TF、不自动写 Flash，无需交接 ZIP。
''',encoding='utf-8')
(root / 'README_归档位置待同步.md').write_text(
    f'# v100 路径说明\n\n工作副本：{root}\n冻结快照：{archive}\n\n以归档索引及 verify 结果为准，不在快照内编译/编辑。继承证据中的 C 盘路径为历史记录，不表示本版新输出放 C 盘。\n',encoding='utf-8')
print(json.dumps({'version':'v100','bit':str(bit),'sha256':sha(bit),
                  'resources':res,'slack_ns':phy['slack_ns'],
                  'preserved_files':len(records),'source_changes':len(changes),
                  'preview':str(preview),'new_hardware_test':False},ensure_ascii=False,indent=2))