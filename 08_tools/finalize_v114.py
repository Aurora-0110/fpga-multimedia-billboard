"""Finalize the source-bound v114 diagnostic SRAM candidate; never touch hardware."""
from pathlib import Path
import argparse, datetime, hashlib, json, re, shutil

root = Path(__file__).resolve().parents[1]
if '01_versions' in root.parts:
    raise SystemExit('Frozen archives are read-only; copy to a work directory first')
ap = argparse.ArgumentParser()
ap.add_argument('--synth-attempt', type=int, default=2)
ap.add_argument('--physical-attempt', type=int, default=1)
ap.add_argument('--bitgen-attempt', type=int, default=1)
a = ap.parse_args()
version = 'v114_audio_triple_review_20261027'
archive_root = Path(r'D:\FPGA_Billboard\99_archive\version_history')
archive = archive_root / '01_versions' / version
baseline_root = archive_root / '01_versions/v113_audio_file_audit_20261027/01_project'
v112_root = archive_root / '01_versions/v112_audio_pingpong_20261027/01_project'
assert not archive.exists(), 'Never overwrite a frozen archive'


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def exact(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        assert sha(src) == sha(dst), str(dst)
    else:
        shutil.copy2(src, dst)
    assert sha(src) == sha(dst)


syp = root / f'05_td/v114_audio_visual_synth_attempt{a.synth_attempt}/attempt.json'
php = root / f'05_td/v114_audio_visual_physical_attempt{a.physical_attempt}/attempt.json'
bgp = root / f'05_td/v114_audio_triple_bitgen_attempt{a.bitgen_attempt}/attempt.json'
sy, ph, bg = map(load, (syp, php, bgp))
assert all(x.get('completed') for x in (sy, ph, bg))
assert len(ph['slack_ns']) == 4 and min(ph['slack_ns'].values()) >= 0
assert bg['reloaded_slack_matches'] and bg['reloaded_timing_check_matches']
assert ph['slack_ns'] == bg['slack_ns'] == bg['reloaded_slack_ns']
assert sha(syp) == bg['synthesis_attempt_sha256']
assert sha(php) == bg['physical_attempt_sha256']
bit = root / '03_bitstreams/v114_audio_triple_720p.bit'
assert bit.stat().st_size == bg['bit_bytes'] and sha(bit) == bg['bit_sha256']
for rel, h in sy['source_sha256'].items():
    assert sha(root / rel) == h, rel
for item in bg['reviewed_reports'].values():
    assert sha(root / item['path']) == item['sha256'], item['path']

# The archiver omits directories named build. Preserve raw earlier and selected
# synthesis outputs elsewhere, without altering or deleting either original.
preserved = []
for attempt in (1, a.synth_attempt):
    src = root / f'05_td/v114_audio_visual_synth_attempt{attempt}/build'
    label = 'v114_final_synthesis_preserved' if attempt == a.synth_attempt else f'v114_earlier_synthesis_attempt{attempt}_preserved'
    dst = root / '04_evidence' / label
    assert src.is_dir(), str(src)
    files = []
    for f in sorted(src.rglob('*')):
        if f.is_file():
            rel = f.relative_to(src)
            q = dst / rel
            exact(f, q)
            files.append(dict(path=rel.as_posix(), sha256=sha(q), bytes=q.stat().st_size))
    record = dict(selected=attempt == a.synth_attempt, original=src.relative_to(root).as_posix(), preserved=dst.relative_to(root).as_posix(), files=files)
    write(dst / 'preservation.json', record)
    preserved.append(record)

gate = syp.parent / 'build/idx_video_Runs/syn_1'
assert sha(gate / 'idx_video_gate.db') == ph['synth_gate_sha256'] == bg['synth_gate_sha256']
assert sha(php.parent / 'physical/sdram_pr.db') == bg['routed_db_sha256']
# Preserve TD project files at the same depth so their relative paths still work.
prj = syp.parent / 'td_project/idx_video.al'
runprj = prj.parent / 'idx_video_Runs/syn_1/idx_video.prj'
exact(syp.parent / 'build/idx_video.al', prj)
exact(gate / 'idx_video.prj', runprj)
refs = []
for f in (prj, runprj):
    for name in re.findall(r'<File Path="([^"]+)"', f.read_text(encoding='utf8')):
        q = (f.parent / name).resolve()
        assert q.is_file() and q.is_relative_to(root), str(q)
        refs.append(dict(project=f.relative_to(root).as_posix(), source=q.relative_to(root).as_posix(), sha256=sha(q)))
write(root / '04_evidence/v114_td_project_relative_paths.json', dict(passed=True, references=refs))

area = (php.parent / 'physical/sdram_phy.area').read_text(encoding='utf8')
routed = {k: int(re.search(r'^#' + k + r'\s+(\d+)', area, re.M).group(1)) for k in ('lut', 'reg', 'bram', 'bram32k', 'dsp', 'pll', 'gclk', 'pad')}
baseline = load(v112_root / 'VERSION_STATUS.json')
exact(baseline_root / 'VERSION_STATUS.json', root / 'BASELINE_v113_VERSION_STATUS.json')
changes = []
for f in sorted((root / '01_project').rglob('*')):
    if f.is_file():
        rel = f.relative_to(root)
        old = baseline_root / rel
        if not old.is_file() or sha(f) != sha(old):
            changes.append(dict(path=rel.as_posix(), sha256=sha(f), previous_sha256=sha(old) if old.is_file() else None))
constraints = {}
for f in sorted((root / '01_project/boards').glob('*')):
    if f.suffix.lower() in {'.adc', '.sdc'}:
        rel = f.relative_to(root)
        assert sha(f) == sha(baseline_root / rel), str(rel)
        constraints[rel.as_posix()] = sha(f)
write(root / '03_docs/v114_SOURCE_CHANGES.json', dict(baseline=str(baseline_root), changes=changes, constraints_unchanged=constraints, raw_synthesis_preservation=preserved))
write(root / '04_evidence/v114_origin.json', dict(version=version, source_frozen=str(baseline_root), work_source=str(root), source_status_sha256=sha(baseline_root / 'VERSION_STATUS.json'), source_production_same_as_v112=True, no_hardware_action=True, no_handoff_zip=True))

boundary = root / bg['reviewed_reports']['sample_edge_negative_control']['path']
boundary_log = boundary.parent / 'run.log'
btext = boundary_log.read_text(encoding='utf8')
assert 'PASS' in btext and 'FATAL' not in btext
review = dict(
    version=version,
    a3_meaning='Sticky PCM underrun; not a file-corruption verdict',
    v109_v110_review='Changes include independent UI, pause/urgent, WAV decode and other resource optimizations; temporal association alone is not a UI-only causal proof',
    controlled_boundary=dict(cases=148, old_v112_a3=2, current_v114_a3=0, clocks_mhz=[49.5, 74.25], sample_hz=48000, fifo_words=32, prefill=1, file_frames=[1, 2, 3, 17], scope='Controlled PCM producer and actual CDC/FIFO/playback. Not a reproduction of the actual long-track card failure.', log=boundary_log.relative_to(root).as_posix(), log_sha256=sha(boundary_log)),
    buffers=dict(sector_banks=3, sector_bytes=512, pcm_frames=4096, pcm_bits=48, staging_slots=3, image_frames=2, extra_sector_vs_v112_ms_at_24bit_stereo_48k=512 / 6 / 48000 * 1000),
    resource_delta_vs_v112={k: routed[k] - baseline['resources_routed'][k] for k in ('lut', 'reg', 'bram', 'dsp', 'pll')},
    no_bandwidth_guarantee_from_finite_buffers=True,
    short_pin_matrix='512-frame FIFO, 5 combinations, behavioral card',
    production_pin_tests='4096-frame FIFO; nominal49.5/74.25MHz,48k,DATA_HALF_DIV4; pause/switch and6001-frame sustained BMP concurrent playback',
    logical_stall_tests='5x sample accelerated virtual sectors;55/108.33ms logical gaps, not real-card guaranteed tolerance',
    no_actual_card_read_this_run=True,
    raw_synthesis_attempt1='Earlier complete build before diagnostic Q/= font update, NOT selected; preserved',
    selected_synthesis=a.synth_attempt, selected_physical=a.physical_attempt, selected_bitgen=a.bitgen_attempt,
    reported_pixel_clock_mhz=74.256, testbench_nominal_pixel_clock_mhz=74.25,
    hardware_acceptance=False)
write(root / '04_evidence/v114_review_decisions.json', review)

open_items = [
    'Actual long-track TF-card A3 root cause not proven fixed; no new hardware playback or card audit',
    'No board programming, audible playback, Flash or cold-start acceptance in this run',
    'RGB332 SDRAM image cache;1280x720 HDMI output, not full24-bit image cache',
    'SDRAM macro relocation /33 abnormal internal input annotations /dummy and external delay review /SiP/PVT/full-address real-device BIST remain open',
    'Routed hold margin +0.023ns is small; nonnegative STA is not PVT/reliability signoff',
    '58/64 BRAM9K used;6 remain. Triple sector prefetch is not triple image buffering',
    'Finite buffering does not cure inadequate sustained average SPI throughput or arbitrary card stalls',
    'WAV48k16/24 mono/stereo only; no on-board FLAC/MP3 decoder, ASR or gapless looping',
    'EOF drains then silence; source away/back restarts. Real WAV mode has no automatic transcript/lyrics claim']
status = dict(
    version=version, date='2026-10-27', generated_at=datetime.datetime.now().astimezone().isoformat(),
    target='VF-E20NG88 / EG4S20NG88 /24MHz / HDMI1280x720',
    purpose='Three CRC-committed512-byte audio banks +4096-frame stereo FIFO +three-slot sample prefetch, pause-safe refill and first-A3 diagnostics; preserve independent UI and image double buffering',
    source_version='v113_audio_file_audit_20261027', work_source=str(root),
    simulation_passed=True, synthesis_completed=True, physical_numerical_check_passed=True, new_bit_generated=True,
    hardware_download=False, hardware_acceptance=False, formal_release_approved=False, flash_modified=False, tf_files_modified=False, actual_tf_card_audited=False, handoff_zip_generated=False,
    actual_long_track_a3_root_cause_closed=False,
    resources_synthesis=sy['resources'], resources_routed=routed,
    baseline_resources_routed=baseline['resources_routed'], resource_delta_vs_v112=review['resource_delta_vs_v112'],
    slack_ns=ph['slack_ns'], baseline_slack_ns=baseline['slack_ns'],
    buffering=dict(image_frames='existing SDRAM front/back unchanged', audio_sector_banks=3, audio_bank_bytes=512, pcm_frames=4096, pcm_width_bits=48, prefill_frames=3072, low_water_frames=3584, pixel_sample_slots=3, sample_hz=48000, ui_stages=5, diagnostic_rgb_stages=3),
    bitstream=str(bit), bitstream_relative=bit.relative_to(root).as_posix(), bit_bytes=bit.stat().st_size, bit_sha256=sha(bit),
    archive_path=str(archive), archive_bitstream=str(archive / '01_project/03_bitstreams' / bit.name), known_open_items=open_items,
    reviewed_reports=bg['reviewed_reports'], check_timing_counts=bg['check_timing_counts'], production_changes=changes, constraints_unchanged=constraints,
    selected_synthesis=syp.relative_to(root).as_posix(), selected_physical=php.relative_to(root).as_posix(), selected_bitgen=bgp.relative_to(root).as_posix())
write(root / 'VERSION_STATUS.json', status)
(root / 'README_归档位置.md').write_text('# v114归档位置\n\n' + str(archive) + '\n\n只在D盘工作副本继续开发；所有旧版本冻结保留。无需交接ZIP。\n', encoding='utf8')

analysis_doc = f"""# v114：独立UI后A3的排查与三缓存测试版

## 先说结论

A3是PCM播放缓存欠载锁存，不能直接解释成音频文件损坏。v113电脑端两份WAV审计通过，但卡上内容没有读取，因此实卡文件、响应间隙和共享SPI带宽仍需取证。
本版已经完成新仿真、综合、布局布线和位流生成；**尚未下载、听音、写Flash或验证冷启动；用户长曲A3根因还没有闭环**。

## 为什么加了UI才暴露

逐文件对比v109/v110发现，不仅加了独立UI，还同步改变了暂停/低水位urgent、WAV解码及多项资源复用。不能把时间先后当成UI唯一根因。差异保留于本工程04_evidence/v114_diff。

本轮实际FIFO/CDC/播放逻辑配受控PCM供数器，在49.5/74.25MHz、48k样本节拍下扫描148组相位/短文件边界：旧v112有2组假欠载，新版0组。条件是32词小FIFO、预填1帧及1/2/3/17帧文件；**这说明旧版存在边界缺陷，不证明用户长音乐的A3一定来自这里**。

旧逻辑可能在FIFO数据恰好返回的样本节拍仍读取旧have值。新版等待真实首样本，再由三槽预取和同拍旁路转发消费，逐样本检查不丢样、不重复。暂停只停止消费，不撤掉低水位补数请求。UI显隐、音频控制退出/进入、暂停/换源组合仿真未发现按键串操作或误复位。

## 三缓存具体是什么

| 层次 | v112 | v114 | 用途 |
|---|---|---|---|
| TF已校验扇区 | 2×512B | 3×512B | 三银行回绕、CRC成功才提交、满不覆盖 |
| PCM异步主FIFO | 4096×48bit | 4096×48bit | 预填3072、低水位3584，跨时钟音频排队 |
| 像素域样本预取 | 单槽/旧have控制 | 三槽与同步读旁路 | 覆盖读返回/消费边界，暂停不丢样 |
| 图片SDRAM | 双帧 | 保持双帧 | 前台显示与后台加载分离 |

不是把整机或图片改成三帧缓存。三扇区比双扇区仅多512B，在24bit双声道48k下约1.78ms；4096帧主FIFO理论约85.33ms（不等于可承诺的卡停顿容忍）。有限缓存不能弥补持续平均吞吐不足。

## 验证证据

- 三银行预取36例，WAV播放8例，WAV解析20例，FAT挂载22例。
- 停顿/背压/暂停/换源5例、欠载后恢复1例、首错快照锁存1例、UI与真实播放链组合1组。
- 148组取样边界对照：旧2次A3、新0次。
- SPI引脚数字模型5组合（测试FIFO512帧）；生产4096帧FIFO下暂停换源，以及6001帧连续播放与BMP读取并发通过。6001大于FIFO容量，强制覆盖启播后补数和回绕。行为卡、32×18 BMP，并非实卡或完整720p内存电气验收。
- 诊断第三行61270像素独立核对，中文UI707状态与5幅720p，顶层/频谱/HDMI/字幕回归；路由后12块ROM初始化核对。
- 旧BMP/缩放/抖动/预处理TMDS证据仅在源码SHA完全匹配时继承，详细选择见VERSION_STATUS.json，不冒称本轮重跑。
- 55ms/108.33ms为5倍采样加速虚拟供数的逻辑停顿，不是实卡响应保证。

## TD最终结果

最终LUT {routed['lut']}/19600（{routed['lut']/19600:.2%}），REG {routed['reg']}/19600，BRAM9K {routed['bram']}/64，DSP {routed['dsp']}/29，PLL {routed['pll']}/4。
比v112增加{review['resource_delta_vs_v112']['lut']} LUT、{review['resource_delta_vs_v112']['bram']} BRAM，不声称资源更少。
SWNS {ph['slack_ns']['SWNS']:+.3f}ns、STNS0、HWNS {ph['slack_ns']['HWNS']:+.3f}ns、HTNS0。保持裕量小；约束未修改、未降频、未加假路径。TD报告像素时钟74.256MHz，TB名义74.25MHz，不是PVT证明。
SDRAM宏重定位、33异常内部输入延时、外部接口延时、SiP/PVT、完整地址实物BIST与RGB332缓存边界继续开放。

## 新音频诊断行（十六进制）

AUD Q=xxxx MIN=xxxx A3Q=xxxx S=xx B=3

Q为当前PCM主FIFO帧数（不含三槽），MIN为非暂停播放采样点最低帧数；MIN=1FFF可能表示尚无有效采样。A3Q和S锁存首次欠载时的水位与状态。
S的bit7..0依次是header、eof、empty、pending读返回、三槽非空、paused、playing、command_pending。S=A2即头有效、EOF未到、FIFO空、无返回/暂存且正在播放；配合A3Q=0更倾向真实供数间隙，但仍需实卡确认。
上两行原Q/MIN是视频水位，新AUD才是音频。换音源会清本源A3/最低水位/首错；全局HIST历史错误仍保留到全局复位，不能把旧HIST当成新欠载。

## 推荐位流与边界

{bit}

{bit.stat().st_size}字节；SHA256 {sha(bit)}。
只做SRAM临时下载。测试时确认UI显示V114；不要使用文件夹里的旧v112位流。按本版测试步骤记录，先不写Flash。
无需改TF、无需换驱动、无需反复解压、无需交接包。
"""
(root / '03_docs/v114_原因分析与测试方法.md').write_text(analysis_doc, encoding='utf8')
test_doc = f"""# v114上板步骤：只测SRAM，不写Flash

本次没有替你下载板卡或改卡，以下是待完成的实物验证。保留现有MUSIC.WAV/ADVOICE.WAV与四张BMP，不重格式化、不重新拷卡，不在通电时改接线。

1. 打开TD下载工具，选SRAM临时下载，使用：
   {bit}
   不选择SPI Flash擦除/写入。下载完成后等待画面稳定，长按K1约1秒显示UI，确认V114。
2. 先在浏览状态短K1选择手动图片，避免先混入自动读图压力；长K0进入音频控制，短K1选音乐文件。连续听约3分钟，期间长K1打开/隐藏UI至少5次；音频不应被UI操作重启/换源。
3. 音乐播放时短K0暂停3秒，再短K0继续，应该保持播放位置；暂停期间也长K1显隐UI，再继续。
4. 长K0退出音频控制，应继续同一音源；再长K0进入。短K1选广告，再切回音乐，换源应从头且无旧音残留。广告到尾静音是正常结束，切走再回来可重播。
5. 保持音乐，退出音频控制。短K0手动换几张，再短K1切自动轮播，至少观察60秒（未到文件末尾时），重复UI显隐。
6. **若出现A3，先不要切音源或重新下载**：保留首错，拍下包含V114、音频A3及整条AUD第三行的画面。说明首次报错发生在选音乐、UI显隐、暂停继续、换图还是切广告时，声音是否中断/恢复。若装饰UI隐藏，故障诊断条仍应显示。

AUD第三行：Q当前音频FIFO水位，MIN播放最低水位，A3Q首次欠载水位，S首次状态，B=3扇区银行数；全部数字为十六进制。上方原Q/MIN是视频，不要混淆。
换音源清当前播放模块A3，但HIST全局历史不会随源清除。如果新源播放正常但HIST仍A3，拍照说明，不要仅凭HIST认定再次欠载。

请反馈：V114；手动静态图音乐3分钟；UI5次；暂停/继续；退出/进入；音乐/广告切换；自动轮播压力；AUD完整照片（如报错）。
本轮未做真实TF读取/哈希比对；若仍A3，将依据首错水位决定查实卡SPI服务间隙、FAT/仲裁还是采样状态，不隐藏A3或盲目覆盖卡文件。
"""
(root / '03_docs/v114_按键与SRAM测试步骤.md').write_text(test_doc, encoding='utf8')
readme = f"""# v114：三扇区音频预取、三槽PCM读前取与首错取证

**已完成本地回归、TD布局布线和新位流；只作为SRAM测试候选，尚未上板、听音、Flash或冷启动验收。真实长曲A3根因未确认。**

- 修复可复现的取样边界：148例旧v112有2次A3，新v114为0；条件为受控短PCM，不冒称实物长曲根因。
- TF音频升级三512B银行；主PCM FIFO维持4096帧，增加三槽读前取和同拍旁路；暂停也保持低水位补数。
- UI/按键保留，新增AUD水位、最低水位与首错状态；图像仍是SDRAM双帧，不是三帧图片缓存。
- 新SPI行为卡持续6001帧、并发BMP读取，UI/暂停/换源与诊断像素回归通过。实物需独立测试。

## 现在只用这个位流

{bit}

{bit.stat().st_size}字节；SHA256：{sha(bit)}

归档同一位流：
{archive / '01_project/03_bitstreams' / bit.name}

无需重拷TF、改驱动或重新解压；只下载SRAM，先不写Flash。步骤见：
{root / '03_docs/v114_按键与SRAM测试步骤.md'}

## 资源与时序

LUT {routed['lut']}/19600（{routed['lut']/19600:.2%}）、REG {routed['reg']}/19600、BRAM9K {routed['bram']}/64、DSP {routed['dsp']}/29、PLL {routed['pll']}/4。
比v112多297 LUT和1 BRAM；SWNS {ph['slack_ns']['SWNS']:+.3f}ns、HWNS {ph['slack_ns']['HWNS']:+.3f}ns，STNS/HTNS=0。保持裕量很小，不是可靠性/PVT签核。ADC/SDC未改，未降频或新增假路径。

详细原因、仿真范围与未完成项：{root / '03_docs/v114_原因分析与测试方法.md'}
相对路径TD工程：{prj}
完整性只读检查：{root / '08_tools/verify_v114.py'}

原始综合/路由DB、两次综合、全部源码/TB/约束/脚本/日志与旧版本保存；选取综合2、物理1、bitgen1。旧BMP/缩放/TMDS/抖动只继承SHA匹配证据，详见VERSION_STATUS.json。
RGB332、SDRAM宏/内部延时/SiP/PVT/全地址实物BIST继续开放。A3仍可能来自实际卡供数或其他链路，不能用更多缓存掩盖。
全部新增文件位于D盘，所有旧版本保留；无需交接ZIP。
"""
(root / 'README_先看这里.md').write_text(readme, encoding='utf8')

files = {}
for f in sorted(root.rglob('*')):
    if not f.is_file():
        continue
    rel = f.relative_to(root)
    if any(p in {'00_tmp', 'build', '__pycache__', '.git'} for p in rel.parts) or f.suffix.lower() in {'.vvp', '.vcd', '.pyc'}:
        continue
    if rel.as_posix() == '04_evidence/v114_release_manifest.json':
        continue
    files[rel.as_posix()] = sha(f)
write(root / '04_evidence/v114_release_manifest.json', dict(version=version, files_sha256=files, checked_artifacts=len(files), scope='Complete non-cache snapshot consistency; no hardware acceptance'))
print(json.dumps(dict(version=version, bit=str(bit), bytes=bit.stat().st_size, sha256=sha(bit), routed=routed, slack_ns=ph['slack_ns'], manifest_entries=len(files)), ensure_ascii=False, indent=2))
