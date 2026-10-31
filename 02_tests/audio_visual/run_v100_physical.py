"""Implement an already synthesized v100 candidate; no programming or Flash.

By default, only place/route/reports. --bit opts into guarded diagnostic bitgen
after the same fresh implementation meets the script's setup/hold guard.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, time

root = Path(__file__).resolve().parents[2]
project = root / '01_project'
parser = argparse.ArgumentParser()
parser.add_argument('--synth-attempt', type=int, default=1)
parser.add_argument('--attempt', type=int, default=1)
parser.add_argument('--bit', action='store_true')
args = parser.parse_args()
synth = root / f'05_td/v100_audio_visual_synth_attempt{args.synth_attempt}'
gate = synth / 'build/idx_video_Runs/syn_1'
assert json.loads((synth / 'attempt.json').read_text(encoding='utf-8'))['completed']
out = root / f'05_td/v100_audio_visual_physical_attempt{args.attempt}'
assert not out.exists(), 'Never overwrite implementation evidence'
out.mkdir(parents=True)
physical = out / 'physical'
td = Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin')
env = dict(os.environ)
env['PATH'] = str(td) + os.pathsep + env.get('PATH', '')
temp_dir=root/'00_tmp';temp_dir.mkdir(exist_ok=True)
env.update(TEMP=str(temp_dir),TMP=str(temp_dir),TMPDIR=str(temp_dir),PYTHONDONTWRITEBYTECODE='1')
env.update(ADB_ROOT=project.as_posix(), ADB_GATE_DIR=gate.as_posix(),
           ADB_PHY_OUT=physical.as_posix())
script = project / 'build_audio_visual_physical_check.tcl'
record = {'scope': 'Actual idx_audio_visual_top place/route/STA; diagnostic bit opt-in; NO download/hardware/Flash',
          'synthesis_attempt': str(synth), 'diagnostic_bit_requested': args.bit,
          'synth_gate_sha256': hashlib.sha256((gate / 'idx_video_gate.db').read_bytes()).hexdigest(),
          'physical_script_sha256': hashlib.sha256(script.read_bytes()).hexdigest()}
wrapper = out / 'invoke.tcl'
wrapper.write_text('set ::ADB_DIAGNOSTIC_BIT ' + ('1' if args.bit else '0') + '\n'
    'if {[catch {source {' + script.as_posix() + '}} msg opts]} {\n'
    ' puts "@@@ TASK_ERROR: $msg"\n puts [dict get $opts -errorinfo]\n}\nexit\n', encoding='utf-8')
start = time.monotonic()
with (out / 'run.log').open('wb') as log:
    try:
        result = subprocess.run([str(td / 'run.exe')], input=('source {' + wrapper.as_posix() + '}\n').encode(),
             cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=900)
        record['returncode'] = result.returncode
    except subprocess.TimeoutExpired:
        record['timeout'] = True
text = (out / 'run.log').read_text(encoding='utf-8', errors='replace')
record.update(elapsed_seconds=round(time.monotonic() - start, 3), task_error='@@@ TASK_ERROR:' in text)
ts = physical / 'sdram_phy.ts'
record['timing_reports_present'] = all((physical / name).is_file() for name in
    ['sdram_phy.ts', 'sdram_pr.timing', 'sdram_check.rpt', 'sdram_netlist.pnl', 'sdram_pr.db'])
if ts.is_file():
    data = ts.read_text(encoding='utf-8', errors='replace')
    record['slack_ns'] = {name: float(m.group(1)) for name in ('SWNS', 'STNS', 'HWNS', 'HTNS')
                         if (m := re.search(name + r':\s*(-?[\d.]+)', data))}
    record['nonnegative_slack'] = len(record['slack_ns']) == 4 and min(record['slack_ns'].values()) >= 0
record['warning_lines'] = sorted(set(line.strip() for line in text.splitlines()
    if 'CRITICAL-WARNING' in line or re.search(r'\bERROR:', line)))
bit = physical / 'v100_audio_spectrum_720p.bit'
record['diagnostic_bit_generated'] = bit.is_file() and bit.stat().st_size > 0
record['route_errors_present'] = bool(re.search(r'\bERROR:', text))
record['completed'] = bool(not record['route_errors_present'] and record.get('returncode') == 0 and not record['task_error'] and
    record['timing_reports_present'] and record.get('nonnegative_slack') and
    (not args.bit or record['diagnostic_bit_generated']))
(out / 'attempt.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record, indent=2), flush=True)
print(out, flush=True)
raise SystemExit(0 if record['completed'] else 1)
