"""Append-only v072 packaging; CRC, per-member SHA256 and extracted offline verification."""
from pathlib import Path
import datetime,hashlib,json,zipfile,subprocess,sys
from verify_v072 import validate
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT.parents[1]/'outputs'
def digest(d):return hashlib.sha256(d).hexdigest()
def allowed(p):return not any(s in {'build','__pycache__','.git'} for s in p.relative_to(ROOT).parts) and p.suffix.lower() not in {'.pyc','.vvp','.vcd'}
def package(dest,entries):
 manifest=[{'path':n,'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for n,p in entries]
 if len({n for n,p in entries})!=len(entries):raise ValueError('Duplicate archive member')
 with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for n,p in entries:
   if p.suffix.lower() in {'.lic','.exe','.msi','.sys'}:raise ValueError('Installer/device-license/driver refused: '+n)
   z.write(p,n)
  z.writestr('PACKAGE_MANIFEST_SHA256.json',json.dumps(manifest,ensure_ascii=False,indent=2))
 with zipfile.ZipFile(dest) as z:
  if z.testzip() is not None:raise RuntimeError('CRC mismatch')
  for item in manifest:
   d=z.read(item['path'])
   if len(d)!=item['bytes'] or digest(d)!=item['sha256']:raise RuntimeError('Member mismatch')
 return {'path':str(dest),'bytes':dest.stat().st_size,'sha256':digest(dest.read_bytes()),'verified_members':len(manifest),'crc_and_sha256_pass':True}
def main():
 OUT.mkdir(exist_ok=True)
 names=['M3_v072_HDMI音视频_上板测试包_20261024.zip','M3_v072_完整代码交接包_20261024.zip']
 report=OUT/'M3_v072_交付包校验_20261024.json';validation=ROOT/'04_evidence/v072_validation.json'
 extraction=OUT/'verify_v072_extracted_20261024'
 for p in [report,validation,extraction,*[OUT/n for n in names]]:
  if p.exists():raise FileExistsError(p)
 validation.write_text(json.dumps(validate(),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 small_files=['README_先看这里.md','VERSION_STATUS.json','03_docs/上板步骤.md','03_docs/设计与验证说明.md','03_docs/v072_验收记录模板.md','03_docs/第三方开源说明.md','03_bitstreams/v072_four_image_audio_720p.bit','04_evidence/v072_validation.json','04_evidence/v072_td_publication.json','04_evidence/v072_test_matrix.json','07_reference/hdl_util_hdmi/LICENSE-MIT','07_reference/hdl_util_hdmi/LICENSE-APACHE','07_reference/hdl_util_hdmi/PROVENANCE.json']
 small=[(s,ROOT/s) for s in small_files]
 small.extend((p.relative_to(ROOT).as_posix(),p) for p in sorted((ROOT/'06_test_media/four_image_playlist').rglob('*')) if p.is_file())
 full=[(p.relative_to(ROOT).as_posix(),p) for p in sorted(ROOT.rglob('*')) if p.is_file() and allowed(p)]
 data={'version':ROOT.name,'created_at':datetime.datetime.now().astimezone().isoformat(),'scope':'Four-image video plus I2S generated tone, actual serial receive, signed gain and HDMI audio multiplexing. Engineering test candidate, not hardware/audio or macro/PVT signoff.','packages':[package(OUT/names[0],small),package(OUT/names[1],full)]}
 extraction.mkdir()
 with zipfile.ZipFile(OUT/names[1]) as z:z.extractall(extraction)
 cp=subprocess.run([sys.executable,str(extraction/'08_tools/verify_v072.py')],capture_output=True,text=True,encoding='utf8')
 if cp.returncode:raise RuntimeError(cp.stderr+cp.stdout)
 data['extracted_full_package_validation']=json.loads(cp.stdout)
 data['extracted_validation_directory']=str(extraction)
 report.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(data,ensure_ascii=True,indent=2))
if __name__=='__main__':main()
