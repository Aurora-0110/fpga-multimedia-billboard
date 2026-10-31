"""Freeze the actual v087 evidence and documentation, without any hardware IO.

Run only in the writable work tree, never inside an archived snapshot.
"""
from datetime import datetime
import hashlib, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
assert ROOT.name == 'v087_scaled_frame_pipeline_20261025'
assert '01_versions' not in ROOT.parts, 'Do not change immutable snapshots'
WORKSPACE = ROOT.parents[1]
BASELINE = WORKSPACE / 'work/v086_dynamic_bmp_scaler_20261025'
REPORTS = {
    'pair_units': '04_evidence/v087_pair_units_20261025_110422/summary.json',
    'pair_memory': '04_evidence/v087_pair_memory_20261025_110438/summary.json',
    'full_scaler': '04_evidence/v087_full_scaler_20261025_110215/summary.json',
    'scaled_spi_memory': '04_evidence/v087_scaled_spi_memory_20261025_110708/summary.json',
    'pair_top': '04_evidence/v087_pair_top_20261025_111742/summary.json',
    'legacy_units': '04_evidence/v081_units_20261025_111752/summary.json',
    'legacy_top': '04_evidence/v081_top_20261025_111808/summary.json',
    'packet_gate': '04_evidence/v081_packet_gate_20261025_111808/summary.json',
    'osd_clock': '04_evidence/v081_clock_20261025_111809/summary.json',
    'system_synthesis': '05_td/v087_scaled_system_synth_attempt2/attempt.json',
    'physical': '05_td/v087_scaled_system_physical_attempt1/attempt.json',
    'bitgen': '05_td/v087_scaled_system_bitgen_attempt1/attempt.json',
}
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))
def put(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')

reports = {name: load(path) for name, path in REPORTS.items()}
checks = []
def check_sources(obj, report):
    if isinstance(obj, dict):
        for label in ('source_sha256', 'sha256'):
            hashes = obj.get(label, {})
            if isinstance(hashes, dict):
                for relative, expected in hashes.items():
                    p = ROOT / relative
                    assert p.is_file() and sha(p) == expected, (report, relative)
                    checks.append({'report': report, 'source': relative, 'sha256': expected})
        for key, child in obj.items():
            if key not in ('source_sha256', 'sha256'):
                check_sources(child, report)
    elif isinstance(obj, list):
        for item in obj:
            check_sources(item, report)
for name, report in reports.items():
    check_sources(report, REPORTS[name])
    if name in ('system_synthesis', 'physical', 'bitgen'):
        assert report['completed'] and not report['task_error'], name
    else:
        assert report.get('result') == 'PASS' or report.get('passed') is True, name
        assert all(c['passed'] for c in report.get('cases', report.get('tests', []))), name

assert len(reports['full_scaler']['cases']) == 2
for case in reports['full_scaler']['cases']:
    assert 'pixels=921600' in '\n'.join(case['result_lines'])
assert 'pixels=7372800' in '\n'.join(reports['pair_memory']['tests'][1]['result_lines'])
assert 'checks=978' in '\n'.join(reports['pair_top']['tests'][0]['result_lines'])
assert reports['physical']['slack_ns'] == {'SWNS': 0.124, 'STNS': 0.0, 'HWNS': 0.014, 'HTNS': 0.0}
assert reports['system_synthesis']['within_capacities']
bit = ROOT / '03_bitstreams/v087_bilinear_full720p.bit'
assert sha(bit) == reports['bitgen']['bit_sha256'] == 'ae01fa2a47fb3fcaced252d7af8cbeba23cdb3307bb14b5072931b64dc5844a1'
fallback = ROOT / '03_bitstreams/v081_picture_controls_720p.bit'
assert sha(fallback) == '60b056d989b3ce37d934d4033e6e9e9de0de634e36c64822d1631809eb40e2e7'

# All existing accepted-path files are kept, not silently switched to scaled RTL.
unchanged = []
for old in (BASELINE / '01_project').rglob('*'):
    if old.is_file() and old.suffix in ('.v', '.vh', '.adc', '.sdc', '.tcl') and 'build' not in old.parts:
        rel = old.relative_to(BASELINE)
        assert sha(ROOT / rel) == sha(old), rel
        unchanged.append(rel.as_posix())
new_files = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / '01_project').rglob('*')
                   if p.is_file() and not (BASELINE / p.relative_to(ROOT)).exists() and 'build' not in p.parts)
assert len(new_files) == 8, new_files

# The official archiver omits directories called build. Keep an unchanged native
# project copy outside that cache name, including .al/.prj/databases/reports/logs.
syn = ROOT / '05_td/v087_scaled_system_synth_attempt2'
preserved = syn / 'native_project_record'
assert not preserved.exists(), 'Do not overwrite retained TD evidence'
shutil.copytree(syn / 'build', preserved)
retained = []
for p in (syn / 'build').rglob('*'):
    if p.is_file():
        q = preserved / p.relative_to(syn / 'build')
        assert sha(p) == sha(q)
        retained.append({'path': q.relative_to(ROOT).as_posix(), 'sha256': sha(q)})
put('05_td/v087_scaled_system_synth_attempt2/README_原生工程留档.md',
    '# 原生 TD 工程留档\n\nnative_project_record 是 build 目录的逐文件原样复制，'
    '供归档保留 .al/.prj/网表数据库/日志/资源报告；不是另一次综合。'
    '其中原相对路径和绝对历史路径不重写。重建请复制完整版本到工作目录，'
    '运行 01_project/build_scaled_video.tcl 或在新 attempt 目录执行测试脚本，'
    '不要直接在归档内运行，更不要把 native_project_record 当成已配置好路径的新工作目录。\n')

phy_dir = ROOT / '05_td/v087_scaled_system_physical_attempt1/physical'
area = (phy_dir / 'sdram_phy.area').read_text(encoding='utf-8')
keys = ('lut', 'reg', 'bram', 'bram32k', 'dsp', 'pll', 'gclk', 'pad')
resources = {k: int(re.search(r'^#' + k + r'\s+(\d+)', area, re.M).group(1)) for k in keys}
assert resources == {'lut': 14413, 'reg': 6553, 'bram': 32, 'bram32k': 0, 'dsp': 13, 'pll': 3, 'gclk': 4, 'pad': 18}
caps = {'lut': 19600, 'reg': 19600, 'bram': 64, 'bram32k': 16, 'dsp': 29, 'pll': 4, 'gclk': 16, 'pad': 66}
assert all(resources[k] <= caps[k] for k in keys)
ts = (ROOT / '05_td/v087_scaled_system_bitgen_attempt1/bit_source.ts').read_text(encoding='utf-8')
assert 'SWNS: 0.124ns' in ts and 'HWNS: 0.014ns' in ts
check = (phy_dir / 'sdram_check.rpt').read_text(encoding='utf-8')
oldcheck = (ROOT / '05_td/v081_attempt1_normal_user/reports/sdram_check.rpt').read_text(encoding='utf-8')
def counts(text):
    return {m.group(1): int(m.group(2)) for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)', text, re.M)}
assert counts(check) == counts(oldcheck) == reports['bitgen']['check_timing_counts']
timing = (phy_dir / 'sdram_pr.timing').read_text(encoding='utf-8')
assert 'STA coverage        : 99.88%' in timing

status = {
    'version': 'v087', 'date': '2026-10-25', 'target': 'VF-E20NG88 / EG4S20NG88 / 24MHz',
    'status': 'SCALED_SYSTEM_DIAGNOSTIC_BIT_READY_AWAITING_HARDWARE',
    'source_baseline': 'v086_dynamic_bmp_scaler_20261025',
    'rollback_hardware_baseline': 'v081 code/bit, user overall acceptance recorded in v082',
    'candidate_top': 'idx_scaled_video_top', 'old_top_preserved': 'idx_video_top',
    'new_bit_generated': True, 'recommended_sram_test_bit': str(bit.relative_to(ROOT)),
    'new_bit_sha256': sha(bit), 'hardware_acceptance_this_version': False,
    'programmed_this_version': False, 'flash_modified': False,
    'source_range': '24bpp BI_RGB, width1..1280, abs(height)1..1024, FAT32 8.3 A/B/C/D.BMP',
    'framebuffer_format': 'RGB332', 'output': '1280x720 full active area, align-corners bilinear stretch',
    'source_read_format': 'RGB888', 'physical_resources': resources,
    'synthesis_only_resources': reports['system_synthesis']['resources'],
    'timing_ns': reports['physical']['slack_ns'], 'sta_coverage_percent': 99.88,
    'formal_release_approved': False, 'zip_created': False, 'reports': REPORTS,
    'unresolved': reports['bitgen']['known_open_review'] + [
        'No full-size single-run SPI-to-HDMI simulation; verification split by subsystem',
        'Full-height slide checked first2steps; all40steps checked reduced-height plus reader wraps',
        'No claim of all source dimensions physically accepted, five-second loading, or24bit framebuffer'],
}
put('VERSION_STATUS.json', json.dumps(status, ensure_ascii=False, indent=2) + '\n')
put('03_bitstreams/v087_SHA256.txt', sha(bit) + '  ' + bit.name + '\n')
put('README_先看这里.md', '''# v087：可变 BMP 双线性缩放已接入 SDRAM/全屏720p（待上板验收）

2026-10-25；VF-E20NG88 / EG4S20NG88 / 24 MHz。

## 现在的进度
新候选顶层 idx_scaled_video_top 已连接：SPI → FAT32/可变尺寸24bit BMP →
双线性 RGB888 插值 → RGB332后台帧 → SDRAM双缓存/双像素预取 → 全屏1280×720 →
亮度/对比度 → 多层OSD → HDMI音视频。保留四图轮播、自动/手动、40帧左右滑动。
**仿真、整机综合、布局布线及当前约束下数值时序检查已通过，并生成临时测试位流；
尚未下载或实物验收本版，不等于所有宏模型、IO、SiP/PVT与可靠性问题已关闭。**

## 你现在只需做这一件事
先保持 TF 原来的四张640×480官方图片和现有接线，在 TD 仅下载
`03_bitstreams/v087_bilinear_full720p.bit` 到 FPGA SRAM。
不要写Flash，不要重新安装驱动，不要先换TF素材。详细步骤：`03_docs/v087_上板测试步骤.md`。
预期原来居中的图片会被拉伸到整个720p有效画面；OSD和4像素白边仍覆盖在图片上。
输出仍是 RGB332 帧缓存的颜色精度，不是24bit帧缓存。

## 本轮已检查
- 两组完整1280×720双线性输出，逐像素比较，共1,843,200像素通过。
- 实际SDRAM控制器/厂商总线模型/异步FIFO/显示：全720p连续8帧7,372,800像素及后台写入通过；
  全高度转场验证前2步，缩短高度另测全40步及旧缓存复用。
- 实际SPI主机→动态BMP→缩放→SDRAM总线模型→显示的小尺寸整链路4场景通过，含补齐跨扇区、
  碎片链、正反行序、重试及后部CRC错误禁止发布；不冒称全720p单次整链仿真。
- 新候选顶层音画门控/OSD/调节/按键/复位联动注入978检查通过，旧回退顶层954检查重新通过。
- 新整机物理映射：LUT14413/19600、REG6553/19600、BRAM9K32/64、DSP13/29、PLL3/4。
- 当前约束数值：SWNS+0.124ns、HWNS+0.014ns、STNS/HTNS=0，覆盖99.88%；保持余量很小。

## 入口
- `VERSION_STATUS.json`：机器可读状态与各份证据索引。
- `03_docs/v087_本轮进度与测试矩阵.md`：精确验证范围、失败尝试原因。
- `03_docs/v087_整机资源与时序边界.md`：实际整机资源，不是独立插值模块资源。
- `03_docs/v087_上板测试步骤.md`：本轮临时下载与可选多尺寸测试。
- `03_docs/v087_实物验收记录_待填.md`：尚未填写，不预设通过。
- `01_project/build_scaled_video.tcl`：新候选构建；旧build_idx_video.tcl和idx_video_top不改。

v081旧bit仅作回退，用户整体通过反馈保存于v082；旧Flash记录v074/v072，本轮未动。
所有历史版本保留；用户独立完成，无需交接压缩包。
''')
put('03_docs/v087_本轮进度与测试矩阵.md', '''# v087 本轮进度与测试矩阵

## 改动与原因
原读通道一个SDRAM时钟最多输出1像素，不能简单把640×480窗口改成全屏。
新增 idx_pair_reader/idx_pair_display/idx_pair_pipeline：24bit FIFO字携带2个RGB332像素和8bit图号/步数标签。
FIFO容量4096对=8192像素；分配与预填单位统一为“对”，标签跟随实际像素而不是裸FIFO输出。
reader有在途/队列/移位缓存，保持注册ACK语义；按完整逻辑帧变更40步转场，80突发/行每步移2突发。
最后一个旧缓存物理读已排空后才允许复用旧银行；尚在FIFO内的数据是独立副本，不依赖旧银行。
新 tf_scaled_loader 等待源校验成功、插值输出排空及最后突发确认后才发布 done。
独立新顶层 idx_scaled_video_top 使用完整 de 区域；其余按键/PLL/原理图引脚/音频/OSD/调节/SDRAM控制器保持。
v086 所有既有生产文件逐个哈希比对未改，原顶层和原构建仍可回退。

## 本轮最新有效结果（所有原始目录见 VERSION_STATUS.json）
|项目|实际范围|结果与限制|
|---|---|---|
|双像素reader|3行全宽、4轮转场含D→A；另720行到前2步|637440 + 3686400像素检查通过；全宽/高尾地址、标签、ACK、FIFO满背压|
|双像素display|注册FIFO响应、两lane、奇数段宽、消隐、缺流、复位重试|624检查/4epoch通过；不是总线或实物|
|SDRAM整读写|实际控制器+IS42s32200模型+异步FIFO+pair显示|8行全40步440320像素；720行8帧7372800像素；后台写入与刷新同时运行，无缺流|
|全720p插值|640×480 top-down、17×11 bottom-up →1280×720|每例921600像素逐个对独立整数模型比较；两例共1843200，通过，非TF整链|
|SPI缩放缓存显示|真实SPI RTL、行为SD卡、实际控制器/总线模型、输出32×18|4场景含1个重试epoch；正反序/碎片链/补齐跨扇区/SDSC/后部CRC拒绝，全部通过；不是全720p整链|
|新顶层接线联动|真实新top、pair显示、调节、OSD、HDMI音频门控；注入FIFO/坐标/epoch|978检查通过；PLL行为替代、SDRAM空壳，不是实际TF/存储图像验收|
|旧路回归|原reader/playlist/OSD/controls/adjust、旧top、音频包门控、时间滚动|全部重新通过，954旧top检查；不借用为新实物记录|
|实际新整机TD|新top，实际ADC/SDC，EG4S20NG88|综合attempt2及物理attempt1通过，bitgen从同一已审查布线DB生成|
|硬件/Flash|未执行|本版待用户临时SRAM测试，Flash不改|

完整720p总线带宽测试最低FIFO占用1942对，后台写57600突发，刷新9520次；这是该模型/该运行范围的数值，不保证所有卡/板/PVT。
第一张图可见后后台预取下一张；图间时间仍由TF读取、插值及预取决定，不能保证每张严格5秒。
新图先完整验证才转场，失败不展示半张后台帧。

## 保留的失败尝试（不能混写成通过）
- reader最初将全720p所有40步放入100ms看门狗，超时；现在全高测前2步，全40步在3/8行测试。
- 总线TB最初在NBA之后检查原de而不是延迟后的dd，行末误报；修正TB采样，新RTL未因此更改。
- SPI整链TB第一次编译因init声明在使用之后失败；修正声明后4场景重跑通过。
- 第一轮全720p插值300s预算在半帧附近超时，无逐像素失配；一次有依据的900s上限重跑，两例分别约551s/479s通过。
- 整机综合attempt1由于TD的file normalize在当前沙箱账户下丢弃Documents路径，实际读入0源码，失败。
  有独立路径诊断日志证明原绝对路径存在、normalize结果不存在；仅新Tcl改为保留绝对路径，attempt2才成功。
- 新top注入TB第一次在内容复位同一拍发frame_start，pair本地队列尚未预填；加入真实启动所需的预填间隔后重跑通过。

未声称全尺寸全40步单次TF→HDMI整链仿真、全尺寸上板或正式STA/PVT签核。
''')
table = '\n'.join(f'| {k.upper()} | {reports["system_synthesis"]["resources"][k]} | {resources[k]} | {caps[k]} | {resources[k]/caps[k]*100:.2f}% |' for k in keys)
put('03_docs/v087_整机资源与时序边界.md', '''# v087 实际整机资源及数值时序

器件EG4S20NG88，顶层idx_scaled_video_top；不是单独插值器或源子系统。
综合与物理映射的优化/打包口径不同，优先用物理列作为本版实现占用。

|资源|综合后|布局布线后|器件总数|物理占比|
|---|---:|---:|---:|---:|
''' + table + '''

BRAM32块都是BRAM9K，BRAM32K为0/16，不把两种块直接相加。
LUT物理14413/19600=73.54%，剩5187；相较旧v081物理12622增加1791。
层级LUT表/LE/汇总不是能再相加的独立资源；PAD余量不是板载可用排针数。
片内RAM表不表示SiP SDRAM容量；RGB332整帧921600字节，两个帧分别从突发0和131072起，未混成24bit帧缓存。

## 如何自己看
用TD/VSCode/记事本打开 `05_td/v087_scaled_system_physical_attempt1/physical/sdram_phy.area`，
搜索 `Utilization Statistics`，先核对顶层和器件，再看#lut/#reg/#bram/#dsp/#pll。
同一目录 `sdram_pr.timing` 和 `sdram_phy.ts` 是本次布线后的时序，
bitgen目录 `bit_source.ts` 是导入同一布线DB后重算的确认。
综合原始报告另见 `05_td/v087_scaled_system_synth_attempt2/native_project_record/idx_video_Runs/syn_1/idx_video_gate.area`。
原生.al/.prj/DB及日志保留在native_project_record，未重写原内部路径；可重建build排除不再丢失这些证据。

## 已通过与未签核分开
SWNS+0.124ns，STNS0，HWNS+0.014ns，HTNS0；STA覆盖99.88%。
setup/hold数值非负，但余量很小，覆盖不是100%，不能宣布可靠性签核。
没有新增放宽时钟、整片false path或掩盖负时序；ADC/SDC与v086完全相同。
check_timing计数与旧v081相同：no-clock/clock-definition/invalid/PLL-clock/loops/no-path/ignored均0；
dummy3、no-input-delay2（异步按键）、no-output-delay7（LED及HDMI）、abnormal-input-delay33仍需审查。
33项包括32根原生SDRAM DQ内部延时注释和TF_MISO的假定输入预算，不应写成“只有32项且全已豁免”。
原生宏仍有PHY-7002初始位置迁移，未强塞BG256或未经支持坐标；未出现新的USR-6135反馈警告。
SiP电压/速度等级、厂商内部DQ模型、SPI板级IO预算、dummy节点、PVT、完整地址实物BIST仍开放。
只提供可回退的SRAM实验位流，不自动固化或把数值通过写成正式release。
''')
put('03_docs/v087_上板测试步骤.md', '''# v087 上板测试：先原四图，再可选不同宽高

## 0. 这次测什么
测试新候选的“BMP动态宽高→双线性→全屏720p SDRAM缓存→音视频/OSD”硬件整合。
这不是重新测试驱动；不要卸载驱动、改许可证或更换引脚接线，也不要先写Flash。

## 1. 先保持原状
1. TF根目录保持原A.BMP/B.BMP/C.BMP/D.BMP四张640×480正式图片；本次不需要取卡换素材。
2. 保持已验证的独立供电、HDMI输入与下载器连接；任何改接线/换卡先断板卡电源。
3. 显示器选原来能显示720p的HDMI输入，先接好并供电，板卡稳定后再下载。

## 2. 在TD临时下载一次
1. 打开已有下载工具，选与之前成功相同的下载器和EG4S20NG88器件。
2. 仅保留本次FPGA SRAM配置操作，选本版 `03_bitstreams/v087_bilinear_full720p.bit`。
   SHA256：ae01fa2a47fb3fcaced252d7af8cbeba23cdb3307bb14b5072931b64dc5844a1。
3. 不选SPI Flash写入/擦除/固化，不改驱动或下载时钟。点击执行，确认下载成功后等待图像。
4. 第一张TF读取需时间，先等约20～30秒；若仍无图，不反复刷bit，记录LED及屏幕提示反馈。

## 3. 第一轮判定
- 输出模式仍应为1280×720；图片从原640×480居中小窗口改为拉伸填满有效画面（非等比保留黑边）。
- 4像素白边、顶部/底部OSD、安路Logo继续存在；OSD会遮挡其下面的图片，这是叠加设计。
- 四张图自动轮播至少2轮；转场40帧左右滑动约0.67秒（名义60Hz），中途不应断信号/闪黑/花屏。
- 图片可见时仍有测试音，首图装载/无图期间不应误播；只检查测试音与图片可见状态联动，不是影音文件播放器。
- L0闪烁，稳定后L1～L5应亮；L6缺流/溢出/音频错误灯、L7 TF加载错误灯应灭。
  L4/L5只代表完整首帧已发布/显示运行，不是逐地址BIST或全部可靠性PASS。
- TF预取较慢时会维持当前图片，按K0也可能等待后台准备；不能保证每张严格5秒或按键瞬间完成。

## 4. 原有交互不能退化
1. VIEW下短按并松开K1，OSD应显示MANUAL，L0应改为较快闪；等待不自动切。
2. 短按并松开K0，在下一图准备好后完成一次滑动；按K1回AUTO。
3. 双键同时按约1秒，全部松开，依次进入EDIT:B→EDIT:C→VIEW（每次需重新双键长按）。
4. EDIT:B/C下K0减、K1加，亮度-64..+64步长16，对比度50..150%步长25%；OSD值应正确且不误切图。
5. 回VIEW继续轮播和音频，观察无花屏、无新错误灯。

## 5. 原图通过后才选做多尺寸
素材在 `06_test_media/v087_variable_size_probes/TF_ROOT`，不是已经写进TF：
A320×240、B853×479 top-down（补齐1字节/行）、C1280×720、D1280×1024。
先备份电脑上/卡中的正式四图，断电、用读卡器更换同名四图、安全弹出并接回，再SRAM下载本bit。
观察四张都拉伸到720p、方向正确、网格无错行、底部/右侧无旧帧残片。图案是校准格，不是正式安路Logo素材替代。
完成后恢复正式四图即可；不要为了测多尺寸销毁原素材。

## 异常与回退
若无信号/只有OSD/错误灯亮：记录下载是否成功、L0～L7、屏幕提示、是否换素材、第一次出现时机。
不要热插拔TF接线，不要连续随机换版本排查。Flash未改，断电后可能回旧固化程序，这是预期。
需要回退时，恢复原640×480四图并SRAM下载本版保留的v081_picture_controls_720p.bit；
它不是本版新生成的bit，用户旧整体通过记录在v082。
当前还没有本版实物PASS记录，不先固化；等你反馈再保存独立验收节点。
''')
put('03_docs/v087_实物验收记录_待填.md', '''# v087 实物验收记录（待用户反馈）

状态：尚未下载/未确认实物；仿真和TD完成不等于本表通过。Flash未操作。

- 日期、显示器、供电：待填
- TD SRAM下载是否成功、位流SHA256：待填
- 原四张640×480图片→满屏1280×720，至少两轮：待填
- OSD/Logo/计时/标语、左右滑动、测试音与图片可见联动：待填
- K0/K1自动手动和参数调节：待填
- L0闪烁、L1～L5、L6/L7及异常：待填
- 多尺寸素材是否另测，各尺寸方向/边缘/切换：未测
- 是否执行Flash：本轮未执行；后续须另外记录

不得据用户总体功能反馈虚构每项测量、冷启动次数或PVT/全地址BIST通过。
''')
put('README_归档位置待同步.md', '''# 归档位置记录说明（历史文件名沿用）

v086 曾因D盘写入审批服务503，先冻结在可写工作区pending归档；该历史事实在INHERITED_v086文档保留。
本版v087最终实际归档位置，以本次归档工具的成功回执及全局版本索引为准；不能只凭这个文件名判定是否已同步。
若D盘写入仍未获批准，则使用当前工作区 `99_archive_pending/version_history` 的官方save/verify保留。
若D盘获批保存，则统一位置为 `D:\\FPGA_Billboard\\99_archive\\version_history\\01_versions\\v087_scaled_frame_pipeline_20261025`。
不会修改旧冻结快照来伪造归档时间、测试状态或审批结果；归档回执保存在工作区outputs之外层记录。
''')
validation = {
    'version': 'v087', 'result': 'PASS', 'checked_at': datetime.now().astimezone().isoformat(),
    'meaning': 'Evidence/source/bit consistency; NOT hardware acceptance or formal STA/PVT signoff',
    'reports': REPORTS, 'source_hash_checks': checks, 'unchanged_baseline_files': unchanged,
    'new_project_files': new_files, 'retained_native_files': retained,
    'physical_resources': resources, 'bit_sha256': sha(bit), 'fallback_bit_sha256': sha(fallback),
    'check_timing_counts_equal_legacy': counts(check), 'hardware': False, 'flash': False, 'zip': False,
}
put('04_evidence/v087_checkpoint_validation.json', json.dumps(validation, ensure_ascii=False, indent=2) + '\n')
print('PASS v087 source/evidence/bit consistency:', len(checks), 'source hashes;', len(unchanged), 'old files unchanged')
print('PHYSICAL RESOURCES', resources)
print('SRAM TEST BIT', bit)
