from pathlib import Path
import hashlib,json,shutil
r=Path(r'D:\FPGA_Billboard\work\v105_center_glass_art_spectrum_20261026')
d=r/'04_evidence/v105_failed_timing_attempt1_sources'
s=(r/'02_tests/ui/tb_v105_ui.sv').read_text(encoding='utf8').replace('x=1;de=0;cycles(44);if(!d.layout_ready)$fatal(1,"frame layout deadline");end endtask','x=1;de=0;cycles(2);end endtask')
p=d/'02_tests/ui/tb_v105_ui.sv';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf8')
report=json.loads((r/'04_evidence/v105_ui_20261026_141009/summary.json').read_text(encoding='utf8'))
expected=next(x for x in report['tests'] if x['name']=='ui')['source_sha256']['02_tests/ui/tb_v105_ui.sv'];assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,'preserved initial TB hash mismatch'
rows=[]
for p in sorted(d.rglob('*')):
 if p.is_file():rows.append({'path':p.relative_to(d).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(d/'SOURCES_MANIFEST.json').write_text(json.dumps({'scope':'first setup-failing physical attempt source copies and original UI TB, exact historical hash checked; not release inputs','files':rows},indent=2),encoding='utf8')
# Guard initial experimental replay helpers against accidental replacement of final RTL.
for name in ['implement_v105.py','implement_v105_spectrum.py','retime_v105_ui.py']:
 p=r/'08_tools'/name;s=p.read_text(encoding='utf-8-sig');p.write_text('''# HISTORICAL development replay only; not the final build/rebuild entry.
# Use run_acceptance.py and generate_v105_ui_font.py instead.
import os
if os.environ.get('REPLAY_HISTORICAL_V105_EXPERIMENT')!='1':
 raise SystemExit('Historical experiment intentionally disabled; use final RTL and run_acceptance.py.')
'''+s,encoding='utf8')
print('First-attempt TB restored only into evidence; exact historic hash matches. Unsafe replay helpers guarded, active RTL not changed.')
