"""Validate the recorded v086 checkpoint and write its documentation, not a build.

Never run this or any build script inside the immutable archive snapshot.
"""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[1]
if 'version_history' in ROOT.parts and '01_versions' in ROOT.parts:
    raise SystemExit('Refusing to write inside an archived version')
assert ROOT.name == 'v086_dynamic_bmp_scaler_20261025'
WORKSPACE = ROOT.parents[1]
HISTORY = Path(r'D:\FPGA_Billboard\99_archive\version_history')
VERSION_ID = ROOT.name
REPORTS = {
    'dynamic_bmp': '04_evidence/v086_dynamic_20261025_014316/summary.json',
    'spi_chain': '04_evidence/v086_actual_spi_20261025_014550/summary.json',
    'full_frame_packer': '04_evidence/v086_full_packer_20261025_015025/summary.json',
    'legacy_fat': '04_evidence/sim_fat_20261025_014348/summary.json',
    'legacy_pixels': '04_evidence/sim_legacy_20261025_014348/summary.json',
    'geometry': '04_evidence/sim_geometry_20261025_014703/summary.json',
    'board_top_injected': '04_evidence/v081_top_20261025_014703/summary.json',
    'subsystem_synthesis': '05_td/v086_dynamic_source_synth_attempt1/attempt.json',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


hash_checks = []


def verify_recorded_sources(value, report):
    if isinstance(value, dict):
        for relative, expected in value.get('source_sha256', {}).items():
            path = ROOT / relative
            assert path.is_file(), f'Missing tested source: {relative}'
            assert sha(path) == expected, f'Tested source changed: {relative}'
            hash_checks.append({'report': report, 'source': relative, 'sha256': expected})
        for key, child in value.items():
            if key != 'source_sha256':
                verify_recorded_sources(child, report)
    elif isinstance(value, list):
        for child in value:
            verify_recorded_sources(child, report)


reports = {name: load(relative) for name, relative in REPORTS.items()}
for name, report in reports.items():
    verify_recorded_sources(report, REPORTS[name])
    if name != 'subsystem_synthesis':
        assert report.get('result') == 'PASS' or (report.get('passed') is True and report.get('complete') is True), name
        for case in report.get('cases', report.get('tests', [])):
            assert case['passed'] is True, (name, case)

assert reports['dynamic_bmp']['requested_cases'] == reports['dynamic_bmp']['completed_cases'] == 76
assert Counter(c['case']['stage'] for c in reports['dynamic_bmp']['cases']) == {0: 30, 1: 23, 2: 23}
assert reports['spi_chain']['requested_cases'] == reports['spi_chain']['completed_cases'] == 7
assert len(reports['full_frame_packer']['cases']) == 4
assert len(reports['legacy_fat']['cases']) == 58
assert len(reports['legacy_pixels']['cases']) == 21
geometry_log = (ROOT / '04_evidence/sim_geometry_20261025_014703/simulation.log').read_text(encoding='utf-8')
assert 'cases=2048 accepted=320 rejected=1728' in geometry_log
assert 'checks=954' in '\n'.join(reports['board_top_injected']['tests'][0]['result_lines'])

synthesis = reports['subsystem_synthesis']
assert synthesis['returncode'] == 0 and synthesis['completed'] and synthesis['within_capacities']
assert synthesis['synth_marker_present'] and synthesis['gate_db_present'] and not synthesis['task_error']
area_relative = '05_td/v086_dynamic_source_synth_attempt1/dynamic_source_Runs/syn_1/dynamic_source_gate.area'
area = (ROOT / area_relative).read_text(encoding='utf-8')
resources = {key: int(re.search(r'^#' + key + r'\s+(\d+)', area, re.M).group(1))
             for key in ('lut', 'reg', 'bram', 'bram32k', 'dsp', 'pll', 'gclk', 'pad')}
assert resources == synthesis['resources'] == {
    'lut': 9330, 'reg': 3597, 'bram': 12, 'bram32k': 0,
    'dsp': 10, 'pll': 0, 'gclk': 0, 'pad': 30,
}
fallback_relative = '03_bitstreams/v081_picture_controls_720p.bit'
fallback_hash = '60b056d989b3ce37d934d4033e6e9e9de0de634e36c64822d1631809eb40e2e7'
assert sha(ROOT / fallback_relative) == fallback_hash
assert list((ROOT / '03_bitstreams').glob('*.bit')) == [ROOT / fallback_relative]

# Prove the actual board build and wiring were not silently switched to the new subsystem.
baseline = WORKSPACE / 'work/v085_scaler_ram_address_20261025'
changed = []
for path in (ROOT / '01_project').rglob('*'):
    if path.is_file():
        relative = path.relative_to(ROOT)
        old = baseline / relative
        if not old.is_file() or sha(path) != sha(old):
            changed.append(relative.as_posix())
assert set(changed) == {
    '01_project/rtl/tf/fat32_bmp_probe.v',
    '01_project/rtl/tf/bmp_pixel_stream.v',
    '01_project/rtl/tf/tf_bmp_source.v',
    '01_project/rtl/tf/tf_bmp_scaled_source.v',
    '01_project/rtl/scale/bmp_scale_bridge.v',
}

for name in ('README_先看这里.md',):
    inherited = ROOT / ('INHERITED_v085_' + name)
    if not inherited.exists():
        shutil.copy2(ROOT / name, inherited)
prepare = WORKSPACE / 'outputs/prepare_v086.py'
if prepare.is_file():
    shutil.copy2(prepare, ROOT / '08_tools/prepare_v086_record.py')


def write(relative, text):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + '\n', encoding='utf-8')


write('README_先看这里.md', '''
# v086：可变尺寸 BMP 接双线性缩放的源链路检查点

2026-10-25；VF-E20NG88 / EG4S20NG88 / 24 MHz。

## 一句话进度
已打通并验证“SPI → FAT32 → 可变宽高 BMP → 双线性缩放 → RGB332 坐标突发打包”的独立源子系统；**尚未接入整机 SDRAM/720p 显示链路，没有新位流，不是缩放功能实物通过**。

## 本版新增
- BMP 动态宽高、每行 DWORD 补齐、正/反行序和提交后的尺寸元数据；默认旧分支仍保留固定 640×480。
- 缩放桥接模块及实际 SPI 源封装；源文件验证和缩放排空均完成后，才允许发布成功。
- 76 例动态 BMP 事务仿真、7 例真实 SPI 主机 RTL 仿真通过；后者使用行为 SD 卡模型，不是物理卡实测。
- 1280×720 突发打包正反行序及两个异常场景共 4 例通过；完整 720p 双线性输出仍未取得通过结论。
- 新源子系统 TD 综合通过：LUT 9330/19600，REG 3597/19600，BRAM9K 12/64，DSP 10/29；不是整机总占用。
- 本轮重新运行旧 FAT32 58 例、旧像素流 21 例、BPB 差分 2048 例和顶层注入 954 检查，均通过；各自范围见测试矩阵。

## 现在你需要做什么
不需要操作板卡、TF 卡或 Flash。当前没有可推荐的新缩放 bit。
03_bitstreams 中的 v081 bit 只是 v082 已记录实物通过的旧功能回退，本轮未生成、下载或重新验收它。
下一步是将新源替换进入后台帧写入，并解决全屏 720p 双像素预取、读带宽与跨时钟标签，之后才做整机编译及上板。

## 目录入口
- VERSION_STATUS.json：当前机器可读状态。
- 03_docs/v086_本轮进度与测试矩阵.md：本轮完成与证据边界。
- 03_docs/v086_可变BMP格式与接口约定.md：支持格式及完成/错误协议。
- 03_docs/v086_资源查看与后续集成.md：本轮资源及下一阶段检查表。
- 04_evidence/v086_checkpoint_validation.json：本轮源码与证据哈希核对。
- 05_td/v086_dynamic_source_synth_attempt1：独立源子系统综合原始报告。

保留 RGB332 帧缓存、宏/内部延时/SiP/PVT/完整地址实物 BIST 边界；功能反馈不等于正式时序与可靠性签核。
旧版本全部保留；用户独立完成，不创建交接压缩包。
''')

write('03_docs/v086_本轮进度与测试矩阵.md', '''
# v086 本轮进度与测试矩阵

## 版本关系
v081 为亮度/对比度/OSD 代码基线；v082 记录用户对该版本的整体实物通过。
v085 解决独立缩放器的行缓存 BRAM 映射，未完成整机缩放。
v086 从 v085 的完整工作树复制发展；本版新增动态 BMP 源子系统，没有改动板级引脚、SDRAM 控制器、视频读端和生产构建 Tcl。
旧生产路径的默认参数仍是固定 640×480 图片居中显示；不能运行旧构建后把旧画面说成新缩放通过。

## 本轮重新运行并取得结果的测试

| 项目 | 结果 | 实际范围 | 证据目录（均在 04_evidence） |
|---|---|---|---|
| 动态 BMP 事务链 | 76/76 PASS | 30 头解析 + 23 原像素 + 23 缩放/打包；缩放输出 32×18 | v086_dynamic_20261025_014316 |
| 真实 SPI 主机 RTL 链 | 7/7 PASS | 合成用 SPI 主机 + 行为 SD 卡模型 + FAT/BMP/缩放/打包，输出 32×18；首例含复位重试 | v086_actual_spi_20261025_014550 |
| 完整尺寸 RGB332 打包 | 4/4 PASS | 合成像素源，1280×720 正反行序各 1 例，各 921600 像素/57600 突发；另 2 例小图错误注入 | v086_full_packer_20261025_015025 |
| 旧 FAT32/BMP 探测 | 58/58 PASS | 当前修改后 RTL 的默认固定尺寸分支 | sim_fat_20261025_014348 |
| 旧原始像素流 | 21/21 PASS | 当前像素流默认旧参数分支 | sim_legacy_20261025_014348 |
| BPB 几何差分 | 2048/2048 PASS | 与保存的 v056 参考几何判定比较；接受 320、拒绝 1728，不是形式穷尽证明 | sim_geometry_20261025_014703 |
| 现有板级顶层注入 | 954 检查 PASS | 注入 FIFO/坐标/内容 epoch，行为 PLL 及无驱动 SDRAM 壳，不证明真实卡和内存链路 | v081_top_20261025_014703 |
| 新源子系统 TD 综合 | PASS | 1280×720 配置的 SPI/FAT32/BMP/缩放/打包；未布局布线/未做系统时序 | ../05_td/v086_dynamic_source_synth_attempt1 |

动态事务测试覆盖行补齐 0/1/2/3 字节、单行/单列、正反行序、碎片 FAT、跨扇区/簇的像素与补齐、65535/65536 偏移、背压、复位重试及无效头/CRC/超时/截断/异常尾链。
有效流包含 1280×3 与 1×1024；1280×1024 在本组只验证文件头接受，不是最大图像整帧播放通过。
像素参考由独立整数四角加权公式产生，按输出坐标检查 RGB332 突发内容。
上游读完但缩放未排空的场景有明确覆盖；坏扇区提交前不可发像素，源错误不可发布半帧成功。

## 明确未完成
- 完整 1280×720 **双线性缩放**输出仿真仍未获得完成结论；本轮 720p 打包测试没有替代该项。
- 缩放结果接入真实 SDRAM 后台帧、720p 视频读端、整机仲裁/跨时钟与下溢测试。
- 新整机综合、布局布线、约束/时序审查及新位流。
- 本轮硬件下载、屏幕实测、冷启动、Flash 固化；全部未做，不继承 v082 的实物通过。
- RGB332、宏/内部延时/SiP/PVT、完整地址实物 BIST 和正式可靠性签核边界仍保留。

## 重跑约定
先将归档完整复制到新工作目录；不要在冻结快照中运行会写日志的脚本。
02_tests/dynamic_bmp 下提供 run_dynamic_tests.py、run_spi_tests.py、run_full_frame_packer.py 入口；需要本机既有 Icarus/TD 环境。
run_source_synth.py 为本次单次综合记录入口，其输出目录已存在会主动拒绝覆盖；再次综合应使用新尝试目录，不能删除历史报告强行复用。
build 中可重建 fixture、vvp、波形未放入归档；生成脚本、case 参数、fixture 哈希、源码哈希、命令和原始日志保留。
继承的 v083/v084/v085 等历史报告按原版本读取，不当作本轮新增结论。
''')

write('03_docs/v086_可变BMP格式与接口约定.md', '''
# v086 可变 BMP 格式与接口约定

## 当前新子系统支持范围（未接入板级生产路径）
- 仅只读 FAT32，沿用现有 512 字节扇区、根目录短文件名与有界扫描规则；不是新增 exFAT/FAT16/长文件名/目录递归支持。
- BMP 必须为 BM、planes=1、24bpp、BI_RGB 无压缩，DIB 头至少 40 字节。
- 默认配置：源宽 1..1280、绝对高度 1..1024；正高度为 bottom-up，负高度为 top-down；拒绝 0、负宽、INT_MIN 高度、越界值。
- 像素偏移 54..65536，DIB 结束必须在像素前；行 stride=(width*3+3)&~3。
- 本版动态分支有意严格要求目录 file_size=offset+stride*height，且 BMP bfSize 与之相等，不接受尾随数据；biSizeImage=0 可接受，非零必须等于 stride*height。
- 补齐字节被消费但不作为 RGB 像素输出；payload CRC32 包括行补齐、不含像素前文件头。
- 仍保留 SD CRC16 校验后才交付的 512 字节隔离缓存、FAT 越界/截断/尾链检查和超时机制。
- RGB888 插值后仍量化为 RGB332 SDRAM 数据；不能因此声称整链路 24bit 显示精度。
- “任意分辨率”在本实现中是上述有界配置内的可变尺寸，不是无限尺寸，也不表示所有尺寸都已实物测试。

## 模块与元数据
fat32_bmp_probe.v：新增 DYNAMIC_SIZE 默认 0；新增 source_width、source_height、row_stride。动态分支用分周期 stride/payload/commit 状态，SD 校验及格式检查全部通过才提交元数据。
bmp_pixel_stream.v：动态模式启动时锁存宽高/方向，跨扇区和碎片簇保留 BGR 与补齐阶段；默认模式保留旧 WIDTH/HEIGHT 路径。
tf_bmp_source.v：传递尺寸及 source_top_down，默认 DYNAMIC_SIZE=0，旧板级实例不自动开启缩放。
bmp_scale_bridge.v：元数据有效后一次性启动缩放，输入与输出均受 valid/ready 背压；要求整次装载 epoch 复位后重试，不支持未复位原地二次启动。
tf_bmp_scaled_source.v：封装合成用 SPI 主机、FAT/BMP 与缩放桥；默认输出 1280×720，提供 RGB888 和逻辑坐标。
bmp_pixel_packer.v：未修改算法，下一阶段应配置 WIDTH=1280/HEIGHT=720，按坐标而非到达顺序生成 16 字节 RGB332 突发。

## 完成、错误与后台帧发布
1. metadata_valid 只能代表合法头与尺寸可用，不是整张图片完成。
2. raw source_done 可能早于缩放器输出排空；桥接 done/ok 仅在源成功验证并且 scaler_done 后置位。
3. 原始源错误优先，立即阻止继续交付，保留源错误码；源 done 且 !ok 但无原始错误码时返回 0x40；缩放错误返回 0x4?。
4. 打包器还需等待最后一个突发 req_ack，不能直接把桥接 done 当成 SDRAM 帧完成。
5. 任何已部分写入的后台帧都不能对前台可见；完成成功才可在安全帧边界发布，失败必须保持原前台并重试/报错。
6. 当前 req_ack 在仿真中由测试平台产生，尚未接入本版真实 SDRAM 仲裁路径。这是后续集成项，不是已经证明的实物行为。

## 外设与板卡约束
坚持 EG4S20NG88、24 MHz 和实际原理图；本版没有新增 PAD 约束，不借用 BG256 管脚或不存在的拨码开关。
原理图、ADC、SDC、生产 Tcl 原样保留。独立综合 harness 的 PAD30 只用于观察输出，不是广告牌实际板级引脚表。
''')

archive_project = HISTORY / '01_versions' / VERSION_ID / '01_project'
resource_doc = f'''
# v086 资源查看与后续集成

## 最新资源结论的范围
本次综合的是整个**新源子系统**：SPI + FAT32 + 动态 BMP + 双线性缩放 + RGB332 打包，输出配置 1280×720。
**不是整机总占用，也不是 v085 的独立插值器。** 没有加入实际 SDRAM 控制、HDMI、OSD、音频、按键或板级时钟实现。

| 资源 | 使用 / 器件容量 | 占比 |
|---|---|---|
| LUT | 9330 / 19600 | 47.60% |
| 寄存器 | 3597 / 19600 | 18.35% |
| BRAM9K | 12 / 64 | 18.75% |
| BRAM32K | 0 / 16 | 0% |
| DSP | 10 / 29 | 34.48% |
| PLL | 0 / 4 | 0% |

诊断 harness 另有 GCLK=0、PAD=30；不能用它判断整机最终时钟/引脚占用。
源链路内部缩放桥的行 RAM 已映射为 12 个 BRAM9K，缩放部分使用 6 个 DSP；其余 DSP 来自源解析/打包等逻辑。
v085 的 LUT1122/DSP6 是更小的独立缩放模块，不能误认为本轮总设计突然增加到该差值。
历史 v081 整机 LUT12622/REG5674/BRAM9K17/DSP3/PLL3 也不是本版结果；新子系统会替换旧源路径，既不能直接相加，也不能承诺集成必然容纳。

## 你如何查看
当前工作副本中的原始面积报告：
`{ROOT / area_relative}`

计划的 D 盘报告位置（仅在 D 盘归档保存成功后才存在）：
`{archive_project / area_relative}`

在 TD 综合完成后打开 *_gate.area，搜索 Utilization Statistics，以 #lut/#reg/#bram/#dsp 等汇总为准，不把层级表的 lut 列当成整体总数（还可能涉及 ripple 等统计）。
对应综合命令、源码哈希与完成标记在同目录上层 attempt.json 与 run.log。
综合仍有匿名网、未驱动节点补零、RAM 初值忽略等告警；不能称为零警告。缓存加载后才被读取，不依赖被忽略的 RAM 初值，但这不替代网表/形式/实物验证。
本轮没有布局布线、实际板级时序报告或可靠性签核。

## 下一阶段按此顺序集成（本版未实现）
1. tf_bmp_loader 替换为新 scaled source，并以 1280×720 打包写后台 bank，最后一个 ack 和全部源校验均通过才允许换帧。
2. 双 bank 的 RGB332 每帧 921600 字节/57600 突发，2 MiB bank、131072 突发 bank 偏移保持隔离；用断言检查最大地址与溢出。
3. 读端从每行 40 突发/480 行改为 80 突发/720 行：列至少 7 位、行至少 10 位、帧内偏移至少 16 位；覆盖最后一行/最后突发及倒序源行。
4. 49.5 MHz 每拍一像素吞吐上限低于 720p60 平均 55.296 M 像素/秒，不能只改分辨率常数。优先设计成对像素 FIFO/预取，明确仲裁、水位、标签和跨时钟边界。
5. 独立验证双像素顺序、FIFO 停顿/下溢恢复、切页/重试/reset epoch、40 步滑动和最后像素地址，避免半帧发布及旧新帧混用。
6. 保留现有四图轮播、手动/自动、亮度/对比度、OSD 及音频可见门控；同步调整有效图像区域和各流水延迟。
7. 补足完整 720p 双线性输出仿真，再做整机资源/布局布线/时序检查，合格后才生成下一版测试 bit。
8. 届时先 SRAM 临时下载并验证多尺寸/补齐/方向/坏卡/重试/冷启动；通过前不覆盖原 Flash 固化基线。

大 BMP 的 SPI 装载时延随原图字节数和背压变化，本版不承诺所有支持尺寸都在 5 秒内载入。
RGB332、SDRAM 宏/内部延时/SiP/PVT/完整地址实物 BIST 的旧边界仍未关闭。
'''
write('03_docs/v086_资源查看与后续集成.md', resource_doc)
write('03_bitstreams/README_v086_没有新位流.md', '''
# v086 没有新测试位流

本轮只完成动态 BMP/缩放源子系统的仿真及独立综合，没有整机实现或新 bit。
目录中的 v081_picture_controls_720p.bit 是已由 v082 记录用户实物通过的旧功能回退；不是 v086 源码生成的位流。
其 SHA256：60b056d989b3ce37d934d4033e6e9e9de0de634e36c64822d1631809eb40e2e7。
本轮无需下载或改动 TF 卡/Flash；待新整机测试位流生成后另行给出步骤。
''')

status = {
    'version': 'v086', 'id': VERSION_ID,
    'status': 'DYNAMIC_BMP_SCALED_SOURCE_VALIDATED_NOT_BOARD_INTEGRATED',
    'date': '2026-10-25',
    'target': {'board': 'VF-E20NG88', 'device': 'EG4S20NG88', 'input_clock_hz': 24000000},
    'parent_version': 'v085_scaler_ram_address_20261025',
    'hardware_fallback': {'code_and_bit': 'v081', 'acceptance_record': 'v082',
                          'bit': fallback_relative, 'sha256': fallback_hash,
                          'newly_generated_or_revalidated': False},
    'implemented_in_new_subsystem': [
        'dynamic BMP metadata, DWORD row padding, top-down/bottom-up',
        'real SPI host RTL to FAT/BMP to bilinear to coordinate RGB332 bursts',
        'source validation plus scaler-drain completion and error gating',
    ],
    'tests': {
        'dynamic_bmp': {'passed': True, 'cases': 76, 'stages': {'header': 30, 'raw': 23, 'scaled_and_packed': 23}, 'scaled_output': [32, 18]},
        'spi_chain': {'passed': True, 'cases': 7, 'sd_card': 'behavioral model, not physical hardware', 'scaled_output': [32, 18]},
        'full_frame_packer': {'passed': True, 'cases': 4, 'full_frames': 2, 'full_frame_pixels': 921600, 'bursts_per_full_frame': 57600, 'source': 'synthetic, not bilinear'},
        'legacy_fat': {'passed': True, 'cases': 58},
        'legacy_pixels': {'passed': True, 'cases': 21},
        'geometry': {'passed': True, 'cases': 2048, 'accepted': 320, 'rejected': 1728, 'formal_proof': False},
        'board_top_injected': {'passed': True, 'checks': 954, 'real_tf_or_sdram': False},
    },
    'independent_source_subsystem_synthesis': {
        'passed': True, 'configured_output': [1280, 720], 'resources': resources,
        'scope': synthesis['scope'], 'area_report': area_relative, 'warnings_remain': True,
    },
    'reports': REPORTS,
    'changed_or_new_project_files': sorted(changed),
    'board_top_scaling_enabled': False,
    'full_720p_bilinear_output_simulation': 'NOT_CLOSED; packer-only result is not a substitute',
    'new_system_synthesis': False, 'new_system_place_route': False,
    'new_system_timing_signoff': False, 'new_bit_generated': False,
    'programming_this_version': False, 'hardware_acceptance_this_version': False,
    'flash_modified': False, 'handoff_zip_created': False,
    'open_items': [
        'SDRAM background-frame integration, full720p reader bandwidth and CDC/tag/underflow tests',
        'complete full720p bilinear simulation and system implementation/resource/timing review',
        'new bit and independent hardware acceptance, cold-start and retry',
        'RGB332 remains; macro/internal-delay/SiP/PVT/full-address physical BIST not closed',
    ],
}
write('VERSION_STATUS.json', json.dumps(status, ensure_ascii=False, indent=2))
validation = {
    'version': 'v086', 'result': 'PASS',
    'checked_at': datetime.now().astimezone().isoformat(),
    'scope': 'Checkpoint evidence/source consistency; does not run simulations, TD or hardware',
    'report_sha256': {relative: sha(ROOT / relative) for relative in REPORTS.values()},
    'source_hash_checks': hash_checks, 'source_hash_check_count': len(hash_checks),
    'fallback_sha256': fallback_hash, 'synthesis_resources_crosschecked_against_area': resources,
    'changed_or_new_project_files': sorted(changed),
    'new_bit_generated': False, 'hardware_acceptance_this_version': False,
}
write('04_evidence/v086_checkpoint_validation.json', json.dumps(validation, ensure_ascii=False, indent=2))
print('PASS v086 checkpoint: all 8 reports checked against current sources;', len(hash_checks), 'source-hash entries')
print('NO NEW BIT, NO HARDWARE OR FLASH TEST, NO ZIP')
