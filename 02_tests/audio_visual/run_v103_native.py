"""Actual externalPCM HDMI wrapper, native TD ODDR at three phase offsets."""
from pathlib import Path
import hashlib,json,os,subprocess,re,datetime
root=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');td=Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\sim_release\eg4')
out=root/'04_evidence'/('v103_visual_native_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir();env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
temp_dir=root/'00_tmp';temp_dir.mkdir(exist_ok=True)
env.update(TEMP=str(temp_dir),TMP=str(temp_dir),TMPDIR=str(temp_dir),PYTHONDONTWRITEBYTECODE='1')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
provenance=[]
for filename,mod in [('eg_logic_io.v','EG_LOGIC_ODDR'),('eg_phy_glbl.v','glbl')]:
 src=td/filename;raw=src.read_text(encoding='utf8');head=raw[:raw.index('`timescale')];match=re.search(r'\bmodule\s+'+mod+r'\s*\(.*?\bendmodule',raw,re.S);assert match
 dest=out/(mod+'.v');dest.write_text(head+'\n`timescale 1ns/1ps\n'+match[0]+'\n',encoding='utf8');provenance.append({'original':str(src),'original_sha256':sha(src),'module':mod,'excerpt_sha256':sha(dest)})
src=[t/'tb_visual_native.sv',*[rtl/s for s in ['ip/hdmi_visual_wrap.v','visual/audio_pcm_frontend.v','audio/i2s_test_tone.v','audio/hdmi_audio_packets.v','video/tmds_encoder.v','video/tmds_serializer.v','video/video_timing.v','common/reset_release.v']],out/'EG_LOGIC_ODDR.v',out/'glbl.v']
rows=[]
for phase in [137,370,1111]:
 exe=out/f'native_{phase}.vvp';cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s','tb_visual_native','-s','glbl',f'-Ptb_visual_native.PHASE_PS={phase}','-o',str(exe),*map(str,src)]
 c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30);text=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  v=subprocess.run([str(b/'vvp.exe'),str(exe)],env=env,capture_output=True,text=True,timeout=90);text+=v.stdout+v.stderr;rc=v.returncode
 (out/f'{phase}.log').write_text(text,encoding='utf8');row={'phase_ps':phase,'compile_rc':c.returncode,'sim_rc':rc,'passed':c.returncode==0 and rc==0 and 'PASS audio_native' in text and 'FATAL' not in text,'source_sha256':{f.relative_to(root).as_posix():sha(f) for f in src+[rtl/'visual/dft_cos_q10.vh']},'results':[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR'))]};rows.append(row);print(row['passed'],row['results'],flush=True)
 if not row['passed']:print(text);break
summary={'passed':len(rows)==3 and all(r['passed'] for r in rows),'scope':'Digital4lane externalPCM HDMI wrapper+installed native ODDR; behavioral clocks/lock, not electrical acceptance','tests':rows,'provenance':provenance}
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(out)
raise SystemExit(0 if summary['passed'] else 1)
