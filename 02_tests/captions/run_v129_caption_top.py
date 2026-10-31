"""Test the actual top caption-event wiring with injected WAV signals, not real TF/SDRAM."""
from pathlib import Path
import datetime,hashlib,json,os,re,subprocess,time
r=Path(__file__).resolve().parents[2];rtl=r/'01_project/rtl';out=r/'04_evidence'/('v129_caption_top_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');td=Path(r'D:\FPGA_Billboard\Anlogic\TD_6.2.1_Engineer_6.2.168.116\sim_release\eg4');native=out/'native';native.mkdir();prov=[]
for file,mod in [('eg_logic_io.v','EG_LOGIC_ODDR'),('eg_phy_glbl.v','glbl')]:
 p=td/file;raw=p.read_text(encoding='utf8');head=raw[:raw.index('`timescale')];m=re.search(r'\bmodule\s+'+mod+r'\s*\(.*?\bendmodule',raw,re.S);assert m;dest=native/(mod+'.v');dest.write_text(head+'\n`timescale 1ns/1ps\n'+m[0]+'\n',encoding='utf8');prov.append(dict(original=str(p),sha256=sha(p),module=mod,excerpt_sha256=sha(dest)))
(out/'native_provenance.json').write_text(json.dumps(prov,indent=2))
# Exclude only real native PLL/HDMI implementation wrappers that are replaced by the explicit simulation shells.
files=[p for p in rtl.rglob('*.v')if '/ip/'not in p.as_posix()]
files +=[rtl/'ip/pll_video720.v',rtl/'ip/hdmi_tx_wrap.v',rtl/'ip/hdmi_visual_wrap.v',r/'01_project/boards/idx_audio_visual_top.v',r/'02_tests/captions/tb_v129_caption_top.sv',native/'EG_LOGIC_ODDR.v',native/'glbl.v']
deps=list(dict.fromkeys(files+list(rtl.rglob('*.vh'))+[Path(__file__)]));bound={p.relative_to(r).as_posix():sha(p)for p in deps}
env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'),TMPDIR=str(r/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
exe=out/'top.vvp';begin=time.monotonic();c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(rtl),'-DSIM_PLL_BEHAV','-s','tb_v129_caption_top','-s','glbl','-o',str(exe),*map(str,files)],env=env,capture_output=True,text=True,timeout=45);text=c.stdout+c.stderr;rc=None
if c.returncode==0:
 try:v=subprocess.run([str(b/'vvp.exe'),str(exe)],env=env,capture_output=True,text=True,timeout=90);text+=v.stdout+v.stderr;rc=v.returncode
 except subprocess.TimeoutExpired:text+='\nTIMEOUT\n'
(out/'run.log').write_text(text,encoding='utf8');rec=dict(passed=c.returncode==0 and rc==0 and 'PASS v129 ACTUAL' in text and 'FATAL'not in text and 'ERROR'not in text,source_sha256=bound,compile_rc=c.returncode,sim_rc=rc,elapsed_seconds=round(time.monotonic()-begin,3),results=[l for l in text.splitlines()if l.startswith(('PASS','FATAL','ERROR'))],scope='ACTUAL top production caption/gain enable and real-sample event wiring with injected valid/consume/first/session/PCM and clock/macro shells. Not WAV parsing,TF,physical SDRAM or hardware.')
(out/'summary.json').write_text(json.dumps(rec,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in rec.items()if k!='source_sha256'},indent=2));print(out)
if not rec['passed']:print(text[-4000:])
raise SystemExit(0 if rec['passed']else 1)
