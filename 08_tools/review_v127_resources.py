"""Same-stage V126/V127 metrics, not reliability signoff."""
from pathlib import Path
import json,re,hashlib
r=Path(__file__).resolve().parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v126_fifo_prefix_20261030\01_project')
syn=r/'05_td/v127_audio_visual_synth_attempt1';phy=r/'05_td/v127_audio_visual_physical_attempt1';sj=json.loads((syn/'attempt.json').read_text());pj=json.loads((phy/'attempt.json').read_text());assert sj['completed']and pj['completed']
for rel,h in sj['source_sha256'].items():assert sha(r/rel)==h,rel
for rel in ['01_project/boards/idx_video.adc','01_project/boards/idx_video.sdc','01_project/rtl/ip/pll_video720.v','01_project/rtl/ip/pll_sdram.v']:assert sha(r/rel)==sha(base/rel),rel
cap=dict(lut=19600,reg=19600,bram=64,bram32k=16,dsp=29,pll=4,gclk=16,pad=66)
def area(p):
 s=p.read_text();return{k:int(re.search(r'^#'+k+r'\s+(\d+)',s,re.M).group(1))for k in cap}
new=area(phy/'physical/sdram_phy.area');old=area(base/'05_td/v126_audio_visual_physical_attempt3/physical/sdram_phy.area');bs=json.loads((base/'05_td/v126_audio_visual_synth_attempt1/attempt.json').read_text())
assert all(new[k]<=v for k,v in cap.items())
timing=(phy/'physical/sdram_pr.timing').read_text();coverage=float(re.search(r'STA coverage\s*:\s*([\d.]+)',timing).group(1))
counts={m.group(1):int(m.group(2))for m in re.finditer(r'^\d+\. checking (.*?)\((\d+)\)',(phy/'physical/sdram_check.rpt').read_text(),re.M)}
changes=[]
for p in (r/'01_project').rglob('*'):
 if p.is_file() and p.suffix in {'.v','.vh','.tcl','.sdc','.adc'}:
  rel=p.relative_to(r);prior=base/rel
  if not prior.exists()or sha(p)!=sha(prior):changes.append(dict(path=rel.as_posix(),old_sha256=sha(prior)if prior.exists()else None,new_sha256=sha(p)))
report=dict(passed=True,scope='Same-stage actual synthesis/routed area and both-corner numeric STA; no benchmark throughput gain, hardware signoff or transcription correctness claimed.',baseline_v126_synthesis=bs['resources'],synthesis_resources=sj['resources'],synthesis_delta={k:sj['resources'][k]-bs['resources'][k]for k in cap},baseline_v126_routed=old,routed_resources=new,routed_delta={k:new[k]-old[k]for k in cap},capacities=cap,remaining={k:cap[k]-new[k]for k in cap},utilization_percent={k:round(new[k]/cap[k]*100,2)for k in cap},slack_ns=pj['slack_ns'],baseline_v126_slack_ns=dict(SWNS=-0.708,STNS=-2.999,HWNS=0.032,HTNS=0),coverage_percent=coverage,check_timing_counts=counts,physical_slice_utilization_percent=97.09,production_changes=changes,formal_release_approved=False,hardware_accepted=False,complete_lyrics=False,known_open_review=['Setup0.193ns and hold0.021ns margins remain small; not robust/PVT/voltage acceptance.','33 abnormal input delays,3 dummy nodes,2 missing input delays,7 output delays need original macro/board diagnostic review; not waived.','RGB332 cache, SDRAM macro/SiP/PVT/internal delays, CDC physical skew and full-address physical BIST remain open.','ASR text/time candidate not human verified; subtitles currently13 partial cues.'],source_sha256={p.relative_to(r).as_posix():sha(p)for p in [syn/'attempt.json',phy/'attempt.json',phy/'physical/sdram_phy.area',phy/'physical/sdram_phy.ts',phy/'physical/sdram_check.rpt',phy/'physical/route.qor',Path(__file__)]})
out=r/'04_evidence/v127_resource_review';assert not out.exists();out.mkdir();(out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
(r/'03_docs/v127_资源时序与布局布线.md').write_text(f'''# V127 同阶段资源和时序

目标EG4S20NG88，24MHz输入，原720p/PLL/ADC/SDC不变。未加虚假false-path、多周期或降频。

| 路由后资源 | V126最后一次 | V127本次 | 容量 |
|---|---:|---:|---:|
'''+''.join(f'| {k.upper()} | {old[k]} | {new[k]} | {cap[k]} |\n'for k in ['lut','reg','bram','dsp'])+f'''
同阶段综合LUT：{bs['resources']['lut']}→{sj['resources']['lut']}。路由后物理slice利用率97.09%，并不宽裕，不应只看LUT余量盲目增加缓冲。

- SWNS：−0.708ns → +0.193ns；STNS：−2.999ns → 0。
- HWNS：+0.021ns；HTNS：0。保持时间仍很紧，不能称为“高裕量”或“完成PVT签核”。
- STA覆盖率：{coverage}%；原内部宏/SiP/异常延时、CDC及实物BIST边界保留。

## 定向修改

1. 将转场step×常量及左右分界列改为每生产帧边界更新的几何寄存器，避免每次SDRAM请求重复串联计算。
2. 仲裁决定授予读/写事务的同一拍锁存地址；不增加请求/ACK空拍，断开长地址组合链与SDRAM控制状态判定。
3. 窄ROM读取字幕时间元数据和紧凑字模；不做64句大并行比较器，不加额外帧缓存或音频三大缓冲。
4. TD使用合法布局、拥塞感知布线和物理hold修复；本轮一次有界布局成功，无换时钟或删约束。

## 验证限制

资源与数值时序通过不等于字幕准确、实际HDMI收端同步或板卡可靠性通过。复核所有初始化ROM（含18bit字幕元数据parity）后才允许生成SRAM候选。Flash和真实板卡未操作。

详见04_evidence/v127_resource_review/summary.json与05_td/v127_audio_visual_physical_attempt1/physical。
''',encoding='utf8')
print(json.dumps(dict(routed=new,slack=pj['slack_ns'],production_changes=[x['path']for x in changes]),ensure_ascii=False,indent=2));print(out)
