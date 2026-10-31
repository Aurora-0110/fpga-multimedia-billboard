from pathlib import Path
import os,subprocess,sys,json,datetime
R=Path(__file__).resolve().parents[1]
binpath=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'))
iverilog=binpath/'iverilog.exe';vvp=binpath/'vvp.exe'
lib=binpath.parent/'lib/ivl'
env=dict(os.environ);env['PATH']=str(binpath)+os.pathsep+env.get('PATH','')
if not iverilog.exists():sys.exit('Set IVERILOG_BIN to directory containing iverilog and vvp')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
O=R/'02_tests/build'/stamp;O.mkdir(parents=True)
E=R/'04_evidence/sim'/stamp;E.mkdir(parents=True)
rtl=[R/'01_project/rtl/spi_byte.v',R/'01_project/rtl/sd_spi_probe.v']
tests=[('spi_byte','tb_spi_byte',[],[],False)]
for mode in range(16):tests.append((f'sd_case_{mode}','tb_sd_spi_probe',['sd_card_model.v'],[f'+CASE={mode}'],False))
tests.extend([('sd_keep_card_power_retry','tb_sd_spi_probe',['sd_card_model.v'],['+CASE=0','+RESTART','+KEEP_CARD_POWER'],False),
 ('sd_reset_retry','tb_sd_spi_probe',['sd_card_model.v'],['+CASE=0','+RESTART'],False),
 ('sd_production_divider','tb_sd_spi_probe',['sd_card_model.v'],['+CASE=0'],True),
 ('board_top','tb_tf_probe_top',['sd_card_model.v'],[],False)])
results=[]
for name,top,extra,args,prod in tests:
 exe=O/(name+'.vvp');src=rtl+[R/'02_tests'/x for x in extra]+[R/'02_tests'/(top+'.v')]
 if top=='tb_tf_probe_top':src += [R/'02_tests/legacy_tf_probe_top.v',R/'01_project/rtl/led_595.v']
 cmd=[str(iverilog),'-B',str(lib),'-g2012','-Wall','-s',top,'-o',str(exe)]+(['-DPROD_DIV'] if prod else [])+list(map(str,src))
 text='COMMAND: '+subprocess.list2cmdline(cmd)+'\n';ok=False
 try:
  cp=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=45)
  text+=cp.stdout+cp.stderr
  if cp.returncode==0:
   run=subprocess.run([str(vvp),'-M',str(lib),str(exe)]+args,capture_output=True,text=True,env=env,timeout=45)
   text+=run.stdout+run.stderr;ok=run.returncode==0 and 'PASS' in run.stdout and 'FATAL' not in run.stdout+run.stderr
 except (OSError,subprocess.TimeoutExpired) as e:
  text+='TOOL_ERROR: '+str(e)+'\n'
 (E/(name+'.log')).write_text(text,encoding='utf-8')
 results.append(dict(name=name,passed=ok,log=str((E/(name+'.log')).relative_to(R))))
 print(('PASS ' if ok else 'FAIL ')+name+' '+text.strip()[-220:],flush=True)
summary=dict(version='v019_fat32_bmp_header_20261019',design_version='legacy_v016_regression',passed=sum(x['passed'] for x in results),total=len(results),tests=results,
 source_sha256={p.relative_to(R).as_posix():__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in sorted(R.rglob('*.v'))},scope='Behavioral SPI/card/board-top simulation, not physical module or card proof',hardware_tested=False)
(E/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
(R/'04_evidence/sim/latest_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
sys.exit(0 if all(x['passed'] for x in results) else 1)
