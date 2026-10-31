from pathlib import Path
import hashlib,json,os,subprocess,sys,time
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
from multires_reference import fixture
tools=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
out=root/'04_evidence'/('v123_multires_spi_memory_'+time.strftime('%Y%m%d_%H%M%S'));out.mkdir()
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
 for case in cases:
  case['stage']=2;directory=build/case['name'];generated=fixture(directory,case)
  cmd=[str(tools/'vvp.exe'),str(build/'test.vvp'),'+FIXTURE='+directory.as_posix(),f'+BLOCKS={generated["blocks"]}',
       f'+ERROR={case.get("error",0)}',f'+RETRY={case.get("retry",0)}',f'+CRC_READ={case.get("crc_read",0)}',f'+SDSC={case.get("sdsc",0)}']
  c=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=240);text=c.stdout+c.stderr
  passed=c.returncode==0 and 'PASS scaled_spi_memory' in text and not any(s in text.upper() for s in ['FATAL','ERROR','VIOLATION'])
  row={'case':case,'fixture':generated,'passed':passed,'returncode':c.returncode,'result_lines':[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR'))]}
  summary['tests'].append(row);(out/(case['name']+'.log')).write_text(text,encoding='utf-8');print(case['name'],row['passed'],row['result_lines'],flush=True);assert passed,text[-5000:]
 summary['result']='PASS'
except Exception as error:
 summary['result']='FAIL';summary['exception']=repr(error)
 raise
finally:
 (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(out,flush=True)
