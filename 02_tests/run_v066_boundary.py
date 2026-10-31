from pathlib import Path
import os,subprocess,json,hashlib,datetime
from PIL import Image
r=Path(__file__).resolve().parents[1];t=r/'02_tests';p=r/'01_project';e=r/'04_evidence'/('boundary_'+datetime.datetime.now().strftime('%H%M%S'));e.mkdir()
b=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'));env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
text=(p/'boards/idx_video_top.v').read_text(encoding='utf8');mux=text[text.index(' reg win_d,edge_d;'):text.index(' hdmi_tx_wrap #')];(e/'v066_actual_screen_mux.vh').write_text(mux)
rows=[]
for letter in 'ABC':
 f=r/f'06_test_media/playlist_ABC/{letter}.BMP';im=Image.open(f).convert('RGB');assert im.size==(640,480)
 data=[((a>>5)<<5)|((b>>5)<<2)|(c>>6) for a,b,c in im.getdata()];fixture=e/(letter+'.hex');fixture.write_text(''.join(f'{v:02x}\n' for v in data))
 row={'image':letter,'bmp_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'right_edge_uniform':len(set(im.getpixel((639,y)) for y in range(480)))==1,'right_edge_top':im.getpixel((639,0)),'right_edge_bottom':im.getpixel((639,479))}
 exe=e/(letter+'.vvp');cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(e),'-s','tb_v066_boundary','-o',str(exe),str(t/'tb_v066_boundary.sv'),str(p/'rtl/video/video_timing.v'),str(p/'rtl/video/idx_display.v'),str(p/'rtl/mem/async_fifo.v')]
 c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30);(e/(letter+'_compile.log')).write_text(c.stdout+c.stderr);row['compile_rc']=c.returncode
 if c.returncode==0:
  try:
   c=subprocess.run([str(b/'vvp.exe'),str(exe),'+IMAGE='+fixture.as_posix()],env=env,capture_output=True,text=True,timeout=240);log=c.stdout+c.stderr;row.update(sim_rc=c.returncode,passed=c.returncode==0 and 'PASS boundary' in log)
  except subprocess.TimeoutExpired as ex:
   def text(v):return v.decode(errors='replace') if isinstance(v,bytes) else (v or '')
   log=text(ex.stdout)+text(ex.stderr)+'\nHOST TIMEOUT after 240 seconds; NOT PASS\n';row.update(passed=False,complete=False,host_timeout_seconds=240)
  (e/(letter+'.log')).write_text(log);print(letter,log,flush=True)
 rows.append(row);(e/'summary.json').write_text(json.dumps({'scope':'Real async FIFO, display, 720p timing and actual top mux. No SPI/SDRAM/TMDS PHY or monitor; source assets not TF readback.','passed':all(x.get('passed',False) for x in rows) and len(rows)==3,'cases':rows},indent=2)+'\n')
 if not row.get('passed'):break
raise SystemExit(0 if len(rows)==3 and all(x.get('passed') for x in rows) else 1)
