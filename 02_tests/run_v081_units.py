from pathlib import Path
import subprocess,os,json,datetime,hashlib
r=Path(__file__).resolve().parents[1];p=r/'01_project';t=r/'02_tests';rtl=p/'rtl'
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
out=r/'04_evidence'/('v081_units_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir();rows=[]
cases={'reader':['video/idx_slide_reader.v'],'playlist':['tf/tf_double_playlist.v'],'osd':['video/osd_layers.v','video/official_logo.v'],'controls':['common/picture_controls.v'],'adjust':['video/picture_adjust.v']}
for name,files in cases.items():
 tbtag='v079' if name in {'reader','playlist'} else 'v080'
 src=[t/f'tb_{tbtag}_{name}.sv',*[rtl/x for x in files]];exe=out/(name+'.vvp')
 cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s','tb_'+tbtag+'_'+name,'-o',str(exe),*map(str,src)]
 c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=30);text=c.stdout+c.stderr;row={'test':name,'compile_rc':c.returncode,'passed':False,'source_sha256':{str(x.relative_to(r)):hashlib.sha256(x.read_bytes()).hexdigest() for x in src}}
 if not c.returncode:
  v=subprocess.run([str(b/'vvp.exe'),str(exe)],capture_output=True,text=True,env=env,timeout=240);text+=v.stdout+v.stderr;row.update(sim_rc=v.returncode,passed=v.returncode==0 and 'PASS' in v.stdout)
 (out/(name+'.log')).write_text(text,encoding='utf8');print(name,row['passed'],text[-1800:],flush=True);rows.append(row)
(out/'summary.json').write_text(json.dumps({'passed':all(x['passed'] for x in rows),'tests':rows},indent=2));print(out)
raise SystemExit(0 if all(x['passed'] for x in rows) else 1)
