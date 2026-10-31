# Read-only V120 freeze/source/Flash-image verifier.
from pathlib import Path,PurePosixPath
import hashlib,json,re
root=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads((root/p).read_text(encoding='utf8'))
def local(rel):
 q=PurePosixPath(rel);assert not q.is_absolute() and '..' not in q.parts and not any(':' in p or '\\' in p for p in q.parts),rel
 return root.joinpath(*q.parts)
s=load('VERSION_STATUS.json');assert s['version']=='v120_flash_release_20261027' and s['design_version']=='v119'
m=load('04_evidence/v120_release_file_manifest.json')
for row in m['files']:
 p=local(row['path']);assert p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
base=load('BASELINE_v119_VERSION_STATUS.json');syn=load(base['synthesis_attempt']+'/attempt.json');n=0
for rel,h in syn['source_sha256'].items():assert sha(local(rel))==h,rel;n+=1
for r in base['reviewed_reports'].values():assert sha(local(r['path']))==r['sha256'],r['path']
assert sha(local(s['bitstream']['path']))==sha(local(s['bitstream']['original_path']))==s['bitstream']['sha256']
assert s['user_approved_for_flash'] and not s['flash']['program_executed'] and not s['flash']['verify_executed'] and not s['flash']['cold_boot_tested']
print(json.dumps(dict(passed=True,files=len(m['files']),inherited_source_hash_entries=n,reviewed_reports=len(base['reviewed_reports']),bit_sha256=s['bitstream']['sha256'],design='V119',flash_executed=False,cold_boot_tested=False),indent=2))