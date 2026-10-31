from pathlib import Path
import argparse,subprocess,os,json
p=Path(__file__).resolve().parent;r=p.parent/'01_project';a=argparse.ArgumentParser();a.add_argument('--iverilog-bin',type=Path,required=True);args=a.parse_args();b=args.iverilog_bin.resolve();env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
o=p/'build/top';o.mkdir(parents=True,exist_ok=True);logs=p/'logs/v054';logs.mkdir(parents=True,exist_ok=True)
native=p/'build/native_oddr';assert (native/'EG_LOGIC_ODDR.v').exists(),'run native ODDR test first'
files=['tf/tf_playlist_ctrl.v','ip/pll_video720.v','ip/hdmi_tx_wrap.v','mem/sdram_ctrl.v','mem/async_fifo.v','video/idx_writer.v','video/idx_reader.v','video/idx_display.v','video/idx_pipeline.v','video/fb_session_ctrl.v','video/video_timing.v','video/tmds_encoder.v','video/tmds_serializer.v','common/reset_release.v','common/key_debounce.v','common/bist_status_595.v']
cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-DSIM_PLL_BEHAV','-s','tb_top_reset','-s','glbl','-o',str(o/'test.vvp'),str(p/'tb_top_reset.sv'),str(p/'vendor/IS42s32200.v'),str(native/'EG_LOGIC_ODDR.v'),str(native/'glbl.v'),str(r/'boards/idx_video_top.v'),*[str(r/'rtl'/f) for f in files]]
c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30);text=c.stdout+c.stderr;row=dict(compile_command=cmd,compile_returncode=c.returncode,passed=False,scope='Production top + pipeline + HDMI encoder/serializer + native ODDR + ISSI bus model; behavioral PLL clocks/lock, START_BITS=4 KEY_CNT=8 test overrides; no PHY electrical signoff')
if c.returncode==0:
 v=subprocess.run([str(b/'vvp.exe'),str(o/'test.vvp')],env=env,capture_output=True,text=True,timeout=120);text+=v.stdout+v.stderr;row.update(sim_returncode=v.returncode,passed=v.returncode==0 and 'PASS top_reset' in text)
row['result_lines']=[x for x in text.splitlines() if x.startswith(('PASS','FATAL','ERROR'))];(logs/'top_reset.log').write_text(text,encoding='utf8');(p/'top_reset_results.json').write_text(json.dumps(row,indent=2),encoding='utf8');print(text);raise SystemExit(0 if row['passed'] else 1)
