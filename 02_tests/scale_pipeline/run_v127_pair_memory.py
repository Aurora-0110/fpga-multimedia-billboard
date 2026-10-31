from pathlib import Path
import hashlib,json,os,subprocess,time,argparse
parser=argparse.ArgumentParser();parser.add_argument("--timeout",type=int,default=1200);parser.add_argument("--resume-h8-from",type=Path);args=parser.parse_args()
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
tools=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
env.update(TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),TMPDIR=str(root/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
out=root/'04_evidence'/('v127_pair_memory_'+time.strftime('%Y%m%d_%H%M%S'));out.mkdir()
src=[here/'v126_idx_pair_pipeline_reference.v',here/'v126_idx_pair_reader_reference.v',here/'tb_v127_pair_memory.sv',root/'02_tests/vendor/IS42s32200.v',*[rtl/s for s in ['common/reset_release.v','mem/sdram_ctrl.v','mem/async_fifo.v','video/idx_pair_reader.v','video/idx_pair_display.v','video/idx_pair_pipeline.v','video/video_timing.v']]]
summary={'result':'IN_PROGRESS','scope':'Real controller/physical SDRAM bus model/paired FIFO/display with synthetic burst writer; full width720p plus concurrent writer; NOT TF or hardware',
         'source_sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src},'tests':[]}
cases=[(8,40),(720,2)]
if args.resume_h8_from:
 prior_path=args.resume_h8_from.resolve();assert prior_path.is_relative_to((root/'04_evidence').resolve())
 prior=json.loads(prior_path.read_text(encoding='utf8'))
 # Retain only a fully completed CURRENT-V127 individual case, never its failed aggregate.
 for rel,hsh in prior['source_sha256'].items():assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==hsh,rel
 row=next(x for x in prior['tests']if x['name']=='h8_step40');assert row['passed']and row['returncode']==0 and not row.get('timeout')
 proof=prior_path.parent/'h8_step40.log';text=proof.read_text(encoding='utf8');assert 'PASS pair_memory' in text and 'AB physical_address_checks='in text and not any(x in text.upper()for x in ['FATAL','ERROR','VIOLATION'])
 row=dict(row,reused_completed_current_v127_case=True,origin_report=prior_path.relative_to(root).as_posix(),origin_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest(),log_sha256=hashlib.sha256(proof.read_bytes()).hexdigest())
 summary['tests'].append(row);summary['reused_current_case_only_not_failed_aggregate']=True;cases=[(720,2)]
summary['source_sha256'][Path(__file__).relative_to(root).as_posix()]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
try:
 for h,step in cases:
  name=f'h{h}_step{step}';exe=out/(name+'.vvp');log=out/(name+'.log')
  cmd=[str(tools/'iverilog.exe'),'-g2012','-Wall','-s','tb_pair_memory',f'-Ptb_pair_memory.HEIGHT={h}',f'-Ptb_pair_memory.STOP_STEP={step}','-o',str(exe),*map(str,src)]
  c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=45);log.write_text(c.stdout+c.stderr,encoding='utf-8')
  row={'name':name,'compile_rc':c.returncode,'passed':False};start=time.monotonic()
  if c.returncode==0:
   with log.open('a',encoding='utf-8') as f:
    try:c=subprocess.run([str(tools/'vvp.exe'),str(exe)],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=args.timeout);row['returncode']=c.returncode
    except subprocess.TimeoutExpired:row['timeout']=True
   text=log.read_text(encoding='utf-8');row['passed']=row.get('returncode')==0 and 'PASS pair_memory' in text and not any(s in text.upper() for s in ['FATAL','ERROR','VIOLATION'])
   row['result_lines']=[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR'))]
  row['elapsed_seconds']=round(time.monotonic()-start,3);summary['tests'].append(row);print(name,row,flush=True);assert row['passed'],log.read_text(encoding='utf-8')[-6000:]
 summary['result']='PASS'
finally:
 (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(out,flush=True)
