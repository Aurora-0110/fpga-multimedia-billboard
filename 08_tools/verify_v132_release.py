"""Read-only V132 release audit. Safe in a frozen archive; no tools or hardware started."""
from pathlib import Path, PurePosixPath
import ast
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'v132_ui_rom_compact_20261031'
BASELINE = 'v130_av_layer_ui_20261030'
SOURCE_SUFFIXES = {'.v', '.vh', '.tcl', '.adc', '.sdc', '.al', '.prj'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def local_path(relative):
    rel = PurePosixPath(relative)
    require(not rel.is_absolute() and '..' not in rel.parts and
            all(':' not in part and '\\' not in part for part in rel.parts),
            'Unsafe release-relative path: ' + relative)
    path = ROOT.joinpath(*rel.parts)
    require(path.resolve().is_relative_to(ROOT.resolve()), 'Path escapes release: ' + relative)
    return path


def evidence_path(recorded):
    """Prefer this release's preserved evidence, not the original working directory."""
    text = str(recorded).replace('\\', '/')
    if re.match(r'^[A-Za-z]:/', text):
        marker = '/04_evidence/'
        require(marker in text, 'Unexpected absolute evidence path: ' + text)
        text = '04_evidence/' + text.split(marker, 1)[1]
    path = local_path(text)
    require(path.is_file(), 'Missing preserved evidence: ' + text)
    return path


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def check_fingerprints(obj):
    count = 0
    if isinstance(obj, dict):
        for key, value in obj.items():
            if (key in ('source_sha256', 'sources') and isinstance(value, dict) and value
                    and all(isinstance(h, str) and re.fullmatch('[0-9a-f]{64}', h)
                            for h in value.values())):
                for relative, expected in value.items():
                    path = local_path(relative.replace('\\', '/'))
                    require(path.is_file() and digest(path) == expected,
                            'Evidence source mismatch: ' + relative)
                    count += 1
            elif isinstance(value, (dict, list)):
                count += check_fingerprints(value)
    elif isinstance(obj, list):
        for item in obj:
            count += check_fingerprints(item)
    return count


def passing_summary(path):
    obj = read_json(path)
    require(obj.get('passed') is True and obj.get('complete', True) is True,
            'Incomplete/failed evidence: ' + str(path))
    return obj


def resources(path):
    text = path.read_text(encoding='utf8')
    result = {}
    for name in ('lut', 'reg', 'bram', 'bram32k', 'dsp', 'pll', 'gclk', 'pad'):
        match = re.search(r'^#' + name + r'\s+(\d+)', text, re.M)
        require(match is not None, 'Missing resource ' + name + ': ' + str(path))
        result[name] = int(match.group(1))
    return result


def main():
    manifest = read_json(ROOT / 'V132_RELEASE_MANIFEST.json')
    status = read_json(ROOT / 'VERSION_STATUS.json')
    require(manifest['version'] == status['version'] == VERSION, 'Wrong release ID')
    require(manifest['baseline'] == status['baseline'] == BASELINE, 'Wrong baseline')
    require(status['target_device'] == 'EG4S20NG88' and status['input_clock_mhz'] == 24,
            'Wrong hardware target')
    for name in ('hardware_downloaded', 'hardware_accepted', 'flash_modified', 'tf_modified',
                 'network_settings_changed', 'automatic_disconnect_scheduled', 'formal_release_approved'):
        require(status[name] is False, 'Unjustified hardware/environment acceptance: ' + name)
    require(status['sram_test_pending'] is True, 'Hardware retest status missing')
    require(manifest['hardware_accepted'] is False and
            manifest['formal_release_approved'] is False, 'Invalid manifest acceptance')
    require(status['feature_set_unchanged'] is True and
            status['ui_pixel_and_control_latency_unchanged'] is True and
            status['supports_show_bin'] is False and
            status['new_external_configs_required'] is False, 'Scope changed')

    for relative, entry in manifest['files'].items():
        path = local_path(relative)
        require(path.is_file() and path.stat().st_size == entry['bytes'] and
                digest(path) == entry['sha256'], 'Manifest mismatch: ' + relative)
    for path in (ROOT / '01_project').rglob('*'):
        if path.is_file():
            require(path.relative_to(ROOT).as_posix() in manifest['files'],
                    'Production file absent from manifest: ' + str(path))

    syn = ROOT / ('05_td/v132_audio_visual_synth_attempt' + str(status['selected_synthesis_attempt']))
    phy = ROOT / ('05_td/v132_audio_visual_physical_attempt' + str(status['selected_physical_attempt']))
    sj, pj = read_json(syn / 'attempt.json'), read_json(phy / 'attempt.json')
    for attempt in (sj, pj):
        require(attempt['completed'] is True and attempt['source_unchanged'] is True and
                attempt['returncode'] == 0 and attempt['timedout'] is False and
                attempt['task_error'] is False, 'Build incomplete/failed')
    current = {p.relative_to(ROOT).as_posix(): digest(p)
               for p in (ROOT / '01_project').rglob('*')
               if p.is_file() and p.suffix in SOURCE_SUFFIXES}
    require(current == sj['source_sha256'] == pj['source_sha256'], 'Build/source mismatch')
    gate = local_path(manifest['preserved_gate_db'])
    require(digest(gate) == manifest['gate_db_sha256'] == sj['gate_db_sha256'] == pj['gate_db_sha256'],
            'Preserved synthesis DB mismatch')
    bit = local_path(status['recommended_bit'])
    require(status['recommended_bit'] == manifest['recommended_bit'] and
            bit.stat().st_size == status['bit_bytes'] and
            digest(bit) == status['bit_sha256'] == manifest['bit_sha256'] ==
            digest(phy / 'physical/v119_audio_pingpong_720p.bit'), 'Selected bit mismatch')

    metric = passing_summary(ROOT / '04_evidence/v132_resource_review/summary.json')
    require(metric == status['metrics'], 'Embedded metric mismatch')
    synthesis_resources = resources(ROOT / '04_evidence/v132_synthesis_preserved_attempt1/idx_video_gate.area')
    routed_resources = resources(phy / 'physical/sdram_phy.area')
    require(synthesis_resources == sj['resources'] == metric['synthesis_resources'], 'Synthesis metrics mismatch')
    require(routed_resources == pj['resources'] == metric['routed_resources'], 'Routed metrics mismatch')
    timing = (phy / 'physical/sdram_phy.ts').read_text(encoding='utf8')
    slack = {name: float(re.search(r'\b' + name + r':\s*([-+]?\d+(?:\.\d+)?)', timing).group(1))
             for name in ('SWNS', 'STNS', 'HWNS', 'HTNS')}
    require(slack == pj['slack_ns'] == metric['slack_ns'] and all(x >= 0 for x in slack.values()),
            'Timing mismatch/negative slack')
    require(all(routed_resources[k] <= v for k, v in metric['capacities'].items()), 'Device capacity exceeded')
    report = (phy / 'physical/sdram_check.rpt').read_text(encoding='utf8')
    counts = {m.group(1): int(m.group(2)) for m in
              re.finditer(r'^\d+\. checking (.*?)\((\d+)\)', report, re.M)}
    require(counts == metric['check_timing_counts'], 'Timing exception review changed')
    coverage = float(re.search(r'STA coverage\s*:\s*([\d.]+)',
                     (phy / 'physical/sdram_pr.timing').read_text(encoding='utf8')).group(1))
    require(coverage == metric['coverage_percent'], 'Coverage mismatch')
    fingerprint_checks = check_fingerprints(metric)

    verified_reports = set()
    for entry in status['tests'] + status.get('supplemental_tests', []):
        path = local_path(entry['path'])
        require(digest(path) == entry['sha256'] and entry['passed'] is True, 'Test record mismatch')
        obj = passing_summary(path)
        fingerprint_checks += check_fingerprints(obj)
        verified_reports.add(path)
        if entry['name'] == 'eight_affected_groups':
            require(len(obj['cases']) == 8, 'Affected group count mismatch')
            for case in obj['cases']:
                require(case['passed'] is True, 'Affected regression failed')
                for recorded in case['summary_paths']:
                    child = evidence_path(recorded)
                    fingerprint_checks += check_fingerprints(passing_summary(child))
                    verified_reports.add(child)
        if entry['name'] == 'all13routed_initialization_memories':
            require(len(obj['mapped_roms']) == 13 and obj['ui_logical_pixels_checked'] == 32768 and
                    obj['ui_packed_banks_checked'] == 3 and obj['all_native_parity_bits_preserved'] is True and
                    all(rom['matched'] is True for rom in obj['mapped_roms']), 'ROM review failed')
        if entry['name'] == 'unchanged_datapath_inherited_source_recheck':
            require(obj['unchanged_production_files'] == 137 and len(obj['inherited_reports']) == 12,
                    'Inherited evidence scope mismatch')
            require(obj['changed_production_sources'] == ['01_project/rtl/visual/media_ui_overlay.v'] and
                    obj['new_production_sources'] == ['01_project/rtl/visual/media_ui_font_packed_v132.vh'],
                    'Production change scope mismatch')
            for previous in obj['inherited_reports']:
                require(previous['not_freshly_rerun'] is True, 'Misstated inherited evidence')
                old = evidence_path(previous['report'])
                require(digest(old) == previous['report_sha256'], 'Inherited report changed')

    syntax = passing_summary(ROOT / '04_evidence/v132_resource_review/new_scripts_syntax.json')
    fingerprint_checks += check_fingerprints(syntax)
    for relative in syntax['source_sha256']:
        ast.parse(local_path(relative).read_text(encoding='utf-8-sig'))
    require(syntax['scripts'] == len(syntax['source_sha256']), 'Syntax script count mismatch')
    recommended = ('D:\\FPGA_Billboard\\99_archive\\version_history\\01_versions\\' + VERSION +
                   '\\01_project\\' + status['recommended_bit'].replace('/', '\\'))
    require(recommended in (ROOT / 'README_先看这里.md').read_text(encoding='utf8'),
            'Wrong documented archived bit path')
    print(json.dumps(dict(passed=True, version=VERSION, root=str(ROOT),
                          manifest_files=len(manifest['files']), verified_reports=len(verified_reports),
                          source_fingerprint_checks=fingerprint_checks,
                          routed_resources=routed_resources, slack_ns=slack,
                          bit_sha256=digest(bit), hardware_accepted=False,
                          read_only=True, scope='File/evidence integrity and numeric TD audit only; SRAM/PVT acceptance pending.'),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps(dict(passed=False, error=str(error), read_only=True), ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
