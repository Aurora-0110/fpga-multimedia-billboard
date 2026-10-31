"""v072 bounded digital control acceptance. Never downloads to hardware."""
from pathlib import Path
import os,subprocess,json,hashlib,datetime,argparse
r=Path(__file__).resolve().parents[1];t=r/'02_tests';p=r/'01_project';rtl=p/'rtl'
a=argparse.ArgumentParser();a.add_argument('--top',action='store_true');args=a.parse_args();args.top=True
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
out=r/'04_evidence'/('v080_top_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
cases=[]
if not args.top:
 for dwell in [1,2,8]:
  for default in [0,1]:
   cases.append((f'modes_d{dwell}_default{default}','tb_v070_modes',[t/'tb_v070_modes.sv',rtl/'tf/tf_playlist_ctrl.v'],[f'-Ptb_v070_modes.DWELL={dwell}',f'-Ptb_v070_modes.DEFAULT_AUTO={default}']))
 cases.append(('keys','tb_v068_keys',[t/'tb_v068_keys.sv',rtl/'tf/tf_playlist_ctrl.v',rtl/'common/key_debounce.v'],[]))
else:
 import re
 native=out/'native';native.mkdir();provenance=[]
 td=Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\sim_release\eg4')
 for filename,mod in [('eg_logic_io.v','EG_LOGIC_ODDR'),('eg_phy_glbl.v','glbl')]:
  src=td/filename;raw=src.read_text(encoding='utf8');head=raw[:raw.index('`timescale')]
  match=re.search(r'\bmodule\s+'+mod+r'\s*\(.*?\bendmodule',raw,re.S);assert match
  dest=native/(mod+'.v');dest.write_text(head+'\n`timescale 1ns/1ps\n'+match[0]+'\n',encoding='utf8')
  provenance.append({'original':str(src),'original_sha256':sha(src),'module':mod,'excerpt_sha256':sha(dest)})
 (out/'native_provenance.json').write_text(json.dumps(provenance,indent=2))
 sources=[*sorted((rtl/'audio').glob('*.v')),*sorted((rtl/'tf').glob('*.v')),*[rtl/s for s in ['ip/pll_video720.v','ip/hdmi_tx_wrap.v','mem/sdram_ctrl.v','mem/async_fifo.v','video/idx_writer.v','video/idx_reader.v','video/idx_display.v','video/idx_pipeline.v','video/idx_dual_pipeline.v','video/idx_slide_reader.v','video/official_logo.v','video/osd_layers.v','video/picture_adjust.v','common/picture_controls.v','video/fb_session_ctrl.v','video/video_timing.v','video/tmds_encoder.v','video/tmds_serializer.v','common/reset_release.v','common/key_debounce.v','common/bist_status_595.v']]]
 cases.append(('top','tb_v080_top',[t/'tb_v080_top.sv',p/'boards/idx_video_top.v',native/'EG_LOGIC_ODDR.v',native/'glbl.v',*sources],['-DSIM_PLL_BEHAV','-s','glbl']))
rows=[]
for name,top,src,extra in cases:
 exe=out/(name+'.vvp');cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s',top,*extra,'-o',str(exe),*map(str,src)]
 c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30);text=c.stdout+c.stderr
 row={'name':name,'compile_rc':c.returncode,'passed':False,'compile_command':cmd,'source_sha256':{s.relative_to(r).as_posix():sha(s) for s in src}}
 if c.returncode==0:
  try:
   v=subprocess.run([str(b/'vvp.exe'),str(exe)],env=env,capture_output=True,text=True,timeout=60);text+=v.stdout+v.stderr;row.update(sim_rc=v.returncode,passed=v.returncode==0 and 'PASS' in v.stdout and 'ERROR' not in v.stdout)
  except subprocess.TimeoutExpired as e:row['timeout']=True;text+=str(e)
 (out/(name+'.log')).write_text(text,encoding='utf8');row['result_lines']=[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR'))];rows.append(row)
 print(name,row['passed'],row['result_lines'],flush=True)
summary={'passed':all(x['passed'] for x in rows),'complete':len(rows)==len(cases),'scope':'Real display/top/wrapper gate and RGB wiring; injected FIFO values/content epoch/coordinates; behavioral PLL and undriven SDRAM shell, NOT TF/memory data or physical verification','tests':rows}
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(out,flush=True)
raise SystemExit(0 if summary['passed'] else 1)
