"""Non-destructive v111 checks/build entry. Never programs JTAG, Flash or TF."""
from pathlib import Path
import argparse,os,sys,json,hashlib,subprocess
r=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser(description=__doc__);a.add_argument('--stage',choices=['check','media','wav','ui','bmp','spi','system','native','synth','physical','rom-init','bitgen','scaler','prepared','dither','underrun'],default='check');a.add_argument('--attempt',type=int,default=1);a.add_argument('--synth-attempt',type=int,default=2);a.add_argument('--physical-attempt',type=int,default=4);x=a.parse_args()
if x.stage=='check':
 p=r/'04_evidence/v111_release_manifest.json'
 if not p.is_file():sys.exit('v111 is not finalized; no new diagnostic-bit acceptance claim.')
 d=json.loads(p.read_text(encoding='utf-8'));bad=[]
 for name,h in d['files_sha256'].items():
  f=r/name
  if not f.is_file()or hashlib.sha256(f.read_bytes()).hexdigest()!=h:bad.append(name)
 print(json.dumps(dict(version=d['version'],passed=not bad,checked_artifacts=len(d['files_sha256']),mismatches=bad,hardware_test=False),ensure_ascii=False,indent=2));sys.exit(1 if bad else 0)
if '01_versions'in r.parts:sys.exit('Frozen archive is read-only. First copy into a D-drive work directory.')
env=dict(os.environ);env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'),TMPDIR=str(r/'00_tmp'))
jobs={
 'underrun':[('02_tests/wav/run_v111_underrun_recovery.py',[])],
 'dither':[('02_tests/multires/run_v111_dither.py',[])],
 'scaler':[('02_tests/scaler/run_v111_scaler_tests.py',['--quick']),('02_tests/scaler/run_v111_address_boundary.py',[]),('02_tests/scale_pipeline/run_v111_full_scaler.py',[])],
 'prepared':[('02_tests/audio_visual/run_v111_prepared_tmds.py',[])],
 'media':[('02_tests/media_controls/run_v111_media.py',[])],
 'wav':[('02_tests/wav/run_v111_wav_tests.py',[]),('02_tests/wav/run_v111_playback_tests.py',[]),('02_tests/wav/run_v111_mount_tests.py',[])],
 'ui':[('02_tests/ui/run_v111_ui.py',[])],
 'bmp':[('02_tests/dynamic_bmp/run_media_probe_v111.py',[]),('02_tests/dynamic_bmp/run_media_probe2048_v111.py',[])],
 'spi':[('02_tests/wav/run_v111_actual_spi_tests.py',['--short','--timeout','600']),('02_tests/wav/run_v111_actual_spi_tests.py',['--mode','2','--timeout','600'])],
 'system':[('02_tests/audio_visual/run_v111_tests.py',[])],
 'native':[('02_tests/audio_visual/run_v111_native.py',[])],
 'synth':[('02_tests/audio_visual/run_v111_synth.py',['--attempt',str(x.attempt)])],
 'physical':[('02_tests/audio_visual/run_v111_physical.py',['--synth-attempt',str(x.synth_attempt),'--attempt',str(x.attempt)])],
 'rom-init':[('02_tests/ui/check_v111_rom_init.py',['--physical-attempt',str(x.physical_attempt)])],
 'bitgen':[('02_tests/audio_visual/run_v111_bitgen.py',['--synth-attempt',str(x.synth_attempt),'--physical-attempt',str(x.physical_attempt),'--attempt',str(x.attempt)])]}
for name,args in jobs[x.stage]:
 print('RUN',name,flush=True);c=subprocess.run([sys.executable,'-B',str(r/name),*args],cwd=r,env=env)
 if c.returncode:sys.exit(c.returncode)
