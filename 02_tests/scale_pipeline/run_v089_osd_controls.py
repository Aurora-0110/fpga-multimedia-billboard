from pathlib import Path
import datetime,hashlib,json,os,re,subprocess,time
r=Path(__file__).resolve().parents[2];h=Path(__file__).resolve().parent;rtl=r/'01_project/rtl'
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
out=r/'04_evidence'/('v089_osd_controls_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
logo_file=rtl/'video/official_logo.v'
logo_text=logo_file.read_text(encoding='utf-8').split('endmodule',1)[0]
logo_rows=re.findall(r"6'd(\d+):\s*rowbits=224'h([0-9a-fA-F]+)",logo_text)
assert len(logo_rows)==56 and {int(y) for y,_ in logo_rows}==set(range(56))
logo_nontransparent=sum(sum(((int(v,16)>>(2*x))&3)!=0 for x in range(112)) for _,v in logo_rows)
assert logo_nontransparent==2017
(out/'logo_coverage.json').write_text(json.dumps({'method':'Independent 2-bit palette decode from source ROM, not DUT coverage',
 'source_nontransparent_pixels':logo_nontransparent,'expanded_expected_pixels':logo_nontransparent*4,
 'rom_sha256':hashlib.sha256(logo_file.read_bytes()).hexdigest()},indent=2),encoding='utf-8')
rows=[]
for name,files in [('controls',['common/picture_controls_osd.v']),('osd',['video/osd_layers_full720.v','video/official_logo.v'])]:
 src=[h/f'tb_v089_{name}.sv',*[rtl/f for f in files]];cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s','tb_v089_'+name,'-o',str(out/(name+'.vvp')),*map(str,src)]
 start=time.monotonic();c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=30);text=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  try:
   c2=subprocess.run([str(b/'vvp.exe'),str(out/(name+'.vvp'))],capture_output=True,text=True,env=env,timeout=240);text+=c2.stdout+c2.stderr;rc=c2.returncode
  except subprocess.TimeoutExpired:text+='\nTIMEOUT\n'
 (out/(name+'.log')).write_text(text,encoding='utf-8')
 row={'name':name,'passed':c.returncode==0 and rc==0 and 'PASS' in text and 'FATAL' not in text,'compile_returncode':c.returncode,'run_returncode':rc,'source_sha256':{s.relative_to(r).as_posix():hashlib.sha256(s.read_bytes()).hexdigest() for s in src+[rtl/'video/osd_font.vh']},'elapsed_seconds':round(time.monotonic()-start,3),'results':[s for s in text.splitlines() if s.startswith(('PASS','FATAL'))]};rows.append(row)
 (out/'summary.json').write_text(json.dumps({'passed':len(rows)==2 and all(x['passed'] for x in rows),'scope':'New short-chord controls and full720p OSD active raster/passthrough checks; NOT SD/board','tests':rows},indent=2),encoding='utf-8');print(row,flush=True)
 if not row['passed']:print(text[-5000:],flush=True);raise SystemExit(1)
print(out,flush=True)
