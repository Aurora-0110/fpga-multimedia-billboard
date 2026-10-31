"""Prepare v117 Flash candidate records, without modifying RTL, TF or the board."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'v117_flash_candidate_20261027'
HISTORY = Path(r'D:\FPGA_Billboard\99_archive\version_history')
ARCHIVE = HISTORY / '01_versions' / VERSION
BASELINE = HISTORY / '01_versions/v116_audio_refill_arbitration_20261027/01_project'
HISTORICAL = HISTORY / '01_versions/v074_flash_coldboot_acceptance_20261024'
MANIFEST = ROOT / '04_evidence/v117_release_manifest.json'
EXCLUDED_DIRS = {'00_tmp', 'build', '__pycache__', '.git'}
EXCLUDED_SUFFIXES = {'.vvp', '.vcd', '.pyc'}
EXPECTED_BIT = '540faced66d96a83d6ab6e54caca5e614c54ae6be8822774f35febe1ee6cfdb6'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(rel, value):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + '\n' if not isinstance(value, str) else value
    path.write_text(text, encoding='utf8')


def snapshot_files():
    result = {}
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(x in EXCLUDED_DIRS for x in rel.parts) or p.suffix.lower() in EXCLUDED_SUFFIXES or p == MANIFEST:
            continue
        if p.is_symlink():
            raise ValueError('Symlink is not a snapshot artifact: ' + str(p))
        result[rel.as_posix()] = sha(p)
    return result


def prepare():
    base = load(ROOT / 'BASELINE_v116_VERSION_STATUS.json')
    for rel in ('06_flash/01_image', '06_flash/02_guides', '06_flash/03_historical_evidence',
                '06_flash/04_optional_tf_music', '07_acceptance', '04_evidence/v117_preflight'):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)
    original_bit = ROOT / base['bitstream_relative']
    assert original_bit.stat().st_size == 645936 and sha(original_bit) == EXPECTED_BIT
    published_bit = ROOT / '06_flash/01_image' / original_bit.name
    shutil.copy2(original_bit, published_bit)
    assert sha(published_bit) == EXPECTED_BIT

    historical_entries = []
    for src_rel, name in (
        ('01_project/04_evidence/program_settings.png', 'v074_历史设置_非本版结果.png'),
        ('01_project/04_evidence/program_flash_success.png', 'v074_历史Program成功_非本版结果.png'),
        ('01_project/04_evidence/verify_flash_success.png', 'v074_历史Verify成功_非本版结果.png'),
        ('01_project/04_evidence/flash_marking_closeup.png', 'v074_历史Flash丝印.png'),
        ('01_project/03_acceptance/用户冷启动反馈.json', 'v074_历史用户冷启动反馈.json'),
        ('VERSION.json', 'v074_历史版本来源.json'),
    ):
        src = HISTORICAL / src_rel
        dst = ROOT / '06_flash/03_historical_evidence' / name
        shutil.copy2(src, dst)
        assert sha(src) == sha(dst)
        historical_entries.append(dict(source=str(src), copy=dst.relative_to(ROOT).as_posix(), sha256=sha(dst)))
    write('06_flash/03_historical_evidence/来源与边界.json', dict(
        source_version='v074_flash_coldboot_acceptance_20261024', design_version='v072', date='2026-10-24',
        scope='Historical same-board Flash settings/marking and old-v072 results only; NOT v116/v117 programming, verification or cold-boot evidence.',
        current_flash_contents_known=False, original_flash_backup_available=False, files=historical_entries))
    write('06_flash/03_historical_evidence/先看这里_这些都是历史证据.md', '''# 历史截图，不是本次固化成功记录

本目录来自2026-10-24的v074验收记录，所写设计是v072。仅用于确认本板以往采用的Flash型号、容量和BitWriter操作方式。

- U5记录：BoyaMicro 25Q16BSTIG，16 Mbits。
- 设置截图底部是更早的SRAM结果，不能把它当作Program Flash通过。
- 另两张成功截图分别是旧位流Program Flash、Verify Flash，不是本次v116的结果。
- 历史只记录了一次用户冷启动反馈，不等于本版冷启动通过，更不是三次重复性结果。
- 当前板内Flash内容未知，未声称已有原始Flash备份；本次没有读取或改写板卡。
''')

    manual = Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\doc\SWUG\SWUG110_BitWizard_User_Guide.pdf')
    assert manual.is_file()
    write('06_flash/02_guides/官方手册依据.json', dict(
        path=str(manual), sha256=sha(manual), title='SWUG110 BitWizard User Guide',
        source_type='Installed TD official manual, read locally',
        pages=[
            dict(pdf_page=10, printed_page=9, topic='.bit has a header; .bin is not made by renaming the extension.'),
            dict(pdf_page=11, printed_page=10, topic='Tools > BitWriter, or bin/bw.exe.'),
            dict(pdf_page=12, printed_page=11, topic='Refresh reads the FPGA device ID, not Flash verification.'),
            dict(pdf_page=19, printed_page=18, topic='JTAG rate and Program SRAM; SRAM configuration is volatile.'),
            dict(pdf_page=20, printed_page=19, topic='Program Flash writes configuration for nonvolatile boot.'),
            dict(pdf_page=21, printed_page=20, topic='Flash Read supports specified address/length/file.'),
            dict(pdf_page=22, printed_page=21, topic='Verify Flash; Erase Flash is a whole-chip erase.'),
            dict(pdf_page=23, printed_page=22, topic='Bitstream file selection supports bit/bin/SVF.')],
        does_not_prove_current_hardware_pass=True))
    write('06_flash/02_guides/固化设置.json', dict(
        release_version='v117', design_version='v116', target_device='EG4S20NG88',
        board='VF-E20NG88', oscillator_mhz=24, hdmi='1280x720',
        download_tool='TD BitWriter', downloader='AL-LINK (same-board historical record)',
        file_relative='06_flash/01_image/' + original_bit.name, sha256=EXPECTED_BIT,
        bytes=645936, program_mode='PROGRAM_FLASH', verify_mode='VERIFY_FLASH',
        speed_mhz=5, memory_size_mbits=16, flash_capacity_bytes=2097152,
        flash_marking_historical='BoyaMicro 25Q16BSTIG (U5)',
        settings_basis='Same-board v074 historical screenshots, not an automatic new device probe',
        must_reconfirm_same_board_and_stable_power=True, address_override=None,
        no_separate_whole_chip_erase=True, no_bin_conversion=True,
        do_not_use=['PROGRAM_SPIBIN', 'DualBoot', 'MultiBoot', 'OTP/security/encryption changes', 'MSEL changes'],
        program_executed=False, verify_executed=False, cold_boot_tested=False))

    music = Path(r'D:\FPGA_Billboard\media\bilibili_BV1h5QaY5EaH_20261027\01_wav\MUSIC.WAV')
    music_sha = 'fd9e3b0060b501c2b66b9ddc57bb5ba6b4969f7ca0cf7e015b5accd1ca4e6839'
    assert music.is_file() and music.stat().st_size == 41301104 and sha(music) == music_sha
    write('06_flash/04_optional_tf_music/可选素材记录.json', dict(
        path=str(music), sha256=music_sha, bytes=41301104, format='PCM1 48000Hz 24-bit stereo; standard 44-byte header',
        duration_seconds=143.406458, included_in_flash=False, copied_to_tf=False,
        source_video_id='BV1h5QaY5EaH', purpose='Optional local TF media, independent of Flash preparation',
        decoding_validation='Prior conversion report; not rerun in v117',
        sha_rechecked_during_v117_preparation=True, public_redistribution_permission_confirmed=False))
    write('06_flash/04_optional_tf_music/说明.md', f'''# 可选音乐不是固化必需文件

新转换的音乐已单独保存在：
`{music}`

48 kHz、24-bit、双声道、PCM WAV；143.406458秒；SHA256：`{music_sha}`。
本版只复核其磁盘文件哈希，不复制入工程、不写TF卡、不写FPGA Flash，也不把文件完好视为播放不卡顿。

本次固化和冷启动先保持当前TF资源不变，便于判断问题来源。以后要换音乐，应停机断电后取TF卡，先备份原MUSIC.WAV，再复制新文件到卡根目录；保持文件名MUSIC.WAV和ADVOICE.WAV不变。
视频音乐的公开传播授权未核实，后续公开GitHub工程不要默认上传该音轨。
''')
    write('07_acceptance/当前用户请求.json', dict(
        task_date='2026-10-27', exact_quote='可以做成可固化版本了',
        interpretation='Request to prepare a Flash-ready release; not a report that v116 SRAM listening or A3 recovery passed.',
        user_v116_30s_listening_pass_explicitly_recorded=False,
        current_request_does_not_supply_program_flash_verify_or_coldboot_evidence=True))
    write('07_acceptance/固化与冷启动验收记录.md', '''# v117固化与冷启动验收记录（待实物填写）

发布记录v117；实际设计V116；本表创建时所有项目均未执行，不能用v074旧截图代替本次证据。
实际测试反馈后另存下一版记录，不修改冻结归档。

## 写入前

- [ ] SRAM连续听音乐至少30秒，无A3、L6报错或卡顿。
- [ ] 暂停/继续、音乐/广告换源、UI显隐与图片轮播并发正常。
- [ ] 如再报A3，已停止固化并保存V116/AUD完整照片。
- [ ] 同一EG4S20NG88板卡，U5容量/型号与本板历史一致。
- [ ] 已知Program Flash将覆盖旧开机配置；当前Flash未声称已备份。

## 非易失写入（目前均未执行）

- 文件：v116_audio_refill_720p.bit
- SHA256：540faced66d96a83d6ab6e54caca5e614c54ae6be8822774f35febe1ee6cfdb6
- [ ] PROGRAM_FLASH / 5 MHz / 16 Mbits，工具成功并保存新截图。
- [ ] 同一文件VERIFY_FLASH，工具成功并保存新截图。
- 实际写入时间、工具日志、截图路径：未记录。
- [ ] 断电前已确认工具结束；未带电拔卡或改杜邦线。

## 不依赖SRAM下载的真实冷启动

|轮次|仅上电能否出图|首次出图秒数|四图轮播|UI/按键|MUSIC连续30秒|ADVOICE播放|A3/L6|备注|
|---|---|---|---|---|---|---|---|---|
|1|未测试|未记录|未测试|未测试|未测试|未测试|未记录| |
|2|未测试|未记录|未测试|未测试|未测试|未测试|未记录| |
|3|未测试|未记录|未测试|未测试|未测试|未测试|未记录| |

三次是工程建议，不是声称的官方验收条款。冷启动时屏幕先通电选HDMI，再只给板卡供电，不点Program SRAM；需避免下载器等线缆反供电导致“假冷启动”。

默认音源是测试音，不是MUSIC自动播放；长K0进入音频控制，短K1选择音乐/广告后再听音。
数值时序通过、Flash校验成功、冷启动可用和音频实测通过属于不同层次。即使上述通过，宏模型/内部延时/SiP/PVT及全地址实物BIST仍未正式签核。
''')
    write('06_flash/02_guides/固化步骤.md', f'''# v117 Flash固化步骤（设计仍为V116）

## 先明确当前进度

本版没有修改RTL、重新综合或生成另一份设计位流。它把v116已生成的同一份bit整理为固化准备版，保留完整源码、约束、TB、TD报告与证据。当前没有代你下载、听音、Program Flash、Verify Flash或冷启动；A3实卡修复尚无明确通过反馈。

## 第一步：未测过v116，先临时测试

保持原接线、TF卡内容和驱动。先用Program SRAM临时下载下列文件，连续听音乐至少30秒，并验证暂停/继续、UI显隐、音乐/广告切换及图片轮播并发。若再报A3或L6亮，停止固化，先拍完整V116/AUD信息。
如果已用同一哈希的v116完成这些实测，可以不重复临时下载。

## 第二步：选定唯一位流与参数

本次推荐文件：
`{ROOT / '06_flash/01_image' / original_bit.name}`

归档同一文件：
`{ARCHIVE / '01_project/06_flash/01_image' / original_bit.name}`

645936字节；SHA256：`{EXPECTED_BIT}`。
保持扩展名.bit；TD BitWriter可直接Program Flash，不要改名.bin、截头、Create Flash File或选择Program SPIBIN/DualBoot。

TD → Tools → BitWriter（独立程序为TD bin目录的bw.exe）。同一板卡的历史设置是：

|项目|本次设置|
|---|---|
|Device|EG4S20NG88|
|Mode|PROGRAM_FLASH|
|Speed|5 MHz|
|MemorySize|16 Mbits（不是16 MB）|
|File|v116_audio_refill_720p.bit|

本板历史U5是BoyaMicro 25Q16BSTIG。上述依据是v074的同板截图，不是本次自动识别结果；换板或型号不一致必须先确认，不能猜容量。Refresh读到FPGA ID不等于已识别Flash。

## 第三步：写入并校验

1. 稳定供电并确认JTAG连接。写入会覆盖旧开机配置；本次没有Flash备份。如必须保留旧内容，先确认工具及芯片支持Flash Read并做可靠备份，再写入。
2. 文件列表只保留本次目标文件。清除的是工具列表条目，不是删除磁盘上的历史文件。
3. 不改MSEL、OTP、安全/加密、QE或启动地址；不额外点整片Erase Flash。Program Flash按流程执行所需擦写。
4. Mode选PROGRAM_FLASH，Speed 5 MHz，MemorySize 16 Mbits，选上面文件；确认后Run。
5. 等日志明确出现PROGRAM_FLASH success !，保存本次截图/日志。过程中不断电、不拔下载器。
6. 同一文件、同一容量，Mode切VERIFY_FLASH，Run；等VERIFY_FLASH success !，再次保存本次结果。

历史成功截图只用于参考设置，不能作为本次成功证据。

## 第四步：真实冷启动

1. 等工具全部结束再断电。移除可能反供电的下载器/JTAG等连接；不要带电拔TF卡或杜邦线。
2. 屏幕先供电，选HDMI输入；再只给板卡上电。此时不要点Program SRAM，观察能否自动出图。
3. 先确认四图轮播，再进入音频控制，测试两份WAV、UI、暂停/继续、切换；每次音乐至少听30秒，记A3/L6。
4. 建议重复3次并记录出图时间，这是工程建议，非官方条款。反馈后保存新的验收版本，不改冻结归档。

默认启动音源为测试音。长K0约1秒进入/退出音频控制；控制中短K1依次切测试音→MUSIC→ADVOICE→测试音；短K0暂停/继续；长K1显示/隐藏UI。退出音频控制不自动停止当前音乐。
浏览状态短K0下一图，短K1切自动/手动；亮度、对比度、OSD等原功能未改。

## TF资源与失败处理

Flash存FPGA逻辑，四张BMP和MUSIC.WAV/ADVOICE.WAV仍从TF读取；固化不需要重新拷卡。本次先不替换新音乐，避免同时变更两项。
若Flash启动失败但同一bit的SRAM正常，优先保存启动/工具证据并排查非易失启动链，不反复盲擦；若SRAM也异常，先排查供电/屏幕/TF/逻辑，不归咎Flash。
如果出现A3，保留AUD首错信息，不把“文件未损坏”当成“缓存补数必然正常”。历史v072只有老功能，不是当前功能完整的原厂恢复镜像。

## 证据边界

继承v116源哈希匹配的仿真、TD与bit证据；本版未重跑仿真/TD。SWNS+0.612 ns，HWNS+0.021 ns，数值通过不等于可靠性签核。RGB332帧缓存、SDRAM宏重定位、33项异常内部输入延时、SiP/PVT与全地址实物BIST仍开放。

官方手册路径及页码、SHA256保存在同目录《官方手册依据.json》。无需交接ZIP。
''')

    status = dict(
        version=VERSION, release_version='v117', design_version='v116', task_date='2026-10-27',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        type='Flash preparation candidate using unchanged v116 design; no new hardware acceptance',
        target=base['target'], source_version=base['version'], source_frozen=str(BASELINE), work_source=str(ROOT),
        archive_path=str(ARCHIVE), new_rtl=False, new_simulation=False, new_td_build=False, new_bitstream=False,
        source_bound_inherited_checks_passed=False, flash_candidate_prepared=True,
        inherited_simulation_passed=base['simulation_passed'], inherited_regression_cases=base['fresh_regression_cases'],
        inherited_unit_cases=base['fresh_unit_cases'], inherited_td_numerical_check_passed=base['physical_numerical_check_passed'],
        inherited_evidence_scope='v116 records rechecked by SHA256, not rerun or new board results',
        resources_routed=base['resources_routed'], slack_ns=base['slack_ns'], buffering=base['buffering'],
        bitstream_relative=published_bit.relative_to(ROOT).as_posix(), original_bitstream_relative=base['bitstream_relative'],
        bit_bytes=645936, bit_sha256=EXPECTED_BIT,
        archive_bitstream=str(ARCHIVE / '01_project' / published_bit.relative_to(ROOT)),
        program_mode='PROGRAM_FLASH', verify_mode='VERIFY_FLASH', speed_mhz=5, memory_size_mbits=16,
        hardware_download=False, hardware_acceptance=False, program_flash_executed=False,
        verify_flash_executed=False, cold_boot_tested=False, formal_release_approved=False,
        flash_modified=False, tf_files_modified=False, handoff_zip_generated=False,
        actual_long_track_a3_root_cause_closed=False,
        historical_flash_evidence_not_current_result=True,
        historical_flash_backup_available=False, current_flash_content_known=False,
        known_open_items=base['known_open_items'] + [
            'v117 is packaging only; design/on-screen version remains V116.',
            'v116 30-second real-device listening and A3 acceptance must precede Flash use.',
            'v117 Program Flash, Verify Flash and unassisted cold boots have not been performed.'])
    write('VERSION_STATUS.json', status)
    write('README_归档位置.md', f'# v117归档位置\n\n`{ARCHIVE}`\n\n只在D盘工作副本继续开发。冻结归档不改写；测试反馈另存新版本。无需交接ZIP。\n')
    write('README_先看这里.md', f'''# v117：可固化准备版（实际设计V116）

## 结论

同一份v116 bit可用于TD BitWriter Program Flash；本版完成文件、器件、源码/报告绑定和固化步骤整理，**没有代你擦写Flash，没有新实物听音或冷启动通过结论**。
新编号v117表示发布记录，不表示另编了一份设计；屏幕/诊断仍显示V116。原版源码、TB、约束、TD工程/路由数据库、报告和测试证据完整保留。

## 你现在用哪个文件

`{ROOT / '06_flash/01_image' / original_bit.name}`

归档同一文件：
`{ARCHIVE / '01_project/06_flash/01_image' / original_bit.name}`

SHA256：`{EXPECTED_BIT}`；645936字节。

1. 若没测过同一v116 bit，先SRAM连续听音乐30秒，验证暂停/切源/UI/轮播；A3再现就不要固化。
2. 本板确认后：PROGRAM_FLASH / 5 MHz / 16 Mbits / EG4S20NG88；只选上面bit。
3. 成功后同一文件VERIFY_FLASH，再做不依赖SRAM下载的冷启动验收。

完整步骤：`{ROOT / '06_flash/02_guides/固化步骤.md'}`。
测试记录模板：`{ROOT / '07_acceptance/固化与冷启动验收记录.md'}`（初始均未执行）。

## 不需要做什么

不重新配环境或驱动，不改TF卡，不转换.bin，不额外全片擦除，不改MSEL/安全配置，不解压交接包。
Flash保存逻辑，BMP/WAV仍从TF读取。新提取音乐单独在D盘媒体目录，只作可选素材记录，不混入Flash、不默认公开到GitHub。

## 继承的资源与边界

LUT17653/19600（90.07%）、REG10418、BRAM9K58/64、DSP15/29、PLL3/4；SWNS+0.612ns、HWNS+0.021ns，STNS/HTNS0。因设计未变，本版不重跑综合或仿真。
A3实卡闭环、RGB332、宏重定位、33异常内部输入延时、SiP/PVT及全地址实物BIST仍未签核；不能把Flash写入成功当全部功能/可靠性验收。

v074的Program/Verify/冷启动旧图明确标历史，只参考同板设置，不冒充本次证据。
完整归档：`{ARCHIVE}`。所有新增D盘；保留旧版；无需交接ZIP。
''')
    print(json.dumps(dict(prepared=True, work=str(ROOT), design='v116', release='v117', bit_sha256=EXPECTED_BIT, hardware_actions=False), ensure_ascii=False, indent=2))


def finalize_manifest():
    proof = ROOT / '04_evidence/v117_preflight/baseline_checks.json'
    result = load(proof)
    assert result['passed'] and result['baseline_artifacts_checked'] == 2934
    assert result['source_hash_checks'] == 647 and result['unchanged_source_set_entries'] == 131
    assert result['bit_sha256'] == EXPECTED_BIT and result['hardware_actions'] is False
    status = load(ROOT / 'VERSION_STATUS.json')
    status['source_bound_inherited_checks_passed'] = True
    status['preflight_report'] = proof.relative_to(ROOT).as_posix()
    status['preflight_report_sha256'] = sha(proof)
    write('VERSION_STATUS.json', status)
    files = snapshot_files()
    write(MANIFEST.relative_to(ROOT), dict(
        version=VERSION, design_version='v116', files_sha256=files, checked_artifacts=len(files),
        scope='Complete non-cache v117 snapshot including inherited v116 records; source/bit integrity only, not hardware acceptance',
        excluded_directories=sorted(EXCLUDED_DIRS), excluded_suffixes=sorted(EXCLUDED_SUFFIXES)))
    print(json.dumps(dict(finalized=True, manifest_entries=len(files), archive=str(ARCHIVE)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    assert '01_versions' not in ROOT.parts, 'Frozen archives are read-only'
    assert ROOT == Path(r'D:\FPGA_Billboard\work\v117_flash_candidate_20261027')
    assert not ARCHIVE.exists(), 'Do not modify a release source after it is archived'
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest-only', action='store_true')
    args = parser.parse_args()
    finalize_manifest() if args.manifest_only else prepare()
