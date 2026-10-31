from pathlib import Path
import datetime,hashlib,json,os,subprocess
r=Path(__file__).resolve().parents[2];h=Path(__file__).resolve().parent;rtl=r/'01_project/rtl'
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
out=r/'04_evidence'/('v130_diagnostics_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir();rows=[]
for mode in (0,1):
 src=[h/'tb_v130_diagnostics.sv',rtl/'video/display_diagnostics_osd.v'];exe=out/f'mode{mode}.vvp';cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s','tb_v130_diagnostics',f'-Ptb_v130_diagnostics.FAULT_ONLY={mode}','-o',str(exe),*map(str,src)]
 c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=30);text=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  q=subprocess.run([str(b/'vvp.exe'),str(exe)],capture_output=True,text=True,env=env,timeout=40);text+=q.stdout+q.stderr;rc=q.returncode
 (out/f'mode{mode}.log').write_text(text,encoding='utf-8')
 row={'fault_only':mode,'passed':c.returncode==0 and rc==0 and 'PASS v089_display_diagnostics' in text and 'FATAL' not in text,'compile_returncode':c.returncode,'run_returncode':rc,'source_sha256':{s.relative_to(r).as_posix():hashlib.sha256(s.read_bytes()).hexdigest() for s in src+[rtl/'video/osd_font.vh']},'results':[s for s in text.splitlines() if s.startswith(('PASS','FATAL'))]};rows.append(row);print(row,flush=True)
 (out/'summary.json').write_text(json.dumps({'passed':len(rows)==2 and all(x['passed'] for x in rows),'scope':'Fault-only/always diagnostics modes, OSD enable passthrough, live/history/reset; NOT board','tests':rows},indent=2),encoding='utf-8')
 if not row['passed']:print(text[-5000:]);raise SystemExit(1)
print(out,flush=True)
