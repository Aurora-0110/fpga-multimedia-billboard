from pathlib import Path
import hashlib
import json
import shutil

workspace = Path(__file__).resolve().parents[1]
history = Path(r'D:\FPGA_Billboard\99_archive\version_history')
versions = json.loads((history / 'versions.json').read_text(encoding='utf-8'))
assert max(int(entry['id'][1:4]) for entry in versions) == 85
previous = workspace / 'work/v085_scaler_ram_address_20261025'
manifest = json.loads((history / '01_versions/v085_scaler_ram_address_20261025/MANIFEST_SHA256.json').read_text(encoding='utf-8'))
for entry in manifest['files']:
    if entry['path'].startswith('01_project/'):
        relative = Path(entry['path']).relative_to('01_project')
        original = previous / relative
        assert hashlib.sha256(original.read_bytes()).hexdigest() == entry['sha256'], relative
target = workspace / 'work/v086_dynamic_bmp_scaler_20261025'
assert not target.exists(), 'Never overwrite an existing version'
shutil.copytree(previous, target, ignore=shutil.ignore_patterns('build', '__pycache__', '*.pyc', '*.vvp', '*.vcd'))
shutil.copy2(target / 'VERSION_STATUS.json', target / 'INHERITED_v085_VERSION_STATUS.json')
(target / 'VERSION_STATUS.json').write_text(json.dumps({
    'version': 'v086', 'status': 'IN_PROGRESS_DYNAMIC_BMP_INTEGRATION',
    'new_bit_generated': False, 'hardware_acceptance_this_version': False,
    'flash_modified': False,
}, indent=2), encoding='utf-8')
print(target)
