from pathlib import Path
import hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
assert ROOT.drive.upper()=='D:'
STEPS=[('visual','02_tests/audio_visual/run_v101_tests.py',1800),('native','02_tests/audio_visual/run_v101_native.py',900),('actual_spi','02_tests/dynamic_bmp/run_v097_spi_tests.py',1200),('scaled_spi_memory','02_tests/scale_pipeline/run_v097_scaled_spi_memory.py',1200),('units','02_tests/run_v097_units.py',1200),('paired_units','02_tests/scale_pipeline/run_v097_pair_units.py',1200),('paired_memory','02_tests/scale_pipeline/run_v097_pair_memory.py',1200)]
OUT=ROOT/'04_evidence'/('v101_regression_orchestrator_'+time.strftime('%Y%m%d_%H%M%S'))
OUT.mkdir()
env=dict(os.environ);env.update(PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',TEMP=str(ROOT/'00_tmp'),TMP=str(ROOT/'00_tmp'),TMPDIR=str(ROOT/'00_tmp'))
result={'result':'IN_PROGRESS','scope':'Fresh full regression sequence, no hardware/TF/Flash access','tests':[],'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for _,p,_ in STEPS}}
try:
 for name,rel,timeout in STEPS:
  start=time.monotonic();print('START',name,flush=True)
  with (OUT/(name+'.log')).open('wb') as log:
   c=subprocess.run([sys.executable,'-B',str(ROOT/rel)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
  text=(OUT/(name+'.log')).read_text(encoding='utf-8',errors='replace')
  row={'name':name,'script':rel,'passed':c.returncode==0,'returncode':c.returncode,'seconds':round(time.monotonic()-start,3)}
  result['tests'].append(row);print(json.dumps(row),flush=True);print(text[-1000:],flush=True)
  assert row['passed'], name+' failed'
 result['result']='PASS'
except Exception as e:
 result.update(result='FAIL',exception=repr(e));raise
finally:
 (OUT/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(OUT,flush=True)
