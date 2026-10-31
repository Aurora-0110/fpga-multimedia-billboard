from pathlib import Path
r=Path(__file__).resolve().parents[1];t=r/'02_tests/audio_visual'
p=r/'02_tests/ui/check_v114_rom_init.py';s=p.read_text().replace("f'05_td/v114_audio_visual_physical_attempt", "f'05_td/v116_audio_visual_physical_attempt").replace("('v114_rom_init_'","('v116_rom_init_'")
(r/'02_tests/ui/check_v116_rom_init.py').write_text(s)
old=(t/'run_v114_bitgen.py').read_text();tail=old[old.index("synth=root/f'"):].replace('v114','v116').replace('V114','V116').replace('v116_audio_triple_bitgen','v116_audio_refill_bitgen').replace('v116_audio_triple_720p','v116_audio_refill_720p')
a=tail.index("record={'scope':");b=tail.index('tcl_lines=')
tail=tail[:a]+'''record={'scope':'v116 diagnostic SRAM candidate: bounded32-cycle urgent-audio refill reservation fixes sector-boundary arbitration holes; no cache-size/clock/format change. Global first-A3 snapshot survives source changes. Model and simulation results do NOT close actual-card A3 root cause.',
 'reviewed_reports':reports,'check_timing_counts':counts,'synthesis_attempt':str(synth.relative_to(root)),'physical_attempt':str(phy.relative_to(root)),
 'synthesis_attempt_sha256':sha(synth/'attempt.json'),'physical_attempt_sha256':sha(phy/'attempt.json'),'synth_gate_sha256':sha(gate/'idx_video_gate.db'),'routed_db_sha256':sha(db),'slack_ns':pr['slack_ns'],
 'formal_release_approved':False,'hardware_test':False,'flash_modified':False,
 'known_open_review':['Real TF-card service latency and v116 listening test remain unverified; no claim of hardware A3 closure',
 'Fresh sustained budget24k-frame tests accelerate both service and consumer16x; not physical SD timing',
 'Fresh pin-protocol integration uses512FIFO and behavior card; inherited v114 full4096 FIFO pin tests use old arbiter and are NOT a current v116 combined acceptance',
 'RGB332 frame cache; BMP source24bit, HDMI1280x720 and PCM24bit stereo48k; no FLAC/MP3 decode or gapless loop',
 'SDRAM macro relocation,33 abnormal input annotations,SiP/PVT and full-address actual-device BIST open',
 'No TF writes, Flash, programming, cold-start or electrical acceptance performed']}
''' +tail[b:]
head=r'''"""Source-bound v116 targeted-regression / STA guard; no programming or Flash."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,time
root=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--check-reports-only',action='store_true');ap.add_argument('--attempt',type=int,default=1);ap.add_argument('--synth-attempt',type=int,default=1);ap.add_argument('--physical-attempt',type=int,default=1);args=ap.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def req(x,m):
 if not x:raise RuntimeError(m)
def local_source(rel):
 p=Path(rel)
 if not p.is_absolute():p=root/p
 req(p.is_relative_to(root),'source outside current project: '+rel)
 return p
def check_hashes(x):
 n=0
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ('source_sha256','sources') and isinstance(v,dict) and v and all(isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h)for h in v.values()):
    for rel,h in v.items():
     p=local_source(rel);req(p.is_file()and sha(p)==h,'source evidence mismatch: '+rel);n+=1
   elif isinstance(v,(dict,list)):n+=check_hashes(v)
 elif isinstance(x,list):
  for y in x:n+=check_hashes(y)
 return n
reports={}
def use_path(name,path):
 data=json.loads(path.read_text(encoding='utf-8-sig'));req(data.get('passed',data.get('pass')) is True,'failed '+str(path));n=check_hashes(data);req(n>0,'unbound '+str(path));reports[name]=dict(path=path.relative_to(root).as_posix(),sha256=sha(path),source_hash_entries=n,scope=data.get('scope',''));return data
def use_latest(name,pattern):
 paths=sorted((root/'04_evidence').glob(pattern+'/summary.json'));req(paths,'Missing '+name);return use_path(name,paths[-1])
reg=use_latest('fresh_regression','v116_regression_*')
req(len(reg['cases'])==11 and all(x['passed']for x in reg['cases']),'incomplete regression')
for row in reg['cases']:
 req(len(row['summary_paths'])==1,'missing result path '+row['case']);d=use_path(row['case'],Path(row['summary_paths'][0]));req(d.get('passed',d.get('pass')) is True,'failed detail')
units=use_latest('arbiter_negative_control_and_persistent_snapshot','v116_units_*');req(len(units['cases'])==3,'missing unit cases')
# First old/new performance pair completed before the broader regression.
use_latest('spc1_old_priority_negative_control','v116_refill_old_20261027_124025*')
use_latest('spc1_fixed_priority','v116_refill_new_20261027_124209*')
rom=use_latest('routed_ui_caption_logo_init','v116_rom_init_*');req(rom.get('physical_attempt')==args.physical_attempt and len(rom['mapped_roms'])==12,'ROM audit mismatch')
# Only inherit reports whose entire recorded source set matches this working copy.
# These modules are untouched; the changed arbiter is covered by fresh tests above.
for label,pattern in [('unchanged_wav_parser','v114_wav_decode_*'),('unchanged_prefetch36','v114_prefetch_*'),('unchanged_ui','v114_ui_20*'),('unchanged_media_controls','v114_media_20*'),('unchanged_native_hdmi','v114_visual_native_*'),('unchanged_scaler720','v114_full_scaler_*'),('unchanged_dither','v114_dither_*')]:
 candidates=sorted((root/'04_evidence').glob(pattern+'/summary.json'))
 for path in reversed(candidates):
  try:use_path(label,path);reports[label]['inherited_not_rerun']=True;break
  except RuntimeError:continue
 else:raise RuntimeError('No source-matching inherited report '+label)
'''
(t/'run_v116_bitgen.py').write_text(head+tail)
print('v116 source-bound release guard and ROM audit prepared')
