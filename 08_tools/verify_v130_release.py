# Read-only release integrity check; safe in frozen archive, never programs hardware.
from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parents[1];m=json.loads((r/'V130_RELEASE_MANIFEST.json').read_text(encoding='utf-8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel,e in m['files'].items():
 p=r/rel;assert p.is_file()and p.stat().st_size==e['bytes']and sha(p)==e['sha256'],rel
s=json.loads((r/'VERSION_STATUS.json').read_text(encoding='utf-8'))
assert s['version']==m['version']=='v130_av_layer_ui_20261030'
assert s['layers']['short_chord_cycle']==['11','10','01','00']and s['persistent_volume_row']and s['subtitle_cell_px']==36
assert s['enabled_cues']==69 and s['caption_tracks']==[1,3]and s['caption_text_and_sample_times_unchanged']
assert s['selected_synthesis_attempt']==s['selected_physical_attempt']==2 and s['diagnostic_pipeline_cycles']==4
assert all(not s[k]for k in ['hardware_accepted','hardware_downloaded','human_timing_verified','flash_modified','tf_modified','network_settings_changed','automatic_disconnect_scheduled','formal_release_approved'])
assert sha(r/m['recommended_bit'])==s['bit_sha256']==m['bit_sha256']
assert sha(r/s['preserved_gate_db'])==json.loads((r/'05_td/v130_sample_caption_bitgen_attempt1/attempt.json').read_text())['synth_gate_sha256']
print('PASS V130 release manifest',len(m['files']),'files; independent layers+volume+rounded font, physical attempt2. Hardware pending; network unchanged.')
