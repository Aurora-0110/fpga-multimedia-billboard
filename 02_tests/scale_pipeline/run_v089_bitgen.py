"""Generate v089 SRAM test bit only after hash-bound simulation and STA guards.

Does not download, erase/write Flash, alter TF media, or grant formal signoff.
Old v087 bitgen runner is historical and must NOT be used for v089.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--attempt', type=int, default=1)
parser.add_argument('--synth-attempt', type=int, default=1)
parser.add_argument('--physical-attempt', type=int, default=1)
args = parser.parse_args()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def checked_hashes(data):
    checked = 0
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'source_sha256':
                for relative, expected in value.items():
                    path = root / relative
                    require(path.is_file() and sha(path) == expected,
                            'Evidence source mismatch: ' + relative)
                    checked += 1
            elif isinstance(value, (dict, list)):
                checked += checked_hashes(value)
    elif isinstance(data, list):
        checked += sum(checked_hashes(item) for item in data)
    return checked


reports = {}
patterns = {
    'new_osd_and_controls': ('v089_osd_controls_*', False),
    'actual_candidate_top': ('v089_pair_top_*', False),
    'fault_banner_modes': ('v089_diagnostics_*', False),
    'legacy_regression_fresh_this_version': ('v081_units_20261025_142656', False),
    'scaled_spi_and_memory_32x18_fresh': ('v089_scaled_spi_memory_*', False),
    'paired_reader_display_units_unchanged': ('v088_pair_units_20261025_141222', True),
    'paired_memory_bus_model_unchanged': ('v088_pair_memory_20261025_140904', True),
    'full720p_interpolation_unchanged': ('v087_full_scaler_20261025_110215', True),
}
for name, (pattern, inherited) in patterns.items():
    paths = sorted((root / '04_evidence').glob(pattern + '/summary.json'))
    require(bool(paths), 'Missing evidence: ' + pattern)
    path = paths[-1]  # never silently fall back past a newer failed attempt
    data = json.loads(path.read_text(encoding='utf-8'))
    require(data.get('passed') is True or data.get('result') == 'PASS',
            'Report not PASS: ' + str(path))
    cases = data.get('tests', data.get('cases', []))
    require(all(case.get('passed') is True for case in cases), 'Failed test: ' + name)
    hashes = checked_hashes(data)
    require(hashes > 0, 'Unbound test evidence: ' + name)
    reports[name] = {'path': path.relative_to(root).as_posix(), 'sha256': sha(path),
                     'inherited_not_rerun': inherited, 'matching_source_hash_entries': hashes,
                     'scope': data.get('scope', 'See report and test logs')}

synth = root / f'05_td/v089_scaled_system_synth_attempt{args.synth_attempt}'
syn = json.loads((synth / 'attempt.json').read_text(encoding='utf-8'))
require(syn['completed'] and syn['within_capacities'], 'Synthesis/capacity guard failed')
require(checked_hashes(syn) > 0, 'Missing synthesis source binding')
gate = synth / 'build/idx_video_Runs/syn_1'
if not gate.exists():
    gate = synth / 'native_project_record/idx_video_Runs/syn_1'
phy = root / f'05_td/v089_scaled_system_physical_attempt{args.physical_attempt}'
physical = phy / 'physical'
pr = json.loads((phy / 'attempt.json').read_text(encoding='utf-8'))
require(pr['completed'] and pr['nonnegative_slack'], 'Physical timing guard failed')
require(not pr['diagnostic_bit_generated'], 'Use the separate guarded bitgen stage')
require(pr['synth_gate_sha256'] == sha(gate / 'idx_video_gate.db'), 'Gate database changed')
require(pr['physical_script_sha256'] == sha(root / '01_project/build_scaled_physical_check.tcl'),
        'Physical implementation script changed')
require(min(pr['slack_ns'].values()) >= 0 and len(pr['slack_ns']) == 4, 'Missing/negative STA metrics')
text = (physical / 'sdram_check.rpt').read_text(encoding='utf-8')
counts = {m.group(1): int(m.group(2)) for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)', text, re.M)}
for name in ('no clock', 'clock definition', 'invalid constraint', 'pll/clock buffer clock constraints',
             'combinational loops', 'no path constraints', 'shadowed/ignored timing exception constraints'):
    require(name in counts and counts[name] == 0, 'check_timing guard failed: ' + name)

out = root / f'05_td/v089_scaled_system_bitgen_attempt{args.attempt}'
require(not out.exists(), 'Never overwrite bitgen evidence; choose another attempt')
bitname = 'v089_full720_osd_toggle.bit'
target = root / '03_bitstreams' / bitname
require(not target.exists(), 'Never overwrite an existing published bitstream')
out.mkdir(parents=True)
db = physical / 'sdram_pr.db'
record = {
    'scope': 'v089 full720p OSD + chord toggle SRAM diagnostic bit; NOT physical acceptance/signoff',
    'reviewed_reports': reports, 'check_timing_counts': counts,
    'synthesis_report_sha256': sha(synth / 'attempt.json'),
    'physical_report_sha256': sha(phy / 'attempt.json'),
    'synth_gate_sha256': sha(gate / 'idx_video_gate.db'), 'routed_db_sha256': sha(db),
    'slack_ns': pr['slack_ns'],
    'known_open_review': [
        'v087 board pictures flash/disappear; root cause NOT confirmed or fixed by this OSD change',
        'PHY-7002 native SDRAM macro relocation; dummy-node review',
        '32 native DQ delay annotations plus SPI input budget flagged abnormal (33 entries)',
        'button/LED/HDMI external IO budgets; SiP/PVT/full-address physical BIST',
        'No seconds-long full720p TF-to-HDMI end-to-end regression or v089 board acceptance'],
    'formal_release_approved': False, 'hardware_test': False, 'flash_modified': False,
}
script = out / 'invoke.tcl'
script.write_text('if {[catch {\n'
    'import_device eagle_s20.db -package EG4S20NG88\n'
    'cd {' + gate.as_posix() + '}\nopen_project idx_video.prj -noanalyze\n'
    'import_db {' + db.as_posix() + '}\ncd {' + out.as_posix() + '}\n'
    'update_timing -mode final\nreport_timing_status -file bit_source.ts\n'
    'set f [open bit_source.ts r]\nset ts [read $f]\nclose $f\nputs $ts\n'
    'foreach metric {SWNS STNS HWNS HTNS} {\n'
    ' if {![regexp [format {%s: *(-?[0-9]+[.][0-9]+)ns} $metric] $ts ignored value]} {error "Missing metric $metric"}\n'
    ' if {$value < 0} {error "Negative timing metric $metric"}\n}\n'
    'check_timing -file bit_source.check -verbose\n'
    'commit_param -step bitgen\nbitgen -bit ' + bitname + '\n'
    'export_bitgen_param -file diagnostic_bitgen_param.f\n'
    'puts "@@@ V089_OSD_SRAM_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE"\n'
    '} msg opts]} {puts "@@@ TASK_ERROR: $msg"; puts [dict get $opts -errorinfo]}\nexit\n', encoding='utf-8')
record['invoke_tcl_sha256'] = sha(script)
td = Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin')
env = dict(os.environ)
env['PATH'] = str(td) + os.pathsep + env.get('PATH', '')
start = time.monotonic()
with (out / 'run.log').open('wb') as log:
    try:
        result = subprocess.run([str(td / 'run.exe')], input=('source {' + script.as_posix() + '}\n').encode(),
            cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        record['returncode'] = result.returncode
    except subprocess.TimeoutExpired:
        record['timeout'] = True
text = (out / 'run.log').read_text(encoding='utf-8', errors='replace')
bit = out / bitname
newcheck = out / 'bit_source.check'
newcounts = {m.group(1): int(m.group(2)) for m in
             re.finditer(r'^\d+\. checking (.*?)\((\d+)\)', newcheck.read_text(encoding='utf-8'), re.M)} if newcheck.is_file() else {}
record.update(elapsed_seconds=round(time.monotonic() - start, 3), task_error='@@@ TASK_ERROR:' in text,
    marker_present='@@@ V089_OSD_SRAM_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE' in text,
    nonempty_bit=bit.is_file() and bit.stat().st_size > 0,
    reloaded_timing_check_matches=newcounts == counts)
record['completed'] = bool(record.get('returncode') == 0 and not record['task_error'] and
    record['marker_present'] and record['nonempty_bit'] and record['reloaded_timing_check_matches'])
if record['completed']:
    require(sha(db) == record['routed_db_sha256'], 'Routed database changed during bitgen')
    checked_hashes(syn)
    shutil.copy2(bit, target)
    record.update(bit_sha256=sha(target), bit_bytes=target.stat().st_size, published_path=str(target))
(out / 'attempt.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record, indent=2), flush=True)
print(out, flush=True)
raise SystemExit(0 if record['completed'] else 1)
