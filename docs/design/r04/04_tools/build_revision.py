"""Revise the user-supplied DOCX without changing page geometry, headers or figure placement."""
from pathlib import Path
from copy import deepcopy
import json,re,hashlib,zipfile
from docx import Document
from docx.shared import Pt, Mm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

ROOT=Path(__file__).resolve().parents[1]
SRC=next((ROOT/'00_source').glob('*.docx'))
OUT=ROOT/'01_docx/基于FPGA的多媒体广告牌_设计文档_V132_r04.docx'
D=Document(SRC);original=list(D.paragraphs);P={i:p for i,p in enumerate(original)}
publish_path=ROOT/'05_github/publish_status.json'
publish=json.loads(publish_path.read_text('utf-8-sig'))if publish_path.exists()else{}
REPO='https://github.com/Aurora-0110/fpga-multimedia-billboard'
remote=publish.get('repository_verified',False)

for name in ['论文正文','论文图注','论文表注','论文注释','论文参考文献','论文目录标题','论文目录条目']:
 if name not in D.styles:D.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH).base_style=D.styles['Normal']

def font(run,size=12,bold=False,east='宋体'):
 run.font.name='Times New Roman';run.font.size=Pt(size);run.font.bold=bold;run.font.color.rgb=RGBColor(0,0,0)
 r=run._element.get_or_add_rPr().get_or_add_rFonts()
 for k,v in [('eastAsia',east),('ascii','Times New Roman'),('hAnsi','Times New Roman'),('cs','Times New Roman')]:r.set(qn('w:'+k),v)
 return run

def clear(p):
 for x in list(p._p):
  if x.tag!=qn('w:pPr'):p._p.remove(x)

def text(p,value):clear(p);font(p.add_run(value));return p

def newp(anchor,value='',style='Normal',after=False):
 node=OxmlElement('w:p');(anchor._p.addnext if after else anchor._p.addprevious)(node)
 p=Paragraph(node,anchor._parent);p.style=D.styles[style]
 if value:font(p.add_run(value))
 return p

def body_style(p,small=False):
 pf=p.paragraph_format;pf.left_indent=Pt(0);pf.right_indent=Pt(0);pf.first_line_indent=Pt(0 if small else 24)
 pf.line_spacing=1.25 if small else 1.5;pf.space_before=Pt(0);pf.space_after=Pt(3 if small else 5);pf.widow_control=True
 p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
 for r in p.runs:font(r,10.5 if small else 12)

def outline(p,level):
 pp=p._p.get_or_add_pPr();node=pp.find(qn('w:outlineLvl'))
 if node is None:node=OxmlElement('w:outlineLvl');pp.append(node)
 node.set(qn('w:val'),str(level))

def bookmark(p,name):
 global bid
 bid+=1;b=OxmlElement('w:bookmarkStart');b.set(qn('w:id'),str(bid));b.set(qn('w:name'),name)
 e=OxmlElement('w:bookmarkEnd');e.set(qn('w:id'),str(bid));p._p.insert(1 if p._p.find(qn('w:pPr'))is not None else 0,b);p._p.append(e)

bid=1000

def field(p,instruction,result,super_=False):
 r=p.add_run();font(r,9 if super_ else 10.5);r.font.superscript=super_
 b=OxmlElement('w:fldChar');b.set(qn('w:fldCharType'),'begin');r._r.append(b)
 r=p.add_run();font(r,9 if super_ else 10.5);r.font.superscript=super_
 i=OxmlElement('w:instrText');i.set(qn('xml:space'),'preserve');i.text=' '+instruction+' ';r._r.append(i)
 r=p.add_run();font(r,9 if super_ else 10.5);r.font.superscript=super_
 s=OxmlElement('w:fldChar');s.set(qn('w:fldCharType'),'separate');r._r.append(s)
 r=p.add_run(str(result));font(r,9 if super_ else 10.5);r.font.superscript=super_
 r=p.add_run();font(r,9 if super_ else 10.5);r.font.superscript=super_
 e=OxmlElement('w:fldChar');e.set(qn('w:fldCharType'),'end');r._r.append(e)

def citation(p,n):
 link=OxmlElement('w:hyperlink');link.set(qn('w:anchor'),'Ref'+str(n));link.set(qn('w:history'),'1')
 r=OxmlElement('w:r');pr=OxmlElement('w:rPr');f=OxmlElement('w:rFonts');f.set(qn('w:ascii'),'Times New Roman');f.set(qn('w:hAnsi'),'Times New Roman');pr.append(f)
 sz=OxmlElement('w:sz');sz.set(qn('w:val'),'18');pr.append(sz);v=OxmlElement('w:vertAlign');v.set(qn('w:val'),'superscript');pr.append(v);r.append(pr)
 t=OxmlElement('w:t');t.text='['+str(n)+']';r.append(t);link.append(r);p._p.append(link)

def external(p,label,url):
 from docx.opc.constants import RELATIONSHIP_TYPE as RT
 rid=p.part.relate_to(url,RT.HYPERLINK,is_external=True);h=OxmlElement('w:hyperlink');h.set(qn('r:id'),rid)
 r=OxmlElement('w:r');pr=OxmlElement('w:rPr');rf=OxmlElement('w:rFonts');rf.set(qn('w:eastAsia'),'宋体');rf.set(qn('w:ascii'),'Times New Roman');pr.append(rf)
 sz=OxmlElement('w:sz');sz.set(qn('w:val'),'21');pr.append(sz);r.append(pr);t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)

# Update only descriptive prose/tables, retaining the original figures, equations and section properties.
text(P[2],'固件基线 V132　文档修订 r04　2026年10月31日')
text(P[4],P[4].text.replace('V130布局布线后使用17749个LUT、62个BRAM9K及17个DSP，数值建立与保持最差裕量分别为0.642 ns和0.024 ns','V132布局布线后使用17739个LUT、61个BRAM9K及17个DSP，数值建立与保持最差裕量分别为0.667 ns和0.021 ns'))
text(P[6],'文档口径：V132原作品的最终功能测试、Flash固化和冷启动均已通过，依据为用户于2026年10月31日的明确实物反馈。功能、仿真、综合、布局布线与用户验收分别记录。UI标题有意保留V130，不作版本判据；以位流文件名和SHA256核对。公开工程已去除TF素材，嵌入的原歌词和Logo图案改为自编示例；原已验收配置与公开示例数据版本明确区分。页面尺寸、页边距、页眉页脚、图像位置与公式对象保持。')
text(P[9],P[9].text+'芯片及板级条件按器件资料与实际原理图核对。[1][2]')
text(P[11],'系统已实现的功能可以组合用于不同展示场景，表中给出商铺、展会、社区公告、活动暖场及教学验证等示例。下列组合是利用现有按键和图层状态进行的操作建议，不代表新增“场景预设”或自动节目编排功能。替换BMP/WAV可改变展示内容；歌词字幕仍需与对应音源和预编译时间轴匹配，不能把任意新WAV自动转成字幕。')
text(P[13],P[13].text+'实现范围与资源结论以冻结工程为准。[3]')
text(P[19],P[19].text+'综合和实现流程使用TD 6.2.1。[4]')
text(P[19],'从板卡时钟、下载与基础显示起步，接通TF/FAT32、BMP及SDRAM轮播，再集成音频、缩放、交互、频谱和字幕。逐版归档，依次检查仿真、综合、布局布线、ROM与数值时序，最后记录上板结果。系统以RGB332、16选频DFT及流水线图层控制资源，保留色深、频点和可靠性边界。[3][4]')
# Merge the brief trade-off subsection into the design-flow paragraph to avoid an orphan page.
for obsolete in (P[20],P[21]):obsolete._p.getparent().remove(obsolete._p)
text(P[26],P[26].text.replace('依据V130 RTL绘制','依据V132 RTL；主通路与V130一致'))
text(P[31],re.sub(r'\[1\]\[4\]$','[1][2]',P[31].text))
text(P[56],P[56].text+'FAT32字段定义参考公开文件系统规范。[5]')
text(P[64],P[64].text+'BMP信息头和BI_RGB语义参考平台格式文档。[6]')
text(P[76],P[76].text.replace('[1][3]','[1][7]'))
text(P[81],P[81].text+'PCM/WAV字段语义依据WAVE格式定义。[8]')
for i in [88,93]:text(P[i],P[i].text.replace('[5]','[9]'))
text(P[109],P[109].text.replace('[6]','[10]'))
text(P[135],'V130修复后的建立裕量为+0.642 ns、保持裕量为+0.024 ns。V132继续保持同一时钟、引脚与SDC，仅把UI中文字库中经验证的零边缘无损省略，将字体ROM由4块BRAM9K压缩为3块，并保留16×16逻辑坐标与五级UI对齐。Noto字库来源及许可保持不变。[11]V132路由后建立裕量为+0.667 ns、保持裕量为+0.021 ns：setup改善25 ps，hold减少3 ps，不能宣称所有指标都优化。整机播放节拍和读卡速率未改变。[3]')
text(P[138],'每个修改及验证节点保存冻结快照，以SHA256关联源码、ROM、约束、报告和位流，并保留失败尝试。V132完整归档5992个文件，发布子集清单校验320个文件；只读核验覆盖15份关键报告及974处源码指纹。12份未变底层报告按哈希一致显式继承，不算本轮重新执行；新增字库及UI相关路径单独回归。')
text(P[139],'工程按“清单及素材核对—模块与集成仿真—TD综合—布局布线与时序—ROM核查—上板—Flash固化—冷启动”完成验证闭环。原作品的最终功能与固化冷启动验收通过；公开工程提供无私有素材的可重建源码，具体复现路径见本节发布说明。不得在冻结快照内运行会改日志的测试。[3][4]')
text(P[142],'作品已完成图片、音频、可视化与交互一体化设计。用户于2026年10月31日确认最终全部功能测试通过，并已完成Flash固化和冷启动。结合既有仿真、综合、布局布线、初始化ROM与归档检查，原V132配置形成“源码—构建—功能测试—固化—冷启动”的完成记录。该实物反馈不被扩写为未经测量的功耗、PVT或厂商可靠性签核。')
text(P[152],P[152].text.replace('V130 RTL仿真界面','V130功能基线RTL仿真界面'))
text(P[155],'图10  公开测试字幕的真实RTL仿真输出')
text(P[156],'中文UI示例和字幕示例均来自实际RTL仿真。字幕图使用自编公开测试文字，替代原歌词截图；不是显示器实拍，也不改变原作品的字幕计数、字库与图层原理。原V132实物功能验收已通过；公开工程重新生成的嵌入素材及位流按其新构建结果单独验证。')
text(P[159],'以下资源与时序数据取自原已验收V132配置第一次物理实现的同阶段报告，综合、路由和独立模块数据不混用。容量按EG4S20NG88计算；公开版替换嵌入示例数据后重建的资源与时序，以新报告为准。[3]')
text(P[162],'BRAM9K由V130的62块降至61块，现余3块；路由LUT减少10个，寄存器增加22个。综合LUT由17510增至17554，路由与综合口径分别列示。当前模型及约束下数值建立与保持检查通过。报告同时列出33项异常输入延时、3个dummy节点、2项缺失输入延时及7项缺失输出延时，属于器件模型与约束审查范围；原作品功能验收不被写成SDRAM宏、内部DQ延时、SiP、CDC与PVT的厂商正式签核。')
text(P[164],'表14  V132验证结果与证据来源')
text(P[166],'验收结论：原作品最终功能测试、Flash固化和冷启动通过，由用户于2026年10月31日确认。公开工程完整保留功能算法与构建测试入口，仅将原嵌入素材替换为自编数据；新构建结果按对应配置验证。')
text(P[167],'测试范围说明：功能验收通过；功耗、端到端音画偏差、完整地址实物BIST及PVT等专项不由本次用户反馈代替。')
text(P[169],'4.1 工程完成与使用边界')
text(P[170],'我们已完成原V132系统的最终功能测试、Flash固化和冷启动，并以逐版归档、源码指纹、报告与用户实物反馈形成可追溯记录。收尾工作集中在公开工程清理、文档规范及复现流程，不再扩展新功能。公开示例更换了原嵌入素材数据，需在重建后独立确认；原实物通过记录保留不变。我们明确RGB332缓存、固定PCM格式和预编译字幕的使用范围，保留器件模型与专项可靠性审查说明，不将正裕量解释为无条件可靠性保证。')
text(P[172],'我们在开发中体会到，在一块资源紧张的小板卡上实现完整多媒体系统，是一项相对不容易的工程任务。难点不在于让某个算法单独输出结果，而在于让低速读卡、SDRAM、多个时钟域和固定节拍的HDMI输出长期协同。V132仍使用约90.51%的LUT和95.31%的BRAM9K，任何局部增加都可能影响布局和时序。我们曾遇到音频进入后A3欠载、界面切换影响播放、显示恢复与状态交接等问题。排查使我们认识到，简单增加双缓冲或三缓冲并不能替代正确的仲裁、预取和读前响应；必须区分“字节已接收”“PCM已提交”“样本已播放”和“后台帧已完整”，再逐项建立可观察证据。我们采用RGB332双帧、双行缩放、共享DFT乘加器、紧凑字幕与UI字库以及分级流水，在色彩、功能、BRAM和裕量之间反复权衡。我们也看到，UI字库省下一块BRAM并不代表系统全面提速，setup改善同时仍可能出现hold小幅变差；因此不能只挑有利指标。我们坚持保存每一版源码、约束、报告与位流，保留失败尝试，明确哪些测试实际执行、哪些依据哈希继承、哪些属于专项测量范围。我们最终完成了全部功能测试、Flash固化与冷启动，交付的是一套职责清楚、版本可追溯、公开代码可复现且如实说明能力边界的单板多媒体系统。')


text(P[144],'图8  原作品V132功能与固化冷启动验收记录示意')
text(P[147],'已完成开发板、TF模块、HDMI终端及音频输出外围组成的桌面原型。系统采用现成模块连接与可靠固定，不将其描述为定制PCB、机箱或机械结构设计。为保护TF素材，公开文档使用验收记录示意呈现功能测试、固化和冷启动的用户通过结果，不把该图称为实物照片。')
text(P[153],'中文界面已完整显示自动或手动轮播、当前图片、资源就绪、亮度、对比度、基础OSD、音频状态、按键提示、音量与AV组状态。独立显隐与唤醒保持图像有效信号及音频会话连续；相关按键、像素与控制仿真通过，原作品最终功能实测通过。')
text(P[165],'3.4 验收结论与测试范围')

# Insert a real use-case matrix, not new firmware features.
anchor=P[12]
h=newp(anchor,'1.2.1 功能组合与场景示例','Module Heading')
p=newp(anchor,'图像、音频、音画图层和独立UI可以并行组合；频谱与字幕仍属于同一AV组，不能描述为已经支持各自独立显隐。下表按当前功能给出现场操作方式。')
cap=newp(anchor,'表0  已实现功能的场景组合','Report Caption')
headers=['场景','功能组合','操作与内容示例','使用边界']
rows=[
 ['商铺商品促销','四图自动轮播＋滑动转场＋广告WAV＋Logo/标语','四图介绍商品；选择广告音源，隐藏UI；按需降低音量','不是按图片自动绑定广告；字幕需另有匹配时间轴'],
 ['展会人工讲解','手动换图＋音频暂停/继续＋临时显隐UI','先用K1切到手动，再短按K0换图；讲解时暂停WAV并隐藏UI','现有双键规则，不新增遥控器或场景预设'],
 ['社区安静公告','自动轮播＋运行时间OSD＋静音＋隐藏AV组','图片显示通知；音量置0%，仅保留基础OSD','时间为上电计时，不是日历或定时发布'],
 ['活动暖场/品牌展示','背景图＋音乐/扩展WAV＋透明频谱＋匹配字幕','选定音源，打开AV组；暂停时字幕与样本进度冻结','16真实频点扩展为64视觉柱；非完整256频点FFT'],
 ['安静阅读与辅助理解','图片＋匹配同步字幕＋低音量/静音','已有对应字幕的音源以样本计数推进；无需依赖墙钟','静音不暂停；字幕不是在线语音识别'],
 ['教学与调试演示','UI＋LED＋首错OSD＋暂停/切歌＋图层组合','显示参数和按键含义；观察A1/A2/A3与L6/L7','功能观察不等于完整内存BIST或PVT签核']]
t=D.add_table(rows=1,cols=4);cap._p.addnext(t._tbl);t.autofit=False
for j,a in enumerate(headers):t.cell(0,j).text=a
for row in rows:
 cells=t.add_row().cells
 for j,a in enumerate(row):cells[j].text=a
note=newp(anchor,'上述示例只重新组合已完成能力。更换音频后，原字幕不会自动适配新歌词；公开播放前仍须确认图片、音频和字幕的使用权。','Report Fine')

# Extend the existing engineering classification with reproducible paths.
org=D.tables[11] if False else next(tb for tb in D.tables if tb.cell(0,0).text=='工程类别')
path_data=[
 '01_project/：顶层、PLL/IP、ADC/SDC及全部生产RTL',
 '02_tests/、06_test_media/：TB、集成回归、公开像素真值与素材生成入口',
 '08_tools/、05_td/、03_bitstreams/：脚本、数值报告与本地位流构建说明',
 '04_evidence/、07_acceptance/：JSON、日志、图像及验收边界',
 '07_reference/：原始开源参考、字体及许可；素材授权单独说明']
for row,value in zip(org.rows[1:],path_data):row.cells[1].text=value

eng=newp(P[140],'2.3.15 GitHub工程归档与复现','Module Heading')
state=('仓库已建立并核对为公开开源仓库，可匿名访问。'if remote else'公开开源工程已准备，远端状态以发布核验记录为准。')
gp=newp(P[140],state+'仓库所有者为Aurora-0110，工程名为fpga-multimedia-billboard。源代码沿用原相对目录，公开最新完整功能源码、必要测试和报告；所有旧版本仍在本地冻结档案中，不将132套历史目录重复复制为一个Git提交。')
linkp=newp(P[140],'工程访问地址：'if remote else'拟发布地址（尚未上传，不能作为已提交证明）：','Report Fine')
external(linkp,REPO,REPO)
newp(P[140],'提交材料覆盖板级RTL、时钟IP及约束、TB和整机回归、公开像素真值、TD构建脚本、原已验收配置的综合与布局布线数值报告、公开仿真日志/图像及来源许可。TD安装器、商业许可证、账号令牌和个人认证文件不属于工程交付内容。保留的第三方代码与字体遵循原许可；自研代码采用MIT，第三方代码与字体保留原许可。TF原歌曲、图片、原歌词、时间轴及含其内容的原位流和截图不公开，历史完整工程在本地归档保留。公开ROM使用自编字幕与Logo占位图案，仍可复现全部功能算法。')
newp(P[140],'跨电脑复现需自行安装匹配TD、申请有效许可并安装下载器驱动。先读README与REPRODUCE说明，再校验文件；工程包含的旧版工具可能保留原机路径，优先使用根目录可配置入口。重要历史波形若原快照未保存，不得写成仓库已经包含；可通过相应TB重新生成。公开发布时核对远端目录树及关键文件SHA256。原V132的用户实物验收已通过；公开示例的重新构建、全新电脑环境和新位流实测按各自记录分别确认。')

# Same-stage V132 tables and independently classified tests.
metrics=next(tb for tb in D.tables if tb.cell(0,0).text=='资源' and tb.cell(0,1).text=='已用／容量')
for row in metrics.rows[1:]:
 if row.cells[0].text=='LUT':vals=['LUT','17739／19600','90.51%','1861']
 elif row.cells[0].text=='寄存器':vals=['寄存器','10676／19600','54.47%','8924']
 elif row.cells[0].text=='BRAM9K':vals=['BRAM9K','61／64','95.31%','3']
 else:continue
 for c,v in zip(row.cells,vals):c.text=v
time=next(tb for tb in D.tables if tb.cell(0,0).text=='项目'and'结果'in tb.cell(0,1).text)
time.cell(0,1).text='V132结果';time.cell(1,1).text='+0.667 ns';time.cell(3,1).text='+0.021 ns'
mainmetrics=next(tb for tb in D.tables if any('17749' in c.text for row in tb.rows for c in row.cells)and tb is not metrics)if any('17749' in c.text for tb in D.tables for row in tb.rows for c in row.cells)else None
if mainmetrics:
 for row in mainmetrics.rows:
  for c in row.cells:c.text=c.text.replace('17749','17739').replace('BRAM9K 62','BRAM9K 61')
valid=next(tb for tb in D.tables if tb.cell(0,0).text=='验证项')
newrows=[['V132受影响回归','8组通过','本轮执行；含音量、HDMI、频谱、UI及媒体控制'],['UI字库与像素','65536次取值；4608015像素','874状态；另有独立UI复跑，字形保持等价'],['字幕像素与播放器','4299516次像素检查','69条端点、暂停冻结及整机接线仿真'],['物理ROM初始化','13块逐位比较通过','UI4、字幕6、元数据1、Logo2；含奇偶位'],['未改变底层通路','12份历史报告哈希复核','按源码一致继承，不算本轮重新执行'],['综合与布局布线','完成并通过数值检查','setup +0.667 ns；hold +0.021 ns；模型及约束范围如实说明'],['发布文件完整性','5992归档文件校验；320发布子集','15份关键报告及974处源码指纹；不是硬件验收'],['最终实物验收','功能、Flash固化与冷启动通过','用户于2026-10-31明确确认；不扩写仪器或厂商专项签核']]
for row,values in zip(valid.rows[1:],newrows):
 for c,v in zip(row.cells,values):c.text=v

# Replace old bibliography; source body citations have explicit new numbering.
for p in original[174:]:p._element.getparent().remove(p._element)
refs=[
 '上海安路信息科技股份有限公司. EG4S20数据手册[Z]. 项目保存的器件技术资料，版本以来源记录为准.',
 'VF-E20NG88板卡资料. AG88_VIP_Board_V1.0原理图及EGS20NG88_Board ADC、SDC约束[Z]. HDK V2.0，2025-10-11.',
 ('本作品工程组. 基于FPGA的多媒体广告牌：V132工程与验证记录[CP/OL]. (2026-10-31)[2026-10-31]. '+REPO+'.'if remote else'本作品工程组. 基于FPGA的多媒体广告牌：V132冻结工程、RTL、测试与物理实现记录[Z]. 2026-10-31. 本地归档；远端发布尚待确认.'),
 '上海安路信息科技股份有限公司. TangDynasty User Guide V6.2[Z]. TD 6.2.1配套技术文档.',
 'MICROSOFT. Microsoft Extensible Firmware Initiative FAT32 File System Specification: Version 1.03[EB/OL]. (2000-12-06)[2026-10-31]. https://download.microsoft.com/download/1/6/1/161ba512-40e2-4cc9-843a-923143f3456c/fatgen103.doc.',
 'MICROSOFT. BITMAPINFOHEADER structure[EB/OL]. [2026-10-31]. https://learn.microsoft.com/en-us/windows/win32/api/wingdi/ns-wingdi-bitmapinfoheader.',
 '上海安路信息科技股份有限公司. 基于ERAM接口实现的高性能SDRAM读写：APUG011，v1.2[Z]. 项目使用的应用指南.',
 'MICROSOFT. WAVEFORMATEXTENSIBLE structure[EB/OL]. [2026-10-31]. https://learn.microsoft.com/en-us/windows/win32/api/mmreg/ns-mmreg-waveformatextensible.',
 'HDL-UTIL. HDMI: reference implementation[CP/OL]. Commit 83b1c9543a91b776671a44e68e130f81cae437b7[2026-10-31]. https://github.com/hdl-util/hdmi. MIT License.',
 'CHILLROUND. ChillRoundM: v1.805[CP/OL]. [2026-10-31]. https://github.com/Warren2060/ChillRound. SIL Open Font License 1.1.',
 'NOTO FONTS. Noto Sans CJK SC Medium[CP/OL]. Commit f8d157532fbfaeda587e826d4cd5b21a49186f7c[2026-10-31]. https://github.com/notofonts/noto-cjk. SIL Open Font License 1.1.',
 '国家市场监督管理总局, 国家标准化管理委员会. 学术论文编写规则：GB/T 7713.2—2022[S/OL]. (2022-12-30)[2026-10-31]. https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=0B963916637B8F34B295FCF4A51A1BE5.',
 '国家市场监督管理总局, 国家标准化管理委员会. 信息与文献 参考文献著录规则：GB/T 7714—2025[S/OL]. (2025-12-02)[2026-10-31]. https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=C6CE52E55AC09B9C79A20AEA77CEDD14.'
]
for n,value in enumerate(refs,1):
 p=D.add_paragraph(style='论文参考文献');p.alignment=WD_ALIGN_PARAGRAPH.LEFT;font(p.add_run('['+str(n)+'] '),10.5)
 pos=0
 for match in re.finditer(r'https?://[^\s]+',value):
  font(p.add_run(value[pos:match.start()]),10.5)
  url=match.group().rstrip('.')
  external(p,url,url)
  if len(url)<len(match.group()):font(p.add_run(match.group()[len(url):]),10.5)
  pos=match.end()
 font(p.add_run(value[pos:]),10.5)
 p.paragraph_format.first_line_indent=Pt(-21);p.paragraph_format.left_indent=Pt(21);p.paragraph_format.line_spacing=1.3;p.paragraph_format.space_after=Pt(5);p.paragraph_format.widow_control=True;p.paragraph_format.keep_together=True
 bookmark(p,'Ref'+str(n))
p=D.add_paragraph('5.1 排版与引用说明',style='Heading 2')
p=D.add_paragraph('本文结构、图表和术语表达参照学术论文编写规则，参考文献采用顺序编码并在正文以上角标标注；目录、图表目录及交叉引用均使用可更新域。参考文献著录依据2026年7月1日起实施的GB/T 7714—2025，不继续把2015版称为现行版。[12][13]')
p=D.add_paragraph('页面沿用原文档设置；正文采用宋体小四、英文和数字Times New Roman、1.5倍行距、首行缩进2字符，图题在下、表题在上、表格采用三线表。该字体与行距属于本稿的统一排版方案，不宣称国家标准只允许这一组字体字号。资料缺少出版年或修订号时不虚构，第三方许可和本作品工程证据分别著录。')

# Caption fields, bookmarks, text references and source notes.
figs=[];tables=[];fnum=0;tnum=0
for p in list(D.paragraphs):
 if p.style.name!='Report Caption':continue
 val=p.text
 if re.match(r'^图\d+',val):
  fnum+=1;desc=re.sub(r'^图\d+\s*','',val);clear(p);p.style='论文图注';font(p.add_run('图'),10.5);field(p,'SEQ 图 \\* ARABIC',fnum);bookmark(p,'Figure'+str(fnum));font(p.add_run('  '+desc),10.5);figs.append((fnum,p,desc))
  note=('用户实物通过记录示意，非照片；2026-10-31确认。[3]'if fnum==8 else '本作品真实RTL仿真帧；字幕为自编公开测试文字，非原歌词或实拍。[3]'if fnum==10 else '本作品RTL仿真帧，非实拍。[3]'if fnum in [6,9]else '本作品依据冻结工程绘制的原理示意。[3]')
  np=newp(p,'注：'+note,'论文注释',after=True)
 elif re.match(r'^表\d+',val):
  tnum+=1;desc=re.sub(r'^表\d+\s*','',val);clear(p);p.style='论文表注';font(p.add_run('表'),10.5);field(p,'SEQ 表 \\* ARABIC',tnum);bookmark(p,'Table'+str(tnum));font(p.add_run('  '+desc),10.5);tables.append((tnum,p,desc))
  # Place source annotation after the associated table, not between title and table.
  node=p._p.getnext()
  if node is not None and node.tag==qn('w:tbl'):
   np=newp(p,'','论文注释',after=True);node.addnext(np._p);font(np.add_run('注：'+('功能组合为现有按键与图层的使用示例，不是新功能或新验收结论。'if '场景组合'in desc else'数据与职责按本版工程整理；同版实现指标不等于正式可靠性签核。')+'[3]'),10.5)
for kind,items in [('图',figs),('表',tables)]:
 for num,cap,desc in items:
  node=cap._p.getprevious();target=None
  for _ in range(8):
   if node is None:break
   if node.tag==qn('w:p'):
    candidate=Paragraph(node,cap._parent)
    if candidate.style.name in ['Normal','论文正文']and len(candidate.text)>25 and not candidate._p.xpath('.//m:oMath'):
     target=candidate;break
   node=node.getprevious()
  if target is None:target=newp(cap,'','论文正文')
  font(target.add_run('相关'+('结构或显示示例见'if kind=='图'else'功能与指标见')),12)
  field(target,'REF '+('Figure'if kind=='图'else'Table')+str(num)+' \\h',kind+str(num));font(target.add_run('。'),12)

# Table style: repeat header, no vertical rules, top/bottom and header separator only.
for tb in D.tables:
 pr=tb._tbl.tblPr;b=pr.find(qn('w:tblBorders'))
 if b is not None:pr.remove(b)
 borders=OxmlElement('w:tblBorders')
 for edge in ['top','bottom','left','right','insideH','insideV']:
  el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single'if edge in['top','bottom']else'nil');el.set(qn('w:sz'),'8');el.set(qn('w:color'),'000000');borders.append(el)
 pr.append(borders)
 for i,row in enumerate(tb.rows):
  trpr=row._tr.get_or_add_trPr()
  if i==0:
   hdr=trpr.find(qn('w:tblHeader'))
   if hdr is None:hdr=OxmlElement('w:tblHeader');trpr.append(hdr)
  for cell in row.cells:
   cp=cell._tc.get_or_add_tcPr()
   for tag in ['w:tcBorders','w:shd']:
    for old in list(cp.findall(qn(tag))):cp.remove(old)
   if i==0:
    cb=OxmlElement('w:tcBorders');bo=OxmlElement('w:bottom');bo.set(qn('w:val'),'single');bo.set(qn('w:sz'),'4');bo.set(qn('w:color'),'000000');cb.append(bo);cp.append(cb)
   for p in cell.paragraphs:
    p.alignment=WD_ALIGN_PARAGRAPH.LEFT;p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.line_spacing=1.15;p.paragraph_format.space_after=Pt(4);p.paragraph_format.space_before=Pt(3)
    for run in p.runs:font(run,10.5,i==0)
    if len(tb.rows)<=9 or i==len(tb.rows)-1:p.paragraph_format.keep_with_next=True

# Normalize body/headings without changing section/header/footer geometry.
for p in D.paragraphs:
 name=p.style.name
 if name=='Normal'and p.text and not p._p.xpath('.//m:oMath'):
  if p is not P[2]and not p.text.startswith('关键词'):body_style(p)
 elif name in ['Report Fine','论文注释']:body_style(p,True)
 elif name in ['论文图注','论文表注']:
  p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.line_spacing=1.15;p.paragraph_format.space_before=Pt(4);p.paragraph_format.space_after=Pt(5);p.paragraph_format.keep_with_next=name=='论文表注'
 elif name in ['Heading 1','Heading 2','Module Heading']:
  level={'Heading 1':0,'Heading 2':1,'Module Heading':2}[name]
  outline(p,level if re.match(r'^(?:第|\d)',p.text) else 9)
  for run in p.runs:font(run,14 if level==0 else 12,True,'黑体')
  p.paragraph_format.keep_with_next=True
# Keep original page geometry but let revised body reflow; old fixed per-topic breaks
# would otherwise strand two-line overflow pages after adding notes/citations.
for p in D.paragraphs:
 if p.style.name != 'Heading 1':
  p.paragraph_format.page_break_before = False
for tb in D.tables:
 for row in tb.rows:
  trpr=row._tr.get_or_add_trPr()
  if trpr.find(qn('w:cantSplit')) is None:trpr.append(OxmlElement('w:cantSplit'))
# Clarify abstract is unnumbered and excluded from the numbered body hierarchy.
outline(P[3],9)

# Real heading-linked contents and separate figure/table lists; Word updates page references.
anchor=P[7]
toc_h=newp(anchor,'目  录','论文目录标题');toc_h.paragraph_format.page_break_before=True;toc_h.alignment=WD_ALIGN_PARAGRAPH.CENTER;font(toc_h.runs[0],16,True,'黑体');outline(toc_h,9)
info=newp(anchor,'本目录覆盖正文三级标题及参考文献；条目和页码可点击跳转。图表目录与正文交叉引用均为可更新域。','论文注释')
tp=newp(anchor,'','论文目录条目');field(tp,'TOC \\o "1-3" \\h \\z \\u','目录将在Word中更新')
lh=newp(anchor,'图表目录','论文目录标题');lh.paragraph_format.page_break_before=True;lh.alignment=WD_ALIGN_PARAGRAPH.CENTER;font(lh.runs[0],16,True,'黑体');outline(lh,9)
fp=newp(anchor,'','论文目录条目');field(fp,'TOC \\h \\z \\t "论文图注,1"','图目录')
sp=newp(anchor,'','论文目录条目');field(sp,'TOC \\h \\z \\t "论文表注,1"','表目录')
P[7].paragraph_format.page_break_before=True

# Turn every body source marker into an actual superscript internal hyperlink.
# Preserve complex equation/REF/SEQ fields while splitting only plain text runs.
for p in D.paragraphs:
 if p.style.name=='论文参考文献':continue
 for run in list(p.runs):
  if not re.search(r'\[\d+\]',run.text)or run._r.xpath('.//w:fldChar|.//w:instrText'):continue
  value=run.text;root=run._r.getparent();idx=root.index(run._r);root.remove(run._r)
  for part in re.split(r'(\[\d+\])',value):
   if not part:continue
   if re.fullmatch(r'\[\d+\]',part):
    n=int(part[1:-1]);citation(p,n);el=p._p[-1];p._p.remove(el);root.insert(idx,el);idx+=1
   else:
    rr=deepcopy(run._r)
    for child in list(rr):
     if child.tag!=qn('w:rPr'):rr.remove(child)
    tx=OxmlElement('w:t');tx.set(qn('xml:space'),'preserve');tx.text=part;rr.append(tx);root.insert(idx,rr);idx+=1

settings=D.settings.element
update=settings.find(qn('w:updateFields'))
if update is None:update=OxmlElement('w:updateFields');settings.append(update)
update.set(qn('w:val'),'true')
D.core_properties.author='';D.core_properties.last_modified_by='';D.core_properties.title='基于FPGA的多媒体广告牌设计文档';D.core_properties.subject='V132工程设计与复现';D.core_properties.comments='';D.core_properties.keywords='FPGA,多媒体广告牌,设计文档'
D.save(OUT)
# Remove unrelated personal properties from package metadata while preserving original media.
with zipfile.ZipFile(OUT)as z:parts={n:z.read(n)for n in z.namelist()}
from lxml import etree as E
if'docProps/app.xml'in parts:
 xml=E.fromstring(parts['docProps/app.xml'])
 for e in xml:
  if E.QName(e).localname in ['Company','Manager']:e.text=''
 parts['docProps/app.xml']=E.tostring(xml,xml_declaration=True,encoding='UTF-8',standalone=True)
if'docProps/custom.xml'in parts:
 xml=E.fromstring(parts['docProps/custom.xml'])
 for e in list(xml):xml.remove(e)
 parts['docProps/custom.xml']=E.tostring(xml,xml_declaration=True,encoding='UTF-8',standalone=True)
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED)as z:
 for n,v in parts.items():z.writestr(n,v)
summary={'input':str(SRC),'output':str(OUT),'version':'V132 r04','geometry_preserved':True,'figures':len(figs),'tables':len(tables),'references':len(refs),'toc_fields':3,'repository_verified':remote,'public_source_media_preserved':True,'claims':'Original V132 user-reported final functional, Flash and cold-start PASS; public data substitution is separately identified','docx_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()}
(ROOT/'03_review/build_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(summary,ensure_ascii=False,indent=2))

