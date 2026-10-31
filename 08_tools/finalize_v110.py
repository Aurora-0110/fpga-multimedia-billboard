"""Freeze v110 artifacts/documents, with strict source/report binding. No programming.
Run only in the mutable D-drive work tree; archive_version.py performs the actual archive.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re
import shutil

root = Path(__file__).resolve().parents[1]
assert '01_versions' not in root.parts, 'Frozen archive is read-only'
assert root.drive.upper() == 'D:', 'Keep artifacts on D drive'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--synth-attempt', type=int, default=4)
parser.add_argument('--physical-attempt', type=int, default=4)
parser.add_argument('--bitgen-attempt', type=int, default=1)
args = parser.parse_args()
version = 'v110_ui_pause_opt_20261026'
archive = Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions') / version
assert not archive.exists(), 'Never edit/overwrite a frozen version'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def copy_exact(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert sha(source) == sha(target), f'Refuse differing preserved artifact: {target}'
    else:
        shutil.copy2(source, target)
    assert sha(source) == sha(target)

synth_path = root/f'05_td/v110_audio_visual_synth_attempt{args.synth_attempt}/attempt.json'
physical_path = root/f'05_td/v110_audio_visual_physical_attempt{args.physical_attempt}/attempt.json'
bitgen_path = root/f'05_td/v110_ui_pause_bitgen_attempt{args.bitgen_attempt}/attempt.json'
sy, ph, bg = map(load, (synth_path, physical_path, bitgen_path))
assert all(record.get('completed') for record in (sy, ph, bg)), 'Build incomplete'
assert min(ph['slack_ns'].values()) >= 0 and ph['nonnegative_slack']
bit = root/'03_bitstreams/v110_ui_pause_720p.bit'
assert sha(bit) == bg['bit_sha256'] and bit.stat().st_size == bg['bit_bytes']
for name, expected in sy['source_sha256'].items():
    assert sha(root/name) == expected, f'Changed synthesized source: {name}'
for entry in bg['reviewed_reports'].values():
    assert sha(root/entry['path']) == entry['sha256'], f'Changed test report: {entry["path"]}'
assert all(entry['current_v110_execution'] for entry in bg['reviewed_reports'].values())

# build is intentionally excluded by the archiver; keep the selected gate DB,
# raw reports, and raw project at a same-depth non-cache location.
gate = synth_path.parent/'build/idx_video_Runs/syn_1'
preserved = root/'04_evidence/v110_final_synthesis_preserved'
kept = []
for source in sorted(gate.iterdir()):
    if source.is_file():
        target = preserved/source.name
        copy_exact(source, target)
        kept.append(dict(file=source.name, bytes=target.stat().st_size, sha256=sha(target)))
write_json(preserved/'preservation.json', dict(
    reason='Final selected synthesis gate DB and raw reports preserved outside excluded build caches',
    selected_attempt=args.synth_attempt, files=kept))
project = synth_path.parent/'td_project/idx_video.al'
run_project = project.parent/'idx_video_Runs/syn_1/idx_video.prj'
copy_exact(synth_path.parent/'build/idx_video.al', project)
copy_exact(gate/'idx_video.prj', run_project)
references = []
for path in (project, run_project):
    for name in re.findall(r'<File Path="([^"]+)"', path.read_text(encoding='utf-8')):
        resolved = (path.parent/name).resolve()
        assert resolved.is_file() and resolved.is_relative_to(root), str(resolved)
        references.append(dict(project=path.relative_to(root).as_posix(),
                               source=resolved.relative_to(root).as_posix(), sha256=sha(resolved)))
write_json(preserved/'td_project_relative_paths.json', dict(passed=True, references=references,
    note='Original TD header retains the original build path. All relative source paths resolve at the preserved same-depth location. Rebuild in a mutable D-drive copy using run_acceptance.py; never compile in a frozen archive.'))

res, slack = sy['resources'], ph['slack_ns']
baseline_path = Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v109_tf_wav_fit_20261026\01_project\VERSION_STATUS.json')
baseline = load(baseline_path)
previous_resources = baseline['resources']
previous_slack = baseline['slack_ns']
routed_area = physical_path.parent/'physical/sdram_phy.area'
baseline_area = baseline_path.parent/'05_td/v109_audio_visual_physical_attempt4/physical/sdram_phy.area'
def parse_area(path):
    text = path.read_text(encoding='utf-8')
    return {key:int(re.search(r'^#'+key+r'\s+(\d+)', text, re.M).group(1))
            for key in ('lut','reg','bram','bram32k','dsp','pll','gclk','pad')}
routed_res = parse_area(routed_area)
previous_routed = parse_area(baseline_area)
for key, capacity in dict(lut=19600,reg=19600,bram=64,bram32k=16,dsp=29,pll=4,gclk=16,pad=66).items():
    assert routed_res[key] <= capacity, (key, routed_res[key], capacity)
comparison_dir = root/'04_evidence/v110_baseline_comparison'
copy_exact(baseline_path, comparison_dir/'v109_VERSION_STATUS.json')
copy_exact(baseline_area, comparison_dir/'v109_sdram_phy.area')
media_path = root/'06_test_media/audio/audio_manifest.json'
media = load(media_path)
for item in media['media']:
    source = root/item['file']
    assert sha(source) == item['sha256'] and source.stat().st_size == item['bytes']
limits = list(bg['known_open_review']) + [
    'No new v110 JTAG download, screen observation, speaker listening, Flash programming or cold-start/endurance acceptance has been performed.',
    'Timing coverage is not 100%; 33 abnormal input-delay entries, dummy nodes and external I/O timing require review. Passing numerical STA is not SiP/PVT or full-address hardware-BIST sign-off.',
    'Setup/hold margins remain small. Setup increases by only 0.014ns over v109; hold is unchanged at 0.030ns. This is not a large reliability-margin gain.',
    'Logo optimization trades two additional BRAM9K blocks for lower LUT use; no loss of Logo pixels or added pipeline latency is claimed beyond RTL/reference and routed-INIT checks.',
    'The shared-SPI tests are digital pin/protocol tests, not real-card electrical, analog power or complete SDRAM720p end-to-end acceptance.',
    'Source media copyright/public redistribution rights are not assumed; do not publish the music/ad audio automatically.',
    'Real TF contents have not been modified; PCM-WAV media are local preparations. Do not format the user card or overwrite existing pictures.',
    'File audio can extend image-load time; no one-second image-transition or hot-swap-recovery guarantee. Sticky transport faults may require a power cycle.',
]
status = dict(
    version=version, parent='v109_tf_wav_fit_20261026', baseline='v109_tf_wav_fit_20261026',
    started_date='2026-10-26', finalized_at=datetime.datetime.now().astimezone().isoformat(),
    target='VF-E20NG88 / EG4S20NG88 / 24MHz / HDMI1280x720',
    scope='Independent UI toggle in audio mode, actual sample-position-preserving pause/resume, and bounded resource/timing optimization',
    resources=res, resource_reporting_stage='synthesis', synthesis_resources=res,
    routed_resources=routed_res, baseline_routed_resources=previous_routed,
    routed_resource_delta={k:routed_res[k]-previous_routed[k] for k in routed_res},
    baseline_resources=previous_resources, resource_delta={k:res[k]-previous_resources[k] for k in res if k in previous_resources},
    slack_ns=slack, baseline_slack_ns=previous_slack,
    selected_attempts=dict(synthesis=args.synth_attempt, physical=args.physical_attempt, bitgen=args.bitgen_attempt),
    validation=bg['reviewed_reports'], check_timing_counts=bg['check_timing_counts'],
    numerical_timing_pass=True, formal_release_approved=False, new_hardware_acceptance=False,
    programmed=False, flash_modified=False, tf_modified=False, no_handoff_zip=True,
    flash_candidate=True, flash_candidate_requires_sram_hardware_acceptance=True,
    bitstream=str(bit), archive_bitstream=str(archive/'01_project/03_bitstreams'/bit.name),
    bit_sha256=sha(bit), bit_bytes=bit.stat().st_size,
    archive_destination=str(archive), known_open_review=limits)
write_json(root/'VERSION_STATUS.json', status)

keys = '''|操作|本版功能|
|---|---|
|浏览时短按 K0|下一图；图像客户端错误时重试|
|浏览时短按 K1|自动/手动轮播切换|
|单独长按 K0 约1秒|进入/退出音频控制模式；退出保留音源与暂停位置|
|音频控制中短按 K0|暂停/继续当前音频；不是静音后在后台继续播放|
|音频控制中短按 K1|跟图内部测试音 → MUSIC.WAV → ADVOICE.WAV → 跟图内部测试音；切源清暂停、从头播|
|单独长按 K1 约1秒|在播放、暂停、音频控制中均独立切换中文 UI 显示/隐藏；不附带短按动作|
|双键短按|装饰 OSD/Logo/频谱/演示字幕显隐，和长 K1 的控制 UI 是两套开关|
|双键长按约1秒|浏览 → 亮度 → 对比度 → 浏览，同时退出音频控制|
|调参中短按 K0/K1|减小/增大当前显示参数；范围不变|

**手动隐藏 UI 后**，普通按键、切源和进出音频模式都不强制唤醒；长 K1 再显示。真实故障优先提示，故障清除后恢复隐藏意图。第一次长 K1 会相对按下前的显隐翻转，不被按键提示的瞬间显示干扰。
'''
steps = f'''1. **目前先用 SRAM 临时下载，不擦除、不写 Flash。** 推荐文件：`{bit}`。保持当前可靠供电和 HDMI 连接；插拔 TF/SPI 接线前断电，正常测试不需每次解压。
2. 卡中保留现有4张图片。如果根目录还没有 `MUSIC.WAV` 和 `ADVOICE.WAV`，断电后取卡，用读卡器只复制 `{root/'06_test_media/audio'}` 中这两个文件到 FAT32 卡根目录；不要格式化、不要删图。文件均为 48kHz/24-bit/双声道 PCM-WAV，不把 FLAC 直接改后缀。
3. 用 TD Programmer 下载上述 `.bit` 到 FPGA SRAM。记录实际下载结果；脚本生成位流不等于下载成功。启动后确认 720p、4图、缩放、Logo、OSD 和轮播仍正常。
4. 长 K0 进入音频控制；短 K1 选音乐。先听约10秒，再短 K0 暂停，保持5秒；应无声而画面/HDMI继续，短 K0恢复应接着原位置，不应跳过5秒。不要用音乐中本来就有的静音段作唯一依据。
5. 音乐播放时长 K1隐藏 UI，确认音频不断；短 K0暂停、短 K1切源、长 K0退出/重新进入都不应擅自弹出 UI。再长 K1重新显示，检查源名与播放/暂停状态一致。
6. 暂停时长 K0退出，再长 K0进入：保留暂停位置，短 K0继续。暂停时短 K1换音源：新音源应解除暂停并从头播放，无上一首残音。
7. 选广告语音：应有声音和随实际 PCM 变化的频谱；播放到约30.08秒后结束静音。切走再切回可从头重播。WAV模式不显示旧固定16秒演示字幕，不代表实现语音识别或真实广告逐字字幕。
8. 检查长按不额外触发短按、双键功能和亮度/对比度；轮播和播放连续运行至少10分钟，切源/暂停组合各20次，记录掉信号、杂音、欠载/故障信息及恢复情况。
9. 以上实物检查通过后，才进入 Flash 固化步骤。固化时还须做写入/校验，并至少3次完全断电冷启动；本轮尚未执行。断电回到旧 Flash 版是预期，不表示刚下载的 SRAM 版保存到了 Flash。
'''
(root/'03_docs/v110_按键与上板步骤.md').write_text('# v110 按键与上板步骤\n\n'+keys+'\n## 实物验收顺序\n\n'+steps, encoding='utf-8')

report = '''# v110 实现、资源优化与验证边界

## 状态
本版完成仿真、综合、布局布线、数值时序检查和位流生成，是**先 SRAM 验收、后固化**的候选。尚未下载板卡、听音、观察新版本画面、写 Flash 或验证冷启动，不能继承旧版实测通过。

## 相对 v109 的实现
- 音频控制模式短 K0 由“退出模式”改为真正暂停/继续；退出改用长 K0。WAV暂停停止真实样本消费并保持FIFO/held/位置，48k输出静音PCM，I2S/HDMI/共享SPI仲裁不复位，图像读取继续。
- 内部测试音暂停冻结相位/beat，恢复不跨过暂停时长；pause/resume清理旧频谱窗口。音源切换清暂停并重播，退出音频控制保留位置。
- UI长K1翻转独立状态，不再被音频选择强制持续显示；保存用户隐藏意图，故障显示具有优先级；中文源名和播放/暂停/预缓冲/结束/故障状态联动。
- WAV头解析使用滚动字段、精确格式标志与紧凑装配；FAT/BMP LBA计算改为有界移位共享加法；尺寸/寻址使用经过边界测试的位宽，保留2048×2048输入上限和双线性/抖动/RGB332链路。
- TMDS预处理移入原输入寄存器边界，流水延迟不加拍；新旧路径及独立编码参考比较。
- UI行解码改并行范围、布局启动tick登记；Logo按128像素补齐行、直接拼接地址、使用TD支持的BRAM推导，ROM内补零，消除大地址加法和输出清零选择器。官方Logo的112×56有效像素和一拍延迟保持。

## 优化实数（不是削减功能后的独立模块数字）
'''
report += '下面采用两版**最终布局布线后**报告，包含物理优化开销，不与综合数值混用。\n\n|资源|v109布局布线后|v110布局布线后/容量|本版占比|变化|\n|---|---:|---:|---:|---:|\n'
for key, capacity, label in [('lut',19600,'LUT'),('reg',19600,'寄存器'),('bram',64,'BRAM9K'),('dsp',29,'DSP'),('pll',4,'PLL')]:
    report += f'|{label}|{previous_routed[key]}|{routed_res[key]}/{capacity}|{routed_res[key]/capacity:.2%}|{routed_res[key]-previous_routed[key]:+d}|\n'
report += f'\n布局布线后LUT减少{previous_routed["lut"]-routed_res["lut"]}个，即相对v109减少{(previous_routed["lut"]-routed_res["lut"])/previous_routed["lut"]:.2%}；Logo多用2个BRAM。\n\n'
report += f'供对照，**综合阶段**LUT {previous_resources["lut"]} → {res["lut"]}（{res["lut"]/19600:.2%}），寄存器 {previous_resources["reg"]} → {res["reg"]}。物理优化会插入/复制逻辑，最终实际占用请看上表。\n\n'
report += '|时序项|v109|v110|\n|---|---:|---:|\n'
for key in ['SWNS','STNS','HWNS','HTNS']:
    report += f'|{key}|{previous_slack[key]:+.3f}ns|{slack[key]:+.3f}ns|\n'
report += '''
setup仅改善0.014ns，hold不变，裕量仍小。没有降低目标时钟、增加假路径、关闭真实检查来宣称优化。SHA256只是内容一致性校验，不是性能指标，不能通过改哈希改善时序。

本轮物理attempt1/2数值通过但裕量不理想；attempt3 setup -0.594ns失败，瓶颈转为Logo输出，不从失败数据库生成位流。修改Logo BRAM后选用综合4、物理4、bitgen1。中间失败/超时证据保留，不充作最终通过。

## 最终验证证据

|项目|本版证据路径（根目录相对）|范围|
|---|---|---|
'''
for name, entry in bg['reviewed_reports'].items():
    report += f'|{name}|`{entry["path"]}`|本次执行，源哈希匹配|\n'
report += '''
- WAV解码20例；16/24-bit mono/stereo、块跳过/padding、非法格式/48k边界、真实音乐/广告前1024帧。
- 播放8种场景：暂停保持真实样本位置、暂停至FIFO满、首帧后暂停、暂停中切源、EOF前暂停等；随机非零48-bit立体声逐帧参考，暂停期间输出零且图片继续。
- FAT32挂载22例；两个BMP链各76例，输出32×18，含padding、top-down/bottom-up、碎片/异常和2048边界，不能冒称这些小图测试本身是完整720p链路。
- 另用真实双线性RTL完整比较两幅1280×720输出，共1,843,200像素：640×480 top-down和17×11 bottom-up；86,090插值比较/12小图及最大源尺寸边界另行通过。
- SPI数字引脚模型5组512-frame测试FIFO矩阵，另2048-frame产品FIFO/4倍消费压力；含暂停、暂停中切源、BMP继续、CMD0只一次和逐帧参考。不是实卡电气或完整SDRAM/HDMI整机仿真。
- UI432状态向量、字库与5幅720p光栅；按键/字幕6组；视觉9组含顶层注入内存反馈；原生HDMI三异步相位；prepared TMDS两组精确参考和时延一致性。
- 最终路由UI/字幕10个BRAM INIT和Logo2个8192×1块INIT分别对照独立字库/原Logo坐标参考，共12块通过。不是回读，也不是路由后功能仿真。
- RGB332抖动/截断4例使用本轮重新执行的测试，不引用旧TB哈希不匹配的v101证据。

## 构建与完整性
'''
report += f'- 正式候选：`{bit}`\n- 大小：{bit.stat().st_size}字节\n- SHA256：`{sha(bit)}`\n'
report += f'- 完整源码、TB、约束和构建入口：`{root}`；冻结归档：`{archive}`。\n'
report += f'- 选定综合原始gate DB/area/prj另存于`{preserved}`，避免build缓存排除后丢失；TD工程的内部相对源码路径已逐一验证。\n'
report += '''- 可在可写工作副本运行 `08_tools/run_acceptance.py --stage check` 只读校验，不编译、不下载、不动TF/Flash。重建使用对应stage和未占用的attempt编号；冻结归档内拒绝编译。
- 发布manifest不自我哈希；归档另有完整MANIFEST_SHA256，所有旧版保留。

## 开放项（未豁免）
'''
report += '\n'.join('- '+item for item in limits)+'\n'
report += '\n## 本次脚本/测试限制记录\n\n- 第一轮bitgen前置守卫发现UI证据仍绑定Logo优化前源码，以及旧dither证据的TB哈希不一致，均未进入位流生成；重新执行当前UI与dither后再检查。\n- 全720p旧runner 900秒墙钟超时，日志保留；最终两case明确2400秒有限上限，实际各约10分钟完成，不跳过像素检查。\n- 初次边界TB继承过小MW/MH造成测试内存越界，修TB为真实2048上限后重跑；不是生产DUT修复结论。\n- 辅助脚本首次utf8-sig拼写错误已修正，仅影响脚本编辑执行；RTL/最终综合数据库未受改动。\n'
(root/'03_docs/v110_实现与验证说明.md').write_text(report, encoding='utf-8')

rows = ['测试日期/人/卡容量/FAT32/供电','位流SHA256/实际SRAM下载结果','720p四图/缩放/Logo/OSD/自动手动',
        '长K0进出音频模式与模式保持','音乐暂停5秒恢复位置/无跳播','暂停至10秒/画面和轮播继续',
        '播放中UI隐藏/显示/无音频中断','隐藏后暂停/切源/进出模式不唤醒','隐藏后真实故障优先显示/恢复隐藏',
        '暂停退出/重新进入/继续位置保留','暂停时换源清暂停/从头播/无残音','广告约30.08秒EOF静音',
        '切源/播放暂停20次/无掉信号杂音','频谱跟随真实PCM/暂停归零衰减','双键/亮度/对比度/不误触',
        '至少10分钟连续运行/错误码/欠载','后续Flash写入/校验（本轮未做）','后续至少3次断电冷启动（本轮未做）']
record = '# v110 实物测试记录：待填写，尚未上板\n\n本表不是通过证据。仿真、编译、下载、看画面、听音、Flash写入/校验、冷启动分别记录。\n\n|检查项|实测结果/现象|\n|---|---|\n'
record += '\n'.join(f'|{label}|待实测|' for label in rows)+'\n'
(root/'03_docs/v110_实物测试记录_待填写.md').write_text(record, encoding='utf-8')

readme = f'''# v110：音频模式独立UI + 真正暂停/继续 + 资源优化

**软件侧完成，尚未做本版板上测试。先SRAM验收，再Flash固化；旧版本全部保留。**

- 推荐唯一新位流：`{bit}`
- 冻结归档目标：`{archive}`
- 开始于2026-10-26；文档完成于{datetime.date.today().isoformat()}。
- **布局布线后**LUT {routed_res['lut']}/19600 ({routed_res['lut']/19600:.2%})，寄存器{routed_res['reg']}，BRAM{routed_res['bram']}/64，DSP{routed_res['dsp']}/29。综合阶段LUT另为{res['lut']}（{res['lut']/19600:.2%}），不要混用统计阶段。
- setup {slack['SWNS']:+.3f}ns、hold {slack['HWNS']:+.3f}ns，数值通过但裕量仍小，**不是可靠性签核**。
- SHA256：`{sha(bit)}`；{bit.stat().st_size}字节。
- 当前未改TF/Flash，不默认生成交接压缩包；无需解压即可使用工作目录中的位流。

## 按键

{keys}
## 上板验收

{steps}
## 文档

- `03_docs/v110_按键与上板步骤.md`
- `03_docs/v110_实现与验证说明.md`
- `03_docs/v110_实物测试记录_待填写.md`
- `VERSION_STATUS.json` 与 `04_evidence/v110_release_manifest.json`

旧说明均标为INHERITED，不能当作v110的新功能或实测记录。RGB332、SDRAM宏/33异常内部延时、SiP/PVT及全地址实物BIST仍开放。两段媒体仅用于本地测试，不自动取得公开分发权。
'''
(root/'README_先看这里.md').write_text(readme, encoding='utf-8')
(root/'README_归档位置.md').write_text(f'# v110 归档位置\n\n冻结目标：`{archive}`\n\n工程内部相对路径保留在归档的01_project下；只读查看，修改或测试先复制到D盘可写工作目录。本文件由定版脚本生成；归档成功/完整性另以archive_version.py save与verify结果为准。\n', encoding='utf-8')

# Optional deterministic RTL previews, never mislabeled as board photographs.
ui_report = root/bg['reviewed_reports']['hidden_ui']['path']
for preview in sorted(ui_report.parent.glob('*_1.png')):
    target = root/'03_docs/v110_UI_RTL预览.png'
    if not target.exists():
        shutil.copy2(preview, target)
    break
# Full release consistency manifest; the outer archive manifest also includes
# historical logs/evidence, while this list binds the selected usable artifacts.
files = {}
def include(path):
    assert path.is_file(), str(path)
    files[path.relative_to(root).as_posix()] = sha(path)
for base in ('01_project','02_tests','03_bitstreams','03_docs','08_tools'):
    for path in sorted((root/base).rglob('*')):
        if path.is_file() and not set(path.relative_to(root).parts) & {'build','__pycache__'} and path.suffix.lower() not in {'.vvp','.vcd','.pyc'}:
            include(path)
for path in (root/'README_先看这里.md', root/'README_归档位置.md', root/'VERSION_STATUS.json',
             synth_path, physical_path, bitgen_path, media_path, project, run_project):
    include(path)
for path in sorted((root/'06_test_media/audio').glob('*.WAV')):
    include(path)
for entry in bg['reviewed_reports'].values():
    include(root/entry['path'])
for path in sorted(preserved.rglob('*')):
    if path.is_file(): include(path)
for folder in (physical_path.parent, bitgen_path.parent, comparison_dir):
    for path in sorted(folder.rglob('*')):
        if path.is_file(): include(path)
write_json(root/'04_evidence/v110_release_manifest.json', dict(
    version=version, files_sha256=files, hardware_test=False, flash_modified=False,
    tf_modified=False, source_bit_consistency_only=True, no_handoff_zip=True))
print(json.dumps(dict(version=version, synthesis_resources=res, routed_resources=routed_res, slack_ns=slack, checked_artifacts=len(files),
                     bit=str(bit), bit_sha256=sha(bit), archive_destination=str(archive),
                     hardware_test=False, flash_modified=False), ensure_ascii=False, indent=2))
