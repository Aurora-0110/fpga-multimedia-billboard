"""v102 hidden UI: independent text/raster oracle and original gesture regression."""
from pathlib import Path
import os,json,hashlib,datetime,subprocess,re,time
r=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=r/'01_project/rtl'
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','');tmp=r/'00_tmp';tmp.mkdir(exist_ok=True);env.update(TEMP=str(tmp),TMP=str(tmp),TMPDIR=str(tmp),PYTHONDONTWRITEBYTECODE='1')
out=r/'04_evidence'/('v102_ui_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
cases=[]
for br in range(-64,65,16):
 for gain in range(2,7):
  for field in range(3):cases.append(dict(br=br,gain=gain,field=field,mode=True,osd=True,image=field,loading=False,failed=False,error=0,audio=True,pv=True,keys=0))
for state in [dict(keys=1),dict(keys=2),dict(keys=3),dict(failed=True,error=0xA7),dict(loading=True,pv=False,audio=False),dict(pv=False,audio=False),dict(mode=False,osd=False)]:
 c=dict(cases[-1]);c.update(state);cases.append(c)
cases.append(dict(br=32,gain=5,field=1,mode=False,osd=False,image=2,loading=False,failed=False,error=0,audio=True,pv=True,keys=1))
last=0;text=[];vectors=[];spec=[]
for c in cases:
 if c['keys']:last=c['keys']
 lines=[list(' '*64) for _ in range(4)]
 def put(row,col,value):
  assert col+len(value)<=64
  lines[row][col:col+len(value)]=value
 put(0,0,f"BR:{c['br']:+03d}");put(0,8,f"CT:{c['gain']*25:03d}%");put(0,17,'EDIT:'+['VIEW','BRI ','CONT'][c['field']]);put(0,32,'AUTO' if c['mode'] else 'MAN ');put(0,39,'IMG:'+chr(65+c['image']));put(0,46,'OSD:'+('ON' if c['osd'] else 'OFF'))
 put(1,0,'K0:'+('DN' if c['keys']&1 else 'UP'));put(1,9,['NEXT','B-','C-'][c['field']]);put(1,21,'K1:'+('DN' if c['keys']&2 else 'UP'));put(1,30,['AUTO/MANUAL','B+','C+'][c['field']]);put(1,44,'LAST:'+['NONE','K0','K1','BOTH'][last]);
 put(2,0,'K0+K1 TAP:OVERLAYS  HOLD:VIEW/BRIGHT/CONTRAST')
 state=f"ERR{c['error']:02X}" if c['failed'] or c['error'] else ('LOAD' if c['loading'] else ('READY' if c['pv'] else 'WAIT'))
 put(3,0,'TF:'+state);put(3,11,'VIDEO:'+('ON' if c['pv'] else 'WAIT'));put(3,23,'AUDIO:'+('ON' if c['audio'] else 'OFF'));put(3,35,'UI:'+('AUTO HIDE' if c['field']==0 else 'EDIT'))
 text.extend(ord(ch) for line in lines for ch in line)
 v=(c['br']&255)|(c['gain']<<8)|(c['field']<<11)|(c['mode']<<13)|(c['osd']<<14)|(c['image']<<15)|(c['loading']<<17)|(c['failed']<<18)|(c['error']<<19)|(c['audio']<<27)|(c['pv']<<28)|(c['keys']<<29);vectors.append(v);spec.append({'parameters':c,'expected_rows':[''.join(line) for line in lines]})
(out/'vectors.hex').write_text(''.join(f'{v:016x}\n' for v in vectors));(out/'text.hex').write_text(''.join(f'{v:02x}\n' for v in text));(out/'text_spec.json').write_text(json.dumps(spec,indent=2))
font=[0]*(256*7)
for ch,raw in re.findall(r'"(.)":bits=35\'b([01_]+);',(rtl/'video/osd_font.vh').read_text()):
 bits=int(raw.replace('_',''),2)
 for y in range(7):font[ord(ch)*7+y]=(bits>>(5*(6-y)))&31
assert font[ord('A')*7]==14 and font[ord('X')*7+3]==4
(out/'font.hex').write_text(''.join(f'{v:02x}\n' for v in font))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
jobs=[('uptime','tb_v102_uptime',[t/'tb_v102_uptime.sv',rtl/'visual/osd_layers_visual.v',rtl/'visual/official_logo_compact_sync.v'],[]),('controls','tb_v089_controls',[r/'02_tests/scale_pipeline/tb_v089_controls.sv',rtl/'common/picture_controls_osd.v'],[]),('ui','tb_v102_ui',[t/'tb_v102_ui.sv',rtl/'visual/ui_help_overlay.v'],[f'+VECTORS={out}/vectors.hex',f'+TEXT={out}/text.hex',f'+FONT={out}/font.hex',f'+CASES={len(cases)}',f'+PREVIEW={out}/v102_ui_actual.ppm'])]
records=[]
for name,top,src,plus in jobs:
 start=time.monotonic();exe=out/(name+'.vvp');cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s',top,'-o',str(exe),*map(str,src)]
 c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=60);log=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  try:
   v=subprocess.run([str(b/'vvp.exe'),str(exe),*plus],env=env,capture_output=True,text=True,timeout=240);log+=v.stdout+v.stderr;rc=v.returncode
  except subprocess.TimeoutExpired:log+='\nTIMEOUT\n'
 (out/(name+'.log')).write_text(log,encoding='utf-8')
 record={'name':name,'passed':c.returncode==0 and rc==0 and 'PASS' in log and 'FATAL' not in log,'compile_returncode':c.returncode,'run_returncode':rc,'elapsed_seconds':round(time.monotonic()-start,3),'source_sha256':{p.relative_to(r).as_posix():sha(p) for p in src+[rtl/'video/osd_font.vh']},'results':[x for x in log.splitlines() if x.startswith(('PASS','FATAL'))]};records.append(record)
 summary={'passed':len(records)==len(jobs) and all(x['passed'] for x in records),'scope':'143 independent character vectors / three full720p UI rasters / original key gesture regression / six initialized BCD rollover boundaries; no board or TF-to-HDMI acceptance','complete':len(records)==len(jobs),'tests':records}
 (out/'summary.json').write_text(json.dumps(summary,indent=2));print(record,flush=True)
 if not record['passed']:print(log[-5000:],flush=True);raise SystemExit(1)
try:
 from PIL import Image
 Image.open(out/'v102_ui_actual.ppm').save(out/'v102_ui_actual.png')
except ImportError:pass
print(out,flush=True)
