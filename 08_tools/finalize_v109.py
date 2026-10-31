"""Freeze source-bound v109 documents and artifacts. No hardware actions."""
from pathlib import Path
import argparse,hashlib,json,shutil,re
from PIL import Image
r=Path(__file__).resolve().parents[1];assert '01_versions'not in r.parts
ap=argparse.ArgumentParser();ap.add_argument('--synth-attempt',type=int,default=6);ap.add_argument('--physical-attempt',type=int,default=4);ap.add_argument('--bitgen-attempt',type=int,default=1);args=ap.parse_args()
vid='v109_tf_wav_fit_20261026';archive=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions')/vid
assert not archive.exists(),'Never edit frozen archive'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(p,q):
 q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():assert sha(p)==sha(q),str(q)
 else:shutil.copy2(p,q)
 assert sha(p)==sha(q)
syn=r/f'05_td/v109_audio_visual_synth_attempt{args.synth_attempt}/attempt.json';phy=r/f'05_td/v109_audio_visual_physical_attempt{args.physical_attempt}/attempt.json';bg=r/f'05_td/v109_tf_wav_bitgen_attempt{args.bitgen_attempt}/attempt.json'
sy,ph,b=map(load,(syn,phy,bg));assert all(x['completed']for x in(sy,ph,b));bit=r/'03_bitstreams/v109_tf_wav_720p.bit';assert sha(bit)==b['bit_sha256'];assert min(ph['slack_ns'].values())>=0
for name,h in sy['source_sha256'].items():assert sha(r/name)==h,name
for info in b['reviewed_reports'].values():assert sha(r/info['path'])==info['sha256'],info['path']
# Preserve selected generated databases and original relative source references.
gate=syn.parent/'build/idx_video_Runs/syn_1';dest=r/'04_evidence/v109_final_synthesis_preserved';kept=[]
for src in sorted(gate.iterdir()):
 if src.is_file():
  q=dest/src.name;copy(src,q);kept.append(dict(file=src.name,bytes=src.stat().st_size,sha256=sha(q)))
write(dest/'preservation.json',dict(reason='Selected gate DB/reports outside excluded build caches',files=kept))
proj=syn.parent/'td_project/idx_video.al';prj=proj.parent/'idx_video_Runs/syn_1/idx_video.prj';copy(syn.parent/'build/idx_video.al',proj);copy(gate/'idx_video.prj',prj)
refs=[]
for f in(proj,prj):
 for name in re.findall(r'<File Path="([^"]+)"',f.read_text(encoding='utf-8')):
  q=(f.parent/name).resolve();assert q.is_file(),str(q);refs.append(dict(project=f.relative_to(r).as_posix(),source=q.relative_to(r).as_posix(),sha256=sha(q)))
write(dest/'td_project_relative_paths.json',dict(passed=True,references=refs,note='Raw project header preserves original build path; relative file references verified. Rebuild in a mutable work copy, not an archive.'))
for name in['README_先看这里.md','README_归档位置.md','VERSION_STATUS.json']:
 p=r/name;q=r/('INHERITED_v107_'+name)
 if p.is_file()and not q.exists():copy(p,q)
res=sy['resources'];sl=ph['slack_ns'];notes=b['known_open_review']+[
 'v109 has not been programmed, viewed/heard, cold-booted or stress-tested on the real board.',
 'Real music/ad files are local test media; public redistribution rights are not assumed.',
 'Image loads may take longer with file audio sharing SPI; no1-second transition claim.',
 'Sticky physical SD transport errors may need a power cycle; no hot-swap recovery claim.']
status=dict(version=vid,parent='v108_tf_wav_development_checkpoint_20261026',baseline='v107_keys_subtitle_20261026',date='2026-10-26',target='VF-E20NG88 / EG4S20NG88 /24MHz',scope='TF MUSIC/ADVOICE PCM-WAV playback/source selection with retained720p images/UI/spectrum',resources=res,slack_ns=sl,validation=b['reviewed_reports'],selected_attempts=dict(synthesis=args.synth_attempt,physical=args.physical_attempt,bitgen=args.bitgen_attempt),numerical_timing_pass=True,formal_release_approved=False,new_hardware_acceptance=False,programmed=False,flash_modified=False,tf_modified=False,bitstream=str(bit),archive_bitstream=str(archive/'01_project/03_bitstreams'/bit.name),bit_sha256=sha(bit),bit_bytes=bit.stat().st_size,check_timing_counts=b['check_timing_counts'],archive_destination=str(archive),known_open_review=notes,no_handoff_zip=True)
write(r/'VERSION_STATUS.json',status)
keys='''|操作|功能|
|---|---|
|浏览时短按K0|下一图；图像客户端错误重试|
|浏览时短按K1|自动/手动轮播|
|长按K0约1秒后松开|进入/退出锁存音频选择，不必持续按住|
|音频选择中短按K1|跟随图片的内部演示音 → MUSIC.WAV音乐 → ADVOICE.WAV广告 → 跟随图片|
|音频选择中短按K0|退出选择，保留当前音源，不切图|
|长按K1约1秒|中文控制UI常显/收起，不附带短按|
|双键短按|装饰OSD/Logo/频谱/演示字幕显隐|
|双键长按约1秒|浏览 → 亮度 → 对比度 → 浏览，退出音频选择|
|调参中短K0/K1|减少/增加当前参数，原范围不变|
'''
steps='''1. **先不固化Flash。** 用本版位流做JTAG/SRAM临时测试；旧Flash不动。
2. 若TF卡还没有两个WAV：先关闭/断开板卡电源，再取出TF卡接读卡器。复制`06_test_media/audio/MUSIC.WAV`和`ADVOICE.WAV`到FAT32卡根目录；保留原`A.BMP/B.BMP/C.BMP/D.BMP`，不要格式化或删图。
3. 安全弹出读卡器，把卡插回**断电**的SPI模块，恢复供电/HDMI/音箱。音箱先低音量，接线与原版本相同。
4. 临时下载`03_bitstreams/v109_tf_wav_720p.bit`。等四张图正常显示，短K1切手动，先排除图片切换干扰。
5. 长K0约1秒并松手，短K1选“音乐文件”。等待挂载/预缓冲，应听到真实音乐，不是旧测试音；频谱随实际PCM变化。短K0退出选择，音乐应继续。
6. 再长K0进入，短K1选“广告语音”。允许短暂静音预缓冲，但**不能HDMI无信号、混入上一段残音或卡死**。广告约30.08秒，结尾应排空后静音。
7. 选择“跟随图片”回到旧内部演示音；再选“音乐文件”应从头播放。当前不做无缝循环，播完后切走再切回即可重播。
8. 切回自动轮播，音乐/广告同时观察四图、720p、中文UI、OSD与频谱。长K1独立开关UI，长短按不应互相误触。真实WAV模式不显示旧16秒演示字幕。
9. 出错先记录错误码、L0-L7、音源和是否正在换图；**不要继续写Flash或带电拔卡**。底层SD传输错误可能需断电重启，未宣称热插拔恢复。
'''
readme=f'''# v109：TF卡音乐/广告播放与选择切换（待实物验证）

目标：VF-E20NG88 / EG4S20NG88 /24MHz，HDMI1280×720。

**本版已完成源码、仿真、综合、布局布线、数值时序和新位流生成；没有下载、实屏/听音、Flash或冷启动验收。不是把旧bit改名。**

## 新增内容
- FAT32根目录读取`MUSIC.WAV`、`ADVOICE.WAV`，支持碎片簇链；图片/音频共用持续工作的SPI主机。
- WAV PCM48kHz，16/24bit、单/双声道，统一内部24bit双声道；2048帧异步FIFO和48k节拍。
- 切换清空旧FIFO，再预缓冲新音源；不复位HDMI/SD主机；EOF排空后静音。
- 频谱来自送往HDMI的实际PCM。保留四图、双线性缩放、RGB332缓存、亮度/对比度、中文UI和原手势。
- 不是MP3/FLAC解码器。原FLAC已另转PCM WAV，不能直接改后缀。真实WAV模式隐藏旧演示字幕，不冒充歌词/广告词识别。

## 推荐测试位流
工作文件：`{bit}`
归档文件：`{archive/'01_project/03_bitstreams'/bit.name}`
SHA256：`{sha(bit)}`；{bit.stat().st_size}字节。**仅SRAM临时测试，先不要写Flash。**

## 按键
{keys}
## 测试步骤
{steps}
## 资源和边界
整机综合LUT {res['lut']}/19600，REG {res['reg']}/19600，BRAM9K {res['bram']}/64，DSP {res['dsp']}/29，PLL {res['pll']}/4。
数值时序SWNS {sl['SWNS']:+.3f}ns，HWNS {sl['HWNS']:+.3f}ns；不是PVT/SiP/电气签核。SDRAM宏重定位、异常内部延时、完整地址实物BIST等开放项保留。

详见`03_docs/v109_实现与验证说明.md`和`03_docs/v109_实物测试记录_待填写.md`。`08_tools/run_acceptance.py`默认只读校验，不下载或改TF/Flash。新增均在D盘，旧版保留，**无需交接压缩包**。
'''
(r/'README_先看这里.md').write_text(readme,encoding='utf-8');(r/'README_归档位置.md').write_text(f'v109冻结归档：`{archive}`\n新增均在D盘，不覆盖旧版，无需交接ZIP。归档只读，构建请先复制到工作目录。\n',encoding='utf-8')
report='''# v109 实现、资源和验证说明

## 数据链路
TF SPI → 单主机扇区仲裁 → FAT32目录/簇链 → CRC确认的512字节隔离缓存 → RIFF/WAV解析 → 2048×48bit异步FIFO → 48k节拍 → 既有衰减/实际PCM频谱 → HDMI LPCM。
图像保持BMP/双线性/RGB332/SDRAM双缓存链路，按扇区共享SPI。低水位音频优先，客户端复位时排空当前扇区，不重新发CMD0。

## 优化与保留的失败记录
- v108布局超限。v109中间综合/物理attempt全部保留，不能冒充发布通过。
- 共享BPB/BMP32bit滚动字段装配；流式MBR首匹配；完整512字节、顺序、CRC有效才提交元数据。
- 不需保留数值的头字段改精确校验标志。文件/根目录共用有界移位加法LBA，最多7次移位，不更改地址边界。
- 频谱混合化简为bg*16+(fg-bg)*alpha，保持Q4向下取整及3拍视频延迟，利用空闲DSP省LUT，不删除UI或频谱。
- 采用TD手册ALL器件适用的high打包和min_control_set=2；能装下不等于时序通过。物理attempt3 SWNS-2.067ns，未发位流。
- 半周期负路径来自SD域下降沿复位释放经仲裁valid到BMP使能。改为异步拉低/上升沿4级同步释放，像素域不变，不加假路径或放宽时钟。
- 中间短FIFO/4倍采样压力例欠载，保留失败；最终512帧/标称节拍矩阵及2048帧/4倍消费例分别记录，不称为电气实测。
- 早期SPI测试编译后源码变化，另有300秒墙钟超时；PROVENANCE_LIMITATION明确排除其最终证据资格。最终runner编译前记录哈希、结束复核。
- UI首次测试误用V108标题参考，修测试期望为V109后重跑；ROM检查首次glob误取probe报告也已修正。所有不完整/失败日志保留。

## 选定构建和资源
'''
report+=f'综合attempt{args.synth_attempt}、物理attempt{args.physical_attempt}、bitgen attempt{args.bitgen_attempt}。\n\n|资源|使用/容量|占比|\n|---|---:|---:|\n'
for k,n,label in [('lut',19600,'LUT'),('reg',19600,'寄存器'),('bram',64,'BRAM9K'),('dsp',29,'DSP'),('pll',4,'PLL')]:report+=f'|{label}|{res[k]}/{n}|{100*res[k]/n:.2f}%|\n'
report+=f'\nSWNS {sl["SWNS"]:+.3f}ns，STNS {sl["STNS"]:.3f}ns，HWNS {sl["HWNS"]:+.3f}ns，HTNS {sl["HTNS"]:.3f}ns。\n\n## 验证证据\n\n|项目|证据路径（工程根目录相对）|本轮执行|\n|---|---|---|\n'
for name,info in b['reviewed_reports'].items():report+=f'|{name}|`{info["path"]}`|{"是"if info["current_v109_execution"]else"源码哈希一致复用"}|\n'
report+='''
WAV解码20例：16/24bit单双声道、未知/奇数块、格式/44.1k/越界/残帧拒绝，以及真实MUSIC/ADVOICE各前1024帧；行为播放4例使用2048帧FIFO，包含2501帧EOF、切换、CRC/索引错误。挂载22例覆盖四MBR槽、首匹配、坏分区/BPB、活动FAT、碎片根目录、缺字节/错序。两个BMP链各76例，新增2048边界TB使用本次新probe；输出32×18以控制仿真时长，完整720p缩放按未改源码哈希复用8例。

实际SPI数字引脚矩阵3例采用512帧测试FIFO/标称采样节拍，另1例采用2048帧产品FIFO/4倍采样消费压力；逐帧对比WAV和BMP缩放像素，核对CMD0仅一次、epoch、无欠载。不是完整720p SDRAM/HDMI/真实卡电气端到端仿真。视觉9组含注入内存顶层；原生HDMI3相位；UI420状态/5帧像素、按键/演示字幕6组；最终路由10个UI/字幕BRAM初始化逐项检查。

## 未完成和边界
'''+ '\n'.join('- '+n for n in notes)+'\n'
(r/'03_docs/v109_实现与验证说明.md').write_text(report,encoding='utf-8')
(r/'03_docs/v109_实物测试记录_待填写.md').write_text('''# v109 实物测试记录（尚未测试）
本表不代表通过；下载、画面、听音、稳定、冷启动分别记录。

|检查项|结果/现象|
|---|---|
|日期/测试人/TF容量/FAT32|待填|
|SRAM文件名/SHA256/下载结果|待填|
|四图/720p/缩放/OSD|待填|
|长K0进入、短K1音乐/广告/演示音|待填|
|短K0退出不切图，音频继续|待填|
|音乐10秒/左右声道/音量/无杂音|待填|
|广告30.08秒与EOF静音|待填|
|切走切回从头重播/无残音|待填|
|切换时HDMI不掉信号|待填|
|真实音乐和自动四图/切图耗时|待填|
|真实PCM频谱/静音消隐|待填|
|长K1独立UI/无误触|待填|
|WAV模式无16秒演示字幕|待填|
|连续10分钟/重复选择20次/错误码/L0-L7|待填|

本轮未改Flash。断电可能回旧Flash版，不能代替v109冷启动验收。
''',encoding='utf-8')
# These are digital RTL renderings, never board photos/acceptance evidence.
u=r/b['reviewed_reports']['hidden_ui']['path']
for p in sorted(u.parent.glob('*.png')):
 if p.name.endswith('_1.png'):copy(p,r/'03_docs/v109_UI_RTL预览.png')
v=r/b['reviewed_reports']['visual']['path'];p=v.parent/'v109_active_spectrum.ppm'
if p.is_file():Image.open(p).save(r/'03_docs/v109_艺术频谱_RTL预览.png')
files={}
for base in['01_project','02_tests','03_bitstreams','03_docs','08_tools']:
 for p in sorted((r/base).rglob('*')):
  if p.is_file()and not set(p.relative_to(r).parts)&{'build','__pycache__'}and p.suffix not in{'.vvp','.vcd','.pyc'}:files[p.relative_to(r).as_posix()]=sha(p)
for p in[r/'README_先看这里.md',r/'README_归档位置.md',r/'VERSION_STATUS.json',syn,phy,bg,r/'06_test_media/audio/audio_manifest.json',*sorted((r/'06_test_media/audio').glob('*.WAV'))]:files[p.relative_to(r).as_posix()]=sha(p)
for x in b['reviewed_reports'].values():files[x['path']]=x['sha256']
for p in dest.rglob('*'):
 if p.is_file():files[p.relative_to(r).as_posix()]=sha(p)
for p in[proj,prj]:files[p.relative_to(r).as_posix()]=sha(p)
write(r/'04_evidence/v109_release_manifest.json',dict(version=vid,files_sha256=files,hardware_test=False,flash_modified=False,tf_modified=False,source_bit_consistency_only=True))
print(json.dumps(dict(version=vid,resources=res,slack_ns=sl,artifact_count=len(files),bit=str(bit),sha256=sha(bit),archive_destination=str(archive),new_hardware=False),ensure_ascii=False,indent=2))
