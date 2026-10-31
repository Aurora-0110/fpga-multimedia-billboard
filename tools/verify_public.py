"""Public-export file manifest and offline verifier; never programs hardware."""
from pathlib import Path
import argparse,json,hashlib,sys
R=Path(__file__).resolve().parents[1]
def sha(f):
 h=hashlib.sha256()
 with f.open('rb')as v:
  for b in iter(lambda:v.read(1048576),b''):h.update(b)
 return h.hexdigest()
def files():
 for f in sorted(R.rglob('*')):
  rel=f.relative_to(R)
  if not f.is_file()or any(p in {'.git','__pycache__','00_tmp','runs','build'}for p in rel.parts):continue
  if f.name=='MANIFEST_SHA256.json'or f.suffix.lower()in {'.pyc','.vcd','.vvp','.ppm'}:continue
  yield rel.as_posix(),f
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-manifest',action='store_true');a=p.parse_args()
 m=R/'MANIFEST_SHA256.json'
 if a.write_manifest:
  if '01_versions'in R.parts:p.error('Do not modify frozen archive')
  record=dict(format=1,scope='Full public export except manifest itself, Git metadata and regenerable caches',files={n:sha(f)for n,f in files()})
  m.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Manifest written:',len(record['files']));return 0
 if not m.is_file():p.error('Public manifest missing')
 spec=json.loads(m.read_text('utf-8'));actual={n:f for n,f in files()};bad=[]
 for n,digest in spec['files'].items():
  f=R/n
  if not f.is_file()or sha(f)!=digest:bad.append(n)
 unexpected=sorted(set(actual)-set(spec['files']))
 forbidden=[n for n,f in actual.items()if f.suffix.lower()in {'.wav','.mp3','.flac','.bmp','.bit','.db','.pnl','.lic','.pem','.pfx'}]
 ok=not bad and not unexpected and not forbidden
 print(json.dumps(dict(passed=ok,verified_files=len(spec['files']),mismatched_or_missing=bad,unexpected_files=unexpected,excluded_private_asset_paths=forbidden,scope='File integrity/public export only; not a new hardware or timing acceptance'),ensure_ascii=False,indent=2));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
