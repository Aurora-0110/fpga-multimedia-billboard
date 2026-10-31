"""Append-only code snapshots: no test execution or hardware downloads."""
from pathlib import Path, PurePosixPath
from datetime import datetime
import argparse, hashlib, json, shutil
ROOT=Path(__file__).resolve().parents[1]
SKIP_DIRS={'build','__pycache__','.git'}
SKIP_SUFFIXES={'.vvp','.vcd','.pyc'}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def refresh():
 versions=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'01_versions').glob('*/VERSION.json'))]
 (ROOT/'versions.json').write_text(json.dumps(versions,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 rows=['# 版本索引','','编号表示本次归档顺序，不代表历史上采用过这些编号。保存日期不替代原文件时间。','','| 版本 | 内容 | 验证状态 |','|---|---|---|']
 for v in versions:rows.append(f"| [{v['id']}](01_versions/{v['id']}/README_版本说明.md) | {v['title']} | {v['status']} |")
 rows+=['','## 当前推荐交接版本','','v004_billboard_handoff_20261017：核心仿真 + 独立彩条，不是完整 TF/SDRAM/音频成品。','','发队友使用 `02_releases/adboard_handoff_20261017.zip`。','']
 (ROOT/'00_版本索引.md').write_text('\n'.join(rows),encoding='utf-8')
def save(a):
 if not a.id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.id):raise ValueError('Use ASCII id')
 dst=ROOT/'01_versions'/a.id
 if dst.exists():raise FileExistsError('Version exists; choose a NEW id')
 src=Path(a.source).resolve()
 if not src.is_dir() or ROOT==src or ROOT.is_relative_to(src):raise ValueError('Invalid source')
 attachments=[Path(p).resolve() for p in a.attachment]
 if any(not p.is_file() for p in attachments):raise ValueError('Missing attachment')
 if len({p.name for p in attachments})!=len(attachments):raise ValueError('Duplicate attachment basename')
 dst.mkdir();project=dst/'01_project';project.mkdir()
 for p in src.rglob('*'):
  rel=p.relative_to(src)
  if any(s in SKIP_DIRS for s in rel.parts) or p.suffix.lower() in SKIP_SUFFIXES:continue
  if p.is_symlink():raise ValueError('Symlink refused: '+str(p))
  if p.is_file():
   q=project/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
   if sha(p)!=sha(q):raise RuntimeError('Copy mismatch')
 att=[]
 for p in attachments:
  q=dst/'02_original_packages'/p.name;q.parent.mkdir(exist_ok=True);shutil.copy2(p,q)
  if sha(p)!=sha(q):raise RuntimeError('Attachment mismatch')
  att.append({'source':str(p),'path':q.relative_to(dst).as_posix(),'sha256':sha(q)})
 info={'id':a.id,'title':a.title,'status':a.status,'archived_at':datetime.now().astimezone().isoformat(),'original_source':str(src),'note':a.note,'attachments':att,'excluded_generated_directories':sorted(SKIP_DIRS),'excluded_generated_suffixes':sorted(SKIP_SUFFIXES),'new_hardware_test_performed_by_archiver':False}
 (dst/'VERSION.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (dst/'README_版本说明.md').write_text(f"# {a.id} — {a.title}\n\n- 保存时间：{info['archived_at']}\n- 来源：`{src}`\n- 状态：**{a.status}**\n- 说明：{a.note}\n\n## 目录\n\n- `01_project`：原工程相对路径保持不变。\n- `02_original_packages`：原始压缩包与附件（如有）。\n- `VERSION.json`：来源与状态。\n- `MANIFEST_SHA256.json`：完整性校验。\n\n不要在快照内编辑或运行测试，先复制到工作目录。归档不等于已上板。排除可重建的 build、波形、仿真可执行缓存；源码、已有日志和正式位流保留。\n",encoding='utf-8')
 files=[{'path':p.relative_to(dst).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(dst.rglob('*')) if p.is_file()]
 (dst/'MANIFEST_SHA256.json').write_text(json.dumps({'version':a.id,'files':files},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 refresh();print('SAVED',a.id,len(files),'files')
def verify():
 n=0
 for mf in sorted((ROOT/'01_versions').glob('*/MANIFEST_SHA256.json')):
  for item in json.loads(mf.read_text(encoding='utf-8'))['files']:
   rel=PurePosixPath(item['path'])
   if rel.is_absolute() or '..' in rel.parts or any(':' in s or '\\' in s for s in rel.parts):raise ValueError('Unsafe path')
   p=mf.parent.joinpath(*rel.parts)
   if not p.is_file() or sha(p)!=item['sha256']:raise RuntimeError('CHANGED/MISSING '+str(p))
   n+=1
 print('PASS:',n,'archived files match manifests')
p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
a=s.add_parser('save');a.add_argument('--id',required=True);a.add_argument('--title',required=True);a.add_argument('--status',required=True);a.add_argument('--source',required=True);a.add_argument('--attachment',action='append',default=[]);a.add_argument('--note',default='')
s.add_parser('verify');s.add_parser('index');a=p.parse_args()
if a.command=='save':save(a)
elif a.command=='verify':verify()
else:refresh()
