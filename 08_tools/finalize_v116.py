"""Finalize v116 source-bound SRAM candidate. No board/card/Flash actions."""
from pathlib import Path
import datetime, hashlib, json, re, shutil

root = Path(__file__).resolve().parents[1]
assert '01_versions' not in root.parts, 'Frozen snapshots are read-only'
version = 'v116_audio_refill_arbitration_20261027'
archive_root = Path(r'D:\FPGA_Billboard\99_archive\version_history')
archive = archive_root / '01_versions' / version
baseline_root = archive_root / '01_versions/v115_tf_wav_audit_20261027/01_project'
v114_root = archive_root / '01_versions/v114_audio_triple_review_20261027/01_project'
assert not archive.exists(), 'Never overwrite an existing archive'
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

def exact(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        assert sha(src) == sha(dst), 'Refuse to replace existing evidence: ' + str(dst)
    else:
        shutil.copy2(src, dst)
    assert sha(src) == sha(dst)

syp = root / '05_td/v116_audio_visual_synth_attempt1/attempt.json'
php = root / '05_td/v116_audio_visual_physical_attempt1/attempt.json'
bgp = root / '05_td/v116_audio_refill_bitgen_attempt1/attempt.json'
sy, ph, bg = (load(p) for p in (syp, php, bgp))
assert all(d['completed'] for d in (sy, ph, bg))
assert sha(syp) == bg['synthesis_attempt_sha256']
assert sha(php) == bg['physical_attempt_sha256']
assert ph['slack_ns'] == bg['slack_ns'] == bg['reloaded_slack_ns']
assert min(ph['slack_ns'].values()) >= 0 and bg['reloaded_timing_check_matches']
for rel, h in sy['source_sha256'].items():
    assert sha(root / rel) == h, rel
for item in bg['reviewed_reports'].values():
    assert sha(root / item['path']) == item['sha256'], item['path']
reg = load(root / bg['reviewed_reports']['fresh_regression']['path'])
assert reg['passed'] and len(reg['cases']) == 11 and all(x['passed'] for x in reg['cases'])
units = load(root / bg['reviewed_reports']['arbiter_negative_control_and_persistent_snapshot']['path'])
assert units['passed'] and len(units['cases']) == 3
bit = root / '03_bitstreams/v116_audio_refill_720p.bit'
assert bit.stat().st_size == bg['bit_bytes'] and sha(bit) == bg['bit_sha256']

# Archive tooling excludes build. Preserve complete selected synthesis outputs.
src = syp.parent / 'build'
dst = root / '04_evidence/v116_final_synthesis_preserved'
files = []
for f in sorted(src.rglob('*')):
    if f.is_file():
        rel = f.relative_to(src)
        q = dst / rel
        exact(f, q)
        files.append(dict(path=rel.as_posix(), bytes=q.stat().st_size, sha256=sha(q)))
write(dst / 'preservation.json', dict(original=src.relative_to(root).as_posix(), preserved=dst.relative_to(root).as_posix(), files=files))
gate = src / 'idx_video_Runs/syn_1'
assert sha(gate / 'idx_video_gate.db') == ph['synth_gate_sha256'] == bg['synth_gate_sha256']
assert sha(php.parent / 'physical/sdram_pr.db') == bg['routed_db_sha256']

# Same directory depth preserves source references in TD's project files.
prj = syp.parent / 'td_project/idx_video.al'
runprj = prj.parent / 'idx_video_Runs/syn_1/idx_video.prj'
exact(src / 'idx_video.al', prj)
exact(gate / 'idx_video.prj', runprj)
refs = []
for f in (prj, runprj):
    for name in re.findall(r'<File Path="([^"]+)"', f.read_text(encoding='utf8')):
        q = (f.parent / name).resolve()
        assert q.is_file() and q.is_relative_to(root), str(q)
        refs.append(dict(project=f.relative_to(root).as_posix(), source=q.relative_to(root).as_posix(), sha256=sha(q)))
write(root / '04_evidence/v116_td_project_relative_paths.json', dict(passed=True, references=refs))

area = (php.parent / 'physical/sdram_phy.area').read_text(encoding='utf8')
routed = {k: int(re.search(r'^#' + k + r'\s+(\d+)', area, re.M).group(1)) for k in ('lut', 'reg', 'bram', 'bram32k', 'dsp', 'pll', 'gclk', 'pad')}
base = load(v114_root / 'VERSION_STATUS.json')
changes = []
for f in sorted((root / '01_project').rglob('*')):
    if f.is_file():
        rel = f.relative_to(root)
        old = baseline_root / rel
        if not old.is_file() or sha(f) != sha(old):
            changes.append(dict(path=rel.as_posix(), sha256=sha(f), previous_sha256=sha(old) if old.is_file() else None))
assert len(changes) == 5, changes
constraints = {}
for f in sorted((root / '01_project/boards').glob('*')):
    if f.suffix.lower() in {'.adc', '.sdc'}:
        rel = f.relative_to(root)
        assert sha(f) == sha(baseline_root / rel), str(rel)
        constraints[rel.as_posix()] = sha(f)
write(root / '03_docs/v116_SOURCE_CHANGES.json', dict(baseline=str(baseline_root), changes=changes, constraints_unchanged=constraints))
write(root / '04_evidence/v116_origin.json', dict(version=version, source_frozen=str(baseline_root), work_source=str(root), source_status_sha256=sha(baseline_root / 'VERSION_STATUS.json'), no_hardware_action=True, no_handoff_zip=True))
review = dict(
    version=version,
    user_photo=dict(version='V114', current='UF=0 OF=0 AU=0 TF=00', history='TF=A3', aud='Q=0000 MIN=1FFF A3Q=0000 S=00 B=3', interpretation='Historical underrun; current source diagnostics reset. Not a captured first-A3 scene.'),
    reproduction=dict(unit_audio_transactions=8, next_request_gap_cycles=12, baseline_interposed_bmp=7, fixed_interposed_bmp=0, finite_no_request_wait_passed=True,
                      budget_samples=24001, budget_spc1_baseline_first_a3_sample=7672, budget_spc64_baseline_first_a3_sample=11768, fixed_spc1_a3=False, fixed_spc64_a3=False,
                      no_bmp_negative_control_no_a3=True, service_and_consumer_acceleration=16,
                      scope='Deterministic transport budgets, NOT measured real-card latency or proof of all actual-device causes'),
    change='Reserve up to32 idle system cycles for next urgent audio request; bounded fallback allows BMP. No preemption of active SD sector.',
    diagnostic_change='Global first A3Q/S captures on pixel clock and persists across UI/source reset until whole reset',
    resources_delta_vs_v114={k: routed[k] - base['resources_routed'][k] for k in ('lut', 'reg', 'bram', 'dsp', 'pll')},
    actual_card_a3_closed=False, more_buffer_added=False, changed_clocks_or_constraints=False,
    reviewed_reports=bg['reviewed_reports'])
write(root / '03_docs/v116_结果与证据汇总.json', review)
status = dict(
    version=version, recorded_at=datetime.datetime.now().astimezone().isoformat(),
    type='Source-bound diagnostic SRAM candidate; actual-device A3 acceptance pending',
    target='VF-E20NG88 / EG4S20NG88 / 24MHz / HDMI1280x720',
    source_version='v115_tf_wav_audit_20261027', source_frozen=str(baseline_root), work_source=str(root),
    simulation_passed=True, fresh_regression_cases=11, fresh_unit_cases=3,
    synthesis_completed=True, physical_numerical_check_passed=True, new_bit_generated=True,
    hardware_download=False, hardware_acceptance=False, formal_release_approved=False, flash_modified=False, tf_files_modified=False, handoff_zip_generated=False,
    actual_long_track_a3_root_cause_closed=False, user_v114_hardware_a3_failure_recorded=True,
    audio_file_audit='Inherited v115 read-only file-content audit passed; no new card reads in v116',
    resources_synthesis=sy['resources'], resources_routed=routed,
    baseline_resources_routed=base['resources_routed'], resource_delta_vs_v114=review['resources_delta_vs_v114'],
    slack_ns=ph['slack_ns'], buffering=dict(image_frames=2, audio_sector_banks=3, sector_bytes=512, pcm_frames=4096, pcm_bits=48, prefill_frames=3072, low_water_frames=3584, pixel_sample_slots=3),
    bitstream=str(bit), bitstream_relative=bit.relative_to(root).as_posix(), bit_bytes=bit.stat().st_size, bit_sha256=sha(bit),
    archive_path=str(archive), archive_bitstream=str(archive / '01_project/03_bitstreams' / bit.name),
    reviewed_reports=bg['reviewed_reports'], check_timing_counts=bg['check_timing_counts'],
    production_changes=changes, constraints_unchanged=constraints,
    selected_synthesis=syp.relative_to(root).as_posix(), selected_physical=php.relative_to(root).as_posix(), selected_bitgen=bgp.relative_to(root).as_posix(),
    known_open_items=bg['known_open_review'])
write(root / 'VERSION_STATUS.json', status)
(root / 'README_归档位置.md').write_text('# v116归档位置\n\n' + str(archive) + '\n\n只在D盘工作副本继续开发；旧版本冻结保留。本版无需交接ZIP。\n', encoding='utf8')
readme = f"""# v116：音频补数调度修复（SRAM测试候选）

## 当前结论

已完成新旧仲裁对照、11组新回归、3组单元对照、TD综合/布局布线/数值时序、新bit和12块路由ROM核对；**尚未替你下载或听音，实卡A3是否解决待验证**。v114照片为失败证据，不继承为本版通过。

A3表示PCM欠样，不是WAV文件损坏的判据。v115对TF来源两份WAV的内容检查通过；本轮没有重新读取或改写卡。

## 修了什么

- 旧调度只照顾已排队音频请求，音频扇区之间生成下一地址时，BMP可能占用空档。8次音频事务单元对照：旧版中间插7次BMP，新版0次。
- 音频低水位时为下一请求有界预留32个空闲系统时钟；没有音频请求仍会放行BMP，退出音源立即释放，不抢占已开始的扇区。
- 24001帧非零双声道PCM的服务预算对照中，旧版可出现A3，新版相同条件无A3；供数和消费同时加速16倍，是逻辑模型，不是实卡延时测量或实物闭环。
- 首错A3Q/S跨退出UI/换源保留，整体复位才清。Q/MIN仍是当前音源，不要把复位初值当首错。
- 未扩缓存、未降频、未改ADC/SDC/格式、未隐藏错误。主FIFO4096帧与3个扇区银行不变。

## 推荐位流

{bit}

{bit.stat().st_size}字节；SHA256：{sha(bit)}

归档同一文件：
{archive / '01_project/03_bitstreams' / bit.name}

**只选择SRAM临时下载，不擦除/写入Flash。保持原TF文件和接线，先连续听30秒。**
操作见：{root / '03_docs/v116_按键与SRAM测试步骤.md'}
若再次A3，先拍完整V116与第三行AUD；不要立即复位或重下位流。

## 最终资源与TD数值

|资源|使用/容量|
|---|---|
|LUT|{routed['lut']}/19600（{routed['lut']/19600:.2%}）|
|寄存器|{routed['reg']}/19600|
|BRAM9K|{routed['bram']}/64|
|DSP|{routed['dsp']}/29|
|PLL|{routed['pll']}/4|

相对v114最终实现：LUT+4、寄存器+6、BRAM/DSP/PLL不变。
SWNS {ph['slack_ns']['SWNS']:+.3f}ns、HWNS {ph['slack_ns']['HWNS']:+.3f}ns，STNS/HTNS=0。保持裕量小，**数值通过不等于PVT可靠性签核**。
RGB332缓存、SDRAM宏重定位、33项异常内部输入延时、SiP/PVT及全地址实物BIST仍开放。

## 文件与证据

- 原因及边界：{root / '03_docs/v116_音频仲裁问题与证据边界.md'}
- 结果汇总：{root / '03_docs/v116_结果与证据汇总.json'}
- 相对路径TD工程：{prj}
- 完整性检查：{root / '08_tools/verify_v116.py'}
- 归档完整路径：{archive}

完整源码/TB/约束/TD/位流/报告与原始照片均保留。旧未改模块仅继承SHA匹配证据；本轮引脚SPI测试使用512帧FIFO行为卡，4096帧引脚长流未重跑，不能冒称全部物理链路验收。所有新增在D盘，不动旧归档；无需交接包。
"""
(root / 'README_先看这里.md').write_text(readme, encoding='utf8')
manifest = {}
for f in sorted(root.rglob('*')):
    if not f.is_file():
        continue
    rel = f.relative_to(root)
    if any(p in {'00_tmp', 'build', '__pycache__', '.git'} for p in rel.parts) or f.suffix.lower() in {'.vvp', '.vcd', '.pyc'}:
        continue
    if rel.as_posix() == '04_evidence/v116_release_manifest.json':
        continue
    manifest[rel.as_posix()] = sha(f)
write(root / '04_evidence/v116_release_manifest.json', dict(version=version, files_sha256=manifest, checked_artifacts=len(manifest), scope='Complete non-cache snapshot consistency; no hardware acceptance'))
print(json.dumps(dict(version=version, bit=str(bit), bytes=bit.stat().st_size, sha256=sha(bit), routed=routed, slack_ns=ph['slack_ns'], manifest_entries=len(manifest)), ensure_ascii=False, indent=2))
