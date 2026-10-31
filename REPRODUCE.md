# 复现与自备素材

## 1. 环境
- VF-E20NG88 / EG4S20NG88，24 MHz，按原理图接 JTAG、HDMI、TF SPI；不要使用 BG256 引脚。
- Python 3.10+ 和 `requirements.txt`；测试使用 Icarus Verilog 的 iverilog/vvp。
- TD 6.2.1 合法安装、有效许可和下载器驱动由使用者自行配置。厂商专有原语/仿真库不分发，从合法工具安装中获取。
- 所有路径通过 `--iverilog-bin` / `--td-bin` 或 FPGA_IVERILOG_BIN / FPGA_TD_BIN 指定。

## 2. 校验和仿真
先运行根 README 中的 verify 和四组 test。公共入口使用公开测试文本及字体独立像素真值，不依赖原 WAV、原歌词或旧 C 盘路径。

`02_tests` 还保留历史 TB 和夹具生成脚本；其缺失的媒体夹具应自行生成，不能把历史开发脚本全部无差别执行。`.vvp`、波形和大型帧文件不提交。

## 3. 媒体
只在新的普通文件夹生成，不自动写卡：

```powershell
python -B tools/generate_demo_media.py --out "D:/fpga-demo-media" --seconds 30
```

生成 A.BMP、B.BMP、C.BMP、D.BMP（640×480、24-bit BI_RGB）和 MUSIC.WAV、ADVOICE.WAV、EXTRA000.WAV（48 kHz、24-bit、双声道 PCM 合成测试音）。确认文件后自行复制到 FAT32 TF 卡根目录，断电插拔卡与接线。

choice 1 查 MUSIC.WAV，choice 2 查 ADVOICE.WAV，choice 3 读取根目录中首个不同于前两者的普通 WAV。第三音源不是无限播放列表；避免同时放入多个无关 WAV。choice 0 为测试音。无需 SHOW.BIN，不支持直接播放 MP3/FLAC。

自编字幕默认 53+16 条，约 28 秒内结束，只是计数/字库测试，不代表合成音的语音内容。要给自己的授权音频配字幕，编辑 `06_test_media/public_captions/captions.json`，校准起止毫秒后运行：

```powershell
python -B tools/generate_public_captions.py
```

每条不超过 24 字、每轨不超过 64 条，总字符不超过 1024、共享字形不超过 320；超界应重新设计和测试。重新生成 ROM 后应重新编译并复测。

公开 Logo 用自编 FPGA 图案；如有合法官方图案/自有 Logo，可本地生成并重新测试：

```powershell
python -B tools/generate_public_logo.py --image "D:/my-authorized-logo.png"
```

公开 ROM 是 112×56、2-bit palette、128×64 补齐，保留同样接口。不要把原 TF 素材或新生成的私有位流提交。

## 4. 按键
- 浏览状态：K0 短按换图，K1 短按自动/手动；实际换图受加载和状态机控制。
- K0 长按进入/退出音频控制；在音频控制中 K1 短按切音源、K0 短按暂停/继续。
- K1 长按独立显隐 UI，播放或暂停时都适用。
- 双键短按轮换基础 OSD/AV 图层组显隐；双键长按依次进入亮度、对比度、音量及返回浏览，按 UI 提示用 K0 减、K1 加。
- 频谱与字幕同属一个 AV 显隐组，不声称二者各自独立开关。

## 5. TD 构建与上板
运行 synthesis / implementation 入口，查看新 runs 目录中的 summary、原始报告和告警。不只看返回码；原器件/内部延时模型与约束审查范围仍保留。

先手动 Program SRAM 验证显示、声音、按键及错误灯。通过后再使用对应位流独立完成 Flash Program/Verify 与断电冷启动。脚本不自动烧板、不写 TF、不改网络。

**原 V132 实物验收已由用户确认；公开版换了嵌入素材数据，因此不提供可冒充原验收的 bit/hash。** `05_td` 明确是原已验收配置报告，不是公开示例新做的布局布线。
