# Read-only release verification; safe inside frozen archive, no generated output.
from pathlib import Path,PurePosixPath
import hashlib,json,re
root=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads((root/p).read_text(encoding='utf8'))
def local(rel):
 q=PurePosixPath(rel)
 assert not q.is_absolute() and '..' not in q.parts and not any(':' in p or '\\' in p for p in q.parts),rel
 return root.joinpath(*q.parts)
status=load('VERSION_STATUS.json');assert status['version']=='v119_three_wav_20261027'
manifest=load('04_evidence/v119_release_file_manifest.json')
for row in manifest['files']:
 p=local(row['path']);assert p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
bit=local(status['bitstream']['path']);assert sha(bit)==status['bitstream']['sha256']
syn=load(status['synthesis_attempt']+'/attempt.json');phy=load(status['physical_attempt']+'/attempt.json');bg=load(status['bitgen_attempt']+'/attempt.json')
assert all(x['completed'] for x in (syn,phy,bg))
assert phy['slack_ns']==bg['slack_ns']==bg['reloaded_slack_ns'] and min(phy['slack_ns'].values())>=0
for rel,h in syn['source_sha256'].items():assert sha(local(rel))==h,rel
assert sha(local(status['preserved_gate_db']))==bg['synth_gate_sha256']
assert sha(local(status['physical_attempt']+'/physical/sdram_pr.db'))==bg['routed_db_sha256']
nsource=0
def check_sources(x):
 global nsource
 if isinstance(x,dict):
  for key,value in x.items():
   if key in ('source_sha256','sources') and isinstance(value,dict) and value and all(isinstance(v,str) and re.fullmatch('[a-f0-9]{64}',v) for v in value.values()):
    for rel,h in value.items():
     p=Path(rel)
     if p.is_absolute():p=p.relative_to(Path(status['work_directory']))
     assert sha(local(p.as_posix()))==h,str(p);nsource+=1
   elif isinstance(value,(dict,list)):check_sources(value)
 elif isinstance(x,list):
  for value in x:check_sources(value)
for report in bg['reviewed_reports'].values():
 p=local(report['path']);assert sha(p)==report['sha256']
 data=json.loads(p.read_text(encoding='utf-8-sig'));assert data.get('passed',data.get('pass',data.get('result')=='PASS')) is True
 check_sources(data)
assert status['verification']['programmed'] is False and status['verification']['flash_written'] is False
print(json.dumps(dict(passed=True,files=len(manifest['files']),source_hash_entries=nsource,bit_sha256=sha(bit),hardware_accepted=False,scope='Read-only file/source/report integrity; no simulation/compile/download/Flash'),ensure_ascii=False,indent=2))