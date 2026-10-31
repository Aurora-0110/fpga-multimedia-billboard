from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
assert '01_versions' not in root.parts,'Frozen archive; do not modify manifest'
target=root/'04_evidence/v122_release_file_manifest.json'
status=json.loads((root/'VERSION_STATUS.json').read_text(encoding='utf8'));assert status['version']=='v122_address_pipeline_20261029'
files=[]
for f in sorted(root.rglob('*')):
 rel=f.relative_to(root)
 if not f.is_file() or f==target or any(part in {'.git','__pycache__','build'}for part in rel.parts)or f.suffix.lower()in{'.pyc','.vcd','.vvp'}:continue
 assert not f.is_symlink(),str(f)
 files.append(dict(path=rel.as_posix(),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
target.write_text(json.dumps(dict(version=status['version'],scope='Files preserved by archive; not hardware acceptance',files=files),ensure_ascii=False,indent=2),encoding='utf8')
print('Recorded',len(files),'files,',sum(f['bytes']for f in files),'bytes')
