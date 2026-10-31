"""Prove V132 changes only UI storage, explicitly revalidate inherited core evidence."""
from pathlib import Path
import json,re,hashlib
R=Path(__file__).resolve().parents[1];assert '01_versions'not in R.parts
B=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v130_av_layer_ui_20261030\01_project')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
allowed={'01_project/rtl/visual/media_ui_overlay.v'};added={'01_project/rtl/visual/media_ui_font_packed_v132.vh'}
old={p.relative_to(B).as_posix():p for p in(B/'01_project').rglob('*')if p.is_file()};new={p.relative_to(R).as_posix():p for p in(R/'01_project').rglob('*')if p.is_file()};assert set(new)-set(old)==added and not set(old)-set(new)
changed={rel for rel in old if sha(old[rel])!=sha(new[rel])};assert changed==allowed
prior=json.loads((B/'04_evidence/v130_unchanged_core_final/summary.json').read_text('utf8'));assert prior['passed']and prior['complete']
def verify(obj,src):
 n=0
 if isinstance(obj,dict):
  for k,v in obj.items():
   if k in['source_sha256','sources']and isinstance(v,dict)and v and all(isinstance(h,str)and re.fullmatch('[0-9a-f]{64}',h)for h in v.values()):
    for rel,h in v.items():
     p=Path(rel);assert not p.is_absolute()and '..'not in p.parts
     assert(src/p).is_file()and sha(src/p)==h,(src,p)
     if rel.startswith('01_project/'):
      assert rel not in allowed|added,(rel,'changed UI cannot inherit old evidence')
      assert(R/p).is_file()and sha(R/p)==h,(rel,'core no longer matches')
     n+=1
   elif isinstance(v,(dict,list)):n+=verify(v,src)
 elif isinstance(obj,list):
  for v in obj:n+=verify(v,src)
 return n
refs=[]
for ent in prior['inherited_reports']:
 p=Path(ent['baseline_report']);assert p.is_file()and sha(p)==ent['baseline_report_sha256'];j=json.loads(p.read_text('utf-8-sig'))
 if ent['label']=='shared_reader_arbiter_units':j=dict(j,cases=[x for x in j['cases']if x['case']in['old_gap','new_gap']])
 n=verify(j,p.parents[2]);assert n>0;refs.append(dict(label=ent['label'],report=str(p),report_sha256=sha(p),revalidated_source_checks=n,not_freshly_rerun=True))
out=R/'04_evidence/v132_unchanged_core';assert not out.exists();out.mkdir()
rec=dict(passed=True,complete=True,baseline=str(B),changed_production_sources=sorted(changed),new_production_sources=sorted(added),unchanged_production_files=len(old)-len(changed),inherited_reports=refs,source_sha256={k:sha(new[k])for k in sorted(set(new)-changed-added)},scope='Only UI ROM storage changed. TF/SPI/FAT32,WAV,SDRAM,FIFO,scaler,HDMI,PLL,ADC,SDC all byte-identical. Prior core reports hash/source revalidated, not fresh reruns or physical BIST/hardware acceptance.')
(out/'summary.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('PASS unchanged production',rec['unchanged_production_files'],'inherited reports',len(refs));print(out)
