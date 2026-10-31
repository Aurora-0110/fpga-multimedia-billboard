"""Optional native-size 24-bit BI_RGB fixtures. Never accesses TF/removable media.
These files keep their original sizes; only FPGA will scale them to 1280x720.
"""
from pathlib import Path
import hashlib, json, struct
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
assert root.drive.upper() == 'D:' and root.name == 'v101_multires_dither_20261026'
dest = root / '06_test_media/v101_multires_probes'
assert not dest.exists(), 'Refuse to replace existing test media'
(dest / 'TF_ROOT').mkdir(parents=True)
records = []
font_path = Path('C:/Windows/Fonts/arial.ttf')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

for letter, w, h, top in [('A',320,240,False),('B',853,479,True),
                           ('C',720,1280,False),('D',1920,1080,True)]:
    pixels = bytearray(w*h*3)
    for y in range(h):
        for x in range(w):
            k = (y*w+x)*3
            pixels[k:k+3] = bytes((x*255//max(1,w-1), y*255//max(1,h-1),
                                  (x+y)*255//max(1,w+h-2)))
    im = Image.frombytes('RGB',(w,h),bytes(pixels)); dr = ImageDraw.Draw(im)
    border = max(2,min(w,h)//160)
    dr.rectangle((0,0,w-1,h-1),outline=(255,255,255),width=border)
    size = max(16,min(w,h)//7); margin = border+3
    for x,y,c in [(margin,margin,(255,0,0)),(w-margin-size,margin,(0,255,0)),
                  (margin,h-margin-size,(0,0,255)),(w-margin-size,h-margin-size,(255,255,0))]:
        dr.rectangle((x,y,x+size-1,y+size-1),fill=c)
    # Fine checkerboard: high-frequency quality/aliasing probe, not an error.
    cell = max(2,min(w,h)//80); x0=w*3//5; y0=h*3//5
    for y in range(y0,h-size-margin-5,cell):
        for x in range(x0,w-margin-5,cell):
            c=(255,255,255) if ((x-x0)//cell+(y-y0)//cell)%2 else (0,0,0)
            dr.rectangle((x,y,min(x+cell-1,w-margin-5),min(y+cell-1,h-size-margin-5)),fill=c)
    fs=max(12,min(w,h)//22)
    font=ImageFont.truetype(str(font_path),fs) if font_path.exists() else ImageFont.load_default()
    text=f'{letter}: {w}x{h}  '+('TOP-DOWN' if top else 'BOTTOM-UP')
    bbox=dr.textbbox((0,0),text,font=font)
    tx=max(margin,(w-(bbox[2]-bbox[0]))//2);ty=h//3
    dr.rectangle((tx-3,ty-2,tx+bbox[2]+3,ty+bbox[3]+3),fill=(15,15,15))
    dr.text((tx,ty),text,font=font,fill=(255,255,255))
    # Native-size custom BMP encoding, not Pillow's default 32-bit/bitfield path.
    raw=im.tobytes('raw','BGR');stride=(w*3+3)&~3;pad=b'\0'*(stride-w*3)
    signed_h=-h if top else h
    size_bytes=54+stride*h
    header=struct.pack('<2sIHHI',b'BM',size_bytes,0,0,54)
    header+=struct.pack('<IiiHHIIiiII',40,w,signed_h,1,24,0,stride*h,2835,2835,0,0)
    p=dest/'TF_ROOT'/f'{letter}.BMP'
    with p.open('wb') as f:
        f.write(header)
        for fy in range(h):
            y=fy if top else h-1-fy
            f.write(raw[y*w*3:(y+1)*w*3]);f.write(pad)
    with Image.open(p) as readback:
        readback.load()
        assert readback.mode=='RGB' and readback.size==(w,h)
        assert readback.tobytes()==im.tobytes(),'BMP round-trip orientation/padding mismatch'
    hdr=p.read_bytes()[:54]
    assert struct.unpack_from('<H',hdr,28)[0]==24 and struct.unpack_from('<I',hdr,30)[0]==0
    records.append({'file':f'TF_ROOT/{letter}.BMP','width':w,'height':h,'signed_height':signed_h,
        'top_down':top,'bits_per_pixel':24,'compression':0,'pixel_offset':54,
        'stride_bytes':stride,'padding_bytes':stride-w*3,'bytes':p.stat().st_size,'sha256':sha(p),
        'purpose':'Native-resolution input; FPGA performs interpolation; not official demonstration assets'})
    thumb=im.copy();thumb.thumbnail((400,240));thumb.save(dest/f'{letter}_source_preview.png')
(dest/'manifest.json').write_text(json.dumps({'version':'v101','kind':'optional_native_input_fixtures',
    'output_on_fpga':[1280,720],'encoding':'24-bit BI_RGB','round_trip':'Pillow exact native RGB checked',
    'files':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(dest/'README_可选换图测试.md').write_text('''# v101 多分辨率源图：可选测试，不是正式官方素材

本脚本只写电脑 D 盘；没有读写 TF 卡，也没有将原图预先缩放成720p。
A=320×240（正高度）；B=853×479（负高度，每行1字节补齐）；
C=720×1280竖图（正高度）；D=1920×1080（负高度）。全部24-bit BI_RGB非压缩。

红/绿/蓝/黄依次在左上/右上/左下/右下；白外框用于检查边界。
渐变测试色阶；细黑白棋盘故意考察强缩小时的锯齿/混叠，本版没有抗混叠预滤波。
本版拉伸铺满1280×720，竖图会拉宽，不是等比留黑边模式。OSD/Logo/频谱仍按720p输出坐标叠加。

## 安全操作顺序

1. 先用现有四张官方A/B/C/D.BMP与v101位流验证，没有异常再换本组。
2. 将TF根目录现有A/B/C/D.BMP全部复制备份到电脑，确认四个文件都在，不能只备份A/B/C。
3. 关闭板卡电源后取卡，经读卡器只更换A/B/C/D.BMP；不需要格式化、不改分区或接线。
4. 复制本目录TF_ROOT下四个文件到TF根目录，安全弹出，重新插卡后通电。
5. 仅临时SRAM下载v101；等待完整加载，D较大可能明显慢于旧640×480图，不承诺固定切换时间。
6. 检查四图方向、四角、铺满、渐变及OSD/Logo/频谱。可切手动模式逐张观察；暂不改Flash。
7. 测后断电取卡，恢复备份的原四图。回滚旧位流前同时恢复与旧版兼容的原尺寸素材。

四张文件均为人工测试图，不是官方Logo或正式广告内容的替代品。
预览是电脑生成的源图缩略图，不是FPGA缩放结果或实屏证据。
''',encoding='utf-8')
print(json.dumps({'media':str(dest),'files':records},ensure_ascii=False,indent=2))
