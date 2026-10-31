from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import time

root = Path(__file__).resolve().parents[2]
project = root / '01_project'
here = Path(__file__).resolve().parent
td = Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin')
output = root / '05_td/v086_dynamic_source_synth_attempt1'
assert not output.exists(), 'A synthesis attempt must use a new output directory'
output.mkdir(parents=True)
files = [project / 'rtl' / relative for relative in (
    'tf/spi_byte.v', 'tf/sd_spi_reader.v', 'tf/fat32_bmp_probe.v', 'tf/bmp_pixel_stream.v',
    'tf/tf_bmp_source.v', 'tf/tf_bmp_scaled_source.v', 'tf/bmp_pixel_packer.v',
    'scale/bmp_scale_bridge.v', 'scale/bilinear_stream_scaler.v', 'scale/bilinear_rgb888.v')]
files.append(here / 'dynamic_source_synth_top.v')
gate = output / 'dynamic_source_Runs/syn_1/dynamic_source_gate.db'
area = gate.with_suffix('.area')
body = 'create_project dynamic_source {' + output.as_posix() + '} -family eg4 -device EG4S20NG88 -speed 1\n'
body += ''.join('add_files {' + path.as_posix() + '}\n' for path in files)
body += 'top_module dynamic_source_synth_top\nset_param -run syn_1 gate pack_seq_in_io off\nlaunch_runs syn_1\nwait_run syn_1 300\n'
body += 'if {![file exists {' + gate.as_posix() + '}]} {error "SYNTHESIS_INCOMPLETE"}\n'
body += 'puts "@@@ DYNAMIC_SOURCE_SYNTH_COMPLETE_NOT_SYSTEM_SIGNOFF"\n'
tcl = output / 'invoke.tcl'
tcl.write_text('if {[catch {\n' + body + '} msg opts]} {\n puts "@@@ TASK_ERROR: $msg"\n puts [dict get $opts -errorinfo]\n}\nexit\n', encoding='utf-8')
environment = dict(os.environ)
environment['PATH'] = str(td) + os.pathsep + environment.get('PATH', '')
record = {'scope': 'Independent SPI/FAT32/dynamicBMP/scaler/RGB332 source subsystem, configured1280x720; NOT whole board, place/route, timing, bit or hardware acceptance',
          'source_sha256': {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}}
start = time.monotonic()
with (output / 'run.log').open('wb') as logfile:
    try:
        completed = subprocess.run([str(td / 'run.exe')], input=('source {' + tcl.as_posix() + '}\n').encode(),
                                   cwd=output, env=environment, stdout=logfile, stderr=subprocess.STDOUT, timeout=360)
        record['returncode'] = completed.returncode
    except subprocess.TimeoutExpired:
        record['timeout'] = True
text = (output / 'run.log').read_text(encoding='utf-8', errors='replace')
record.update(elapsed_seconds=round(time.monotonic() - start, 3),
              synth_marker_present='@@@ DYNAMIC_SOURCE_SYNTH_COMPLETE_NOT_SYSTEM_SIGNOFF' in text,
              task_error='@@@ TASK_ERROR:' in text, gate_db_present=gate.is_file(),
              area_present=area.is_file())
if area.is_file():
    statistics = area.read_text(encoding='utf-8', errors='replace')
    record['resources'] = {key: int(re.search(r'^#' + key + r'\s+(\d+)', statistics, re.M).group(1))
                           for key in ('lut', 'reg', 'bram', 'bram32k', 'dsp', 'pll', 'gclk', 'pad')}
    capacities = {'lut': 19600, 'reg': 19600, 'bram': 64, 'bram32k': 16, 'dsp': 29, 'pll': 4, 'gclk': 16, 'pad': 66}
    record['within_capacities'] = all(record['resources'][key] <= capacity for key, capacity in capacities.items())
record['completed'] = bool(record['synth_marker_present'] and record['gate_db_present'] and record['area_present'] and not record['task_error'] and not record.get('timeout'))
(output / 'attempt.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record, indent=2), flush=True)
raise SystemExit(0 if record['completed'] and record.get('within_capacities') else 2)
