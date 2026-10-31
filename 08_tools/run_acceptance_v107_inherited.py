"""Single non-destructive acceptance entry; defaults to offline source/evidence/bit hash review.
Run from a WORK copy, not an immutable archive, for stages other than check.
No stage programs JTAG, writes Flash, modifies TF or installs drivers.
"""
from pathlib import Path
import argparse,sys,os,json,hashlib,subprocess
r=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stage',choices=['check','media','ui','modules','legacy','system','native','sim-all','synth','physical','rom-init','bitgen'],default='check');ap.add_argument('--attempt',type=int,default=1);ap.add_argument('--synth-attempt',type=int,default=1);ap.add_argument('--physical-attempt',type=int,default=1);a=ap.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if a.stage=='check':
 p=r/'04_evidence/v107_release_manifest.json'
 if not p.is_file():sys.exit('Not finalized: release manifest missing; run required simulations, synthesis, STA and guarded bitgen first.')
 m=json.loads(p.read_text(encoding='utf8'));bad=[]
 for rel,h in m['files_sha256'].items():
  f=r/rel
  if not f.is_file() or sha(f)!=h:bad.append(rel)
 print(json.dumps({'version':m['version'],'checked_artifacts':len(m['files_sha256']),'passed':not bad,'mismatch':bad,'hardware_test':False,'note':'Artifact/source consistency only; NOT proof of hardware or PVT reliability.'},ensure_ascii=False,indent=2));sys.exit(1 if bad else 0)
if '01_versions' in r.parts:sys.exit('Archived versions are read-only. Copy to D:/FPGA_Billboard/work before executing tests/builds.')
tmp=r/'00_tmp';tmp.mkdir(exist_ok=True);env=dict(os.environ);env.update(TEMP=str(tmp),TMP=str(tmp),TMPDIR=str(tmp),PYTHONDONTWRITEBYTECODE='1')
stages={
 'media':[(r/'02_tests/media_controls/run_v107_media.py',[]),(r/'02_tests/media_controls/run_v107_subtitle_import.py',[])],
 'ui':[(r/'02_tests/ui/run_v107_ui.py',[])],
 'modules':[(r/'02_tests/acceptance/run_v103_acceptance.py',[])],
 'legacy':[(r/'02_tests/run_v103_units.py',[])],
 'system':[(r/'02_tests/audio_visual/run_v107_tests.py',[])],
 'native':[(r/'02_tests/audio_visual/run_v107_native.py',[])],
 'synth':[(r/'02_tests/audio_visual/run_v107_synth.py',['--attempt',str(a.attempt)])],
 'physical':[(r/'02_tests/audio_visual/run_v107_physical.py',['--attempt',str(a.attempt),'--synth-attempt',str(a.synth_attempt)])],
 'rom-init':[(r/'02_tests/ui/check_v107_rom_init.py',['--physical-attempt',str(a.physical_attempt)])],
 'bitgen':[(r/'02_tests/ui/check_v107_rom_init.py',['--physical-attempt',str(a.physical_attempt)]),(r/'02_tests/audio_visual/run_v107_bitgen.py',['--attempt',str(a.attempt),'--synth-attempt',str(a.synth_attempt),'--physical-attempt',str(a.physical_attempt)])]}
steps=sum((stages[x] for x in ['media','ui','modules','legacy','system','native']),[]) if a.stage=='sim-all' else stages[a.stage]
for script,args in steps:
 print('RUN',script.relative_to(r),flush=True)
 rc=subprocess.run([sys.executable,'-B',str(script),*args],env=env,cwd=r).returncode
 if rc:sys.exit(rc)
