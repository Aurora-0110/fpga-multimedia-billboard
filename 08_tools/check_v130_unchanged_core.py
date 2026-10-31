"""V130 immutable-baseline proof; new controls/UI/overlay covered by fresh tests."""
from pathlib import Path
import json,hashlib,re
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
base=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v129_third_track_captions_20261030\01_project')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
allowed={'01_project/rtl/video/display_diagnostics_osd.v','01_project/boards/idx_audio_visual_top.v','01_project/rtl/common/media_controls.v',*[f'01_project/rtl/visual/{n}'for n in ['media_ui_overlay.v','subtitle_overlay.v','music_caption_config.vh','music_caption_meta_init.vh','music_caption_text_init.vh','music_caption_font_init.vh','media_ui_zh_glyph_ids.vh','media_ui_zh_font_init.vh','media_ui_zh_text_init.vh']]}
changed=[];unchanged={}
for p in (r/'01_project').rglob('*'):
 if not p.is_file()or p.suffix not in ['.v','.vh','.tcl','.adc','.sdc','.prj']:continue
 rel=p.relative_to(r).as_posix();prior=base/rel;assert prior.is_file(),('new unreviewed production file',rel)
 if sha(p)!=sha(prior):
  assert rel in allowed,('unreviewed change',rel);changed.append(dict(path=rel,baseline_sha256=sha(prior),current_sha256=sha(p)))
 else:unchanged[rel]=sha(p)
assert len(changed)==12,(len(changed),changed)
prior=json.loads((base/'04_evidence/v129_unchanged_core_with_spi/summary.json').read_text(encoding='utf-8'));assert prior['passed']and prior['complete']
refs=[]
def verify(x,source_root):
 n=0
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ['source_sha256','sources']and isinstance(v,dict)and v and all(isinstance(h,str)and re.fullmatch('[0-9a-f]{64}',h)for h in v.values()):
    for rel,h in v.items():
     p=Path(rel);assert not p.is_absolute()and '..'not in p.parts;assert (source_root/p).is_file()and sha(source_root/p)==h,(source_root,rel)
     if rel.startswith('01_project/'):
      assert rel not in allowed,('inherited report exercises changed design; requires new test instead',rel)
      assert sha(r/p)==h,('current datapath changed',rel)
     n+=1
   elif isinstance(v,(dict,list)):n+=verify(v,source_root)
 elif isinstance(x,list):
  for v in x:n+=verify(v,source_root)
 return n
for ent in prior['inherited_reports']:
 p=Path(ent['baseline_report']);assert sha(p)==ent['baseline_report_sha256'];j=json.loads(p.read_text(encoding='utf-8-sig'))
 extra={}
 if ent['label']=='shared_reader_arbiter_units':
  assert [x['case']for x in j['cases']]==['old_gap','new_gap','first_error']
  j=dict(j,cases=[x for x in j['cases']if x['case']!='first_error'])
  extra=dict(retained_cases=['old_gap','new_gap'],excluded_changed_case='first_error',replacement='fresh V130 diagnostic regression includes tb_v116_diag_persistent')
 n=verify(j,p.parents[2]);assert n>0
 refs.append(dict(**ent,**extra,v130_current_core_verified=True,v130_source_checks=n))
out=r/'04_evidence/v130_unchanged_core_final';assert not out.exists();out.mkdir()
rec=dict(passed=True,complete=True,baseline=str(base),source_sha256=unchanged,changed_production_sources=changed,inherited_reports=refs,scope='Only12UI/layer/font/diagnostic sources changed; diagnostic first-error case freshly rerun, not inherited. WAV reader/sample events,PCM gain,DFT,SPI,FAT32,SDRAM,FIFO,scaler,HDMI,clocks,pins,SDC unchanged. Inherited reports are not fresh reruns or hardware acceptance. New player/layout/control integration freshly tested.')
(out/'summary.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8');print('PASS unchanged',len(unchanged),'changed',len(changed),'inherited',len(refs));print(out)
