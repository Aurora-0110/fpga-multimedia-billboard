from pathlib import Path
import hashlib,json,os,subprocess,sys,time,argparse,concurrent.futures
ap=argparse.ArgumentParser();ap.add_argument("--timeout",type=int,default=900);args=ap.parse_args()
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
from multires_reference import fixture
tools=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
env.update(TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),TMPDIR=str(root/'00_tmp'),PYTHONDONTWRITEBYTECODE='1')
out=root/'04_evidence'/('v128_multires_spi_memory_'+time.strftime('%Y%m%d_%H%M%S'));out.mkdir()
build=here/'build'/out.name;build.mkdir(parents=True)
src=[here/'tb_v101_spi_memory.sv',root/'02_tests/vendor/IS42s32200.v',here/'sd_fat_card_model_large.v',
 *[rtl/s for s in ['tf/spi_byte.v','tf/sd_spi_reader.v','tf/fat32_bmp_probe.v','tf/bmp_pixel_stream.v','tf/tf_bmp_source.v','tf/tf_bmp_scaled_source.v','tf/tf_scaled_loader.v','tf/bmp_pixel_packer.v','scale/bmp_scale_bridge.v','scale/bilinear_stream_scaler.v','scale/bilinear_rgb888.v','common/reset_release.v','mem/sdram_ctrl.v','mem/async_fifo.v','video/idx_pair_reader.v','video/idx_pair_display.v','video/idx_pair_pipeline.v','video/video_timing.v']]]
summary={'result':'IN_PROGRESS','scope':'SPI host + behavioral SD card + dynamicBMP/scaler/loader + physical SDRAM bus model + paired FIFO/display at32x18; NOT full720p end-to-end or hardware',
 'source_sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src+[Path(__file__),here/'multires_reference.py',root/'02_tests/dynamic_bmp/run_dynamic_tests.py']},'tests':[]}
try:
 cmd=[str(tools/'iverilog.exe'),'-g2012','-Wall','-s','tb_v101_spi_memory','-o',str(build/'test.vvp'),*map(str,src)]
 c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=45);(out/'compile.log').write_text(c.stdout+c.stderr,encoding='utf-8');assert c.returncode==0,c.stderr
 cases=[{'name':'max_width_bottom_retry','width':2048,'height':3,'retry':1},
        {'name':'odd_width_top','width':2047,'height':3,'top':True},
        {'name':'max_height_padding_top','width':1,'height':2048,'top':True,'sdsc':1},
        {'name':'late_crc_no_publish','width':13,'height':20,'crc_read':6,'error':0x1a}]
 def run(case):
  case['stage']=2;directory=build/case['name'];generated=fixture(directory,case)
  cmd=[str(tools/'vvp.exe'),str(build/'test.vvp'),'+FIXTURE='+directory.as_posix(),f'+BLOCKS={generated["blocks"]}',
       f'+ERROR={case.get("error",0)}',f'+RETRY={case.get("retry",0)}',f'+CRC_READ={case.get("crc_read",0)}',f'+SDSC={case.get("sdsc",0)}']
  log=out/(case['name']+'.log');start=time.monotonic();rc=None;timed_out=False
  with log.open('w',encoding='utf8')as f:
   try:c=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=args.timeout);rc=c.returncode
   except subprocess.TimeoutExpired:timed_out=True
  text=log.read_text(encoding='utf8');passed=rc==0 and 'PASS scaled_spi_memory'in text and not any(x in text.upper()for x in ['FATAL','ERROR','VIOLATION'])
  row=dict(case=case,fixture=generated,passed=passed,returncode=rc,timeout=timed_out,elapsed_seconds=round(time.monotonic()-start,3),result_lines=[line for line in text.splitlines()if line.startswith(('PASS','FATAL','ERROR'))])
  print(case['name'],passed,row['result_lines'],flush=True);return row
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:summary['tests']=list(pool.map(run,cases))
 assert all(row['passed']for row in summary['tests']),'Some bounded multi-resolution/SPI/SDRAM cases failed or timed out'
 summary['result']='PASS'
except Exception as error:
 summary['result']='FAIL';summary['exception']=repr(error)
 raise
finally:
 (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(out,flush=True)
