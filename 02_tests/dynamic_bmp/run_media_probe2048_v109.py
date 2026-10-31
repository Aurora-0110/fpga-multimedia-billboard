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


def color(horizontal, vertical):
    return ((horizontal * 37 + vertical * 13 + 17) & 255,
            (horizontal * 7 + vertical * 53 + horizontal * vertical) & 255,
            (horizontal * 91 + vertical * 19 + 67) & 255)


def interpolate(width, height, top_down):
    result = []
    for output_row in range(OUTPUT_HEIGHT):
        source_row, remainder_y = divmod(output_row * (height - 1), OUTPUT_HEIGHT - 1)
        fraction_y = remainder_y * 256 // (OUTPUT_HEIGHT - 1)
        row_pair = (source_row, min(source_row + 1, height - 1))
        for output_column in range(OUTPUT_WIDTH):
            source_column, remainder_x = divmod(output_column * (width - 1), OUTPUT_WIDTH - 1)
            fraction_x = remainder_x * 256 // (OUTPUT_WIDTH - 1)
            column_pair = (source_column, min(source_column + 1, width - 1))
            corners = [color(column, row if top_down else height - 1 - row)
                       for row in row_pair for column in column_pair]
            weights = ((256 - fraction_x) * (256 - fraction_y), fraction_x * (256 - fraction_y),
                       (256 - fraction_x) * fraction_y, fraction_x * fraction_y)
            channels = [((sum(corners[index][channel] * weights[index] for index in range(4)) + 32768) >> 16)
                        for channel in range(3)]
            result.append((channels[0] << 16) | (channels[1] << 8) | channels[2])
    return result


def fixture(directory, case):
    directory.mkdir(parents=True)
    width, height = case.get('width', 5), case.get('height', 3)
    top_down = case.get('top', False)
    offset, sectors_per_cluster = case.get('offset', 54), case.get('spc', 1)
    stride = (width * 3 + 3) & ~3
    raster_size = stride * height
    file_size = offset + raster_size
    header = bytearray(54)
    struct.pack_into('<2sIHHI', header, 0, b'BM', file_size, 0, 0, offset)
    struct.pack_into('<IiiHHIIiiII', header, 14, 40, width, -height if top_down else height, 1, 24, 0,
                     raster_size, 0, 0, 0, 0)
    for byte_offset, size, value in case.get('patches', []):
        header[byte_offset:byte_offset + size] = (value & ((1 << (size * 8)) - 1)).to_bytes(size, 'little')
    file_bytes = bytearray(header)
    raw_pixels = []
    if case['stage']:
        file_bytes.extend(bytes([0xD7]) * (offset - 54))
        for file_row in range(height):
            logical_row = file_row if top_down else height - 1 - file_row
            for column in range(width):
                red, green, blue = color(column, logical_row)
                file_bytes.extend((blue, green, red))
                raw_pixels.append((red << 16) | (green << 8) | blue)
            file_bytes.extend(bytes((0x91 + file_row + index) & 255 for index in range(stride - width * 3)))
    else:
        file_bytes.extend(bytes(512 - len(file_bytes)))
    boot = bytearray(512)
    boot[0] = 0xEB
    struct.pack_into('<H', boot, 11, 512)
    boot[13] = sectors_per_cluster
    struct.pack_into('<H', boot, 14, 32)
    boot[16] = 2
    struct.pack_into('<I', boot, 32, 1056 + 65525 * sectors_per_cluster)
    struct.pack_into('<I', boot, 36, 512)
    struct.pack_into('<I', boot, 44, 2)
    boot[510:512] = b'\x55\xaa'
    root = bytearray(512)
    root[:11] = b'A       BMP'
    root[11] = 0x20
    struct.pack_into('<H', root, 26, 3)
    struct.pack_into('<I', root, 28, case.get('directory_size', file_size))
    sectors = {0: boot, 1056: root}
    sector_count = (len(file_bytes) + 511) // 512
    cluster_count = (sector_count + sectors_per_cluster - 1) // sectors_per_cluster
    for cluster_index in range(cluster_count):
        cluster = 3 + cluster_index * 137
        next_cluster = cluster + 137 if cluster_index + 1 < cluster_count else 0x0FFFFFFF
        if 'last_link' in case and cluster_index + 1 == cluster_count:
            next_cluster = case['last_link']
        if 'first_link' in case and cluster_index == 0:
            next_cluster = case['first_link']
        fat_lba = 32 + cluster // 128
        if fat_lba not in sectors:
            sectors[fat_lba] = bytearray(512)
        struct.pack_into('<I', sectors[fat_lba], (cluster % 128) * 4, next_cluster)
    for file_sector in range(sector_count):
        cluster_index, within_cluster = divmod(file_sector, sectors_per_cluster)
        cluster = 3 + cluster_index * 137
        logical_lba = 1056 + (cluster - 2) * sectors_per_cluster + within_cluster
        payload = file_bytes[file_sector * 512:(file_sector + 1) * 512]
        sectors[logical_lba] = payload + bytes([0xEC]) * (512 - len(payload))
    assert len(sectors) <= 256
    (directory / 'lbas.hex').write_text(''.join(f'{address:08x}\n' for address in sorted(sectors)), encoding='ascii')
    (directory / 'data.hex').write_text(''.join(f'{byte:02x}\n' for address in sorted(sectors) for byte in sectors[address]), encoding='ascii')
    if case['stage']:
        scaled = interpolate(width, height, top_down)
        (directory / 'raw.hex').write_text(''.join(f'{pixel:06x}\n' for pixel in raw_pixels), encoding='ascii')
        (directory / 'scaled.hex').write_text(''.join(f'{pixel:06x}\n' for pixel in scaled), encoding='ascii')
        indexed = [0] * len(scaled)
        for output_index, pixel in enumerate(scaled):
            file_row, column = divmod(output_index, OUTPUT_WIDTH)
            display_row = file_row if top_down else OUTPUT_HEIGHT - 1 - file_row
            indexed[display_row * OUTPUT_WIDTH + column] = ((pixel >> 16) & 0xE0) | ((pixel >> 11) & 0x1C) | ((pixel >> 6) & 3)
        (directory / 'indexed.hex').write_text(''.join(f'{pixel:02x}\n' for pixel in indexed), encoding='ascii')
    return {
        'blocks': len(sectors), 'width': width, 'height': height, 'stride': stride,
        'crc': zlib.crc32(file_bytes[offset:]) if case['stage'] else 0,
        'fixture_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in directory.iterdir()},
    }


def cases():
    result = []
    valid_headers = [
        ('minimum', 1, 1, False), ('odd_top', 7, 11, True), ('maximum', 2048, 2048, False),
        ('maximum_top', 2048, 2048, True), ('legacy_dimensions', 640, 480, False),
    ]
    for name, width, height, top in valid_headers:
        result.append(dict(name='header_' + name, stage=0, width=width, height=height, top=top))
    invalid_headers = [
        ('signature', [(0, 2, 0)], 0x29), ('bpp16', [(28, 2, 16)], 0x2A),
        ('compressed', [(30, 4, 1)], 0x2A), ('planes', [(26, 2, 2)], 0x2A),
        ('dib_short', [(14, 4, 12)], 0x2A), ('width_zero', [(18, 4, 0)], 0x2B),
        ('width_negative', [(18, 4, 0xFFFFFFFF)], 0x2B), ('width_large', [(18, 4, 2049)], 0x2B),
        ('width_signed_max', [(18, 4, 0x7FFFFFFF)], 0x2B), ('height_zero', [(22, 4, 0)], 0x2B),
        ('height_large', [(22, 4, 2049)], 0x2B), ('height_negative_large', [(22, 4, -2049)], 0x2B),
        ('height_intmin', [(22, 4, 0x80000000)], 0x2B), ('offset_small', [(10, 4, 53)], 0x2C),
        ('offset_large', [(10, 4, 65537)], 0x2C), ('offset_overflow', [(10, 4, 0xFFFFFFF0)], 0x2C),
        ('dib_overlap', [(14, 4, 41)], 0x2C), ('dib_overflow', [(14, 4, 0xFFFFFFFF)], 0x2C),
        ('size_short', [(2, 4, 101)], 0x2C), ('size_large', [(2, 4, 103)], 0x2C),
        ('image_bytes', [(34, 4, 45)], 0x2C),
    ]
    for name, patches, error in invalid_headers:
        result.append(dict(name='header_' + name, stage=0, patches=patches, error=error))
    result.extend([
        dict(name='header_size_zero', stage=0, patches=[(34, 4, 0)]),
        dict(name='header_directory_truncated', stage=0, directory_size=101, error=0x2C),
        dict(name='header_directory_trailer_rejected', stage=0, directory_size=103, error=0x2C),
        dict(name='header_crc_rejected', stage=0, fault=1, error=0x1A),
    ])
    valid_streams = [
        dict(name='pad1', width=1, height=1, drain=1),
        dict(name='pad2', width=2, height=7, top=True),
        dict(name='pad3', width=3, height=5), dict(name='pad0', width=4, height=5, top=True),
        dict(name='row_fragmented', width=13, height=20),
        dict(name='row_top_fragmented', width=13, height=20, top=True),
        dict(name='bgr_cross_sector', width=7, height=11, offset=511),
        dict(name='padding_cross_sector', width=1, height=9, offset=508),
        dict(name='padding_final_sector', width=1, height=9, offset=510, top=True),
        dict(name='multi_sector_cluster', width=17, height=33, spc=2),
        dict(name='maximum_offset', width=2, height=3, offset=65536, spc=128),
        dict(name='unaligned_offset', width=3, height=7, offset=65535, spc=2, top=True),
        dict(name='maximum_width', width=2048, height=3),
        dict(name='maximum_height', width=1, height=2048, top=True),
        dict(name='single_row', width=19, height=1, top=True, retry=1),
        dict(name='image_size_zero', width=5, height=3, patches=[(34, 4, 0)]),
    ]
    invalid_streams = [
        dict(name='payload_crc_first', width=13, height=20, fault=2, error=0x1A),
        dict(name='payload_crc_late', width=13, height=20, fault=2, fail_sector=1, partial=1, error=0x1A),
        dict(name='payload_index', width=13, height=20, fault=3, error=0x33),
        dict(name='payload_timeout', width=13, height=20, fault=4, error=0x35),
        dict(name='premature_eoc', width=13, height=20, first_link=0x0FFFFFFF, partial=1, error=0x36),
        dict(name='free_chain', width=13, height=20, first_link=0, partial=1, error=0x36),
        dict(name='final_overallocated', width=3, height=2, last_link=140, partial=1, error=0x37),
    ]
    for stage in (1, 2):
        for case in valid_streams + invalid_streams:
            entry = dict(case, stage=stage, name=('raw_' if stage == 1 else 'scaled_') + case['name'])
            if stage == 1:
                entry.pop('drain', None)
            result.append(entry)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--filter', default='')
    options = parser.parse_args()
    selected_cases = [case for case in cases() if options.filter in case['name']]
    assert selected_cases
    stamp = time.strftime('%Y%m%d_%H%M%S')
    build = HERE / 'build' / stamp
    evidence = ROOT / '04_evidence' / ('v109_media_probe2048_' + stamp)
    build.mkdir(parents=True)
    evidence.mkdir(parents=True)
    environment = dict(os.environ)
    environment['PATH'] = str(TOOLS) + os.pathsep + environment.get('PATH', '')
    sources = [HERE / 'tb_media_bmp_2048_v109.sv', RTL / 'tf/media_bmp_probe.v', RTL / 'tf/bmp_pixel_stream.v',
               RTL / 'tf/bmp_pixel_packer.v', RTL / 'scale/bmp_scale_bridge.v',
               RTL / 'scale/bilinear_stream_scaler.v', RTL / 'scale/bilinear_rgb888.v']
    source_hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    summary = {'version': 'v109', 'scope': 'Sector-transaction FAT32/BMP -> bilinear -> RGB332 coordinate bursts; NOT real SPI, SDRAM, full720p output, video, timing or hardware acceptance',
               'output_size': [OUTPUT_WIDTH, OUTPUT_HEIGHT], 'requested_cases': len(selected_cases),
               'source_sha256': source_hashes, 'result': 'IN_PROGRESS', 'cases': []}
    start = time.monotonic()
    try:
        for stage in sorted({case['stage'] for case in selected_cases}):
            command = [str(TOOLS / 'iverilog.exe'), '-g2012', '-Wall', '-s', 'tb_dynamic_bmp_chain',
                       f'-Ptb_dynamic_bmp_chain.STAGE={stage}', '-o', str(build / f'stage{stage}.vvp'), *map(str, sources)]
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
