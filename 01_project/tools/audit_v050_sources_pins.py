from pathlib import Path
import hashlib,json,re,sys
root=Path(__file__).resolve().parents[2]
project=root/'01_project';out=root/'05_td/v050_loop_try2'
sys.path.insert(0,str(project/'tools'))
from inspect_macro_netlist import parse
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
attempt=json.loads((out/'attempt.json').read_text(encoding='utf8'))
text=(out/'reports/sdram_netlist.pnl').read_text(); inst,pins=parse(text)
fail=[]
source_checks={name:(project/name).is_file() and sha(project/name)==digest for name,digest in attempt['source_sha256'].items()}
if not all(source_checks.values()):fail.append('source hash changed since build')
baseline=json.loads((root/'03_docs/v050_baseline_preservation.json').read_text(encoding='utf8'))
rows=baseline.get('files',baseline.get('checks',[]))
# Re-evaluate recorded baseline hashes against the actual current files, too.
for row in rows:
    name=row.get('path',row.get('file'))
    if name and (project/name).exists() and sha(project/name)!=row['baseline_sha256']:fail.append('baseline changed '+name)
expected={'clk24m':'P13','key0_n':'P51','led_dout':'P45','led_latch':'P57','led_sclk':'P59'}
external={n:v for n,v in inst.items() if v['model']=='iol' and not v['attrs'].get('SIP_INFO')}
if len(external)!=5:fail.append('expected exactly 5 external IOLs')
actual={}; details={}
adc=(project/'boards/sdram_bist.adc').read_text()
for name,loc in expected.items():
    matches=[(n,v) for n,v in external.items() if n.startswith(name+'_syn_')]
    if len(matches)!=1:fail.append('IOL instance mismatch '+name);continue
    n,v=matches[0];a=v['attrs'];actual[name]=a.get('LOCATION');details[name]={'instance':n,**a}
    if a.get('LOCATION')!=loc or a.get('IOTYPE')!='LVCMOS33' or a.get('MODE')!=('IN' if name in ('clk24m','key0_n') else 'OUT'):fail.append('pad attribute mismatch '+name)
    if not re.search(r'\{\s*'+name+r'\s*\}\s*\{\s*LOCATION\s*=\s*'+loc+r';\s*IOSTANDARD\s*=\s*LVCMOS33;',adc):fail.append('ADC mismatch '+name)
if not re.search(r'package\s+EG4S20NG88;',text):fail.append('wrong package')
area=(out/'reports/sdram_phy.area').read_text();resources={}
for kind,used,total in re.findall(r'^#(lut|reg|bram|bram32k|dsp|pad|pll|gclk)\s+(\d+)\s+out of\s+(\d+)',area,re.M):
    resources[kind]={'used':int(used),'available':int(total)}
    if int(used)>int(total):fail.append('resource overflow '+kind)
if len(resources)!=8:fail.append('incomplete resource audit')
if 'Device: EG4S20NG88' not in area:fail.append('wrong report device')
timing=(out/'reports/final_timing.rpt').read_text()
clock_ok=bool(re.search(r'clk0:\s+49\.500\b',timing)) and bool(re.search(r'clk0\s+local\s+[^\r\n]*20\.202\s+49\.500',timing))
if not clock_ok:fail.append('49.5MHz actual timing report not confirmed')
result=dict(passed=not fail,failures=fail,external_pins=actual,external_instances=details,source_hash_matches=source_checks,resources=resources,clock_49_5_mhz_report_confirmed=clock_ok,target='EG4S20NG88',scope='Source hashes, PNL pad attributes, ADC, actual TD clock/resource reports. Not vendor macro/PVT signoff.')
(out/'source_pin_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in ('source_hash_matches','external_instances')},ensure_ascii=False,indent=2))
raise SystemExit(0 if result['passed'] else 2)

