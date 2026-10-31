from pathlib import Path
import argparse
import hashlib
import json
import os
import struct
import subprocess
import time
import zlib

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RTL = ROOT / '01_project/rtl'
TOOLS = Path(os.environ.get('IVERILOG_BIN', r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'))
OUTPUT_WIDTH, OUTPUT_HEIGHT = 32, 18


from multires_reference import fixture


def cases():
 result=[]
 for name,w,h,td in [('maximum',2048,2048,False),('maximum_top',2048,2048,True),('minimum',1,1,False)]:
  result.append(dict(name='header_'+name,stage=0,width=w,height=h,top=td))
 for name,patch in [('width2049',(18,4,2049)),('height2049',(22,4,2049)),('negative_height2049',(22,4,-2049)),('widthzero',(18,4,0)),('negative_width',(18,4,-1)),('heightzero',(22,4,0)),('height_intmin',(22,4,0x80000000))]:
  result.append(dict(name='header_reject_'+name,stage=0,patches=[patch],error=0x2b))
 streams=[dict(name='max_width_bottom',width=2048,height=3,retry=1),dict(name='odd_width_top',width=2047,height=3,top=True),dict(name='max_height_bottom',width=1,height=2048),dict(name='max_height_top',width=1,height=2048,top=True),dict(name='offset511_top',width=7,height=11,offset=511,top=True),dict(name='single_pixel_drain',width=1,height=1,drain=1),dict(name='late_crc',width=13,height=20,fault=2,fail_sector=1,partial=1,error=0x1a),dict(name='bad_index',width=13,height=20,fault=3,error=0x33),dict(name='timeout',width=13,height=20,fault=4,error=0x35)]
 for stage in (1,2):
  for c in streams:
   z=dict(c,stage=stage,name=f'stage{stage}_'+c['name'])
   if stage==1:z.pop('drain',None)
   result.append(z)
 return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--filter', default='')
    options = parser.parse_args()
    selected_cases = [case for case in cases() if options.filter in case['name']]
    assert selected_cases
    stamp = time.strftime('%Y%m%d_%H%M%S')
    build = HERE / 'build' / stamp
    evidence = ROOT / '04_evidence' / ('v101_multires_chain_' + stamp)
    build.mkdir(parents=True)
    evidence.mkdir(parents=True)
    environment = dict(os.environ)
    environment['PATH'] = str(TOOLS) + os.pathsep + environment.get('PATH', '')
    sources = [HERE / 'tb_v101_multires_chain.sv', RTL / 'tf/fat32_bmp_probe.v', RTL / 'tf/bmp_pixel_stream.v',
               RTL / 'tf/bmp_pixel_packer.v', RTL / 'scale/bmp_scale_bridge.v',
               RTL / 'scale/bilinear_stream_scaler.v', RTL / 'scale/bilinear_rgb888.v']
    sources_for_hashes = sources + [HERE/'multires_reference.py', Path(__file__), ROOT/'02_tests/dynamic_bmp/run_dynamic_tests.py']
    source_hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources_for_hashes}
    summary = {'version': 'v101', 'scope': 'Sector-transaction FAT32/BMP -> bilinear -> RGB332 coordinate bursts; NOT real SPI, SDRAM, full720p output, video, timing or hardware acceptance',
               'output_size': [OUTPUT_WIDTH, OUTPUT_HEIGHT], 'requested_cases': len(selected_cases),
               'source_sha256': source_hashes, 'result': 'IN_PROGRESS', 'cases': []}
    start = time.monotonic()
    try:
        for stage in sorted({case['stage'] for case in selected_cases}):
            command = [str(TOOLS / 'iverilog.exe'), '-g2012', '-Wall', '-s', 'tb_v101_multires_chain',
                       f'-Ptb_v101_multires_chain.STAGE={stage}', '-o', str(build / f'stage{stage}.vvp'), *map(str, sources)]
            completed = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=45)
            (evidence / f'compile_stage{stage}.log').write_text(completed.stdout + completed.stderr, encoding='utf-8')
            assert completed.returncode == 0, completed.stdout + completed.stderr
        for case in selected_cases:
            directory = build / case['name']
            generated = fixture(directory, case)
            arguments = {'BLOCKS': generated['blocks'], 'WIDTH': generated['width'], 'HEIGHT': generated['height'],
                         'STRIDE': generated['stride'], 'TOP': int(case.get('top', False)), 'ERROR': case.get('error', 0),
                         'FAULT': case.get('fault', 0), 'FAIL_SECTOR': case.get('fail_sector', 0),
                         'RETRY': case.get('retry', 0), 'PARTIAL': case.get('partial', 0), 'DRAIN': case.get('drain', 0)}
            command = [str(TOOLS / 'vvp.exe'), str(build / f'stage{case["stage"]}.vvp'), '+FIXTURE=' + directory.as_posix(),
                       f'+CRC={generated["crc"]:08x}', *[f'+{key}={value}' for key, value in arguments.items()]]
            completed = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=90)
            log = completed.stdout + completed.stderr
            passed = completed.returncode == 0 and 'PASS dynamic' in log and not any(word in log for word in ('FATAL', 'ERROR'))
            record = {'case': case, 'fixture': generated, 'command': command, 'returncode': completed.returncode, 'passed': passed,
                      'result_lines': [line for line in log.splitlines() if line.startswith(('PASS', 'FATAL', 'ERROR'))]}
            summary['cases'].append(record)
            (evidence / (case['name'] + '.log')).write_text(log, encoding='utf-8')
            (evidence / (case['name'] + '.json')).write_text(json.dumps(record, indent=2), encoding='utf-8')
            print(case['name'], passed, '; '.join(record['result_lines']), flush=True)
            assert passed, log
        summary['result'] = 'PASS'
    except Exception as error:
        summary['result'] = 'FAIL'
        summary['exception'] = repr(error)
        raise
    finally:
        summary['completed_cases'] = len(summary['cases'])
        summary['elapsed_seconds'] = round(time.monotonic() - start, 3)
        (evidence / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print(evidence, flush=True)


if __name__ == '__main__':
    main()
