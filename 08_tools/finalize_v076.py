from pathlib import Path
import json, hashlib, shutil, datetime, re
R=Path(__file__).resolve().parents[1]
BASE=R.parent/'v072_hdmi_audio_pipeline_20261024'
ID='v076_picture_audio_sync_20261024'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def text(p,s):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def check_hashes(d,prefix):
 for k,v in d.items():
  p=prefix/k
  assert p.is_file(),p
  assert sha(p)==v,('source mismatch',p)
def check_record(p):
 d=read(p);assert d['passed'],p
 if 'complete' in d: assert d['complete'],p
 if 'source_sha256' in d: check_hashes(d['source_sha256'],R)
 for t in d.get('tests',[]):
  assert t['passed'],(p,t['name'])
  check_hashes(t['source_sha256'],R)
 return d
T=R/'05_td/v076_attempt2_authorized'
attempt=read(T/'attempt.json');audit=read(T/'audit.json')
assert attempt['returncode']==0 and audit['numerical_checkpoint_pass'] and audit['diagnostic_bit_generated']
check_hashes(attempt['source_sha256'],R/'01_project')
records=[
 'v076_visibility_20261024_193154/summary.json',
 'v076_top_20261024_193814/summary.json',
 'v076_packet_gate_20261024_194131/summary.json',
 'v072_modes_20261024_193637/summary.json',
 'v072_modes_20261024_193638/summary.json']
for n in records:check_record(R/'04_evidence'/n)
A=R/'04_evidence/v076_audio_sync_20261024_193326'
sim=read(A/'simulation.json');decode=read(A/'independent_decode.json')
assert sim['compile_rc']==0 and sim['sim_rc']==0
check_hashes(sim['source_sha256'],R)
assert 'PASS v076_gated_audio_video' in (A/'sim.log').read_text(encoding='utf-8')
assert decode['passed'] and decode['muted_pcm_negative_control']
check_hashes(decode['trace_sha256'],A)
review={
 'passed':True,'scope':'Existing unchanged simulation traces re-decoded with corrected checker; no production RTL change',
 'initial_record':'simulation.json (passed=false) and decode.log retained unchanged',
 'initial_failure':'Independent checker KeyError 6234: assumed 14 cycles from packet selection to received island; output register makes it 15 cycles.',
 'evidence':'gate trace selection cycle 1283, first island symbol cycle 1298; checker now uses gates[c-15].',
 'final_record':'independent_decode.json','corrected_log':'decode_corrected.log',
 'checker_sha256':sha(R/'02_tests/check_v076_audio_sync.py'),
 'simulation_source_sha256':sim['source_sha256'],'trace_sha256':decode['trace_sha256'],
 'reset_scope':'Reset flushing checked; second segment contains only 3 I2S frames, no HDMI audio packet. Long post-reset playback NOT established.',
 'physical_sink_latency_measured':False}
write(A/'validation_final.json',review)
# Keep vendor simulation excerpts outside excluded build/ directories.
retained=[]
for label,result,build in [
 ('v076_audio_native','tmds_v076_audio_native_results.json','v076_audio_native'),
 ('v072_audio_native','tmds_v072_audio_native_results.json','audio_native')]:
 d=read(R/'02_tests'/result);assert d['passed'] and len(d['cases'])==3
 for c in d['cases']:
  assert c['passed'] and c['compile_returncode']==0 and c['sim_returncode']==0
  assert any('PASS' in s and int(re.search(r'four_lane_bits=(\d+)',s).group(1))>=719860 for s in c['result_lines'])
 for entry in d['cases'][0]['provenance']:
  fn=entry['module']+'.v';src=R/'02_tests/build'/build/fn
  assert sha(src)==entry['excerpt_sha256']
  dst=R/'04_evidence/retained_test_sources'/label/fn
  dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
  retained.append({'path':dst.relative_to(R).as_posix(),'sha256':sha(dst),'provenance':entry})
# Synthesis run log would otherwise be excluded with build/.
syn=T/'build/idx_video_Runs/syn_1/run.log';dst=R/'04_evidence/v076_td_synthesis_run.log'
assert syn.is_file();shutil.copy2(syn,dst)
# Document exact project delta against archived functional baseline.
changed=[];unchanged=[]
for p in sorted((R/'01_project').rglob('*')):
 if not p.is_file() or any(x in p.parts for x in ['build','__pycache__']):continue
 rel=p.relative_to(R/'01_project');old=BASE/'01_project'/rel
 if old.is_file() and sha(old)==sha(p):unchanged.append(rel.as_posix())
 else: changed.append(rel.as_posix())
expected={
 'boards/idx_video_top.v','rtl/video/idx_pipeline.v','rtl/video/idx_display.v',
 'rtl/ip/hdmi_tx_wrap.v','rtl/audio/hdmi_audio_packets.v',
 'build_idx_physical_check.tcl','tools/run_idx_bitstream.py'}
assert set(changed)==expected,changed
write(R/'04_evidence/v076_baseline_diff.json',{'baseline':str(BASE),'changed':changed,'unchanged':unchanged,'constraints_pll_tf_sdram_unchanged':True})
bit=T/'reports/v076_picture_audio_sync_720p.bit'
assert sha(bit)==attempt['bit_sha256'] and bit.stat().st_size==attempt['bit_bytes']
shutil.copy2(bit,R/'03_bitstreams'/bit.name)
# Preserve original baseline docs as historical references, not current instructions.
history=R/'07_reference/inherited_v072_primary_docs'
for rel in ['README_先看这里.md','VERSION_STATUS.json','03_docs/上板步骤.md','03_docs/设计与验证说明.md']:
 dst=history/rel
 if not dst.exists():
  dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dst)
text(history/'README.md','# 历史文件，非 v076 操作入口\n\n这是从 v072 复制时的原始文档。持续测试音等描述已被 v076 的图片门控替代。当前入口见工程根目录 README_先看这里.md。\n')
text(R/'03_bitstreams/README_选择位流.md','''# 本轮请选择 v076
- 当前待测：`v076_picture_audio_sync_720p.bit`（629633 字节）。
- `v072_four_image_audio_720p.bit` 只保留为历史回退，不是本轮联动测试位流。
- 只做 SRAM 临时下载，勿选 PROGRAM_FLASH / ERASE_FLASH；本轮不改已固化基线。
''')
status={
 'version':ID,'archive_id':ID,'date':'2026-10-24','target':'VF-E20NG88 / EG4S20NG88 / 24 MHz',
 'baseline':'v072 functional source; same bitstream as user-accepted v074 Flash baseline',
 'v075_osd_merged':False,'scope':'Picture-visible-gated generated HDMI test audio; NOT MP4 or TF music playback',
 'playlist_images':4,'visible_dwell_seconds':5,'source_resolution':[640,480],'source_bpp':24,
 'framebuffer_format':'RGB332','output_resolution':[1280,720],
 'audio':{'sample_rate_hz':48000,'sample_bits':24,'channels':2,'tone_hz':1000,'gain':'signed divide by 4','audio_files_required':False,'new_external_i2s_wires_required':False,'gate':'First actual FIFO pixel sets picture_visible; hidden/disable/epoch reset/underflow silences PCM at audio-packet selection, AFTER FIFO. I2S, ACR and HDMI keep running.'},
 'bitstream':'03_bitstreams/'+bit.name,'bit_bytes':bit.stat().st_size,'bit_sha256':sha(bit),
 'tests':'04_evidence/v076_release_integrity.json','td':audit,
 'resources':{'lut':[10906,19600],'reg':[4949,19600],'bram9k':[4,64],'dsp':[1,29],'pad':[18,66],'pll':[3,4]},
 'constraints_changed':False,'clocks_changed':False,'hardware_programmed':False,'new_hardware_acceptance':False,
 'audible_playback_verified':False,'new_flash_write_performed':False,'formal_release_approved':False,
 'open_items':audit['open_review']+[
 'Physical display/audio acceptance of v076 pending; source/sink buffer and sound latency not measured.',
 'Full TF-to-physical-SDRAM simulation not freshly executed; unchanged existing path plus injected-FIFO top simulation.',
 'K0 may stop image mid-frame (inherited immediate epoch restart); not frame-boundary-atomic switching.',
 'Overflow/load_error are not new direct mute gate inputs; do not claim universal fault muting.',
 'RGB332 does not preserve full 24-bit BMP color precision; no EDID/DDC/audio format negotiation.',
 'v075 separate OSD enhancement not merged; this version does not certify all contest basic requirements.'],
 'created_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()}
write(R/'VERSION_STATUS.json',status)
text(R/'README_先看这里.md',f'''# v076：图片显示与 HDMI 测试音联动（待上板）

## 本轮只解决一个问题
| 图片状态 | HDMI 音频 |
|---|---|
| 上电等待、TF 读图、图片区域隐藏 | 静音（持续发送零 PCM） |
| 第一个真实帧缓存像素进入显示、图片正常显示 | 约 1 kHz 测试音 |
| 切换下一张、重试、显示欠流 | 静音，下一张真正显示后恢复 |

声音在图片显示期间持续，不会跟随每行消隐断断续续；不是每张只响一下。
HDMI 同步信号、I2S 采样和音频时钟包不中断，不靠重置显示链路静音。
已选音频包发送完才切换，新包门控已检查；不是声学输出零延迟承诺。

## 你现在做什么
按 `03_docs/上板步骤.md`，用 TD Programmer **SRAM 临时下载**：
`03_bitstreams/{bit.name}`

原 TF 卡四张官方 A/B/C/D.BMP 不变，不用新增 WAV/MP4，不用改驱动/接线。
需要能接收 HDMI 音频的设备；屏幕无喇叭时，用其支持音频输出的耳机口或 HDMI 音频分离器接有源音箱。
**Flash 已固化基线不改，先验证本版。**

## 本版状态
- 已完成代码、仿真、TD 综合/布局布线/位流生成；没有替你下载，也没有实屏/试听验收。
- 可见状态 85 项；顶层接线/黑屏遮罩 197 项；包门控 76 个采样、6 次切换；HDMI 独立解码 800 个 PCM 帧（396 静音 / 404 发声）。
- 模式 7 作业及旧顶层 1962 检查；原厂 ODDR 三相位串行比对通过。测试范围和初始失败记录见 `04_evidence`。
- TD SWNS +0.476 ns / HWNS +0.014 ns；器件资源未超出 EG4S20NG88。工具数值通过不等于宏/SiP/PVT 正式签核。
- PHY-7002、33 条内部异常输入延时等仍待审查，不以本次仿真替代完整地址实物 BIST。

## 版本关系
源于已通过的 v072 功能基线（v074 记录其 Flash 冷启动反馈）。v075 状态栏独立保留，未混入本版，便于隔离测试。
`07_reference/inherited_v072_primary_docs`、旧 v069/v070/v072 验收表和旧证据是历史参考，不是本次 PASS。
未实现 MP4 解码或 TF 音乐播放；本轮是图片/测试音启停联动，不据此宣称赛题全部通过。

## 文件分类
01_project 源码/约束/TD 脚本；02_tests TB/运行脚本；03_bitstreams 位流；03_docs 操作/验收；04_evidence 仿真/审核；05_td 编译报告；06_test_media 原素材；07_reference 来源/历史；08_tools 整理工具。
位流 SHA256：`{sha(bit)}`。
''')
text(R/'03_docs/上板步骤.md','''# v076 上板步骤：只临时下载，不改 Flash

## 1. 先不动接线与 TF 卡
- 卡内仍是已通过的 A.BMP / B.BMP / C.BMP / D.BMP（Logo、苹果、草莓、西瓜），无需再拔卡或写文件。
- 保持板卡、TF、下载器原接线，HDMI 从板卡接到显示/音频接收端；屏幕继续独立稳定供电。
- 若必须改线，先停止下载并给板卡断电。不要带电换 TF 或杜邦线。
- 用已有 HDMI 音频输出接耳机/有源音箱，或使用支持 HDMI 音频的电视/分离器。单独给 USB 喇叭供电不等于接入声音。
- 音量先调低；不接 FPGA GPIO 直接驱动喇叭，不加 I2S 排线。

## 2. 下载
1. 先开屏幕，选对 HDMI 输入；再给板卡上电。板卡可能先运行 Flash 中的旧版本，属于正常。
2. 打开此前使用成功的 TD Programmer，连接原下载器并扫描同一器件链，确认 EG4S20NG88。
3. 选择 **FPGA SRAM / JTAG 临时配置**，不要选择 PROGRAM_FLASH、ERASE_FLASH 或 VERIFY_FLASH。
4. 选择本版 `03_bitstreams/v076_picture_audio_sync_720p.bit`，确认不是旧 v072/v075 文件。
5. 下载并等待明确成功；过程不要断电/拔线。不必再进行综合。
6. 等第一张读完，不连续按键。初次加载期间应静音，图片出现后应发出约 1 kHz 测试音。

## 3. 检查三件事
1. 自动轮播：A→B→C→D→A 至少两轮。每张实际显示约 5 秒；读下一张时图片区域变黑/隐藏并静音，下一张出现后恢复发声。背景/外框仍可能存在，不应变成显示器“无信号”。加载时间不是固定 5 秒。
2. 手动：短按 K1 切手动（L0 快闪），等待至少 10 秒，当前图与音都保持；短按 K0 切下一张，检查“旧图消失→静音→新图出现→发声”。加载中重复 K0 会被忽略。
3. 再按 K1 回自动（L0 慢闪），确认继续四图轮播。图片稳定期间声音不应每行或每帧断续；记录是否明显提前/滞后、杂音或爆音。

K0 继承原设计的即时内容重启，不保证在整帧结束切换。门控有包边界延迟，显示器/音响也有缓存，是否感知同步必须实物确认。
不要带电拔 TF 制造故障；欠流/重试已做数字仿真，正常验收先不注入电气故障。

## 4. 灯态
- L0 自动慢闪 / 手动快闪；L1 视频 PLL 锁定；L2 SDRAM PLL 锁定；L3 SDRAM 初始化。
- L4 帧写完；L5 显示运行（切图期间可变化）；L6 欠流/溢出/音频 FIFO 错误；L7 TF 格式/读取错误。
- 稳定显示时 L6/L7 应灭；这些不是像素比较或声音实测 PASS。

## 5. 出现问题时只记录，不改环境
- 有图无声：核对音频输出设备/音源/静音/分离器 LPCM 2CH，勿先改 TF 或驱动。
- 无信号：记录下载前后、L1/L2/L6/L7及屏幕供电；不要把整屏无信号当成预期“静音黑底”。
- 要回退：正常断电再上电将恢复原 Flash 基线；本版 SRAM 配置会丢失，这是预期。重试 v076 需再临时下载一次。
- 反馈：①图片显示有无声音；②切图阶段有无静音；③手动/自动是否都正常；④是否丢信号；⑤L6/L7。
本版通过后另建新版本记录验收，再决定是否固化，当前不要覆盖 Flash。
''')
text(R/'03_docs/设计与验证说明.md','''# v076 设计与验证范围

## 数据路径和新改动
沿用 SPI→FAT32/BMP→FIFO→SDRAM RGB332→HDMI 1280×720，以及 I2S 测试音→串行接收→有符号除4→HDMI 音频。
idx_display 的 picture_visible 在第一笔真实 FIFO 像素弹出时置位，匹配注册后的像素；加载/内容复位/禁止显示/欠流时清零，正常行场消隐期间保持。
该信号经 idx_pipeline/top 到 hdmi_tx_wrap，随 RGB 同拍寄存，再在音频 FIFO 后、IEC60958 校验/BCH 编码前决定发送采样值还是零。已经选中的音频包完整发完，不截断包或清空 HDMI 时序。
黑色图片也是有效图片，不根据 RGB 是否非零判断发声。

## 仿真与 TD
- 可见性单测85检查：预填充、第一像素、消隐、重启、disable、欠流及重试。
- 真实顶层197检查：真实 display/top/wrapper，但注入 FIFO 数据/内容时刻/坐标，PLL 行为模型，SDRAM 空壳。非真实 TF 读取或物理 SDRAM 验收。
- 快速包门控：6次启停、19组、76个采样；所测最长门控至下一音频包选择5865像素周期，断言上限10000周期。加上已选包完成/输出流水，且接收端有额外缓存，不承诺物理零延迟。
- 整帧数字接收器解码：真实 I2S 串行接收、增益、TERC4、BCH、InfoFrame、N6144/CTS74250（48kHz）、IEC状态/奇偶；800 PCM帧，396静音404发声。BCH故意损坏和静音泄漏负例都被拒绝。
- 首次独立解码器误用14周期偏移而失败；实际含输出寄存为15周期。保留旧simulation.json/decode.log，修正后复核原始未变轨迹通过，见 validation_final.json。没有用改 RTL 掩盖检查器错误。
- 复位后的短段只有3个 I2S 帧，无 HDMI 音频包，不据此宣称长时间复位恢复播放；原厂ODDR三相位另做串行/复位检查，不替代接收端协议验证。
- 模式7作业/旧顶层1962检查通过；门控版及兼容未门控版的原厂ODDR三相位各通过719860～719868比特/相位。
- TD 数值SWNS+0.476/HWNS+0.014ns，覆盖99.86%，位流629633字节；LUT10906/19600、寄存器4949/19600、BRAM4/64、DSP1/29、PAD18/66、PLL3/4。

## 不宣称解决的事
未上板、未试听、未重新固化；无 MP4 解码、TF 音乐、EDID/DDC；不是所有故障都新增直接静音门控。K0 为继承的即时重启，不是帧边界原子切换。
TF/SDRAM/PLL/引脚约束未改，不重跑完整 TF→物理 SDRAM 仿真；宏PHY-7002、33内部延时、SiP/电压速度级/全地址实物BIST/PVT等开放项不豁免。
RGB332保留原有色深限制。v075状态栏独立待测，未整合；本版是基础联动一项，不等于全部赛题验收结论。
''')
text(R/'03_docs/v076_验收记录模板.md','''# v076 用户实测记录（待填写，不是通过记录）
- 日期/接收设备型号/音频输出路径：
- SRAM 下载文件及成功截图：
- 首次加载静音 / 首图出现发声：
- 自动两轮 A/B/C/D：图片停留、切图静音、丢信号情况：
- K1 手动保持10秒 / K0 下一张联动：
- K1 恢复自动：
- 可感知音画提前/滞后、噪声/爆音：
- 稳态 L0～L7：
- Flash 未改确认 / 回退如有：
- 结论：未测 / 部分通过 / 通过 / 失败（注明实际测试范围）：
''')
# Hash all relevant current test tools and HDL; archive manifest covers all other files.
source_paths=[p for p in (R/'01_project').rglob('*') if p.is_file() and p.suffix in ['.v','.vh','.adc','.sdc','.tcl','.py'] and 'build' not in p.parts and '__pycache__' not in p.parts]
source_paths += [p for p in (R/'02_tests').glob('*') if p.is_file() and (p.name.startswith(('tb_v076','run_v076','check_v076')))]
write(R/'04_evidence/v076_release_integrity.json',{
 'passed':True,'version':ID,'current_source_sha256':{p.relative_to(R).as_posix():sha(p) for p in sorted(source_paths)},
 'td_source_matches_attempt':True,'bit_sha256':sha(bit),'bit_bytes':bit.stat().st_size,
 'test_records':['04_evidence/'+n for n in records]+['04_evidence/v076_audio_sync_20261024_193326/validation_final.json','02_tests/tmds_v076_audio_native_results.json','02_tests/tmds_v072_audio_native_results.json'],
 'retained_vendor_excerpts':retained,'td_synthesis_log_sha256':sha(R/'04_evidence/v076_td_synthesis_run.log'),
 'test_scope':'Digital layered tests, not real TF/memory/sink acceptance. Historical and failed evidence retained, not falsely counted as current passes.',
 'new_hardware_acceptance':False,'new_flash_write_performed':False})
print('PASS v076 final source/test/bit integrity; docs updated. BIT:',R/'03_bitstreams'/bit.name)


