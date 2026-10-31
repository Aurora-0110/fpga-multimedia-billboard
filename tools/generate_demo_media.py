"""Generate deterministic synthetic test assets. Output is a NEW folder, never a TF device. Use --seconds 30 to cover the public caption timeline."""
from pathlib import Path
import argparse,math,struct,wave,json,hashlib
from PIL import Image,ImageDraw

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--seconds',type=int,default=3);a=p.parse_args();out=Path(a.out)
 if not 1<=a.seconds<=120:p.error('--seconds must be 1..120')
 if out.exists():p.error('Choose a new output directory; no overwrite.')
 out.mkdir(parents=True);rec=[]
 for n in range(4):
  im=Image.new('RGB',(640,480));d=ImageDraw.Draw(im)
  for y in range(6):
   for x in range(8):
    d.rectangle((x*80,y*80,x*80+79,y*80+79),fill=((x*32+n*64)%256,(y*42+n*32)%256,((x+y)*24+n*16)%256))
  d.rectangle((12,12,270,55),fill='white');d.text((22,25),'FPGA SAMPLE '+chr(65+n),fill='black')
  path=out/(chr(65+n)+'.BMP');im.save(path,'BMP');rec.append(path.name)
 for name,base in [('MUSIC.WAV',440),('ADVOICE.WAV',660),('EXTRA000.WAV',880)]:
  data=bytearray()
  for i in range(48000*a.seconds):
   amp=0.15*(0.5+0.5*math.sin(2*math.pi*i/48000));value=int(amp*(2**23-1)*math.sin(2*math.pi*base*i/48000))
   sample=value.to_bytes(3,'little',signed=True);data.extend(sample+sample)
  with wave.open(str(out/name),'wb')as w:w.setnchannels(2);w.setsampwidth(3);w.setframerate(48000);w.writeframes(data)
  rec.append(name)
 report=dict(scope='Deterministic geometry and synthetic tones only; no copyrighted music; not matching built-in lyric timelines.',files={x:hashlib.sha256((out/x).read_bytes()).hexdigest()for x in rec},image='640x480 RGB888 uncompressed BMP',audio='48kHz24bitstereo PCM WAV',no_device_write=True)
 (out/'MEDIA_MANIFEST.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(out)
if __name__=='__main__':main()
