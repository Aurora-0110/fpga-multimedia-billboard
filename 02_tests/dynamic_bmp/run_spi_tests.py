from pathlib import Path
import hashlib
import json
import os
import subprocess
import time
from run_dynamic_tests import fixture, ROOT, HERE, RTL, TOOLS

stamp = time.strftime('%Y%m%d_%H%M%S')
build = HERE / 'build' / ('spi_' + stamp)
evidence = ROOT / '04_evidence' / ('v086_actual_spi_' + stamp)
build.mkdir(parents=True)
evidence.mkdir(parents=True)
environment = dict(os.environ)
environment['PATH'] = str(TOOLS) + os.pathsep + environment.get('PATH', '')
sources = [HERE / 'tb_dynamic_bmp_spi.sv', ROOT / '02_tests/legacy_tf/sd_fat_card_model.v',
           *[RTL / relative for relative in (
               'tf/spi_byte.v', 'tf/sd_spi_reader.v', 'tf/fat32_bmp_probe.v', 'tf/bmp_pixel_stream.v',
               'tf/tf_bmp_source.v', 'tf/tf_bmp_scaled_source.v', 'tf/bmp_pixel_packer.v',
               'scale/bmp_scale_bridge.v', 'scale/bilinear_stream_scaler.v', 'scale/bilinear_rgb888.v')]]
command = [str(TOOLS / 'iverilog.exe'), '-g2012', '-Wall', '-s', 'tb_dynamic_bmp_spi', '-o', str(build / 'test.vvp'), *map(str, sources)]
completed = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=45)
(evidence / 'compile.log').write_text(completed.stdout + completed.stderr, encoding='utf-8')
assert completed.returncode == 0, completed.stdout + completed.stderr
cases = [
    dict(name='bottomup_fragmented', width=13, height=20, retry=1),
    dict(name='topdown_fragmented', width=13, height=20, top=True),
    dict(name='padding_sector_boundary', width=1, height=9, offset=510, sdsc=1),
    dict(name='header_crc', width=13, height=20, crc_read=3, error=0x1A),
    dict(name='first_payload_crc', width=13, height=20, crc_read=4, error=0x1A),
    dict(name='late_payload_crc', width=13, height=20, crc_read=6, error=0x1A),
    dict(name='final_fat_cycle', width=3, height=2, last_link=3, error=0x37),
]
summary = {'version': 'v086', 'result': 'IN_PROGRESS', 'cases': [], 'requested_cases': len(cases),
           'scope': 'Real synthesizable SPI host -> behavioral SD card -> FAT32 dynamic BMP -> bilinear -> coordinate RGB332 bursts at32x18; NOT real hardware, SDRAM, HDMI or full720p',
           'source_sha256': {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}}
try:
    for case in cases:
        case['stage'] = 2
        directory = build / case['name']
        generated = fixture(directory, case)
        assert generated['blocks'] <= 16
        arguments = {'BLOCKS': generated['blocks'], 'WIDTH': generated['width'], 'HEIGHT': generated['height'],
                     'STRIDE': generated['stride'], 'TOP': int(case.get('top', False)), 'ERROR': case.get('error', 0),
                     'SDSC': case.get('sdsc', 0), 'CRC_READ': case.get('crc_read', 0), 'RETRY': case.get('retry', 0)}
        command = [str(TOOLS / 'vvp.exe'), str(build / 'test.vvp'), '+FIXTURE=' + directory.as_posix(),
                   f'+CRC={generated["crc"]:08x}', *[f'+{name}={value}' for name, value in arguments.items()]]
        completed = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=90)
        log = completed.stdout + completed.stderr
        passed = completed.returncode == 0 and 'PASS dynamic actual_SPI' in log and not any(word in log for word in ('FATAL', 'ERROR'))
        record = {'case': case, 'fixture': generated, 'command': command, 'passed': passed,
                  'result_lines': [line for line in log.splitlines() if line.startswith(('PASS', 'FATAL', 'ERROR'))]}
        summary['cases'].append(record)
        (evidence / (case['name'] + '.log')).write_text(log, encoding='utf-8')
        print(case['name'], passed, record['result_lines'], flush=True)
        assert passed, log
    summary['result'] = 'PASS'
finally:
    summary['completed_cases'] = len(summary['cases'])
    (evidence / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(evidence, flush=True)
