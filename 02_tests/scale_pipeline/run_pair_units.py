from pathlib import Path
import hashlib,json,os,subprocess,time
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent
tools=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
out=root/'04_evidence'/('v088_pair_units_'+time.strftime('%Y%m%d_%H%M%S'));out.mkdir()
summary={'result':'IN_PROGRESS','scope':'Pair reader transaction/address tests and registered-FIFO display tests; NOT physical SDRAM or hardware','tests':[]}
try:
 for name,params in [('reader',{'LINES':3,'COMPLETIONS':4}),('reader',{'LINES':720,'COMPLETIONS':1,'STOP_AFTER_STEP':2}),('display',{})]:
  label=name+'_'+('_'.join(f'{k}{v}' for k,v in params.items()) or 'unit')
  top='tb_pair_'+name;src=[here/(top+'.sv'),root/('01_project/rtl/video/idx_pair_'+name+'.v')]
  cmd=[str(tools/'iverilog.exe'),'-g2012','-Wall','-s',top,*[f'-P{top}.{k}={v}' for k,v in params.items()],'-o',str(out/(label+'.vvp')),*map(str,src)]
  c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=30);text=c.stdout+c.stderr
  row={'name':label,'compile_rc':c.returncode,'passed':False,'source_sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}}
  if c.returncode==0:
   c=subprocess.run([str(tools/'vvp.exe'),str(out/(label+'.vvp'))],capture_output=True,text=True,env=env,timeout=120)
   text+=c.stdout+c.stderr;row['returncode']=c.returncode;row['passed']=c.returncode==0 and 'PASS pair_' in text and not any(s in text for s in ['FATAL','ERROR'])
  (out/(label+'.log')).write_text(text,encoding='utf-8');row['result_lines']=[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR'))]
  summary['tests'].append(row);print(label,row['passed'],row['result_lines'],flush=True);assert row['passed'],text
 summary['result']='PASS'
finally:
 (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(out,flush=True)
