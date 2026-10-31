"""Read-only v117 verifier. It never opens the board, TF card or a mutable old work tree."""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'v117_flash_candidate_20261027'
EXCLUDED_DIRS = {'00_tmp', 'build', '__pycache__', '.git'}
EXCLUDED_SUFFIXES = {'.vvp', '.vcd', '.pyc'}
METADATA_MAP = {name: 'BASELINE_v116_' + name for name in
                ('VERSION_STATUS.json', 'README_先看这里.md', 'README_归档位置.md')}
EXPECTED_BIT = '540faced66d96a83d6ab6e54caca5e614c54ae6be8822774f35febe1ee6cfdb6'


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inside(rel):
    path = (ROOT / rel).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), 'Missing or unsafe artifact: ' + str(rel)
    return path


def included_files():
    result = set()
    for p in ROOT.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(x in EXCLUDED_DIRS for x in rel.parts) or p.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        assert not p.is_symlink(), str(p)
        result.add(rel.as_posix())
    return result


def verify(baseline_only=False):
    baseline_manifest = load(inside('04_evidence/v116_release_manifest.json'))
    for rel, expected in baseline_manifest['files_sha256'].items():
        assert sha(inside(METADATA_MAP.get(rel, rel))) == expected, 'Inherited artifact changed: ' + rel
    base = load(inside('BASELINE_v116_VERSION_STATUS.json'))
    old_work = Path(base['work_source'])

    def source_path(name):
        p = Path(name)
        if p.is_absolute():
            assert p.is_relative_to(old_work), 'Outside snapshot source reference: ' + name
            p = p.relative_to(old_work)
        return inside(p)

    def check_hashes(obj):
        count = 0
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ('source_sha256', 'sources') and isinstance(value, dict) and all(
                        isinstance(h, str) and re.fullmatch('[0-9a-f]{64}', h) for h in value.values()):
                    for name, expected in value.items():
                        assert sha(source_path(name)) == expected, 'Source/report mismatch: ' + name
                        count += 1
                elif isinstance(value, (dict, list)):
                    count += check_hashes(value)
        elif isinstance(obj, list):
            for value in obj:
                count += check_hashes(value)
        return count

    sy = load(inside(base['selected_synthesis']))
    ph = load(inside(base['selected_physical']))
    bg = load(inside(base['selected_bitgen']))
    source_checks = check_hashes(sy)
    for report in base['reviewed_reports'].values():
        p = inside(report['path'])
        assert sha(p) == report['sha256'], report['path']
        count = check_hashes(load(p))
        assert count == report['source_hash_entries'], report['path']
        source_checks += count
    assert source_checks == 647
    current_paths = included_files()
    source_set = load(inside(base['reviewed_reports']['fresh_regression']['path']))['source_sha256']
    assert len(source_set) == 131
    for name, expected in source_set.items():
        assert sha(source_path(name)) == expected, name
    for prefix in ('01_project/', '02_tests/'):
        before = {rel for rel in baseline_manifest['files_sha256'] if rel.startswith(prefix)}
        after = {rel for rel in current_paths if rel.startswith(prefix)}
        assert before == after, 'Unrecorded source additions/removals: ' + prefix

    original_bit = inside(base['bitstream_relative'])
    assert original_bit.stat().st_size == base['bit_bytes'] == 645936
    assert sha(original_bit) == base['bit_sha256'] == bg['bit_sha256'] == EXPECTED_BIT
    header = original_bit.read_bytes()[:4096]
    for tag in (b'# Design name: idx_audio_visual_top', b'# Architecture: eagle_s20', b'# Package: EG4S20NG88'):
        assert tag in header, 'Unexpected bit header: ' + repr(tag)
    assert original_bit.stat().st_size < 16 * 1024 * 1024 // 8
    gate = inside('04_evidence/v116_final_synthesis_preserved/idx_video_Runs/syn_1/idx_video_gate.db')
    route = inside(str(Path(base['selected_physical']).parent / 'physical/sdram_pr.db'))
    assert sha(gate) == ph['synth_gate_sha256'] == bg['synth_gate_sha256']
    assert sha(route) == bg['routed_db_sha256']
    assert sha(inside(base['selected_synthesis'])) == bg['synthesis_attempt_sha256']
    assert sha(inside(base['selected_physical'])) == bg['physical_attempt_sha256']
    assert all(d['completed'] for d in (sy, ph, bg))
    assert base['slack_ns'] == ph['slack_ns'] == bg['slack_ns'] == bg['reloaded_slack_ns']
    assert min(base['slack_ns'].values()) >= 0 and bg['reloaded_timing_check_matches']
    refs = load(inside('04_evidence/v116_td_project_relative_paths.json'))
    project_references = 0
    for entry in refs['references']:
        assert sha(inside(entry['source'])) == entry['sha256'], entry['source']
        project = inside(entry['project'])
        for name in re.findall(r'<File Path="([^"]+)"', project.read_text(encoding='utf8')):
            p = (project.parent / name).resolve()
            assert p.is_relative_to(ROOT) and p.is_file(), str(p)
            project_references += 1
    for rel, expected in base['constraints_unchanged'].items():
        assert sha(inside(rel)) == expected, rel

    status = load(inside('VERSION_STATUS.json'))
    assert status['version'] == VERSION and status['release_version'] == 'v117' and status['design_version'] == 'v116'
    for key in ('new_rtl', 'new_simulation', 'new_td_build', 'new_bitstream', 'hardware_download',
                'hardware_acceptance', 'program_flash_executed', 'verify_flash_executed', 'cold_boot_tested',
                'formal_release_approved', 'flash_modified', 'tf_files_modified', 'handoff_zip_generated',
                'actual_long_track_a3_root_cause_closed'):
        assert status[key] is False, 'Unsupported completion claim: ' + key
    published = inside(status['bitstream_relative'])
    assert sha(published) == sha(original_bit) == status['bit_sha256'] and published.stat().st_size == status['bit_bytes']
    assert status['slack_ns'] == base['slack_ns'] and status['resources_routed'] == base['resources_routed']
    settings = load(inside('06_flash/02_guides/固化设置.json'))
    assert settings['program_mode'] == 'PROGRAM_FLASH' and settings['verify_mode'] == 'VERIFY_FLASH'
    assert settings['target_device'] == 'EG4S20NG88' and settings['speed_mhz'] == 5 and settings['memory_size_mbits'] == 16
    assert settings['file_relative'] == status['bitstream_relative'] and settings['sha256'] == EXPECTED_BIT
    assert not any(settings[k] for k in ('program_executed', 'verify_executed', 'cold_boot_tested'))
    historical = load(inside('06_flash/03_historical_evidence/来源与边界.json'))
    assert historical['design_version'] == 'v072' and historical['date'] == '2026-10-24'
    for item in historical['files']:
        assert sha(inside(item['copy'])) == item['sha256'], item['copy']
    request = load(inside('07_acceptance/当前用户请求.json'))
    assert request['user_v116_30s_listening_pass_explicitly_recorded'] is False
    optional = load(inside('06_flash/04_optional_tf_music/可选素材记录.json'))
    assert optional['included_in_flash'] is False and optional['copied_to_tf'] is False

    full_count = None
    if not baseline_only:
        assert status['source_bound_inherited_checks_passed'] is True
        proof = inside(status['preflight_report'])
        assert sha(proof) == status['preflight_report_sha256'] and load(proof)['passed']
        manifest = load(inside('04_evidence/v117_release_manifest.json'))
        assert manifest['version'] == VERSION and manifest['design_version'] == 'v116'
        assert set(manifest['files_sha256']) == current_paths - {'04_evidence/v117_release_manifest.json'}
        for rel, expected in manifest['files_sha256'].items():
            assert sha(inside(rel)) == expected, 'v117 artifact changed: ' + rel
        full_count = len(manifest['files_sha256'])
        assert full_count == manifest['checked_artifacts']
    return dict(passed=True, version=VERSION, design_version='v116',
                scope='baseline_only' if baseline_only else 'complete_v117_integrity',
                baseline_artifacts_checked=len(baseline_manifest['files_sha256']), source_hash_checks=source_checks,
                unchanged_source_set_entries=len(source_set), td_relative_references_checked=project_references,
                v117_manifest_entries=full_count, bitstream=str(published), bit_bytes=published.stat().st_size,
                bit_sha256=sha(published), hardware_actions=False, flash_modified=False,
                new_simulation=False, new_td_build=False, new_bitstream=False,
                a3_actual_device_acceptance=False, coldboot_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.baseline_only), ensure_ascii=False, indent=2))
