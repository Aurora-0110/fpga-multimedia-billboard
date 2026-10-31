"""Non-destructive TD build: every invocation gets a NEW run folder. No stale-bit fallback."""
from pathlib import Path
import os,sys,subprocess,datetime,xml.etree.ElementTree as ET,json,hashlib,shutil,re
R=Path(__file__).resolve().parents[1];P=R/'01_project'
TD=os.environ.get('TD_HOME')
if not TD:
 for parent in [Path(r'C:\Anlogic'),Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Anlogic']:
  if parent.exists():
   for p in sorted(parent.glob('TD_*')):
    if (p/'bin/run.exe').exists():TD=str(p)
if not TD:sys.exit('TD not found; set TD_HOME to installed TD directory.')
TD=Path(TD);run=TD/'bin/run.exe'
if not run.exists():sys.exit('Missing '+str(run))
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f');O=P/'td_project'/('run_'+stamp);O.mkdir(parents=True,exist_ok=False)
src=['boards/bmp_stream_top.v','rtl/spi_byte.v','rtl/sd_spi_reader.v','rtl/fat32_bmp_probe.v','rtl/bmp_pixel_stream.v','rtl/led_595.v']

def project_file(folder):
 root=ET.Element('Project',Version='1',Path='.')
 for k,v in [('Project_Created_Time',''),('TD_Version','6.2.168116'),('UCode','00000000'),('Name','tf_probe')]:ET.SubElement(root,k).text=v
 hw=ET.SubElement(root,'HardWare');ET.SubElement(hw,'Family').text='EG4';ET.SubElement(hw,'Device').text='EG4S20NG88'
 sf=ET.SubElement(root,'Source_Files')
 def section(tag,paths,group):
  sec=ET.SubElement(sf,tag)
  for i,p in enumerate(paths,1):
   f=ET.SubElement(sec,'File',Path=os.path.relpath(p,folder).replace('\\','/'));info=ET.SubElement(f,'FileInfo')
   for k,v in [('UsedInSyn','true'),('UsedInP&R','true'),('BelongTo',group),('CompileOrder',str(i+1 if tag=='SDC_FILE' else i))]:ET.SubElement(info,'Attr',Name=k,Val=v)
 section('Verilog',[P/x for x in src],'design_1')
 section('ADC_FILE',[P/'boards/tf_probe.adc'],'constrain_1')
 section('SDC_FILE',[P/'boards/tf_probe.sdc'],'constrain_1')
 fs=ET.SubElement(root,'FileSets');ET.SubElement(fs,'FileSet',Name='constrain_1',Type='ConstrainFiles');design=ET.SubElement(fs,'FileSet',Name='design_1',Type='DesignFiles');conf=ET.SubElement(design,'Config');ET.SubElement(conf,'Option',Name='IncludeDir',Val=os.path.relpath(P/'rtl',folder).replace('\\','/'))
 top=ET.SubElement(root,'TOP_MODULE');ET.SubElement(top,'LABEL').text='bmp_stream_top';ET.SubElement(top,'MODULE').text='bmp_stream_top';ET.SubElement(top,'CREATEINDEX')
 for tag in ['Property','Device_Settings','Configurations','Project_Settings']:ET.SubElement(root,tag)
 ET.indent(root,space='  ');ET.ElementTree(root).write(folder/'tf_probe.prj',encoding='utf-8',xml_declaration=True)
project_file(O);project_file(P/'td_project')
# Standalone SPI probe; no video PLLs or framebuffers.
tcl=r"""import_device eagle_s20.db -package EG4S20NG88
open_project tf_probe.prj
elaborate -top bmp_stream_top
read_adc ../../boards/tf_probe.adc
optimize_rtl
report_area -file tf_rtl.area
optimize_gate -packarea tf_gate.area
read_sdc ../../boards/tf_probe.sdc
legalize_phy_inst
place
route
update_timing -mode final
report_area -io_info -file tf_phy.area
report_timing_status -file tf_phy.ts
report_timing_summary -file tf_pr.timing
bitgen -bit tf_probe.bit
export_db tf_probe_pr.db
puts "V022_PIXEL_BUILD_COMPLETE"
exit
"""
(O/'build.tcl').write_text(tcl,encoding='utf-8')
E=R/'04_evidence/td';E.mkdir(parents=True,exist_ok=True)
log=E/('build_'+stamp+'.log');env=dict(os.environ);env['PATH']=str(TD/'bin')+os.pathsep+env.get('PATH','')
print('TD_HOME',TD,flush=True);print('NEW_RUN',O,flush=True)
with (O/'build.tcl').open('rb') as inp,log.open('wb') as out:
 proc=subprocess.run([str(run)],cwd=O,stdin=inp,stdout=out,stderr=subprocess.STDOUT,env=env,timeout=1200)
text=log.read_text(encoding='utf-8',errors='replace');bit=O/'tf_probe.bit'
generated=proc.returncode==0 and bit.exists() and 'V022_PIXEL_BUILD_COMPLETE' in text
status=(O/'tf_phy.ts').read_text(encoding='utf-8',errors='replace') if (O/'tf_phy.ts').exists() else ''
slacks={key:float(value) for key,value in re.findall(r'(SWNS|STNS|HWNS|HTNS):\s*([-+0-9.]+)ns',status)}
timing_ok=len(slacks)==4 and slacks['SWNS']>=0 and slacks['HWNS']>=0 and slacks['STNS']==0 and slacks['HTNS']==0
critical=[line for line in text.splitlines() if re.search(r'\b(?:ERROR|CRITICAL-WARNING)\b|Undriven pin|Using 0 for all undriven',line)]
ok=generated and timing_ok and not critical
# A bit plus success marker does not prove timing. Store exact timing report for separate inspection.
result=dict(version='v022_bmp_pixel_stream_20261020',run_dir=str(O),td_home=str(TD),exit_code=proc.returncode,bit_generated=generated,timing_passed=timing_ok,slacks_ns=slacks,critical_messages=critical,release_ready_for_hardware_test=ok,hardware_downloaded=False,hardware_tf_tested=False,source_sha256={x:hashlib.sha256((P/x).read_bytes()).hexdigest() for x in src+['boards/tf_probe.adc','boards/tf_probe.sdc']})
if generated:
 for name in ['tf_phy.area','tf_phy.ts','tf_pr.timing','tf_rtl.area','tf_gate.area']:
  if (O/name).exists():shutil.copy2(O/name,E/name)
if ok:
 dst=R/'03_bitstreams/v022_bmp_pixel_stream.bit';shutil.copy2(bit,dst)
 result['bit_file']=dst.relative_to(R).as_posix();result['bit_sha256']=hashlib.sha256(dst.read_bytes()).hexdigest()
 for name in ['tf_phy.area','tf_phy.ts','tf_pr.timing','tf_rtl.area','tf_gate.area']:
  if (O/name).exists():shutil.copy2(O/name,E/name)
(E/'build_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('BUILD_PASS' if ok else 'BUILD_FAILED',flush=True);print(text[-6000:],flush=True)
sys.exit(0 if ok else 1)
