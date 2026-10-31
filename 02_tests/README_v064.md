# v064 验证入口与证据索引

新证据只看上层 `04_evidence/`，本目录中继承的旧 JSON/log 对应旧版，不冒充 v064 新回归。

```powershell
# 可设置 IVERILOG_BIN 为含 iverilog.exe、vvp.exe 的目录
python .\run_v064_speed.py --group all
python .\run_v064_baseline.py --group all
```

每次生成新的时间戳输出目录，不覆盖历史；需要 Python 3 与 Icarus Verilog。默认工具路径是本机 D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin，队友应按本机设置 IVERILOG_BIN。

- speed quick：字节边沿、分频中途变化、SDHC/SDSC、CRC 首扇区/数据扇区错误、复位重试。
- speed timing：真实分频 124/124 与 124/25 各 80 burst，对照数据/地址；额外 MISO 40 ns 行为延迟。不是实卡测速，也不是板级时序验证。
- speed full：A/B/C 与 top-down 各 307200 像素完整 SPI 加载、地址和 CRC32；用加速分频 6/1。A/B/C 为模型对同一基础图片做明确异或变换，不是三次读取同名未改数据。
- baseline：轮播/按键控制、运行时文件名、各文件 80 burst，以及 A→B→C→A 四帧真实 SDRAM 控制器读写与视频评分。
- 最后一项通过 sector 服务模型绕过 SPI；不等于一次完整 SPI→SDRAM→HDMI 物理全链测试。
- PLL 行为模型不替代原生 PLL 库一致性或上板锁定验证。

运行整图/内存模型可能持续数分钟到数十分钟。以 summary.json 中 complete=true 且 passed=true 为完成，不根据已打印的中间 PASS 推断整个组通过。

## 本轮已记录的基线限制

`04_evidence/sim_v064_all_20261023_200904/summary.json` 的 `complete=true` 表示测试进程已结束，**并不表示所有用例通过**。本轮前 11 项 PASS，最后 `autoplay_memory_A_B_C_A` 为 1500 秒宿主超时，`passed=false`；日志显示前三张完成、第四张加载中，后续需补完，不把它改成 PASS。
