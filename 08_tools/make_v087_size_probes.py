"""Create optional BMP input fixtures; never accesses a removable drive.

These are source images for demonstrating the FPGA's scaler, not software
pre-scaled 720p output. Keep the normal official playlist unchanged.
"""
from pathlib import Path
import hashlib, json, struct

root = Path(__file__).resolve().parents[1]
assert root.name == 'v087_scaled_frame_pipeline_20261025'
dest = root / '06_test_media/v087_variable_size_probes/TF_ROOT'
assert not dest.exists(), 'Do not overwrite existing media'
dest.mkdir(parents=True)
rows = []
for index, (width, height, top) in enumerate(((320, 240, False), (853, 479, True),
                                           (1280, 720, False), (1280, 1024, False))):
    stride = (width * 3 + 3) & ~3
    size = 54 + stride * height
    header = struct.pack('<2sIHHI', b'BM', size, 0, 0, 54)
    header += struct.pack('<IiiHHIIiiII', 40, width, -height if top else height,
                          1, 24, 0, stride * height, 2835, 2835, 0, 0)
    pixels = bytearray()
    for file_y in range(height):
        y = file_y if top else height - 1 - file_y
        row = bytearray(stride)
        for x in range(width):
            red = x * 255 // max(1, width - 1)
            green = y * 255 // max(1, height - 1)
            blue = 255 if ((x // max(1, width // 12)) ^ (y // max(1, height // 8))) & 1 else 0
            if x < 2 or y < 2 or x >= width - 2 or y >= height - 2:
                red, green, blue = 255, 255, 255
            row[x * 3:x * 3 + 3] = bytes((blue, green, red))
        pixels.extend(row)
    path = dest / (chr(65 + index) + '.BMP')
    path.write_bytes(header + pixels)
    rows.append({'file': path.name, 'width': width, 'height': height, 'top_down': top,
        'row_stride': stride, 'row_padding': stride - width * 3, 'bytes': path.stat().st_size,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
(dest.parent / 'manifest.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
(dest.parent / 'README_仅可选测试素材.md').write_text('''# v087 可变尺寸输入测试图（可选，不是正式四图素材）

先用 TF 卡原来的四张官方图片测试 v087，暂时不用换图。
本组是另一个独立测试集合：A=320×240 bottom-up；B=853×479 top-down（每行1字节补齐）；
C=1280×720；D=1280×1024。全部24bit BI_RGB，输出由 FPGA 缩放成1280×720。
白边、红绿渐变和蓝色网格是人为测试图案，不是原官方素材或安路Logo替代品。

原素材验收通过后，若要检验多种宽高，请先备份 TF 根目录现有 A/B/C/D.BMP 到电脑另一个文件夹，
断板卡电源，拔卡再用读卡器更换为本组 TF_ROOT 中的四个文件；安全弹出后再接回板卡。
不要把两组同名文件混在一起，不要在板卡通电时插拔 TF 模块/卡。
本脚本仅生成电脑工作目录里的图片，未改 TF 卡，也没有用软件代替 FPGA 的插值计算。
测试结束可恢复原四图；旧 v081 位流只支持640×480，恢复它时必须同时恢复旧尺寸素材。
''', encoding='utf-8')
print(dest)
