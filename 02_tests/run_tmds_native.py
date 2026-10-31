"""Native TD ODDR word/DDR-bit scoreboard, not SIM_TMDS_MODEL.
Extracts only unmodified plaintext modules from the user's installed official
TD library for Icarus; records source/excerpt hashes. No encrypted logic used.
"""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,re
ap=argparse.ArgumentParser();ap.add_argument('--iverilog-bin',type=Path,required=True);ap.add_argument('--td-sim-dir',type=Path,required=True);a=ap.parse_args()
t=Path(__file__).resolve().parent;b=a.iverilog_bin.resolve();out=t/'build/native_oddr';out.mkdir(parents=True,exist_ok=True);log=t/'logs/v054';log.mkdir(parents=True,exist_ok=True)
provenance=[]
for name,mod in [('eg_logic_io.v','EG_LOGIC_ODDR'),('eg_phy_glbl.v','glbl')]:
 p=a.td_sim_dir/name;raw=p.read_bytes();text=raw.decode('utf8');head=text[:text.index('`timescale')]
 match=re.search(r'\bmodule\s+'+mod+r'\s*\(.*?\bendmodule',text,re.S);assert match,mod
 excerpt=head+'\n`timescale 1ns/1ps\n'+match[0]+'\n';q=out/(mod+'.v');q.write_text(excerpt,encoding='utf8')
 provenance.append(dict(original=str(p),module=mod,source_sha256=hashlib.sha256(raw).hexdigest(),excerpt_sha256=hashlib.sha256(q.read_bytes()).hexdigest(),unchanged_module=True))
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-s','tb_tmds_native','-s','glbl','-o',str(out/'test.vvp'),str(t/'tb_tmds_native.sv'),str(t.parent/'01_project/rtl/video/tmds_serializer.v'),str(out/'EG_LOGIC_ODDR.v'),str(out/'glbl.v')]
c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30);text=c.stdout+c.stderr
row=dict(compile_returncode=c.returncode,passed=False,provenance=provenance,compile_command=cmd)
if c.returncode==0:
 r=subprocess.run([str(b/'vvp.exe'),str(out/'test.vvp')],env=env,capture_output=True,text=True,timeout=30);text+=r.stdout+r.stderr;row.update(sim_returncode=r.returncode,passed=r.returncode==0 and 'PASS native_ODDR' in text)
row['result_lines']=[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR'))]
(log/'native_oddr.log').write_text(text,encoding='utf8');(t/'tmds_native_results.json').write_text(json.dumps(row,indent=2),encoding='utf8');print(text);raise SystemExit(0 if row['passed'] else 1)
