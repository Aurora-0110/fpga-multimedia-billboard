from pathlib import Path
import os,sys,subprocess,json,hashlib,datetime
r=Path(__file__).resolve().parents[1];out=r/'04_evidence'/('v130_diagnostic_units_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'))
rows=[]
for top,tb in [('tb_v103_diagnostics','02_tests/acceptance/tb_v103_diagnostics.sv'),('tb_v116_diag_persistent','02_tests/wav/tb_v116_diag_persistent.sv')]:
 src=[r/tb,r/'01_project/rtl/video/display_diagnostics_osd.v'];exe=out/(top+'.vvp')
 c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(r/'01_project/rtl'),'-s',top,'-o',str(exe),*map(str,src)],env=env,capture_output=True,text=True);text=c.stdout+c.stderr;rc=-1
 if c.returncode==0:
  d=subprocess.run([str(b/'vvp.exe'),str(exe)],env=env,capture_output=True,text=True,timeout=30);text+=d.stdout+d.stderr;rc=d.returncode
 (out/(top+'.log')).write_text(text,encoding='utf-8');row=dict(case=top,passed=c.returncode==0 and rc==0 and 'PASS'in text and 'FATAL'not in text,source_sha256={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in src+[r/'01_project/rtl/video/osd_font.vh']});rows.append(row);print(top,row['passed'],text[-500:],flush=True)
rec=dict(passed=all(x['passed']for x in rows),complete=len(rows)==2,cases=rows,scope='Fresh hidden/history/fault five-source capture,first audio error single-clock capture;4-cycle pixel alignment covered by separate V130 rasters.')
(out/'summary.json').write_text(json.dumps(rec,indent=2),encoding='utf-8');print(out);sys.exit(0 if rec['passed']else 1)
