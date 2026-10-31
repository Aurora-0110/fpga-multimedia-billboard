"""Capture representative selected UI-font addressing signals; never programs hardware."""
from pathlib import Path
import argparse,os,subprocess,sys,datetime,gzip,hashlib,json
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--iverilog-bin',required=True);a=p.parse_args();b=Path(a.iverilog_bin)
env=dict(os.environ);env.update(PYTHONDONTWRITEBYTECODE='1',TEMP=str(R/'00_tmp'),TMP=str(R/'00_tmp'))
subprocess.run([sys.executable,'-B',str(R/'tools/reproduce.py'),'test','--case','font','--iverilog-bin',str(b)],env=env,check=True)
font=sorted((R/'04_evidence').glob('v132_font_datapath_*/font.hex'))[-1]
out=R/'04_evidence'/('v133_font_wave_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
trace=out/'trace_capture.sv'
trace.write_text('module trace_capture;initial begin $dumpfile("font_selected.vcd");$dumpvars(0,tb_v132_font_datapath.d.font_addr1);$dumpvars(0,tb_v132_font_datapath.d.font_bit2);$dumpvars(0,tb_v132_font_datapath.d.font_bank2);end endmodule\n',encoding='ascii')
rtl=R/'01_project/rtl';tb=R/'02_tests/ui_compact/tb_v132_font_datapath.sv';exe=out/'trace.vvp';iv=b/('iverilog.exe'if os.name=='nt'else'iverilog');vp=b/('vvp.exe'if os.name=='nt'else'vvp')
c=subprocess.run([str(iv),'-g2012','-I',str(rtl),'-s','tb_v132_font_datapath','-s','trace_capture','-o',str(exe),str(tb),str(trace),str(rtl/'visual/media_ui_overlay.v')],cwd=out,env=env,capture_output=True,text=True,timeout=60)
log=c.stdout+c.stderr
if c.returncode==0:
 d=subprocess.run([str(vp),str(exe),'+FONT='+font.as_posix()],cwd=out,env=env,capture_output=True,text=True,timeout=60);log+=d.stdout+d.stderr;ok=d.returncode==0 and'PASS V132 runtime UI font datapath checks=65536'in log
else:ok=False
(out/'run.log').write_text(log,encoding='utf8')
wave=out/'font_selected.vcd';require=ok and wave.is_file()
if require:
 with gzip.open(out/'font_selected.vcd.gz','wb')as f:f.write(wave.read_bytes())
summary=dict(passed=require,checks=65536 if require else 0,scope='Representative selected-address signal waveform plus actual exhaustive font TB; not full-system or routed waveform.',waveform='font_selected.vcd.gz',source_sha256={f.relative_to(R).as_posix():hashlib.sha256(f.read_bytes()).hexdigest()for f in[tb,trace,rtl/'visual/media_ui_overlay.v',rtl/'visual/media_ui_font_packed_v132.vh',Path(__file__)]},hardware_tested=False)
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8');print(out);raise SystemExit(0 if require else 1)


