from pathlib import Path
import datetime,subprocess,os,json,hashlib,re
r=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;out=r/'04_evidence'/('v125_fifo_prefix_feasibility_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
old=r/'01_project/rtl/mem/async_fifo.v';candidate=t/'async_fifo_prefix_candidate.v'
a=old.read_text(encoding='utf8');b=candidate.read_text(encoding='utf8').replace('module async_fifo_prefix_candidate #(','module async_fifo #(')
strip=lambda s:re.sub(r'    function \[AW:0\] gray2bin\(.*?    endfunction','<gray2bin>',s,flags=re.S)
assert strip(a)==strip(b),'Outside the converter function no RTL changes are allowed'
bin=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(bin)+os.pathsep+env.get('PATH',''),TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'))
rows=[];src=[t/'tb_fifo_prefix.sv',old,candidate]
for aw in [2,4,8,9,10,11,12]:
 exe=out/f'aw{aw}.vvp';c=subprocess.run([str(bin/'iverilog.exe'),'-g2012','-s','tb_fifo_prefix',f'-Ptb_fifo_prefix.AW={aw}','-o',str(exe),*map(str,src)],env=env,capture_output=True,text=True);text=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  p=subprocess.run([str(bin/'vvp.exe'),str(exe)],env=env,capture_output=True,text=True,timeout=90);text+=p.stdout+p.stderr;rc=p.returncode
 (out/f'{aw}.log').write_text(text,encoding='utf8');passed=c.returncode==0 and rc==0 and 'PASS' in text;rows.append(dict(aw=aw,passed=passed));print(aw,passed,text[-500:],flush=True)
 if not passed:break
rec=dict(passed=len(rows)==7 and all(x['passed']for x in rows),cases=rows,only_conversion_function_changed=True,source_sha256={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in src+[Path(__file__)]},scope='SIDECAR FEASIBILITY ONLY: balanced-prefix converter is NOT integrated into V125 or its bit. Exhaustive conversion+cycle/flag/data A-B; not CDC physical/electrical signoff.')
(out/'summary.json').write_text(json.dumps(rec,indent=2),encoding='utf8');print(out);raise SystemExit(0 if rec['passed']else 1)
