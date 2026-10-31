from pathlib import Path
import json,re,hashlib,datetime
root=Path(__file__).resolve().parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((root/'BASELINE_v120_VERSION_STATUS.json').read_text(encoding='utf8'));v119=json.loads((root/'BASELINE_v119_VERSION_STATUS.json').read_text(encoding='utf8'))
phy=root/v119['physical_attempt']/'physical';timing=(phy/'sdram_pr.timing').read_text(encoding='utf8');area=(phy/'sdram_phy.area').read_text(encoding='utf8')
now=datetime.datetime.now().astimezone().isoformat();archive=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions/v121_performance_audit_20261029')
record=dict(version='v121_performance_audit_20261029',type='Read-only baseline audit; no RTL or bit change',created=now,design_version='v119',target=base['target'],resources=base['physical_resources'],slack_ns=base['slack_ns'],sta_coverage_percent=float(re.search(r'STA coverage\s*:\s*([\d.]+)%',timing)[1]),check_counts=base['check_timing_counts'],
 measured_scope='Existing V119 routed reports and validated source evidence, not new board measurements',
 derived_budget=dict(sd_clock_hz=49500000,spi_init_hz=49500000/248,spi_data_hz=49500000/8,spi_raw_bytes_per_second=49500000/8/8,audio_bytes_per_second=48000*24*2/8,raw_remaining_bytes_per_second=49500000/64-288000,pcm_fifo_frames=4096,pcm_fifo_ms=4096/48,prefill_ms=3072/48,low_water_ms=3584/48,video_frame_pixels=1280*720,frame_cache_bytes=1280*720,double_cache_bytes=2*1280*720,transition_frames=40,nominal_transition_s=40/60,reader_fifo_pairs=4096,reader_fifo_pixels=8192,reader_fifo_us_at_nominal_active_rate=8192/74.25),
 derived_budget_limits='Raw SPI ceiling excludes byte handshakes/commands/token/CRC/FAT/SD stalls; not a measured guaranteed throughput. No claim of load-time/FPS/latency improvement.',
 hotspots=[dict(instance='real_tf$loader',logic_lut=4223,ripple=1108,bram=13,dsp=10),dict(instance='real_tf$loader/source/source/probe',logic_lut=2310,ripple=626,bram=0,dsp=1),dict(instance='spectrum',logic_lut=1293,ripple=192,bram=1,dsp=2),dict(instance='help_ui',logic_lut=954,ripple=306,bram=5,dsp=0),dict(instance='pipe/reader',logic_lut=318,ripple=40,bram=0,dsp=1),dict(instance='real_tf$loader/packer',logic_lut=369,ripple=65,bram=0,dsp=1)],
 open_review=[
 dict(priority='P1',item='Resource headroom',evidence='LUT90.26%, BRAM90.62%',action='First eliminate per-burst constant-multiply addressing in reader/packer; retain all functions'),
 dict(priority='P1',item='Hold margin/PVT',evidence='HWNS24ps, both-corner TD analysis only',action='Compare routed-to-routed; do not waive constraints; measured board/PVT/vendor annotations remain open'),
 dict(priority='P1',item='CDC physical constraints',evidence='Gray dual-clock FIFO and audio mailbox present; async groups cut timing between domains',action='Review Gray-bus physical skew/max-delay support and actual crossing endpoints; no blanket declaration CDC passed'),
 dict(priority='P1',item='Memory macro annotations',evidence='PHY-7002 relocation,33 abnormal input delays,3 dummy categories and incomplete external IO budgets',action='Keep vendor/SiP/IO boundary explicit; not waived'),
 dict(priority='P1',item='Sustained SD bandwidth',evidence='SPI raw ceiling773437.5B/s; stereo PCM288000B/s',action='Instrument measured service latency/minimum FIFO level during image+audio; do not simply raise SPI rate'),
 dict(priority='P2',item='Clock naming/nominal cadence',evidence='Derived video clock report74.256MHz vs nominal74.25 sample clock model',action='Record ppm mismatch and verify HDMI ACR/sample cadence together; no one-sided clock changes'),
 dict(priority='P2',item='Function completeness',evidence='Four BMP files; root extra-WAV slot; fixed DEMO captions; bounded2048 dimensions; EOF stops',action='Do not market dynamic playlist/video decode/ASR/gapless loop or arbitrary image sizes'),
 dict(priority='P2',item='Physical performance/robustness',evidence='No new long soak,latency,card removal,power/thermal/PVT data',action='Provide repeatable board matrix and log rather than fabricate PASS')],
 source_sha256={p.relative_to(root).as_posix():sha(p)for p in (root/'01_project').rglob('*')if p.is_file()},new_simulation=False,new_synthesis=False,new_bit=False,new_hardware=False,flash_modified=False)
out=root/'04_evidence/v121_audit';out.mkdir(exist_ok=True);(out/'metrics.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
doc='''# V121全链路性能审计：先定义边界，再优化

## 基线与本次完成范围

当前稳定冻结来源V120，实际设计V119。已重新核对3306项文件、122条综合源哈希和23份报告；审计未改RTL、未重编译或写板。
历史仿真/编译/应用级固化许可不等于新一轮硬件性能或可靠性验收。

## 指标表

| 指标 | 当前值 | 结论/证据边界 |
|---|---|---|
| LUT | 17691/19600，90.26% | V119最终布线 |
| 寄存器 | 10429/19600，53.21% | 同上 |
| BRAM9K | 58/64，90.62% | 剩6块，不能盲加缓存 |
| DSP/PLL | 15/29、3/4 | 优先减少低价值寻址DSP |
| Setup/Hold | +0.663ns/+0.024ns | 数值满足，保持余量偏紧 |
| STA coverage | 99.81% | 不等于全部外部/宏/CDC签核 |
| SPI数据时钟 | 6.1875MHz | 代码参数推导，非示波器测量 |
| SPI原始吞吐上限 | 773437.5字节/秒 | 未扣协议/CRC/FAT/卡停顿 |
| WAV负载 | 288000字节/秒 | 48k/24bit/双声道 |
| PCM FIFO | 4096帧，85.33ms | 预填64ms，低水位74.67ms |
| 图像缓存 | RGB332，2×921600字节 | SDRAM双帧，不占双份片上帧BRAM |
| 转场 | 40输出帧，名义约0.667秒 | 不含下一图加载时间 |
| 源尺寸 | 最大2048×2048，双线性至720p | 不是无上限任意尺寸 |

## 从头到尾的检查清单

| 环节 | 已核对/已有证据 | 本轮仍需验证 |
|---|---|---|
| 复位/PLL | 域内释放、丢锁恢复路径及历史仿真 | 实物反复上下电/独立丢锁 |
| SD SPI | 单主机CRC提交、初始化/数据分频 | 多卡型号实际服务延迟与电气时序 |
| FAT/BMP | 有限目录扫描、边界校验、补齐/反向行序 | 大目录/异常卡实物矩阵 |
| 缩放/量化 | 双线性与RGB332抖动有独立逐像素参考 | 当前整机大源图加载耗时 |
| SDRAM | 双帧、读优先阈值、刷新与既有模型 | 全地址实卡BIST、宏内部延时/SiP/PVT |
| 音频 | 三扇区+4096FIFO、暂停/切换/欠样恢复 | 原音乐/广告/扩展与轮播并发长稳测 |
| CDC | Gray指针与请求/确认mailbox | 物理Gray跨位偏斜约束及逐交叉审查 |
| 视频/OSD/UI | 720p连续输出、固定流水延迟及历史raster oracle | 优化后的全回归和实屏 |
| DFT/艺术频谱 | 256采样、16真实频点、64插值显示条 | 音频静音/切换视觉过渡实物复核 |
| 布局布线 | 保留Both corner报告、hold repair | 每个候选实际路由对照，不只看综合 |

## 第一轮优化（另建V122，不能修改本冻结审计）

1. 读取地址的row×LINE_BURSTS改为逐行累加，缩短地址组合链并尝试释放DSP。
2. 写入打包地址也采用逐行基址与有限列索引，保留上下行序、valid/ack和最终完成语义。
3. 用旧RTL独立并排逐周期对照，覆盖随机背压、复位、正反行序、参数与非法坐标；再跑缩放/轮播/音频/UI/HDMI回归。
4. 重新综合与布线；只有资源/时序证据可接受才发布SRAM诊断bit。没证明提升的尝试保留失败记录，不包装为优化成功。
5. 不提高时钟/SPI、不减少颜色精度、不关闭诊断/图层，不修改ADC/SDC来换取表面通过。

## 电脑空间

C盘只读盘点初始剩余约7.5GiB。清理只选72小时以上旧版编译DB/PNL、旧下载暂存TAR、Intel安装崩溃dump；先在D盘逐文件备份/校验，再单文件删除C副本。
不删除Windows/WinSxS、ProgramFiles、驱动、正在使用的TD/runtime、源码/bit/TB、个人文档、微信/WPS/浏览器资料、许可证或未同步云文件。
清理日志与可恢复原路径备份位于 D:\\FPGA_Billboard\\90_tools\\maintenance\\20261029。没有把电脑所有非基础文件当成垃圾。

## 推荐当前上板文件

仍用V120冻结的V119原bit，不因审计重新下载。V122优化候选只有全部验证后另行给出，旧Flash不动。
无需交接压缩包。
'''
(root/'03_docs/v121_性能审计与优化路线.md').write_text(doc,encoding='utf8')
status=dict(record,archive_directory=str(archive),recommended_bit='03_bitstreams/v119_three_wav_720p.bit',recommended_bit_sha256=v119['bitstream']['sha256'])
(root/'VERSION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf8')
(root/'README_先看这里.md').write_text('# V121全链路性能审计（设计仍V119）\n\n本版只做审计及指标定义，未改设计、未编译或上板。详见03_docs/v121_性能审计与优化路线.md和04_evidence/v121_audit/metrics.json。\n\n下一轮在V122优化读/写行地址生成器并独立回归。当前不要更新Flash，继续保留V120。\n\n归档：`'+str(archive)+'`。旧版本全部保留，无需交接包。\n',encoding='utf8')
(root/'README_归档位置.md').write_text(str(archive)+'\n',encoding='utf8')
print(json.dumps(dict(version=record['version'],source_files=len(record['source_sha256']),sta_coverage=record['sta_coverage_percent'],new_bit=False),indent=2))