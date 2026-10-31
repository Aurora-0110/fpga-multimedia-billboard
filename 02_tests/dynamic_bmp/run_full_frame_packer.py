from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

root = Path(__file__).resolve().parents[2]
here = Path(__file__).resolve().parent
tools = Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
stamp = time.strftime('%Y%m%d_%H%M%S')
build = here / 'build' / ('packer_' + stamp)
evidence = root / '04_evidence' / ('v086_full_packer_' + stamp)
build.mkdir(parents=True)
evidence.mkdir(parents=True)
environment = dict(os.environ)
environment['PATH'] = str(tools) + os.pathsep + environment.get('PATH', '')
sources = [here / 'tb_full_frame_packer.sv', root / '01_project/rtl/tf/bmp_pixel_packer.v']
summary = {'result': 'IN_PROGRESS', 'scope': 'Full1280x720 coordinate-to-RGB332-burst packer ONLY with synthetic pixels; NOT bilinear full-frame simulation, SDRAM, reader or video acceptance',
           'source_sha256': {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}, 'cases': []}
try:
    for size, width, height in [('full', 1280, 720), ('small', 32, 18)]:
        command = [str(tools / 'iverilog.exe'), '-g2012', '-Wall', '-s', 'tb_full_frame_packer',
                   f'-Ptb_full_frame_packer.WIDTH={width}', f'-Ptb_full_frame_packer.HEIGHT={height}',
                   '-o', str(build / (size + '.vvp')), *map(str, sources)]
        completed = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=30)
        (evidence / (size + '_compile.log')).write_text(completed.stdout + completed.stderr, encoding='utf-8')
        assert completed.returncode == 0, completed.stderr
        modes = [(0, 0), (1, 0)] if size == 'full' else [(0, 1), (0, 2)]
        for top, mode in modes:
            command = [str(tools / 'vvp.exe'), str(build / (size + '.vvp')), f'+TOP={top}', f'+MODE={mode}']
            completed = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=120)
            log = completed.stdout + completed.stderr
            passed = completed.returncode == 0 and 'PASS packer' in log and not any(word in log for word in ('FATAL', 'ERROR'))
            (evidence / f'{size}_{top}_{mode}.log').write_text(log, encoding='utf-8')
            summary['cases'].append({'size': [width, height], 'top': top, 'mode': mode, 'passed': passed, 'log': log})
            print(log.strip(), flush=True)
            assert passed, log
    summary['result'] = 'PASS'
finally:
    (evidence / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(evidence, flush=True)
