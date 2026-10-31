"""Read-only complete v112 artifact, source, bit and TD-report consistency check."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
manifest=load(root/'04_evidence/v112_release_manifest.json')
for rel,h in manifest['files_sha256'].items():
 p=root/rel
 assert p.is_file() and sha(p)==h,rel
status=load(root/'VERSION_STATUS.json')
sy=load(root/status['selected_synthesis'])
ph=load(root/status['selected_physical'])
bg=load(root/status['selected_bitgen'])
for rel,h in sy['source_sha256'].items():assert sha(root/rel)==h,rel
for report in status['reviewed_reports'].values():assert sha(root/report['path'])==report['sha256'],report['path']
bit=root/status['bitstream_relative']
assert bit.stat().st_size==status['bit_bytes'] and sha(bit)==status['bit_sha256']==bg['bit_sha256']
raw=root/'04_evidence/v112_final_synthesis_preserved/idx_video_Runs/syn_1/idx_video_gate.db'
assert sha(raw)==ph['synth_gate_sha256']==bg['synth_gate_sha256']
route=(root/status['selected_physical']).parent/'physical/sdram_pr.db'
assert sha(route)==bg['routed_db_sha256']
assert all(d['completed'] for d in (sy,ph,bg))
assert status['slack_ns']==ph['slack_ns']==bg['slack_ns']==bg['reloaded_slack_ns']
assert min(status['slack_ns'].values())>=0 and bg['reloaded_timing_check_matches']
assert not any(status[k] for k in ('hardware_download','hardware_acceptance','formal_release_approved','flash_modified','tf_files_modified','handoff_zip_generated'))
print(json.dumps(dict(passed=True,checked_artifacts=len(manifest['files_sha256']),version=status['version'],bitstream=str(bit),bit_bytes=bit.stat().st_size,bit_sha256=sha(bit),hardware_test=False,flash_modified=False),ensure_ascii=False,indent=2))
