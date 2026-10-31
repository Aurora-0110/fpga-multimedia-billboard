"""Production dual-domain wrapper + four-lane native TD ODDR scoreboard.
Extracts only unmodified plaintext modules from the user's installed official
TD library for Icarus; records source/excerpt hashes. No encrypted logic used.
"""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,re
ap=argparse.ArgumentParser();ap.add_argument('--iverilog-bin',type=Path,required=True);ap.add_argument('--td-sim-dir',type=Path,required=True);a=ap.parse_args()
t=Path(__file__).resolve().parent;b=a.iverilog_bin.resolve();out=t/'build/v076_audio_native';out.mkdir(parents=True,exist_ok=True);log=t/'logs/v076';log.mkdir(parents=True,exist_ok=True)
provenance=[]
for name,mod in [('eg_logic_io.v','EG_LOGIC_ODDR'),('eg_phy_glbl.v','glbl')]:
 p=a.td_sim_dir/name;raw=p.read_bytes();text=raw.decode('utf8');head=text[:text.index('`timescale')]
 match=re.search(r'\bmodule\s+'+mod+r'\s*\(.*?\bendmodule',text,re.S);assert match,mod
 excerpt=head+'\n`timescale 1ns/1ps\n'+match[0]+'\n';q=out/(mod+'.v');q.write_text(excerpt,encoding='utf8')
 provenance.append(dict(original=str(p),module=mod,source_sha256=hashlib.sha256(raw).hexdigest(),excerpt_sha256=hashlib.sha256(q.read_bytes()).hexdigest(),unchanged_module=True))
env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
rows=[]
project=t.parent/'01_project'
for phase in [137,370,1111]:
 files=[t/'tb_v076_audio_native.sv',project/'rtl/video/tmds_serializer.v',project/'rtl/video/tmds_encoder.v',project/'rtl/ip/hdmi_tx_wrap.v',project/'rtl/common/reset_release.v',project/'rtl/video/video_timing.v',*sorted((project/'rtl/audio').glob('*.v')),out/'EG_LOGIC_ODDR.v',out/'glbl.v']
 cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-s','tb_v076_audio_native','-s','glbl','-P',f'tb_v076_audio_native.PHASE_PS={phase}','-o',str(out/f'test_{phase}.vvp'),*[str(f) for f in files]]
 c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30);text=c.stdout+c.stderr
 row=dict(phase_ps=phase,compile_returncode=c.returncode,passed=False,provenance=provenance,compile_command=cmd)
 if c.returncode==0:
  r=subprocess.run([str(b/'vvp.exe'),str(out/f'test_{phase}.vvp')],env=env,capture_output=True,text=True,timeout=30);text+=r.stdout+r.stderr;row.update(sim_returncode=r.returncode,passed=r.returncode==0 and 'PASS audio_native' in text)
 row['result_lines']=[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR'))];rows.append(row)
 (log/f'dual_reset_{phase}.log').write_text(text,encoding='utf8');print(text,flush=True)
 if not row['passed']:break
passed=len(rows)==3 and all(r['passed'] for r in rows)
(t/'tmds_v076_audio_native_results.json').write_text(json.dumps(dict(passed=passed,cases=rows),indent=2),encoding='utf8')
raise SystemExit(0 if passed else 1)
