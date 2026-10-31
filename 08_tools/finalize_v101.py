"""Finalize the source-bound v101 candidate; D: only, no hardware/TF/Flash I/O."""
from pathlib import Path
from datetime import datetime
import argparse, hashlib, json, shutil

root = Path(__file__).resolve().parents[1]
archive_root = Path(r'D:\FPGA_Billboard\99_archive\version_history')
parent = archive_root / '01_versions/v100_transparent_spectrum_tmds_20261026/01_project'
archive = archive_root / '01_versions' / root.name
ap = argparse.ArgumentParser()
ap.add_argument('--synth-attempt', type=int, default=2)
ap.add_argument('--physical-attempt', type=int, default=2)
ap.add_argument('--bitgen-attempt', type=int, default=1)
args = ap.parse_args()

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for data in iter(lambda: f.read(1024*1024), b''):
            h.update(data)
    return h.hexdigest()

def load(p):
    return json.loads(p.read_text(encoding='utf8'))

def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def validate_source_hashes(obj):
    count = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'source_sha256':
                for rel, expected in v.items():
                    require((root/rel).is_file() and sha(root/rel) == expected,
                            'Current-source mismatch: '+rel)
                    count += 1
            elif isinstance(v, (dict, list)):
                count += validate_source_hashes(v)
    elif isinstance(obj, list):
        for value in obj:
            count += validate_source_hashes(value)
    return count

require(root.drive.upper() == 'D:', 'All outputs must remain on D:')
require(not archive.exists(), 'v101 already frozen; do not rewrite a released version')
synpath = root/f'05_td/v101_audio_visual_synth_attempt{args.synth_attempt}/attempt.json'
phypath = root/f'05_td/v101_audio_visual_physical_attempt{args.physical_attempt}/attempt.json'
bgpath = root/f'05_td/v101_audio_spectrum_bitgen_attempt{args.bitgen_attempt}/attempt.json'
syn, phy, bg = load(synpath), load(phypath), load(bgpath)
require(syn['completed'] and syn['within_capacities'], 'Synthesis incomplete')
require(phy['completed'] and phy['nonnegative_slack'] and not phy['route_errors_present'], 'Physical result failed')
require(bg['completed'] and bg['reloaded_timing_check_matches'], 'Guarded bit generation incomplete')
require(sha(synpath) == bg['synthesis_attempt_sha256'], 'Synthesis evidence changed')
require(sha(phypath) == bg['physical_attempt_sha256'], 'Physical evidence changed')
require(all(phy['slack_ns'][m] >= 0 for m in ('SWNS','STNS','HWNS','HTNS')), 'Negative slack')
require(validate_source_hashes(syn) > 0, 'Synthesis source binding missing')
reports = {}
for name, ref in bg['reviewed_reports'].items():
    p = root/ref['path']
    require(sha(p) == ref['sha256'], 'Changed reviewed report: '+name)
    data = load(p)
    require(validate_source_hashes(data) > 0, 'Regression source binding missing: '+name)
    reports[name] = data
for name, count in {'multires_chain':28,'multires_scaler':8,'multires_spi_memory':4,'dither':4}.items():
    data = reports[name]
    cases = data.get('tests',data.get('cases',[]))
    require(data.get('result') == 'PASS' and len(cases) == count and all(t['passed'] for t in cases),
            'Incomplete release suite: '+name)
require(reports['visual'].get('complete') and len(reports['visual']['tests']) == 9, 'Incomplete visual suite')

bit = root/'03_bitstreams/v101_multires_dither_720p.bit'
require(bit.is_file() and sha(bit) == bg['bit_sha256'], 'Candidate bit missing or changed')
res = syn['resources']
base = load(parent/'VERSION_STATUS.json')
gate = synpath.parent/'build/idx_video_Runs/syn_1'
require(sha(gate/'idx_video_gate.db') == bg['synth_gate_sha256'], 'Synthesis gate DB changed')
require(sha(phypath.parent/'physical/sdram_pr.db') == bg['routed_db_sha256'], 'Routed DB changed')

# Archive excludes build everywhere. Copy exact final reports and all DBs out
# of that cache, and hash every preserved file. No edits to raw evidence.
preserved = root/'04_evidence/v101_final_synthesis_preserved'
preserved.mkdir(parents=True, exist_ok=True)
records = []
for source in sorted(gate.iterdir()):
    if not source.is_file():
        continue
    target = preserved/source.name
    if target.exists():
        require(sha(target) == sha(source), 'Refusing to overwrite preserved evidence')
    else:
        shutil.copy2(source,target)
    require(sha(target) == sha(source), 'Preserved evidence mismatch')
    records.append({'source':source.relative_to(root).as_posix(),
                    'preserved':target.relative_to(root).as_posix(),
                    'bytes':target.stat().st_size,'sha256':sha(target)})
require(any(r['preserved'].endswith('idx_video_gate.db') for r in records), 'Gate DB not preserved')
require(any(r['preserved'].endswith('idx_video_gate.area') for r in records), 'Area report not preserved')
write_json(preserved/'preservation.json',records)

changes = []
for branch in ['01_project','02_tests','08_tools']:
    for path in sorted((root/branch).rglob('*')):
        if not path.is_file() or path.suffix not in {'.v','.vh','.sv','.py','.tcl','.adc','.sdc'}:
            continue
        if any(p in {'build','__pycache__'} for p in path.relative_to(root).parts):
            continue
        rel = path.relative_to(root).as_posix()
        old = parent/rel
        if not old.exists() or sha(old) != sha(path):
            changes.append({'path':rel,'change':'modified' if old.exists() else 'added',
                            'parent_sha256':sha(old) if old.exists() else None,'sha256':sha(path)})
write_json(root/'03_docs/v101_SOURCE_CHANGES.json',
           {'parent_frozen_snapshot':str(parent),'version':root.name,'changes':changes})

# Clarify historical raw records that were left IN_PROGRESS by earlier test
# runners; preserve originals rather than rewriting a failed attempt as PASS.
attempt_history = [
    {'path':'04_evidence/v101_multires_chain_20261026_101657',
     'outcome':'FAIL: Icarus expression assertion before simulations',
     'resolution':'Equivalent separate quantizer wires/generate; all current suites re-run; synthesis/physical attempt2 uses final RTL.'},
    {'path':'04_evidence/v101_multires_scaler_20261026_101952',
     'outcome':'ABORTED/FAILED: raw summary remains IN_PROGRESS; TB watchdog too tight for tall source',
     'resolution':'TB cycle budget corrected to include source input and row skipping; current 8-case suite passed.'},
    {'path':'04_evidence/v101_multires_spi_memory_20261026_102236',
     'outcome':'ABORTED/FAILED: raw summary remains IN_PROGRESS; card fixture model capacity overflow',
     'resolution':'Isolated large card model with FIXTURE_BLOCKS=128; current four cases passed; legacy model unchanged.'},
    {'path':'05_td/v101_audio_visual_synth_attempt1',
     'outcome':'SUPERSEDED: pre-Icarus-expression-workaround RTL, not the v101 final source/bit binding'},
    {'path':'05_td/v101_audio_visual_physical_attempt1',
     'outcome':'SUPERSEDED: do not use for current v101 timing claims'}
]
write_json(root/'03_docs/v101_attempt_history.json',attempt_history)

capacities = {'LUT':19600,'REG':19600,'BRAM9K':64,'DSP':29,'PLL':4}
resource = {'LUT':res['lut'],'REG':res['reg'],'BRAM9K':res['bram'],
            'BRAM32K':res['bram32k'],'DSP':res['dsp'],'PLL':res['pll'],
            'GCLK':res['gclk'],'PAD':res['pad']}
delta = {k:resource[k]-base['resource'][k] for k in ('LUT','REG','BRAM9K','DSP')}
media = root/'06_test_media/v101_multires_probes'
manifest = load(media/'manifest.json')

open_review = [
    'No v101 board programming, screen/audio acceptance, cold-start test or Flash modification.',
    'Final SWNS is only +0.001ns (1ps); numerical pass is not practical margin or reliability signoff.',
    'Valid source width and height are independently 1..2048, not unlimited arbitrary dimensions; 24-bit BI_RGB BMP only.',
    'Stretch-to-fill 1280x720; aspect-preserving letterbox/crop and anti-alias downscale prefilter are not implemented.',
    'Q0.8 align-corners bilinear plus stationary 4x4 Bayer RGB332 quantization; SDRAM still RGB332, not RGB888 storage.',
    'Ordered dither reduces broad color bands but can introduce fine static texture; loading large BMP over SPI takes longer; no fixed five-second guarantee.',
    'Full720p standalone scaler is tested, but full720p TF->physical SDRAM model->HDMI combined end-to-end simulation is not complete.',
    'PHY-7002 macro relocation, 33 abnormal input-delay entries, 2 missing input-delay groups, 7 missing output-delay groups and 3 dummy-node groups remain open.',
    'SiP voltage/speed, internal DQ timing, PVT and full-address real-device SDRAM BIST remain open.',
    'Audio remains FPGA internal 24-bit I2S demo (use_external=0); no TF WAV/MP3 music playback or external ADC capture.',
    'Spectrum is 16 selected-frequency rectangular-window DFT, not a full-band calibrated FFT analyzer.'
]
status = {
    'version':'v101','directory':root.name,'parent':'v100',
    'parent_frozen_snapshot':str(parent),'generated_at':datetime.now().astimezone().isoformat(),
    'target':'VF-E20NG88 / EG4S20NG88 / 24MHz / HDMI 1280x720',
    'status':'Source-bound regressions PASS; synthesis PASS; routed STA numerical PASS with 1ps setup margin; guarded SRAM candidate generated; NO new hardware/Flash/formal signoff',
    'storage':str(root),'archive':str(archive),
    'source_dimensions':{'width_min':1,'width_max':2048,'height_min':1,'height_max':2048},
    'input_format':'24-bit uncompressed BI_RGB BMP; positive/negative height; 4-byte padded rows',
    'output_resolution':[1280,720],
    'scaler':'align-corners Q0.8 four-corner bilinear; stretch-to-fill; no anti-alias prefilter',
    'framebuffer':'RGB332; stationary 4x4 Bayer ordered quantization enabled in top, optional in reusable packer/loader',
    'resource':resource,'resource_capacity':capacities,'resource_delta_vs_v100':delta,
    'timing_ns':phy['slack_ns'],'setup_margin_ps':1,'check_timing_counts':bg['check_timing_counts'],
    'reviewed_regressions':bg['reviewed_reports'],
    'synthesis':synpath.relative_to(root).as_posix(),
    'final_physical':phypath.relative_to(root).as_posix(),
    'bitgen':bgpath.relative_to(root).as_posix(),
    'preserved_synthesis_manifest':(preserved/'preservation.json').relative_to(root).as_posix(),
    'bitstream':bit.relative_to(root).as_posix(),'bitstream_sha256':sha(bit),
    'bitstream_bytes':bit.stat().st_size,'bit_generated':True,
    'hardware_tested':False,'flash_changed':False,'tf_modified':False,
    'formal_release_approved':False,'handoff_zip_generated':False,
    'optional_test_media':media.relative_to(root).as_posix(),
    'optional_test_media_manifest_sha256':sha(media/'manifest.json'),
    'audio_source':'FPGA internal 24-bit I2S demo; use_external=0',
    'last_user_hardware_feedback':'v089, recorded in v090; later versions do not inherit hardware acceptance',
    'open':open_review,
    'storage_note':'All newly created outputs/temp/builds on D:. Old inherited evidence may contain historical C: paths; no C: work trees changed.'
}
write_json(root/'VERSION_STATUS.json',status)

rows = ['| 资源 | 使用 / 容量 | 占比 | 比 v100 |','|---|---:|---:|---:|']
for k in ('LUT','REG','BRAM9K','DSP','PLL'):
    dd = delta.get(k,resource[k]-base['resource'][k])
    rows.append(f'| {k} | {resource[k]:,} / {capacities[k]:,} | {100*resource[k]/capacities[k]:.2f}% | {dd:+d} |')
table = '\n'.join(rows)
evidence_rows = ['| 验证 | 当前结果及范围 |','|---|---|']
for name,desc in [
 ('multires_chain','28/28：信息头、范围拒绝、正反行序、偏移511、补齐、错误帧不提交、重试'),
 ('multires_scaler','8/8：包含320×240→720p、2048×2048→720p；两例各逐像素比较921,600个输出；另有单行/单列/竖图/奇数尺寸'),
 ('multires_spi_memory','4/4：真实SPI比特流+FAT32+物理SDRAM行为模型；大源宽/高、SDSC、重试、CRC；输出32×18，非完整720p系统'),
 ('dither','4/4：开关×正反行序，每例4096像素；256值×16相位×两个量化器精确比较、背压、最后ack等待及复位'),
 ('visual','9组：PCM活动/能量/Logo/DFT/透明频谱/OSD/顶层/PCM/TMDS'),
 ('native_hdmi','原生HDMI包与厂商ODDR三相位检查'),
 ('actual_spi','原SPI/FAT32读取回归'),
 ('scaled_spi_memory','原缩放SPI+物理SDRAM模型链回归'),
 ('legacy_units','原控制/读写基础单测'),
 ('paired_units','原双图读取/切换单测'),
 ('paired_memory','原双图内存回归含720p扫描；合成写入源，不等价于TF端到端')]:
    ref=bg['reviewed_reports'][name]
    evidence_rows.append(f'| {name} | PASS：{desc}；`{ref["path"]}` |')

report = f'''# v101 多分辨率BMP与量化画质优化记录

日期：2026-10-26。目标：VF-E20NG88 / EG4S20NG88 / 24MHz。父版本：v100冻结快照。

## 1. 本次实际改动

- 整机入口把图片宽、高上限各扩大到2048。最小各1像素，不把“任意分辨率”解释成无限尺寸。
- 读取BMP原始宽高，支持24-bit BI_RGB非压缩、正高度倒序/负高度正序、4字节行补齐。尺寸和格式不合法时拒绝，不提交损坏后台帧。
- 保留现有逐流双行缓存、Q0.8坐标权重的四邻域双线性插值，统一输出1280×720。没有在电脑预缩放代替FPGA算法。
- 新增**静态4×4 Bayer有序抖动量化**：双线性计算仍为RGB888，写入原RGB332缓存前按逻辑输出坐标量化，改善渐变大色块；不会逐帧改变相位制造闪烁。
- 无额外DSP/BRAM：量化器用移位加法实现；复用模块默认关抖动以保持旧调用行为，整机入口显式开启。
- 保留四图轮播/手动切换、双后台帧、OSD/Logo开关、亮度对比度、HDMI演示音和透明频谱。此处“保留”指源码/回归，不是本版实物验收。
- 工程修改：`01_project/boards/idx_audio_visual_top.v`、`rtl/tf/tf_scaled_loader.v`、`rtl/tf/bmp_pixel_packer.v`及两份TD构建脚本。逐文件SHA见本目录v101_SOURCE_CHANGES.json。

## 2. 缩放与画质边界

输出：1280×720拉伸铺满，**不是等比留黑边**，竖图会拉宽。范围：宽和高各1～2048。
原始素材可以不同尺寸；OSD、Logo、频谱在缩放后按720p输出坐标叠加，不受源图宽高影响。
强缩小暂未加抗混叠预滤波；细棋盘/文字仍可能有混叠。有序抖动减轻色带但会出现细点纹理，并非凭空增加真实色深。
缓存仍为RGB332；支持24-bit BMP读取和RGB888运算/HDMI接口，不等于24-bit全帧缓存。
SPI需读取完整源图，大图装载可能明显慢于640×480，本版不承诺5秒完成切换。

量化：Bayer阈值=rank×16+8；R/G=floor((v×7+阈值)/255)，B=floor((v×3+阈值)/255)。
黑白端点不被破坏；抖动的坐标相位对BMP正反序和停顿保持一致。

## 3. 新鲜验证（不是继承旧PASS）

{chr(10).join(evidence_rows)}

独立全720p缩放验证不是TF→SDRAM→HDMI全链720p仿真。原双图720p内存模型回归用合成写入源，不冒充真实TF链。
小输出真实SPI+SDRAM模型测试和完整720p核心测试是不同覆盖层次。

### 早期失败记录

首次Icarus遇表达式断言，已改为等价独立量化线网/generate，重新跑最终综合/布局布线和全部测试。
早期大尺寸TB看门狗和卡模型容量不足分别修正；原始失败/IN_PROGRESS文件保留，不改写为PASS。
attempt1综合/物理结果属于旧表达式源码，不用于最终位流；详见v101_attempt_history.json。

## 4. 整机资源（TD最终综合attempt{args.synth_attempt}）

{table}

另有GCLK {res['gclk']}，PAD {res['pad']}。不超器件容量，但LUT已超过七成，不表示资源可以无限扩展。
资源原报告：`{preserved/'idx_video_gate.area'}`，搜索Utilization Statistics。
{len(records)}个最终综合报告/数据库逐字节复制到非build目录，SHA记录于preservation.json；避免归档排除build后遗失证据。

## 5. 数值时序与风险

最终：SWNS **+{phy['slack_ns']['SWNS']:.3f}ns**，STNS {phy['slack_ns']['STNS']:.3f}ns，HWNS **+{phy['slack_ns']['HWNS']:.3f}ns**，HTNS {phy['slack_ns']['HTNS']:.3f}ns；覆盖率99.79%。
**最差setup余量仅1ps，数值过线但裕量非常紧；只提供临时SRAM试验候选，不是正式可靠性签核。**
最差setup在picture_adjust输出至OSD overlay，后续若上板反馈或继续扩展，应优先做显示链路时序优化，而非增加无约束例外。
权威最终hold-fix后报告：`05_td/v101_audio_visual_physical_attempt{args.physical_attempt}/physical/sdram_pr.timing`、`sdram_phy.ts`、`sdram_check.rpt`。
同目录final_timing.rpt是hold-fix前记录，不能代替最终报告。
check_timing：时钟/定义/无路径/无效约束等核心检查为0；仍有dummy node 3组、无input delay 2组、无output delay 7组、异常input delay 33组，不予豁免。
PHY-7002宏初始重定位、内部DQ、SiP电压/速度级、PVT、完整地址实物BIST仍开放。

## 6. 位流与素材

临时SRAM位流：`{bit}`
SHA256：`{sha(bit)}`；大小：{bit.stat().st_size}字节。
门控生成脚本核对所有必需测试/源码哈希/综合与布线数据库/四项slack后才发布；没有自动下载或修改Flash。

现有四张官方图优先保持不变。完整官方四图原备份：`{root/'06_test_media/four_image_playlist/TF_ROOT'}`。
可选不同尺寸测试图：`{media/'TF_ROOT'}`，含320×240、853×479、720×1280、1920×1080；54字节BMP头、24-bit BI_RGB、正反序及奇数行补齐。
素材由电脑生成测试图，不预缩放，不等于FPGA输出证据；四角颜色和白边用于定位方向/边界，源图缩略预览只作识别。
不自动访问TF，换图前先备份全部A/B/C/D，改线/拔卡前断电，勿格式化。

## 7. 完成度与开放项

本版仿真、综合、布局布线数值STA、位流生成完成；本版上板、实屏/试听、冷启动、Flash均未执行。
最近明确用户实物反馈为v089（在v090登记）；不把后来的仿真版冒称已实测回退版。
音频仍内部24-bit I2S演示源，use_external=0；TF WAV/MP3、外接ADC采音尚未实现。
全部新增文件/临时目录在D盘；旧版本完整保留；无需交接ZIP。
'''
(root/'03_docs/v101_实现与资源时序记录.md').write_text(report,encoding='utf8')

steps = f'''# v101 上板测试步骤（临时SRAM，不固化）

## 第一轮：不要动TF卡，先查原功能

1. 保持原供电、TF、HDMI屏幕、下载器连接。若需重新接线或拔卡，先断电；保持外接屏幕独立稳定供电。
2. TD Programmer选择EG4S20NG88，沿用此前成功的SRAM临时下载方式，文件：
   `{bit}`
   **不要选择Flash擦除、写入或固化。**
3. 等完整加载，观察至少两轮四图；原图像、方向、四角、OSD/Logo、声音、频谱应保持；不应黑屏/无信号/长期花屏。
4. K0切图/重试，K1切手动/自动；K0+K1短按并释放隐藏/恢复OSD/Logo/频谱；长按保留原参数调节，不混用。
5. 看渐变是否比硬截位色块更细；可以有稳定细点纹理，但不能有随机彩点、周期闪烁或边缘像素漂移。
6. 本次setup数值裕量只有1ps，出现不稳定先记录，不写Flash；保留现有已验收启动版本。

## 第二轮（第一轮正常再做）：四张不同原尺寸

1. 先备份TF根目录**全部A.BMP、B.BMP、C.BMP、D.BMP**到电脑，并核实四个文件均在。不要仅备份前三张。
2. 板卡断电后取卡，读卡器连接电脑，不需要格式化，不改分区。将：
   `{media/'TF_ROOT'}`
   内四张BMP复制到TF根目录替换同名文件，安全弹出，再插回断电板卡。
3. 通电后重新临时SRAM下载同一v101位流。等待大图完整装载；本版不保证原5秒切换目标。可用K1切手动，K0逐张观察。
4. A：320×240底向上；B：853×479顶向下/行补齐；C：720×1280竖图；D：1920×1080顶向下。它们应都输出为1280×720铺满。**竖图拉宽属于本版设计，不是错误。**
5. 四角应依次是左上红/右上绿/左下蓝/右下黄，四周白边完整；小字和细棋盘可能因强缩小混叠，OSD/Logo/频谱仍位于720p固定位置。
6. 观察切换无长期残影/无信号，音频和按键无回归；记录哪张、方向/边界、加载约多久、是否闪烁。不要把装载慢误报为不支持分辨率。
7. 测后先断电，恢复原四张备份再回滚旧位流；旧版不保证兼容新增大尺寸。完整旧官方四图另备于：
   `{root/'06_test_media/four_image_playlist/TF_ROOT'}`

## 请反馈

- 原四图及声音/OSD/频谱/按键是否仍正常？
- 不同尺寸A/B/C/D是否都能显示、方向/四角是否正确？
- 渐变细点是否可接受，有无随机闪烁/失锁？
- D图加载大概多久？

详细记录：`{root/'03_docs/v101_实现与资源时序记录.md'}`。
本版未实物验收，先只临时下载；不改Flash；无需交接包。
'''
(root/'03_docs/v101_上板测试步骤.md').write_text(steps,encoding='utf8')

(root/'README_先看这里.md').write_text(f'''# v101 多分辨率BMP读取、720p双线性缩放与色阶优化候选

- 板卡：VF-E20NG88 / EG4S20NG88 / 24MHz；HDMI 1280×720。
- 输入宽、高各1～2048；24-bit BI_RGB非压缩BMP，正反行序/行补齐；双线性拉伸铺满。
- 静态4×4有序抖动改善原RGB332缓存色阶，无额外DSP/BRAM；不是24-bit全帧缓存，无强缩小抗混叠预滤波/等比留边。
- 新28例事务、8例核心（含两例完整720p逐像素）、4例SPI+内存模型、4例量化打包及全部原功能回归通过；覆盖层次独立，不冒称720p全链端到端完成。
- 资源：LUT {res['lut']}/19600，REG {res['reg']}/19600，BRAM9K {res['bram']}/64，DSP {res['dsp']}/29，PLL {res['pll']}/4；相对v100 +207LUT/+21REG，BRAM/DSP不增加。
- TD最终数值：SWNS+0.001ns、STNS0、HWNS+0.030ns、HTNS0。**setup仅1ps余量；仅SRAM候选，非正式可靠性签核。**
- 位流：`{bit}`
- SHA256：`{sha(bit)}`。
- 上板步骤：`{root/'03_docs/v101_上板测试步骤.md'}`。
- 完整记录：`{root/'03_docs/v101_实现与资源时序记录.md'}`。
- 先不换TF内容，验证原四图；然后可选测试素材：`{media/'TF_ROOT'}`。换图必须备份A/B/C/D且断电，不格式化。
- 本版没有上板/试听/冷启动验收，未写Flash/未自动改TF；TF音乐播放尚未实现。
- 工作副本：`{root}`；冻结快照：`{archive}`（以save+verify及索引为准）。
- 全部新增输出在D盘，旧版保留；无需交接ZIP。
''',encoding='utf8')
(root/'README_归档位置待同步.md').write_text(f'''# v101 路径说明

工作副本：`{root}`。
冻结快照：`{archive}`。

以归档索引及verify结果为准。不在快照内编辑/编译，工作副本可测试。
历史继承证据里的C盘路径不是本版新写入位置。本版新增输出均在D盘。
''',encoding='utf8')
print(json.dumps({'version':'v101','bit':str(bit),'sha256':sha(bit),
                  'resources':resource,'delta_vs_v100':delta,
                  'slack_ns':phy['slack_ns'],'preserved_files':len(records),
                  'source_changes':len(changes),'hardware_tested':False,
                  'handoff_zip_generated':False},ensure_ascii=False,indent=2))
