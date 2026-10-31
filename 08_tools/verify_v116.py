"""Read-only v116 complete artifact and source-bound TD/bit/evidence verifier."""
from pathlib import Path
import hashlib, json, re
root = Path(__file__).resolve().parents[1]
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

manifest = load(root / '04_evidence/v116_release_manifest.json')
for rel, h in manifest['files_sha256'].items():
    p = root / rel
    assert p.is_file() and sha(p) == h, rel
status = load(root / 'VERSION_STATUS.json')
work_source = Path(status['work_source'])

def source_path(name):
    p = Path(name)
    if p.is_absolute():
        # Read the archived copy, not a mutable work file, when checking reports
        # that recorded absolute current-work source names.
        assert p.is_relative_to(work_source), 'Outside snapshot source reference: ' + name
        p = p.relative_to(work_source)
    q = root / p
    assert q.resolve().is_relative_to(root), str(q)
    return q


def check_hashes(obj):
    n = 0
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in ('source_sha256', 'sources') and isinstance(value, dict) and all(isinstance(h, str) and re.fullmatch('[0-9a-f]{64}', h) for h in value.values()):
                for name, h in value.items():
                    p = source_path(name)
                    assert p.is_file() and sha(p) == h, name
                    n += 1
            elif isinstance(value, (dict, list)):
                n += check_hashes(value)
    elif isinstance(obj, list):
        for value in obj:
            n += check_hashes(value)
    return n

sy = load(root / status['selected_synthesis'])
ph = load(root / status['selected_physical'])
bg = load(root / status['selected_bitgen'])
source_checks = check_hashes(sy)
for report in status['reviewed_reports'].values():
    p = root / report['path']
    assert sha(p) == report['sha256'], report['path']
    n = check_hashes(load(p))
    assert n == report['source_hash_entries'], report['path']
    source_checks += n
bit = root / status['bitstream_relative']
assert bit.stat().st_size == status['bit_bytes'] and sha(bit) == status['bit_sha256'] == bg['bit_sha256']
raw = root / '04_evidence/v116_final_synthesis_preserved/idx_video_Runs/syn_1/idx_video_gate.db'
assert sha(raw) == ph['synth_gate_sha256'] == bg['synth_gate_sha256']
route = (root / status['selected_physical']).parent / 'physical/sdram_pr.db'
assert sha(route) == bg['routed_db_sha256']
assert sha(root / status['selected_synthesis']) == bg['synthesis_attempt_sha256']
assert sha(root / status['selected_physical']) == bg['physical_attempt_sha256']
assert all(d['completed'] for d in (sy, ph, bg))
assert status['slack_ns'] == ph['slack_ns'] == bg['slack_ns'] == bg['reloaded_slack_ns']
assert min(status['slack_ns'].values()) >= 0 and bg['reloaded_timing_check_matches']
assert not any(status[k] for k in ('hardware_download', 'hardware_acceptance', 'formal_release_approved', 'flash_modified', 'tf_files_modified', 'handoff_zip_generated', 'actual_long_track_a3_root_cause_closed'))
refs = load(root / '04_evidence/v116_td_project_relative_paths.json')
for entry in refs['references']:
    assert sha(root / entry['source']) == entry['sha256'], entry['source']
    project = root / entry['project']
    for name in re.findall(r'<File Path="([^"]+)"', project.read_text(encoding='utf8')):
        q = (project.parent / name).resolve()
        assert q.is_relative_to(root) and q.is_file(), str(q)
for rel, h in status['constraints_unchanged'].items():
    assert sha(root / rel) == h, rel
print(json.dumps(dict(passed=True, checked_artifacts=len(manifest['files_sha256']), source_hash_checks=source_checks, version=status['version'], bitstream=str(bit), bit_bytes=bit.stat().st_size, bit_sha256=sha(bit), hardware_test=False, flash_modified=False), ensure_ascii=False, indent=2))
