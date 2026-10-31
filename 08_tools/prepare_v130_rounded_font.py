from pathlib import Path
from urllib.request import Request,urlopen
import json,zipfile,hashlib,io
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
out=r/'07_reference/fonts/chill_round';assert not out.exists();out.mkdir()
base='https://raw.githubusercontent.com/Warren2060/ChillRound/main/'
headers={'User-Agent':'FPGA-Billboard-font-license-review'}
url='https://github.com/Warren2060/ChillRound/releases/download/v1.805/ChillRoundM_v1.805.zip'
data=urlopen(Request(url,headers=headers),timeout=60).read();(out/'ChillRoundM_v1.805.zip').write_bytes(data)
z=zipfile.ZipFile(io.BytesIO(data));print([(i.filename,i.file_size)for i in z.infolist()])
lic=urlopen(Request(base+'LICENSE',headers=headers),timeout=20).read();(out/'LICENSE').write_bytes(lic);print(lic.decode('utf-8')[:900])
for n in z.namelist():
 if n.lower().endswith(('.ttf','.otf')):
  assert '..'not in Path(n).parts
  (out/Path(n).name).write_bytes(z.read(n))
(out/'SOURCE.json').write_text(json.dumps(dict(repository='https://github.com/Warren2060/ChillRound',release='v1.805',asset_url=url,zip_sha256=hashlib.sha256(data).hexdigest(),license='SIL Open Font License1.1',license_url=base+'LICENSE',license_sha256=hashlib.sha256(lic).hexdigest(),purpose='FPGA subtitle bitmap glyphs; font software/license preserved for reproducible assets'),ensure_ascii=False,indent=2),encoding='utf-8')
