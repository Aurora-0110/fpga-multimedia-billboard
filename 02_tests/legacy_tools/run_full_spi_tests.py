from pathlib import Path
import os,sys,subprocess,json,datetime,hashlib
R=Path(__file__).resolve().parents[1];B=Path(os.environ.get('IVERILOG_BIN',r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin'));L=B.parent/'lib/ivl'
env=dict(os.environ);env['PATH']=str(B)+os.pathsep+env.get('PATH','')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f');O=R/'02_tests/build'/('full_spi_'+stamp);E=R/'04_evidence/sim'/('full_spi_'+stamp);O.mkdir(parents=True);E.mkdir(parents=True)
raw=(R/'02_tests/fixtures/reference_A.bmp').read_bytes();(O/'reference.hex').write_text('\n'.join(f'{x:02x}' for x in raw)+'\n')
rtl=[R/'01_project/rtl'/n for n in ['spi_byte.v','sd_spi_reader.v','fat32_bmp_probe.v','bmp_pixel_stream.v','led_595.v']];src=rtl+[R/'01_project/boards/bmp_stream_top.v',R/'02_tests/sd_bmp_card_model.v',R/'02_tests/tb_bmp_stream_board.v'];exe=O/'board.vvp'
cmd=list(map(str,[B/'iverilog.exe','-B',L,'-g2012','-Wall','-s','tb_bmp_stream_board','-o',exe]+src));cp=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=45);(E/'compile.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout+cp.stderr
results=[]
for label,args in [('crc_first_sector',['+CRC_READ=7','+ERROR=1']),('full_reference',['+ERROR=0']),('different_valid_image',['+FLIP=1','+ERROR=9'])]:
 cmd=list(map(str,[B/'vvp.exe','-M',L,exe,f'+IMAGE={O/"reference.hex"}']+args));cp=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=600);t=cp.stdout+cp.stderr;good=cp.returncode==0 and 'PASS' in t and 'FATAL' not in t;(E/(label+'.log')).write_text(subprocess.list2cmdline(cmd)+'\n'+t);results.append(dict(name=label,passed=good,log=(E/(label+'.log')).relative_to(R).as_posix()));print(('PASS ' if good else 'FAIL ')+label+' '+t[-500:],flush=True)
summary=dict(version=R.name,passed=sum(x['passed'] for x in results),total=len(results),tests=results,hardware_tested=False,scope='Behavioral full SPI SD + FAT32 probe + fragmented complete BMP payload + CRC + board LED/key; not electrical or physical proof',source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.rglob('*.v'))})
(E/'summary.json').write_text(json.dumps(summary,indent=2));(R/'04_evidence/sim/full_spi_latest_summary.json').write_text(json.dumps(summary,indent=2));sys.exit(0 if summary['passed']==summary['total'] else 1)
