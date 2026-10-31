from pathlib import Path
import json,re,hashlib,datetime,argparse
r=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--physical-attempt',type=int,default=1);args=a.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=r/'BASELINE_v122_VERSION_STATUS.json';old=json.loads(base.read_text(encoding='utf8'))
syn=r/'05_td/v124_audio_visual_synth_attempt1';phy=r/f'05_td/v124_audio_visual_physical_attempt{args.physical_attempt}'
sj=json.loads((syn/'attempt.json').read_text(encoding='utf8'));pj=json.loads((phy/'attempt.json').read_text(encoding='utf8'))
assert sj['completed'] and pj['completed'],'No successful current setup/hold implementation; do not release bit'
text=(phy/'physical/sdram_phy.area').read_text(encoding='utf8');resources={k:int(re.search(r'^#'+k+r'\s+(\d+)',text,re.M).group(1))for k in ['lut','reg','bram','bram32k','dsp','pll','gclk','pad']}
capacities=dict(lut=19600,reg=19600,bram=64,bram32k=16,dsp=29,pll=4,gclk=16,pad=66)
assert all(resources[k]<=v for k,v in capacities.items())
baseline_root=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v122_address_pipeline_20261029\01_project')
changes=[]
for f in (r/'01_project').rglob('*'):
 if f.is_file():
  rel=f.relative_to(r);prior=baseline_root/rel
  if not prior.exists()or sha(prior)!=sha(f):changes.append(dict(path=rel.as_posix(),new_sha256=sha(f),old_sha256=sha(prior)if prior.exists()else None))
for rel in ['01_project/boards/idx_video.adc','01_project/boards/idx_video.sdc','01_project/rtl/ip/pll_video720.v','01_project/rtl/ip/pll_sdram.v']:
 assert sha(r/rel)==sha(baseline_root/rel),rel
counts={m.group(1):int(m.group(2))for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',(phy/'physical/sdram_check.rpt').read_text(encoding='utf8'),re.M)}
coverage=float(re.search(r'STA coverage\s*:\s*([\d.]+)',(phy/'physical/sdram_pr.timing').read_text(encoding='utf8')).group(1))
out=r/'04_evidence/v124_resource_review';assert not out.exists();out.mkdir()
rec=dict(passed=True,scope='Same-stage routed resource/STA comparison; V124 adds real volume function. This is not proof of lower LUT/BRAM, lower runtime latency or hardware acceptance.',selected_physical_attempt=args.physical_attempt,synthesis_resources=sj['resources'],routed_resources=resources,capacities=capacities,remaining={k:capacities[k]-resources[k]for k in capacities},baseline_v122_routed=old['metrics']['routed_resources'],deltas={k:resources[k]-old['metrics']['routed_resources'][k]for k in resources},slack_ns=pj['slack_ns'],coverage_percent=coverage,check_timing_counts=counts,production_changes=changes,source_sha256={p.relative_to(r).as_posix():sha(p)for p in [base,phy/'attempt.json',phy/'physical/sdram_phy.area',phy/'physical/sdram_phy.ts',phy/'physical/sdram_check.rpt',Path(__file__)]},timing_fix='Register only offscreen spectrum restart; preserve same-edge frame/epoch/opacity and3cycle pixels;1346050 exact A/B pixels. No SDC/pin/PLL waivers.',volume_tradeoff='24bit signed Q8 coefficient with per-sample ramp; same -12.04dB ceiling and one-cycle valid latency. No new explicit volume FIFO. Whole-system mapped BRAM/DSP changes must still be counted.',subtitle_recognition_implemented=False,hardware_accepted=False,formal_release_approved=False)
(out/'summary.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in rec.items()if k not in ['source_sha256','production_changes']},ensure_ascii=False,indent=2));print(out)
