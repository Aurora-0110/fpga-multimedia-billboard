"""Quality checks for the revised design document and its rendered PDF."""
from pathlib import Path
import json,zipfile,re,hashlib,io,posixpath
from collections import Counter
from lxml import etree as E
from docx import Document
from pypdf import PdfReader
R=Path(__file__).resolve().parents[1];src=next((R/'00_source').glob('*.docx'));out=next((R/'01_docx').glob('*.docx'));pdf=next((R/'02_pdf').glob('*.pdf'))
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
checks=[]
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail))
a=Document(src);b=Document(out)
attrs=['page_width','page_height','top_margin','bottom_margin','left_margin','right_margin','header_distance','footer_distance','orientation']
check('Original section dimensions/margins/header/footer distances preserved',len(a.sections)==len(b.sections)and all(getattr(x,k)==getattr(y,k)for x,y in zip(a.sections,b.sections)for k in attrs))
with zipfile.ZipFile(src)as z,zipfile.ZipFile(out)as v:
 old=Counter(hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()if n.startswith('word/media/')and not n.endswith('/'))
 new=Counter(hashlib.sha256(v.read(n)).hexdigest()for n in v.namelist()if n.startswith('word/media/')and not n.endswith('/'))
 check('Sanitized public-source media bytes preserved',not(old-new),dict(original=sum(old.values()),output=sum(new.values())))
 d=E.fromstring(v.read('word/document.xml'))
 body='\n'.join(''.join(p.xpath('.//w:t/text()',namespaces=NS))for p in d.xpath('//w:p',namespaces=NS))
 (R/'03_review/final_plain_text.txt').write_text(body,encoding='utf8')
 # Word is allowed to split field instructions across multiple runs; reconstruct them.
 stack=[];inst=[]
 for node in d.iter():
  if node.tag=='{'+NS['w']+'}fldChar':
   kind=node.get('{'+NS['w']+'}fldCharType')
   if kind=='begin':stack.append(dict(parts=[],collect=True))
   elif kind=='separate'and stack:stack[-1]['collect']=False
   elif kind=='end'and stack:inst.append(''.join(stack.pop()['parts']))
  elif node.tag=='{'+NS['w']+'}instrText'and stack and stack[-1]['collect']:stack[-1]['parts'].append(node.text or'')
 inst.extend(d.xpath('//w:fldSimple/@w:instr',namespaces=NS))
 check('Three live contents/list fields',sum(x.strip().startswith('TOC ')for x in inst)==3)
 check('All ten figures use SEQ',sum(bool(re.match(r'SEQ\s+图(?:\s|$)',x.strip()))for x in inst)==10)
 check('All fifteen tables use SEQ',sum(bool(re.match(r'SEQ\s+表(?:\s|$)',x.strip()))for x in inst)==15)
 check('Figure/table body cross references',sum(bool(re.match(r'REF (Figure|Table)\d+',x.strip()))for x in inst)==25)
 links=d.xpath('//w:hyperlink[starts-with(@w:anchor,"Ref")]',namespaces=NS)
 check('Every reference cited in body',set(x.get(qn)for x in links for qn in ['{'+NS['w']+'}anchor'])=={'Ref'+str(i)for i in range(1,14)},len(links))
 check('Citations are superscript internal hyperlinks',all(x.xpath('.//w:vertAlign[@w:val="superscript"]',namespaces=NS)for x in links))
 bookmarks=d.xpath('//w:bookmarkStart/@w:name',namespaces=NS)
 check('Reference bookmarks and figure/table targets',all('Ref'+str(i)in bookmarks for i in range(1,14))and all('Figure'+str(i)in bookmarks for i in range(1,11))and all('Table'+str(i)in bookmarks for i in range(1,16)))
 check('Eight original editable equations preserved',len(d.xpath('//m:oMath',namespaces=NS))==8)
 check('No unrelated personal/school identity',not any(x in body for x in ['指导教师','指导老师','学校名称','华南农业','33938','C:\\Users','D:\\Users']))
 check('No revision tracking/comments',not d.xpath('//w:ins|//w:del|//w:commentRangeStart',namespaces=NS))
 core=E.fromstring(v.read('docProps/core.xml'))
 check('No personal author metadata',all(not(e.text or'').strip()for e in core if E.QName(e).localname in ['creator','lastModifiedBy']))
 tables=d.xpath('//w:tbl',namespaces=NS)
 check('All tables repeat header and prevent row splits',len(tables)==15 and all(t.find('w:tr/w:trPr/w:tblHeader',NS)is not None and all(tr.find('w:trPr/w:cantSplit',NS)is not None for tr in t.findall('w:tr',NS))for t in tables))
 check('Three-line tables without vertical rules',all(t.xpath('w:tblPr/w:tblBorders/w:insideV[@w:val="nil"]',namespaces=NS)and t.xpath('w:tblPr/w:tblBorders/w:top[@w:val="single"]',namespaces=NS)for t in tables))
 check('Correct V132 metrics and explicit user hardware acceptance',all(x in body for x in ['17739','10676','61／64','0.667','0.021','最终功能测试、Flash固化和冷启动均已通过','不是语音识别']))
 check('Use cases and we-subject reflection',all(x in body for x in ['商铺商品促销','展会人工讲解','社区安静公告','活动暖场','教学与调试','在一块资源紧张的小板卡上实现完整多媒体系统','我们']))
 check('Current 2025 reference standard specified','GB/T 7714—2025'in body and '2026年7月1日'in body)
 check('Manual scenario matches K0/K1 controls','先用K1切到手动，再短按K0换图'in body and '用K1换页'not in body)
 check('UI V130 title not confused with firmware identity','UI标题有意保留V130，不作版本判据'in body and '位流文件名和SHA256核对'in body)
 check('Verified public GitHub repository accurately described','仓库已建立并核对为公开开源仓库'in body and 'https://github.com/Aurora-0110/fpga-multimedia-billboard'in body and '发布状态：尚待远端发布确认'not in body)
 check('Accepted functional/Flash/cold-start states do not remain pending',all(t not in body for t in ['V132尚待SRAM实测','尚无本版上板反馈','V132仍待SRAM','3.4 尚待闭合的验收事项']))
 check('Public illustrations accurately identified', ('原作品V132功能与固化冷启动验收记录示意'in body and '历史实物屏幕照片'not in body))
 check('Source of final acceptance and public-data distinction explicit','用户于2026年10月31日确认最终全部功能测试通过'in body and '公开示例'in body and '仪器'in body)

texts=[p.extract_text()or''for p in PdfReader(pdf).pages]
check('No broken Word fields in rendered PDF',not any(any(k in t for k in ['错误!','Error!','未定义书签','目录将在Word中更新'])for t in texts))
check('No empty/two-line orphan pages',all(len(re.sub(r'\s','',t))>160 for t in texts),[(i+1,len(re.sub(r'\s','',t)))for i,t in enumerate(texts)if len(re.sub(r'\s','',t))<=160])
render=json.loads((R/'03_review/word_render.json').read_text('utf-8-sig'))
with zipfile.ZipFile(out)as z:content_hash=hashlib.sha256(z.read('word/document.xml')).hexdigest()
check('Rendered document content matches final DOCX',content_hash==render.get('document_xml_sha256'))
report=dict(passed=all(c['passed']for c in checks),checks=checks,pages=len(texts),input_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest())
(R/'03_review/quality_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for c in checks:print('PASS'if c['passed']else'FAIL',c['name'],c['detail']if c['detail']is not None else'')
raise SystemExit(0 if report['passed'] else 1)

