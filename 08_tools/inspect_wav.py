"""Read-only PCM-WAV validation for the FPGA-supported format (not an audio converter)."""
from pathlib import Path
import argparse,json,struct,hashlib
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('file',nargs='+');a=ap.parse_args()
allok=True
for name in a.file:
 p=Path(name).resolve();s=p.read_bytes();pos=12;fmt=None;size=None;bounded=True
 if len(s)>=12 and s[:4]==b'RIFF' and s[8:12]==b'WAVE':
  end=int.from_bytes(s[4:8],'little')+8;bounded=end<=len(s)
  while pos+8<=min(end,len(s)):
   n=int.from_bytes(s[pos+4:pos+8],'little');nxt=pos+8+n+(n&1)
   if nxt>min(end,len(s)):bounded=False;break
   if s[pos:pos+4]==b'fmt ' and n>=16:fmt=struct.unpack_from('<HHIIHH',s,pos+8)
   if s[pos:pos+4]==b'data':size=n;break
   pos=nxt
 else:bounded=False
 ok=bool(bounded and fmt and fmt[0]==1 and fmt[1]in(1,2) and fmt[2]==48000 and fmt[5]in(16,24) and fmt[4]==fmt[1]*fmt[5]//8 and fmt[3]==48000*fmt[4] and size and size%fmt[4]==0)
 print(json.dumps(dict(path=str(p),fpga_format_supported=ok,format_fields=fmt,data_bytes=size,duration_seconds=round(size/fmt[3],3)if ok else None,sha256=hashlib.sha256(s).hexdigest(),writes_performed=False),ensure_ascii=False,indent=2));allok=allok and ok
raise SystemExit(0 if allok else 1)
