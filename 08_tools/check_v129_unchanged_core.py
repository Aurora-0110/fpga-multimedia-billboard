"""V129 production-core hash proof and explicit INHERITED passing evidence."""
from pathlib import Path
import json,hashlib,re
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
base=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v128_lyrics_alignment_20261030\01_project')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
allowed={'01_project/boards/idx_audio_visual_top.v',*[f'01_project/rtl/visual/{n}'for n in ['pcm_caption_player.v','subtitle_overlay.v','music_caption_config.vh','music_caption_meta_init.vh','music_caption_text_init.vh','music_caption_font_init.vh']]}
changed=[];unchanged={}
for p in (r/'01_project').rglob('*'):
 if not p.is_file()or p.suffix not in ['.v','.vh','.tcl','.adc','.sdc','.prj']:continue
 rel=p.relative_to(r).as_posix();prior=base/rel;assert prior.is_file(),('new unreviewed production file',rel)
 if sha(p)!=sha(prior):
  assert rel in allowed,('unreviewed change',rel)
  changed.append(dict(path=rel,baseline_sha256=sha(prior),current_sha256=sha(p)))
 else:unchanged[rel]=sha(p)
assert len(changed)==7
priorpath=base/'04_evidence/v128_unchanged_core_with_spi/summary.json';prior=json.loads(priorpath.read_text(encoding='utf-8'));assert prior['passed']and prior['complete']
def verify_hashes(x,source_root):
 n=0
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ['source_sha256','sources']and isinstance(v,dict)and v and all(isinstance(h,str)and re.fullmatch('[0-9a-f]{64}',h)for h in v.values()):
    for rel,h in v.items():
     p=Path(rel);assert not p.is_absolute()and '..'not in p.parts,rel
     assert (source_root/p).is_file()and sha(source_root/p)==h,(str(source_root),rel)
     # All production sources exercised by inherited unit tests must also be unchanged now.
     if rel.startswith('01_project/')and rel not in allowed:assert sha(r/p)==h,('current datapath mismatch',rel)
     n+=1
   elif isinstance(v,(dict,list)):n+=verify_hashes(v,source_root)
 elif isinstance(x,list):
  for v in x:n+=verify_hashes(v,source_root)
 return n
assert verify_hashes(prior,base)>100
refs=[]
for ent in prior['inherited_reports']:
 p=Path(ent['baseline_report']);assert sha(p)==ent['baseline_report_sha256'];j=json.loads(p.read_text(encoding='utf-8-sig'))
 frozen=p.parents[2];assert frozen.name=='01_project';n=verify_hashes(j,frozen);assert n>0
 refs.append(dict(**ent,current_core_verified_against_v128=True,current_baseline_source_checks=n))
for label,pattern in [('three_real_WAVs_4096_FIFO','v128_three_wav_[0-9]*'),('shared_reader_arbiter_units','v128_units_[0-9]*')]:
 p=sorted((base/'04_evidence').glob(pattern))[-1]/'summary.json';j=json.loads(p.read_text(encoding='utf-8'));assert j['passed']
 n=verify_hashes(j,base);assert n>0
 refs.append(dict(label=label,baseline_report=str(p),baseline_report_sha256=sha(p),baseline_source_hashes_verified=n,inherited_not_rerun=True,scope='Byte-identical WAV/SPI/arbiter core. V129 subtitle player/top/overlay not covered by inherited results.'))
out=r/'04_evidence/v129_unchanged_core_with_spi';assert not out.exists();out.mkdir()
rec=dict(passed=True,complete=True,baseline=str(base),source_sha256=unchanged,changed_production_sources=changed,inherited_reports=refs,production_scope='Only seven subtitle assets/player/overlay/top-enable sources changed. No WAV PCM/event,TF/FAT32,SPI,SDRAM,FIFO,scaler,HDMI,volume,UI,clock,pin or SDC changes.',fresh_subtitle_and_top_tests_required=True,inherited_reports_are_not_fresh_run_or_hardware_acceptance=True)
(out/'summary.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8');print('PASS unchanged production',len(unchanged),'changed',len(changed),'inherited reports',len(refs));print(out)
