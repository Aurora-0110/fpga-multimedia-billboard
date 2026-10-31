"""Package v026 acceptance checkpoint, never overwrite a ZIP or rewrite test history."""
from pathlib import Path
import hashlib,json,zipfile,subprocess,sys
from verify_release import check_provenance
R=Path(__file__).resolve().parents[1];VID='v026_bmp_pixel_hw_pass_20261020'
O=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else R.parent.parent/'outputs'/VID
Z=O/(VID+'.zip');assert not Z.exists(),'No overwrites'
sim,td=check_provenance()
def include(p):
 rel=p.relative_to(R)
 if any(x in ('.git','__pycache__','build') or x.startswith('run_') for x in rel.parts):return False
 if p.name=='RELEASE_MANIFEST_SHA256.json' or p.suffix.lower() in ('.pyc','.vvp','.vcd','.db','.back'):return False
 if p.suffix.lower()=='.bit' and rel.as_posix()!=td['bit_file']:return False
 return True
files=sorted(p for p in R.rglob('*') if p.is_file() and include(p));m=dict(version=VID,algorithm='SHA256',files={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
M=R/'RELEASE_MANIFEST_SHA256.json';M.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');O.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(Z,'x',zipfile.ZIP_DEFLATED) as z:
 for p in files+[M]:z.write(p,VID+'/'+p.relative_to(R).as_posix())
with zipfile.ZipFile(Z) as z:
 assert z.testzip() is None
 assert sum(n.endswith('.bit') for n in z.namelist())==1
 for n,h in m['files'].items():assert hashlib.sha256(z.read(VID+'/'+n)).hexdigest()==h
 ex=O/'verification_extract';assert not ex.exists();z.extractall(ex)
cp=subprocess.run([sys.executable,str(ex/VID/'tools/verify_release.py')],capture_output=True,text=True,encoding='utf-8');assert cp.returncode==0,cp.stdout+cp.stderr
h=hashlib.sha256(Z.read_bytes()).hexdigest();(O/(Z.name+'.sha256.txt')).write_text(h+'  '+Z.name+'\n',encoding='utf-8')
report=dict(version=VID,zip=str(Z),sha256=h,bytes=Z.stat().st_size,files=len(files)+1,zip_crc_passed=True,per_file_sha256_passed=True,extracted_verification=cp.stdout.strip(),tf_full_pixel_crc_user_acceptance=True,new_simulation_or_td_or_download=False,sdram_tested=False,hdmi_image_tested=False)
(O/'packaging_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
