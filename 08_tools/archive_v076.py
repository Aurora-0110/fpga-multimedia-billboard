from pathlib import Path
import json,subprocess,sys,hashlib
R=Path(__file__).resolve().parents[1]
ROOT=R.parents[1]
H=Path(r'D:\FPGA_Billboard\99_archive\version_history')
ID='v076_picture_audio_sync_20261024'
v=json.loads((H/'versions.json').read_text(encoding='utf-8'))
assert max(int(x['id'][1:4]) for x in v)==75,'Recheck next version; do not reuse an ID'
assert not (H/'01_versions'/ID).exists(),'Frozen version cannot be overwritten'
s=json.loads((R/'VERSION_STATUS.json').read_text(encoding='utf-8'))
i=json.loads((R/'04_evidence/v076_release_integrity.json').read_text(encoding='utf-8'))
assert i['passed'] and s['td']['numerical_checkpoint_pass']
assert not s['new_hardware_acceptance'] and not s['new_flash_write_performed']
for rel,h in i['current_source_sha256'].items():
 assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==h,rel
assert hashlib.sha256((R/s['bitstream']).read_bytes()).hexdigest()==s['bit_sha256']
status='可见性85/顶层197/包门控76采样、整帧独立音频解码及ODDR三相位通过；TD SWNS+0.476/HWNS+0.014ns生成位流；未下载未试听，Flash不改，正式签核开放'
note='EG4S20NG88/24MHz；从v072/v074功能基线实现首个真实像素触发音频、切图/隐藏/欠流零PCM；HDMI/I2S持续运行。v075状态栏独立保留未合并。保留独立解码器14→15周期检查器修正及初始失败记录；编译源码、测试源码和位流哈希匹配。TF/SDRAM/PLL/约束未改，1280x720输出，RGB332帧缓存。宏/SiP/PVT及33条内部输入延时等开放，非正式验收；仅计划SRAM临时下载。用户独立完成，不默认生成队友ZIP。旧版全保留。'
subprocess.run([sys.executable,'-B',str(H/'90_tools/archive_version.py'),'save','--id',ID,'--title','图片可见状态与HDMI测试音启停联动（待实物）','--status',status,'--source',str(R),'--note',note],check=True)
p=H/'00_版本索引.md';t=p.read_text(encoding='utf-8');marker='## 当前推荐交接版本';assert marker in t
p.write_text(t.split(marker)[0]+marker+'''\n\n用户独立完成，不再默认制作队友交接包；以完整版本快照和实测记录为准。

- 当前待测：v076_picture_audio_sync_20261024，图片/测试音启停联动，仿真及TD通过；未临时下载、未试听。本轮不改Flash。
- 独立保留：v075_osd_status_20261024，底部状态栏增强，尚未实物验收，未混入v076。
- 已固化功能基线：v074_flash_coldboot_acceptance_20261024（v072同位流），用户一次冷启动反馈通过；不以其代替v076联动验收。
- 保留全部旧版本与失败证据；宏/SiP/PVT等正式审查未关闭。
''',encoding='utf-8')
r=subprocess.run([sys.executable,'-B',str(H/'90_tools/archive_version.py'),'verify'],capture_output=True,text=True,encoding='utf-8',check=True)
(ROOT/'outputs').mkdir(exist_ok=True)
(ROOT/'outputs/v076_archive_verify.log').write_text(r.stdout+r.stderr,encoding='utf-8')
print(r.stdout);print('ARCHIVE:',H/'01_versions'/ID)
