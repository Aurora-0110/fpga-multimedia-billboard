from pathlib import Path
import datetime,subprocess,os,json,hashlib,re
r=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent
out=r/'04_evidence'/('v126_fifo_equivalence_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
prod=r/'01_project/rtl/mem/async_fifo.v';ref=t/'async_fifo_v125_reference.v'
old=ref.read_bytes().replace(b'module async_fifo_v125_reference #(',b'module async_fifo #(');new=prod.read_bytes()
pat=rb'    function \[AW:0\] gray2bin\(.*?    endfunction'
assert len(re.findall(pat,old,flags=re.S))==len(re.findall(pat,new,flags=re.S))==1
assert re.sub(pat,b'<gray2bin>',old,flags=re.S)==re.sub(pat,b'<gray2bin>',new,flags=re.S),'Non-converter source changed'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Pin the immutable original source, not a convenient untested work copy.
frozen=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v125_pcm_pipeline_20261030\01_project\01_project\rtl\mem\async_fifo.v')
assert old==frozen.read_bytes()
bin=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(bin)+os.pathsep+env.get('PATH',''),TEMP=str(r/'00_tmp'),TMP=str(r/'00_tmp'))
rows=[];src=[t/'tb_fifo_prefix.sv',ref,prod]
for aw in [2,4,8,9,10,11,12]:
 for phase in [137,1375,6157]:
  exe=out/f'aw{aw}_p{phase}.vvp';c=subprocess.run([str(bin/'iverilog.exe'),'-g2012','-s','tb_fifo_prefix',f'-Ptb_fifo_prefix.AW={aw}',f'-Ptb_fifo_prefix.PHASE_PS={phase}','-o',str(exe),*map(str,src)],env=env,capture_output=True,text=True);text=c.stdout+c.stderr;rc=None
  if c.returncode==0:
   p=subprocess.run([str(bin/'vvp.exe'),str(exe)],env=env,capture_output=True,text=True,timeout=90);text+=p.stdout+p.stderr;rc=p.returncode
  (out/f'aw{aw}_p{phase}.log').write_text(text,encoding='utf8');passed=c.returncode==0 and rc==0 and 'PASS' in text;rows.append(dict(aw=aw,phase_ps=phase,passed=passed));print(aw,phase,passed,text[-350:],flush=True)
  if not passed:break
 if not passed:break
rec=dict(passed=len(rows)==21 and all(x['passed']for x in rows),cases=rows,outside_function_byte_identical=True,old_production_sha256=hashlib.sha256(old).hexdigest(),new_production_sha256=sha(prod),exhaustive_widths=[2,4,8,9,10,11,12],phase_ps=[137,1375,6157],source_sha256={p.relative_to(r).as_posix():sha(p)for p in src+[Path(__file__)]},scope='V126 production parallel-prefix Gray converter: exhaustive XOR oracle and same-cycle FIFO data/count/flag A-B versus frozen V125, 7 widths x3 independent phases, full/empty/wrap/async-reset. Used only as an explicitly declared semantic equivalence certificate for inherited digital regressions; does not establish CDC physical skew/electrical signoff.')
(out/'summary.json').write_text(json.dumps(rec,indent=2),encoding='utf8');print(out);raise SystemExit(0 if rec['passed']else 1)
