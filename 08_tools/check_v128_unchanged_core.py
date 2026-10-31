"""Prove unchanged core sources; retain explicitly INHERITED baseline evidence."""
from pathlib import Path
import json,hashlib,re
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
base=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v127_sample_captions_20261030\01_project')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
allowed={f'01_project/rtl/visual/{n}'for n in ['subtitle_overlay.v','music_caption_config.vh','music_caption_meta_init.vh','music_caption_text_init.vh','music_caption_font_init.vh','media_ui_zh_glyph_ids.vh','media_ui_zh_font_init.vh','media_ui_zh_text_init.vh']}
changed=[];unchanged={}
for p in (r/'01_project').rglob('*'):
 if not p.is_file()or p.suffix not in ['.v','.vh','.tcl','.adc','.sdc','.prj']:continue
 rel=p.relative_to(r).as_posix();prior=base/rel
 assert prior.is_file(),('unexpected new production source',rel)
 if sha(p)!=sha(prior):
  assert rel in allowed,('unreviewed core change',rel)
  changed.append(dict(path=rel,baseline_sha256=sha(prior),current_sha256=sha(p)))
 else:unchanged[rel]=sha(p)
assert changed and len(changed)<=8
# Baseline reports are checked against the FROZEN baseline, not called fresh V128.
def verify_baseline_hashes(x):
 n=0
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ['source_sha256','sources']and isinstance(v,dict)and v and all(isinstance(h,str)and re.fullmatch('[0-9a-f]{64}',h)for h in v.values()):
    for rel,h in v.items():
     p=Path(rel);assert not p.is_absolute()and '..'not in p.parts,rel
     assert (base/p).is_file()and sha(base/p)==h,rel
     n+=1
   elif isinstance(v,(dict,list)):n+=verify_baseline_hashes(v)
 elif isinstance(x,list):
  for v in x:n+=verify_baseline_hashes(v)
 return n
refs=[]
for label,pattern in [('reader_address_AB','v127_address_ab_[0-9]*'),('physical_SDRAM_bus_AB','v127_pair_memory_[0-9]*'),('long_reader_AB','v127_address_long_[0-9]*'),('multires_SPI_SDRAM','v127_multires_spi_memory_[0-9]*'),('FIFO_equivalence','v126_fifo_equivalence_[0-9]*'),('WAV_parser','v114_wav_decode_[0-9]*'),('audio_prefetch','v114_prefetch_[0-9]*'),('720p_scaler','v11[0124]_full_scaler_[0-9]*'),('dither','v122_dither_[0-9]*'),('production_SPI_pins','v127_extra_spi_[0-9]*')]:
 dirs=sorted((base/'04_evidence').glob(pattern));assert dirs,label
 p=dirs[-1]/'summary.json';j=json.loads(p.read_text(encoding='utf-8-sig'))
 assert j.get('passed',j.get('pass'))is True or j.get('result')=='PASS',p
 n=verify_baseline_hashes(j);assert n>0,(label,'no baseline source hashes')
 refs.append(dict(label=label,baseline_report=str(p),baseline_report_sha256=sha(p),baseline_source_hashes_verified=n,inherited_not_rerun=True,scope='Unchanged datapath/control core only; new UI/caption assets and overlay covered by fresh V128 tests, not these inherited reports.'))
out=r/'04_evidence/v128_unchanged_core_with_spi';assert not out.exists();out.mkdir()
rec=dict(passed=True,complete=True,baseline=str(base),source_sha256=unchanged,changed_production_sources=changed,inherited_reports=refs,new_caption_and_UI_tests_required=True,scope='Source equivalence for unchanged TF/FAT/WAV/FIFO/scaler/SDRAM/HDMI/PCM event cores. Baseline simulations not falsely labelled rerun or hardware acceptance.')
(out/'summary.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
print('Unchanged core source hashes',len(unchanged),'changed assets/overlay',len(changed),'inherited reports',len(refs));print(out)
