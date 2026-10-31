"""Reuse the reviewed routed database for a guarded SRAM-only diagnostic bit.

Does NOT download, change Flash, or declare physical/PVT acceptance.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess, time

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--attempt', type=int, default=1)
args = parser.parse_args()
reports = {
    'pair_units': '04_evidence/v087_pair_units_20261025_110422/summary.json',
    'pair_memory': '04_evidence/v087_pair_memory_20261025_110438/summary.json',
    'full_scaler': '04_evidence/v087_full_scaler_20261025_110215/summary.json',
    'scaled_spi_memory': '04_evidence/v087_scaled_spi_memory_20261025_110708/summary.json',
    'pair_top': '04_evidence/v087_pair_top_20261025_111742/summary.json',
}
for name, relative in reports.items():
    data = json.loads((root / relative).read_text(encoding='utf-8'))
    assert data.get('result') == 'PASS' or data.get('passed') is True, name
    assert all(c.get('passed') is True for c in data.get('cases', data.get('tests', []))), name
synth = root / '05_td/v087_scaled_system_synth_attempt2'
syn = json.loads((synth / 'attempt.json').read_text(encoding='utf-8'))
assert syn['completed'] and syn['within_capacities']
for relative, expected in syn['source_sha256'].items():
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, relative
gate = synth / 'build/idx_video_Runs/syn_1'
phy = root / '05_td/v087_scaled_system_physical_attempt1'
physical = phy / 'physical'
pr = json.loads((phy / 'attempt.json').read_text(encoding='utf-8'))
assert pr['completed'] and pr['nonnegative_slack'] and not pr['diagnostic_bit_generated']
text = (physical / 'sdram_check.rpt').read_text(encoding='utf-8')
counts = {m.group(1): int(m.group(2)) for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)', text, re.M)}
for name in ('no clock', 'clock definition', 'invalid constraint', 'pll/clock buffer clock constraints',
             'combinational loops', 'no path constraints', 'shadowed/ignored timing exception constraints'):
    assert counts[name] == 0, (name, counts[name])

out = root / f'05_td/v087_scaled_system_bitgen_attempt{args.attempt}'
assert not out.exists(), 'Never overwrite bit generation evidence'
out.mkdir(parents=True)
db = physical / 'sdram_pr.db'
record = {'scope': 'Diagnostic SRAM bit from reviewed v087 routed database; NOT formal signoff/hardware/Flash',
    'reviewed_reports': reports, 'check_timing_counts': counts,
    'routed_db_sha256': hashlib.sha256(db.read_bytes()).hexdigest(),
    'known_open_review': ['PHY-7002 native macro relocation', 'dummy node review',
        '32 native DQ delay annotations and SPI input budget flagged abnormal',
        'button/LED/HDMI external IO budgets', 'SiP/PVT/full-address physical BIST',
        'new scaled board design not physically tested'],
    'formal_release_approved': False, 'hardware_test': False, 'flash_modified': False}
script = out / 'invoke.tcl'
script.write_text('if {[catch {\n'
    'import_device eagle_s20.db -package EG4S20NG88\n'
    'cd {' + gate.as_posix() + '}\nopen_project idx_video.prj -noanalyze\n'
    'import_db {' + db.as_posix() + '}\ncd {' + out.as_posix() + '}\n'
    'update_timing -mode final\nreport_timing_status -file bit_source.ts\n'
    'set f [open bit_source.ts r]\nset ts [read $f]\nclose $f\nputs $ts\n'
    'foreach metric {SWNS STNS HWNS HTNS} {\n'
    ' if {![regexp "$metric: *(-?\\\\d+\\\\.\\\\d+)ns" $ts ignored value]} {error "Missing timing metric $metric"}\n'
    ' if {$value < 0} {error "Negative timing metric $metric"}\n}\n'
    'commit_param -step bitgen\nbitgen -bit v087_bilinear_full720p.bit\n'
    'export_bitgen_param -file diagnostic_bitgen_param.f\n'
    'puts "@@@ V087_ROUTED_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE"\n'
    '} msg opts]} {puts "@@@ TASK_ERROR: $msg"; puts [dict get $opts -errorinfo]}\nexit\n', encoding='utf-8')
td = Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin')
env = dict(os.environ)
env['PATH'] = str(td) + os.pathsep + env.get('PATH', '')
start = time.monotonic()
with (out / 'run.log').open('wb') as log:
    try:
        c = subprocess.run([str(td / 'run.exe')], input=('source {' + script.as_posix() + '}\n').encode(),
             cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        record['returncode'] = c.returncode
    except subprocess.TimeoutExpired:
        record['timeout'] = True
text = (out / 'run.log').read_text(encoding='utf-8', errors='replace')
bit = out / 'v087_bilinear_full720p.bit'
record.update(elapsed_seconds=round(time.monotonic() - start, 3), task_error='@@@ TASK_ERROR:' in text,
    marker_present='@@@ V087_ROUTED_DIAGNOSTIC_BIT_GENERATED_NOT_HARDWARE_ACCEPTANCE' in text,
    nonempty_bit=bit.is_file() and bit.stat().st_size > 0)
record['completed'] = record.get('returncode') == 0 and not record['task_error'] and record['marker_present'] and record['nonempty_bit']
if record['completed']:
    target = root / '03_bitstreams' / bit.name
    assert not target.exists(), 'Never overwrite published bit'
    shutil.copy2(bit, target)
    record.update(bit_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), published_path=str(target))
(out / 'attempt.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record, indent=2), flush=True)
print(out, flush=True)
raise SystemExit(0 if record['completed'] else 1)
