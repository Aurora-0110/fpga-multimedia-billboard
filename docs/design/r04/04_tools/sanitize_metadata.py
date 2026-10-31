"""Clear automatic author properties after Word saves without changing content."""
from pathlib import Path
from lxml import etree as E
import json,zipfile,hashlib
r=Path(__file__).resolve().parents[1]
p=next((r/'01_docx').glob('*.docx'))
with zipfile.ZipFile(p)as z:parts=[(i,z.read(i.filename))for i in z.infolist()]
h=hashlib.sha256(dict((i.filename,b)for i,b in parts)['word/document.xml']).hexdigest()
new=[]
for info,b in parts:
 if info.filename in ('docProps/core.xml','docProps/app.xml'):
  x=E.fromstring(b)
  for e in x:
   if E.QName(e).localname in ('creator','lastModifiedBy','Company','Manager'):e.text=''
  b=E.tostring(x,xml_declaration=True,encoding='UTF-8',standalone=True)
 new.append((info,b))
with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED)as z:
 for i,b in new:z.writestr(i,b)
q=r/'03_review/word_render.json';j=json.loads(q.read_text('utf-8-sig'));j['document_xml_sha256']=h;j['author_properties_cleared']=True
q.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Metadata cleared; rendered content fingerprint:',h)
