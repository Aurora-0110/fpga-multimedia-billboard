"""Dedicated active media gesture/timeline/caption tests, no hardware operations."""
from pathlib import Path
import os,json,hashlib,subprocess,datetime,time,concurrent.futures
from PIL import Image,ImageDraw,ImageFont
r=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=r/'01_project/rtl';bin=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
out=r/'04_evidence'/('v130_media_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
env=dict(os.environ);env.update(TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'),TMPDIR=str(r/'00_tmp'),PYTHONDONTWRITEBYTECODE='1');env['PATH']=str(bin)+os.pathsep+env.get('PATH','')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=json.loads((r/'03_docs/v107_subtitle_spec.json').read_text(encoding='utf8'));fontfile=r/'07_reference/fonts/noto_cjk/NotoSansCJKsc-Medium.otf';assert sha(fontfile)==spec['font_sha256'];font=ImageFont.truetype(str(fontfile),14)
rows=[]
for n in range(128):
 ch=spec['glyphs'][n] if n<len(spec['glyphs']) else ' ';im=Image.new('L',(16,16))
 if ch!=' ':
  l,tt,rr,b=font.getbbox(ch);ImageDraw.Draw(im).text(((16-(rr-l))//2-l,(16-(b-tt))//2-tt),ch,font=font,fill=255)
 rows.extend(sum(1<<(15-x) for x in range(16) if im.getpixel((x,y))>=112) for y in range(16))
(out/'font.hex').write_text(''.join(f'{v:04x}\n' for v in rows))
text=[];length=[]
for n in range(8):
 line=spec['cues'][n]['text'] if n<len(spec['cues']) else '';length.append(len(line));text.extend(spec['glyph_ids'][c] for c in line.ljust(32))
(out/'text.hex').write_text(''.join(f'{v:02x}\n' for v in text));(out/'length.hex').write_text(''.join(f'{v:08x}\n' for v in length))
jobs=[('controls','tb_v130_controls',[t/'tb_v130_controls.sv',rtl/'common/media_controls.v'],[],[]),('ui_pin','tb_v130_ui_pin',[t/'tb_v130_ui_pin.sv',rtl/'common/media_controls.v',rtl/'visual/media_ui_overlay.v'],[],[])]
def run(job):
 name,top,src,extra,plus=job;begin=time.monotonic();exe=out/(name+'.vvp')
 deps=src+list((rtl/'visual').glob('subtitle_*.vh'))+list((rtl/'visual').glob('media_ui_*.vh'))+[Path(__file__),fontfile,r/'03_docs/v107_subtitle_spec.json']
 bound={p.relative_to(r).as_posix():sha(p) for p in deps}
 c=subprocess.run([str(bin/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s',top,*extra,'-o',str(exe),*map(str,src)],env=env,capture_output=True,text=True,timeout=45);log=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  try:v=subprocess.run([str(bin/'vvp.exe'),str(exe),*plus],env=env,capture_output=True,text=True,timeout=360);log+=v.stdout+v.stderr;rc=v.returncode
  except subprocess.TimeoutExpired:log+='\nTIMEOUT\n'
 (out/(name+'.log')).write_text(log,encoding='utf8')
 rec=dict(name=name,passed=c.returncode==0 and rc==0 and 'PASS' in log and 'FATAL' not in log and 'ERROR' not in log,compile_rc=c.returncode,sim_rc=rc,elapsed_seconds=round(time.monotonic()-begin,3),source_sha256=bound,results=[l for l in log.splitlines() if l.startswith(('PASS','FATAL','ERROR'))]);print(json.dumps({k:v for k,v in rec.items() if k!='source_sha256'},ensure_ascii=False),flush=True)
 if not rec['passed']:print(log[-5000:],flush=True)
 return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(run,jobs))
summary=dict(passed=all(v['passed'] for v in records),complete=len(records)==len(jobs),tests=records,scope='Fresh active media-control gestures and UI pin integration only; V128 sample captions tested separately. No hardware')
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
for p in out.glob('*.ppm'):Image.open(p).save(p.with_suffix('.png'))
print(out,flush=True);raise SystemExit(0 if summary['passed'] else 1)
