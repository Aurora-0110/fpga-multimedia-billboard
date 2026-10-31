# 当前板级工程

目标 VF-E20NG88 / EG4S20NG88，24 MHz。当前功能基线 V132，公开数据导出版 v135。

推荐入口为根目录 `tools/reproduce.py`。生产综合脚本 `build_audio_visual_synth.tcl`；顶层 `boards/idx_audio_visual_top.v`；约束 `boards/idx_video.adc`、`boards/idx_video.sdc`。

保留历史脚本和模块便于追溯，但不能把文件名 v119/v130 当作实际版本号。原作品实物、Flash 与冷启动已通过；公开字幕及 Logo 数据替换的重建结果需单独确认。
