from pathlib import Path
import hashlib,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'02_tests/dynamic_bmp'))
from run_dynamic_tests import fixture as original_fixture, color, interpolate
BAYER=((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5))
def indexed(pixel,x,y,enabled=True):
 r,g,b=(pixel>>16)&255,(pixel>>8)&255,pixel&255
 if not enabled:return (r&224)|((g>>3)&28)|(b>>6)
 th=BAYER[y%4][x%4]*16+8
 return ((r*7+th)//255)<<5|((g*7+th)//255)<<2|((b*3+th)//255)
def fixture(directory,case):
 result=original_fixture(directory,case)
 if case['stage']:
  scaled=[int(v,16) for v in (directory/'scaled.hex').read_text().split()]
  expected=[0]*len(scaled)
  for i,p in enumerate(scaled):
   row,x=divmod(i,32);y=row if case.get('top',False) else 17-row
   expected[y*32+x]=indexed(p,x,y)
  (directory/'indexed.hex').write_text(''.join(f'{p:02x}\n' for p in expected))
 result['fixture_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}
 return result
