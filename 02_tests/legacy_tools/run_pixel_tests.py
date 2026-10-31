from pathlib import Path
import os,sys,subprocess,json,datetime,hashlib,zlib
R=Path(__file__).resolve().parents[1];B=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'));L=B.parent/'lib/ivl'
env=dict(os.environ);env['PATH']=str(B)+os.pathsep+env.get('PATH','')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f');O=R/'02_tests/build'/('pixels_'+stamp);E=R/'04_evidence/sim'/('pixels_'+stamp);O.mkdir(parents=True);E.mkdir(parents=True)
ref=R/'02_tests/fixtures/reference_A.bmp';raw=ref.read_bytes();(O/'reference.hex').write_text('\n'.join(f'{x:02x}' for x in raw)+'\n')
crcs=[zlib.crc32(bytes((i*17+11)&255 for i in range(36))),zlib.crc32(raw[54:])]
results=[]
def invoke(cmd,label,timeout=120):
 cp=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,env=env,timeout=timeout);t=cp.stdout+cp.stderr;(E/(label+'.log')).write_text(subprocess.list2cmdline(list(map(str,cmd)))+'\n'+t,encoding='utf-8');return cp.returncode==0 and 'FATAL' not in t,t
for full in (False,True):
 exe=O/('full.vvp' if full else 'small.vvp');cmd=[B/'iverilog.exe','-B',L,'-g2012','-Wall','-s','tb_bmp_pixel_stream','-o',exe]+(['-DFULL_IMAGE'] if full else [])+[R/'01_project/rtl/bmp_pixel_stream.v',R/'02_tests/tb_bmp_pixel_stream.v']
 good,t=invoke(cmd,'compile_'+str(full));assert good,t
 cases=[('baseline',0,54,1,0,0),('cross_sector',0,500,1,0,0),('cross_two_clusters',0,1023,1,0,0),('top_down',0,500,1,1,0),('spc2',0,1000,2,0,0),('spc128',0,65536,128,0,0),('unaligned_large_offset',0,65535,1,1,0),('free_chain',5,500,1,0,6),('bad_cluster',6,500,1,0,6),('early_eoc',7,500,1,0,6),('cycle',8,500,1,0,7),('index_duplicate',9,54,1,0,3),('index_first',10,54,1,0,3),('missing_byte',11,54,1,0,3),('crc_reject',12,54,1,0,1),('ready_timeout',13,54,1,0,5),('accept_timeout',14,54,1,0,5),('data_timeout',15,54,1,0,5),('short_size',16,54,1,0,2),('lba_overflow',17,54,1,0,4),('invalid_spc',18,54,1,0,2),('invalid_cluster',19,54,1,0,2),('invalid_offset',20,54,1,0,2),('offset_limit',0,65537,1,0,2),('overallocated_final',21,54,1,0,7),('crc_later_sector',23,500,1,0,1),('out_of_range_chain',24,500,1,0,6),('reserved_chain',25,500,1,0,6)] if not full else [('full_reference_bottom_up',0,54,8,0,0),('full_reference_top_down',0,54,8,1,0)]
 for name,mode,offset,spc,top,error in cases:
  cmd=[B/'vvp.exe','-M',L,exe,f'+MODE={mode}',f'+OFFSET={offset}',f'+SPC={spc}',f'+TOP={top}',f'+ERROR={error}',f'+CRC={crcs[int(full)]:08x}',f'+REF={O/"reference.hex"}']
  good,t=invoke(cmd,name,180);good=good and 'PASS' in t;results.append(dict(name=name,passed=good,log=(E/(name+'.log')).relative_to(R).as_posix()));print(('PASS ' if good else 'FAIL ')+name+' '+t[-260:].strip(),flush=True)
summary=dict(version=R.name,passed=sum(x['passed'] for x in results),total=len(results),tests=results,hardware_tested=False,scope='Pixel stream bus tests; complete 307200 reference pixels in both orientations; no physical card or display proof',source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.rglob('*.v'))})
(E/'summary.json').write_text(json.dumps(summary,indent=2));(R/'04_evidence/sim/pixel_latest_summary.json').write_text(json.dumps(summary,indent=2));sys.exit(0 if summary['passed']==summary['total'] else 1)
