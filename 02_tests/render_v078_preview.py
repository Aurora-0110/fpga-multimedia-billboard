from pathlib import Path
import os,subprocess,datetime,json,hashlib
from PIL import Image
r=Path(__file__).resolve().parents[1];rtl=r/'01_project/rtl';t=r/'02_tests'
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
out=r/'04_evidence'/('v078_preview_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
im=Image.open(r/'06_test_media/four_image_playlist/TF_ROOT/B.BMP').convert('RGB')
assert im.size==(640,480)
# Match actual RGB332 quantization/expansion, not original 24-bit BMP precision.
pixels=[]
for rr,g,bb in im.getdata():
 rr>>=5;g>>=5;bb>>=6;pixels.append(((rr<<5)|(rr<<2)|(rr>>1),(g<<5)|(g<<2)|(g>>1),bb*85))
q=Image.new('RGB',im.size);q.putdata(pixels);canvas=Image.new('RGB',(1280,720),(8,24,48));canvas.paste(q,(320,120))
from PIL import ImageDraw
ImageDraw.Draw(canvas).rectangle((0,0,1279,719),outline='white',width=4)
source=out/'input.hex';source.write_text(''.join('%02x%02x%02x\n'%c for c in canvas.getdata()))
exe=out/'preview.vvp';dest=out/'output.hex'
sources=[t/'tb_v078_preview.sv',rtl/'video/osd_layers.v',rtl/'video/official_logo.v']
c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(rtl),'-s','tb_v078_preview','-o',str(exe),*map(str,sources)],capture_output=True,text=True,env=env,check=True)
v=subprocess.run([str(b/'vvp.exe'),str(exe),'+SOURCE='+str(source),'+DEST='+str(dest)],capture_output=True,text=True,env=env,timeout=90)
(out/'run.log').write_text(c.stdout+c.stderr+v.stdout+v.stderr)
assert v.returncode==0 and 'PASS preview' in v.stdout,v.stdout+v.stderr
image=Image.frombytes('RGB',(1280,720),bytes.fromhex(dest.read_text()));image.save(out/'v078_osd_rtl_preview.png')
# Preserve rendered evidence and source hash, remove only rebuildable hex dumps in this fresh evidence directory.
source.unlink();dest.unlink()
(out/'summary.json').write_text(json.dumps({'passed':True,'scope':'osd_layers RTL single raster on RGB332 BMP B; not HDMI, SDRAM or hardware; timer starts at zero','source_sha256':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[rtl/'video/osd_font.vh']}},indent=2))
print(v.stdout);print(out)
