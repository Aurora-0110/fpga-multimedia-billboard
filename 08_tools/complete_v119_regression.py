"""Retain ten successful jobs; repair moved-vendor-library top test only."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prior=root/'04_evidence/v119_regression_20261027_225218/summary.json'
old=json.loads(prior.read_text(encoding='utf8'))
assert old['sources_unchanged_during_run']
assert all(sha(root/k)==v for k,v in old['source_sha256'].items())
rows=[]
for item in old['cases']:
 if item['case']=='top720p':
  assert not item['passed'];continue
 assert item['passed'] and sha(root/item['script'])==item['script_sha256']
 rows.append(dict(item,reused_same_v119_source_run=True))
assert len(rows)==10
out=root/'04_evidence'/('v119_regression_complete_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
env=dict(os.environ);env.update(PYTHONIOENCODING='utf-8',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),TMPDIR=str(root/'00_tmp'))
script=root/'02_tests/audio_visual/run_v114_tests.py'
c=subprocess.run([sys.executable,str(script),'--only','top'],cwd=root,env=env,capture_output=True,text=True,timeout=700)
text=c.stdout+c.stderr;(out/'top720p.log').write_text(text,encoding='utf8')
paths=[line.strip()+'/summary.json' for line in text.splitlines() if line.strip().startswith(str(root/'04_evidence')) and Path(line.strip()).is_dir()]
assert len(paths)==1,text[-4000:]
new=json.loads(Path(paths[0]).read_text(encoding='utf8'))
rows.append(dict(case='top720p',script=script.relative_to(root).as_posix(),script_sha256=sha(script),args=['--only','top'],returncode=c.returncode,passed=c.returncode==0 and new['passed'] and new['complete'],summary_paths=paths,reused_same_v119_source_run=False))
unchanged=all(sha(root/k)==v for k,v in old['source_sha256'].items())
record=dict(passed=all(row['passed'] for row in rows) and unchanged,cases=rows,source_sha256=old['source_sha256'],sources_unchanged_during_run=unchanged,previous_attempt=prior.relative_to(root).as_posix(),previous_attempt_sha256=sha(prior),scope='Eleven regression jobs on unchanged v119 RTL. Ten passed in initial run; top repaired only for relocated native simulation library, then rerun. Protocol models, accelerated budget tests and injected SDRAM are not physical TF/SDRAM/HDMI/listening acceptance.')
(out/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print(text[-3000:]);print(out);raise SystemExit(0 if record['passed'] else 1)
