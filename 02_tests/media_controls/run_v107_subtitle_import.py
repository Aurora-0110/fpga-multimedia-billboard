"""Reject malformed/unsupported SRT before any active RTL ROM is modified."""
from pathlib import Path
import subprocess,os,sys,json,hashlib,datetime,ast
r=Path(__file__).resolve().parents[2]
if '01_versions' in r.parts:raise SystemExit('Run from a working copy')
p=r/'08_tools/generate_v107_subtitles.py';ast.parse(p.read_text(encoding='utf-8-sig'))
out=r/'04_evidence'/('v107_subtitle_import_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir();env=dict(os.environ);env.update(TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'),TMPDIR=str(r/'00_tmp'),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={str(f):sha(f) for f in (r/'01_project/rtl/visual').glob('*.vh')}
cases={
 'empty':'','overlap':'1\n00:00:00,000 --> 00:00:02,000\n字幕\n\n2\n00:00:01,000 --> 00:00:03,000\n字幕',
 'reverse':'1\n00:00:02,000 --> 00:00:01,000\n字幕','html':'1\n00:00:00,000 --> 00:00:01,000\n<b>字幕</b>',
 'too_long':'1\n00:00:00,000 --> 00:00:01,000\n'+'字'*25,'bad_time':'1\n00:00:60,000 --> 00:00:61,000\n字幕',
 'multiline':'1\n00:00:00,000 --> 00:00:01,000\n字幕\n第二行','axis_overflow':'1\n00:00:00,000 --> 00:00:16,001\n字幕'}
records=[]
for name,text in cases.items():
 f=out/(name+'.srt');f.write_text(text,encoding='utf8');c=subprocess.run([sys.executable,'-B',str(p),'--srt',str(f)],cwd=r,env=env,capture_output=True,text=True,timeout=20)
 unchanged=all(sha(Path(k))==h for k,h in before.items());passed=c.returncode!=0 and 'AssertionError' in c.stderr and unchanged
 (out/(name+'.log')).write_text(c.stdout+c.stderr,encoding='utf8');records.append(dict(name=name,passed=passed,rejected_returncode=c.returncode,rtl_assets_unchanged=unchanged));assert passed,name
rec=dict(passed=True,tests=records,scope='Eight malformed/unsupported SRT cases rejected before ROM writes; 16-second prototype axis enforced',source_sha256={Path(__file__).relative_to(r).as_posix():sha(Path(__file__)),p.relative_to(r).as_posix():sha(p),**{Path(k).relative_to(r).as_posix():h for k,h in before.items()}})
(out/'summary.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf8');print('PASS',len(records),'strict SRT rejection cases',out)
