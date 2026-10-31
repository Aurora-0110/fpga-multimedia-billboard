"""Same-stage V128/V129 routed results; no hardcoded pass or margin values."""
from pathlib import Path
import json,re,hashlib
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v128_lyrics_alignment_20261030\01_project')
syn=r/'05_td/v129_audio_visual_synth_attempt1';phy=r/'05_td/v129_audio_visual_physical_attempt1';sj=json.loads((syn/'attempt.json').read_text());pj=json.loads((phy/'attempt.json').read_text());assert sj['completed']and pj['completed']
for rel,h in sj['source_sha256'].items():assert sha(r/rel)==h,rel
for rel in ['01_project/boards/idx_video.adc','01_project/boards/idx_video.sdc','01_project/rtl/ip/pll_video720.v','01_project/rtl/ip/pll_sdram.v']:assert sha(r/rel)==sha(base/rel),rel
cap=dict(lut=19600,reg=19600,bram=64,bram32k=16,dsp=29,pll=4,gclk=16,pad=66)
def area(p):
 s=p.read_text();return{k:int(re.search(r'^#'+k+r'\s+(\d+)',s,re.M).group(1))for k in cap}
new=area(phy/'physical/sdram_phy.area');old=area(base/'05_td/v128_audio_visual_physical_attempt1/physical/sdram_phy.area');bs=json.loads((base/'05_td/v128_audio_visual_synth_attempt1/attempt.json').read_text());bp=json.loads((base/'05_td/v128_audio_visual_physical_attempt1/attempt.json').read_text())
assert all(new[k]<=v for k,v in cap.items())
timing=(phy/'physical/sdram_pr.timing').read_text();coverage=float(re.search(r'STA coverage\s*:\s*([\d.]+)',timing).group(1))
counts={m.group(1):int(m.group(2))for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',(phy/'physical/sdram_check.rpt').read_text(),re.M)}
slack=pj['slack_ns'];report=dict(passed=True,scope='Actual same-stage synthesis/routed area and numeric setup/hold; not timing/PVT/reliability/hardware or human lyric-time signoff.',baseline_v128_synthesis=bs['resources'],synthesis_resources=sj['resources'],synthesis_delta={k:sj['resources'][k]-bs['resources'][k]for k in cap},baseline_v128_routed=old,routed_resources=new,routed_delta={k:new[k]-old[k]for k in cap},capacities=cap,remaining={k:cap[k]-new[k]for k in cap},utilization_percent={k:round(new[k]/cap[k]*100,2)for k in cap},slack_ns=slack,baseline_v128_slack_ns=bp['slack_ns'],coverage_percent=coverage,check_timing_counts=counts,formal_release_approved=False,hardware_accepted=False,full_user_text_covered=True,human_timing_verified=False,known_open_review=['Numeric margins remain small; not PVT/voltage/temperature or HDMI sink latency acceptance.','Original33abnormal input delay/3dummy/2missing input/7missing output issues remain reviewed boundaries, not waived.','RGB332 cache,SDRAM macro/SiP/internal delays,CDC physical skew and complete-address physical BIST stay open.','MUSIC52user lines/53cues unchanged; third16new user lines/cues added; human listening/time validation is still required.'],source_sha256={p.relative_to(r).as_posix():sha(p)for p in [syn/'attempt.json',phy/'attempt.json',phy/'physical/sdram_phy.area',phy/'physical/sdram_phy.ts',phy/'physical/sdram_check.rpt',phy/'physical/route.qor',Path(__file__)]})
out=r/'04_evidence/v129_resource_review';assert not out.exists();out.mkdir();(out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
doc='# V129 资源、时序与布局布线\n\n同阶段与V128比较；EG4S20NG88，24MHz输入，720p与引脚/PLL/SDC不变。未降频或添加时序豁免。\n\n| 路由后资源 | V128 | V129 | 容量 |\n|---|---:|---:|---:|\n'+''.join(f'|{k.upper()}|{old[k]}|{new[k]}|{cap[k]}|\n'for k in ['lut','reg','bram','dsp'])
doc+='\n'+''.join(f'- {k}: {v:+.3f}ns\n'for k,v in slack.items())+f'- STA覆盖率: {coverage}%\n\n字库逐字保存12x12完整像素，每字144bit打包为8个18bit字。320字槽显式拆成2048x18与512x18，共5块字库BRAM；共286字/9bitID，不直接补齐到512字造成浪费；未缩小或裁剪字形。新增解包寻址不改变RGB/坐标/控制的4拍对齐。\n\n'
doc+='## 验证边界\n'+'\n'.join('- '+x for x in report['known_open_review'])+'\n\n数值通过不等于正式可靠性签核。尚未下载/Flash/TF写入/实物验收。\n'
(r/'03_docs/v129_资源时序与布局布线.md').write_text(doc,encoding='utf-8')
print(json.dumps(dict(routed=new,slack=slack,coverage=coverage),indent=2));print(out)
