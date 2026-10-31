# 基于 FPGA 的多媒体广告牌

**公开开源工程｜VF-E20NG88 / EG4S20NG88｜24 MHz｜原作品固件 V132**

单块 FPGA 实现本地 TF/FAT32、24-bit 非压缩 BMP 解析、双线性缩放、RGB332 SDRAM 双帧、1280×720 HDMI、PCM WAV 音频、真实 DFT 频谱、播放样本同步字幕与中文双按键 UI。运行时无 CPU、软核或外接处理器。

## 完成状态

- **原作品功能测试、Flash 固化、冷启动通过**：用户于 **2026-10-31** 明确确认。证据类型为用户实物反馈，见 `07_acceptance/USER_ACCEPTANCE_20261031.json`。
- 原 V132 同阶段路由报告：LUT **17739/19600**、REG **10676/19600**、BRAM9K **61/64**、DSP **17/29**；SWNS **+0.667 ns**，HWNS **+0.021 ns**，STNS/HTNS 为 0。
- 本次公开版完整保留生产算法、顶层、引脚和时钟约束。**仅原歌词字幕 ROM 与原 TF Logo 图案改为自编公开示例数据**，保持存储接口和布局。原 TF 图片、音乐、歌词、时间轴、原位流与含这些内容的历史对象不公开。
- 因 ROM 数据不同，公开示例重建的位流不等于原已固化位流。不能把原作品实物通过自动写成公开示例位流通过；公开版测试范围见 `PUBLIC_TEST_STATUS.json`。
- UI 标题仍保留 V130；实际固件身份以构建记录和 SHA256 为准。

## 已实现功能

1. SPI 读取 FAT32：四张 BMP 自动/手动轮播，解析宽高、正反行与行补齐；支持范围内的不同尺寸经双线性插值输出 720p。
2. RGB332 双帧缓存、异步 FIFO、SDRAM 仲裁与滑动切换；输入 BMP 为 RGB888，不把帧缓存描述成 24-bit 真彩色。
3. OSD 时间、标语、Logo 多图层混合；中文双列半透明 UI 可独立显隐，显示状态、按键提示、亮度、对比度和音量。
4. 48 kHz / 24-bit / 双声道 PCM WAV，音乐、广告、扩展文件与测试音切换，暂停/继续及音量调节，HDMI 输出音视频。
5. 256 点、16 个选定频点的真实 DFT，映射为 64 根视觉频谱柱；不是 256-bin FFT。
6. 字幕按实际播放样本计数，暂停冻结、恢复继续、切歌重置；频谱/字幕作为 AV 图层组可与基础 OSD 分开显隐。字幕为预编译时间轴，不是语音识别。

## 目录

| 目录 | 内容 |
|---|---|
| `01_project/` | 完整当前 RTL、顶层、PLL 包装、ADC/SDC、TD 构建入口 |
| `02_tests/` | 模块与集成 TB，公开便携回归 |
| `tools/` | 可配置复现、公开字幕/Logo/合成媒体生成、文件校验 |
| `08_tools/` | 历史开发脚本与算法辅助工具；原机路径脚本不是跨机默认入口 |
| `03_docs/` | 公开字体/字幕规格与数据布局 |
| `04_evidence/` | 本次公开数据版本的仿真结果、日志与示例帧 |
| `05_td/` | 原已验收配置的综合/布局布线数值报告，不含私有数据网表 |
| `06_test_media/` | 自编测试字幕及素材说明；不含原 TF 素材 |
| `07_acceptance/` | 原作品用户验收记录与测试范围 |
| `07_reference/` | HDMI 参考源码、字体及原始许可证 |
| `docs/design/r04/` | 新版设计文档 DOCX/PDF、匿名化源稿与复现脚本 |
| `03_bitstreams/` | 自行构建说明；原含歌词位流不公开 |

公开数据附加检查：`python -B tools/reproduce.py test --case logo --iverilog-bin "D:/tools/iverilog/bin"`。

## 快速复现

安装 Python 3.10+、Icarus Verilog；综合需自行合法安装 TD 6.2.1 并配置许可证。不要把 TD、许可证或驱动传到本仓库。

```powershell
python -m pip install -r requirements.txt
python -B tools/reproduce.py verify
python -B tools/reproduce.py test --case font --iverilog-bin "D:/tools/iverilog/bin"
python -B tools/reproduce.py test --case controls --iverilog-bin "D:/tools/iverilog/bin"
python -B tools/reproduce.py test --case ui --iverilog-bin "D:/tools/iverilog/bin"
python -B tools/reproduce.py test --case captions --iverilog-bin "D:/tools/iverilog/bin"
```

综合与实现：

```powershell
python -B tools/reproduce.py synthesis --td-bin "D:/Anlogic/TD/bin"
python -B tools/reproduce.py implementation --td-bin "D:/Anlogic/TD/bin"
```

每次构建使用新输出目录；入口不向板卡、TF 或 Flash 写入。详细流程、生成自备素材和按键规则见 `REPRODUCE.md`。

## 使用边界和许可

原功能验收通过与仪器/厂商可靠性签核分开记录：当前报告仍保留 SDRAM 宏、内部延时/SiP、CDC/PVT 与完整地址实物 BIST 等审查范围，正 slack 不代替完整签核；不虚构功耗、音画误差或耐久测试数值。

本项目自研代码按 **MIT** 开源；第三方代码、字体遵守原许可，见 `THIRD_PARTY_NOTICES.md`。自编测试字幕按 CC0-1.0 提供。原音乐、广告、图片、歌词和赛事/厂商商标不在 MIT 授权范围内。

工程地址：https://github.com/Aurora-0110/fpga-multimedia-billboard
