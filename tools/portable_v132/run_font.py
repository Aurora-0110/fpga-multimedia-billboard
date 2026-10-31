# Portable harness copy; production RTL and original harness remain untouched.
"""Independent source-font oracle -> exhaustive runtime compact-UI datapath."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib,datetime,subprocess,os
R=Path(__file__).resolve().parents[2];assert '01_versions'not in R.parts
OUT=R/'04_evidence'/('v132_font_datapath_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));OUT.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=R/'03_docs/v130_ui_font_spec.json';s=json.loads(spec.read_text('utf8'));fontfile=R/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf';assert sha(fontfile)==s['font_sha256'];font=ImageFont.truetype(str(fontfile),14);rows=[]
for g in range(128):
 im=Image.new('L',(16,16));ch=s['glyphs'][g]if g<len(s['glyphs'])else' '
 if ch!=' ':
  l,t,r,b=font.getbbox(ch);ImageDraw.Draw(im).text(((16-r+l)//2-l,(16-b+t)//2-t),ch,font=font,fill=255)
 for y in range(16):rows.append(sum(1<<(15-x)for x in range(16)if im.getpixel((x,y))>=112))
(OUT/'font.hex').write_text(''.join(f'{r:04x}\n'for r in rows),encoding='ascii')
b=Path(os.environ['FPGA_IVERILOG_BIN']);env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(R/'00_tmp'),TMP=str(R/'00_tmp'),PYTHONDONTWRITEBYTECODE='1');rtl=R/'01_project/rtl';tb=R/'02_tests/ui_compact/tb_v132_font_datapath.sv';exe=OUT/'test.vvp';cmd=[str(b/('iverilog.exe' if os.name=='nt' else 'iverilog')),'-g2012','-Wall','-I',str(rtl),'-s','tb_v132_font_datapath','-o',str(exe),str(tb),str(rtl/'visual/media_ui_overlay.v')]
c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=60);text=c.stdout+c.stderr;rc=None
if c.returncode==0:
 d=subprocess.run([str(b/('vvp.exe' if os.name=='nt' else 'vvp')),str(exe),f'+FONT={OUT}/font.hex'],env=env,capture_output=True,text=True,timeout=60);rc=d.returncode;text+=d.stdout+d.stderr
(OUT/'run.log').write_text(text,encoding='utf8');ok=c.returncode==0 and rc==0 and'PASS'in text and'FATAL'not in text
sources=[tb,Path(__file__),spec,fontfile,rtl/'visual/media_ui_overlay.v',rtl/'visual/media_ui_font_packed_v132.vh',rtl/'visual/media_ui_zh_text_init.vh',rtl/'visual/media_ui_zh_glyph_ids.vh']
record=dict(passed=ok,complete=True,checks=65536 if ok else None,source_sha256={p.relative_to(R).as_posix():sha(p)for p in sources},scope='Independent Noto font raster verifies packed ROM data plus actual runtime word/bit/bank/override path; not hardware.')
(OUT/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(text[-1800:]);print(OUT);raise SystemExit(0 if ok else 1)
