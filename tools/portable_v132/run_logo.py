"""All-coordinate equivalence test for the public demo logo data; no hardware."""
from pathlib import Path
import os,subprocess,json,datetime,hashlib
r=Path(__file__).resolve().parents[2];rtl=r/'01_project/rtl';b=Path(os.environ['FPGA_IVERILOG_BIN'])
out=r/'04_evidence'/('public_logo_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
env=dict(os.environ);env.update(TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'),PATH=str(b)+os.pathsep+env.get('PATH',''))
src=[r/'02_tests/public_assets/tb_public_logo.sv',rtl/'video/official_logo.v',rtl/'visual/official_logo_compact_sync.v'];exe=out/'test.vvp'
c=subprocess.run([str(b/('iverilog.exe'if os.name=='nt'else'iverilog')),'-g2012','-s','tb_public_logo','-o',str(exe),*map(str,src)],capture_output=True,text=True,env=env,timeout=30);log=c.stdout+c.stderr;rc=None
if c.returncode==0:
 v=subprocess.run([str(b/('vvp.exe'if os.name=='nt'else'vvp')),str(exe)],capture_output=True,text=True,env=env,timeout=30);rc=v.returncode;log+=v.stdout+v.stderr
ok=c.returncode==0 and rc==0 and'PASS public logo'in log
(out/'run.log').write_text(log,encoding='utf-8');(out/'summary.json').write_text(json.dumps(dict(passed=ok,compile_rc=c.returncode,sim_rc=rc,source_sha256={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in src},scope='Public self-authored logo interface/data equivalence, not hardware or new P&R'),indent=2)+'\n',encoding='utf-8');print(log);print(out);raise SystemExit(0 if ok else 1)
