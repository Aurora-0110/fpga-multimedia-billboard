from pathlib import Path
import os,subprocess,json,datetime,hashlib
root=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=root/'01_project/rtl';b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
out=root/'04_evidence'/('v119_units_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir();env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'))
rows=[]
for label,top,sources,defines in [('old_gap','tb_v116_arbiter_gap',[t/'tb_v116_arbiter_gap.sv',t/'v114_media_sd_arbiter_reference.v'],['-DBASELINE']),('new_gap','tb_v116_arbiter_gap',[t/'tb_v116_arbiter_gap.sv',rtl/'tf/media_sd_arbiter.v'],[]),('first_error','tb_v116_diag_persistent',[t/'tb_v116_diag_persistent.sv',rtl/'video/display_diagnostics_osd.v'],[])]:
 hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources+[Path(__file__)]};exe=out/(label+'.vvp')
 c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(rtl),*defines,'-s',top,'-o',str(exe),*map(str,sources)],env=env,capture_output=True,text=True);text=c.stdout+c.stderr
 if c.returncode==0:
  c=subprocess.run([str(b/'vvp.exe'),str(exe)],env=env,capture_output=True,text=True,timeout=30);text+=c.stdout+c.stderr
 (out/(label+'.log')).write_text(text);passed=c.returncode==0 and'PASS'in text;rows.append(dict(case=label,passed=passed,source_sha256=hashes));print(label,text,flush=True)
 if not passed:break
rec=dict(passed=len(rows)==3 and all(row['passed']for row in rows),cases=rows);(out/'summary.json').write_text(json.dumps(rec,indent=2));print(out);raise SystemExit(0 if rec['passed']else 1)
