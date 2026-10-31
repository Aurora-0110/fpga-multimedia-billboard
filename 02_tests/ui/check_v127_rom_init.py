"""Audit final routed initialized ROM bits against independent V127 oracles.
Checks metadata parity bits as two 9-bit lanes, not a misleading 16-bit truncation.
No hardware readback/acceptance is claimed.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,re
root=Path(__file__).resolve().parents[2];a=argparse.ArgumentParser();a.add_argument('--physical-attempt',type=int,default=1);args=a.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pnl=root/f'05_td/v127_audio_visual_physical_attempt{args.physical_attempt}/physical/sdram_netlist.pnl';raw=pnl.read_text(encoding='utf8')
def latest(pattern):
 dirs=sorted((root/'04_evidence').glob(pattern));assert dirs
 p=dirs[-1]/'summary.json';j=json.loads(p.read_text(encoding='utf8'));assert j.get('passed') and j.get('complete'),str(p)
 return p,j
ui,uj=latest('v127_ui_[0-9]*');cap,cj=latest('v127_captions_[0-9]*')
for j in [uj,cj]:
 for test in j['tests']:
  for rel,h in test['source_sha256'].items():assert sha(root/rel)==h,rel
specpath=root/'03_docs/v127_ui_font_spec.json';spec=json.loads(specpath.read_text(encoding='utf8'))
uitext=[]
for i in range(64):uitext.extend(spec['glyph_ids'][c]for c in (spec['messages'][i]if i<len(spec['messages'])else'').ljust(16))
ref={'help_ui':dict(font=[int(x,16)for x in (ui.parent/'font.hex').read_text().split()],text=uitext),
 'captions':dict(font=[int(x,16)for x in (cap.parent/'font.hex').read_text().split()],text=[int(x,16)for x in (cap.parent/'text.hex').read_text().split()])}
meta=[int(x,16)for x in (cap.parent/'metadata.hex').read_text().split()]+[0]*256
logosource=root/'01_project/rtl/video/official_logo.v';mod=logosource.read_text(encoding='utf8').split('endmodule',1)[0]
logorows={int(y):int(v,16)for y,v in re.findall(r"6'd(\d+):\s*rowbits=224'h([0-9a-fA-F]+)",mod)};assert set(logorows)==set(range(56))
logopixels=[((logorows[y]>>(2*x))&3)if x<112 and y<56 else 0 for y in range(64)for x in range(128)]
lanes={}
for name,body in re.findall(r'\tnet ([^\n]+)\n\t\{(.*?)\n\t\}',raw,re.S):
 m=re.fullmatch(r'overlay/lp1\[([01])\]',name)
 if m:
  pins=re.findall(r'(overlay/logo/[^\s,;]+),\s*doa\[0\];',body);assert len(pins)==1;lanes[pins[0]]=int(m.group(1))
assert len(lanes)==2 and set(lanes.values())=={0,1}
found=[]
for name,body in re.findall(r'\tinstance ([^\n]+)\n\t\{(.*?)\n\t\}',raw,re.S):
 group=name.split('/')[0];logo=name.startswith('overlay/logo/')
 if 'INIT_00'not in body or (group not in ref and group!='captions_clock' and not logo):continue
 init={int(i,16):int(v,16)for i,v in re.findall(r"\bINIT_([0-9A-F]+)=256'h([0-9A-Fa-f]+)",body)};assert set(init)==set(range(32)),name
 ip={int(i,16):int(v,16)for i,v in re.findall(r"\bINITP_([0-9A-F]+)=256'h([0-9A-Fa-f]+)",body)};assert set(ip)==set(range(4)),name
 bits=sum(v<<(256*i)for i,v in init.items());parity=sum(v<<(256*i)for i,v in ip.items());width=int(re.search(r'DATA_WIDTH_A:(\d+)',body).group(1))
 rec=dict(group='logo'if logo else group,instance=name,physical_width=width,matched=True)
 if logo:
  assert width==1 and name in lanes;lane=lanes[name]
  assert [(bits>>i)&1 for i in range(8192)]==[(v>>lane)&1 for v in logopixels],name
  rec.update(role='logo',words=8192,bit_offset=lane)
 elif group=='captions_clock':
  assert width==18,name
  # Physical payload stores two bytes; parity stores bit8 and bit17 of each18-bit word.
  words=[((bits>>(16*i))&255)|(((parity>>(2*i))&1)<<8)|(((bits>>(16*i+8))&255)<<9)|(((parity>>(2*i+1))&1)<<17)for i in range(512)]
  assert words==meta,(name,'metadata including9bit-lane parity mismatch')
  rec.update(role='metadata',words=512,logical_width=18,parity_bits_checked=1024)
 elif width==9:
  words=[((bits>>(8*i))&255)|(((parity>>i)&1)<<8)for i in range(1024)]
  assert words==ref[group]['text'],(name,'text INIT mismatch')
  rec.update(role='text',words=1024,parity_bits_checked=1024)
 elif width==4:
  words=[(bits>>(4*i))&15 for i in range(2048)]
  matches=[offset for offset in range(0,16,4)if words==[(v>>offset)&15 for v in ref[group]['font']]]
  assert len(matches)==1,(name,matches);rec.update(role='font',words=2048,bit_offset=matches[0])
 else:raise AssertionError((name,width))
 found.append(rec)
for group,nibbles in [('help_ui',{0,4,8,12}),('captions',{0,4,8})]:
 subset=[x for x in found if x['group']==group];assert len(subset)==len(nibbles)+1
 assert sum(x['role']=='text'for x in subset)==1
 assert {x['bit_offset']for x in subset if x['role']=='font'}==nibbles
assert sum(x['group']=='captions_clock'for x in found)==1 and len(found)==12
inputs=[pnl,ui,cap,specpath,root/'03_docs/v127_caption_spec.json',logosource,Path(__file__),ui.parent/'font.hex',cap.parent/'font.hex',cap.parent/'text.hex',cap.parent/'metadata.hex',*sorted((root/'01_project/rtl/visual').glob('music_caption*.vh')),*sorted((root/'01_project/rtl/visual').glob('media_ui_*.vh'))]
out=root/'04_evidence'/('v127_rom_init_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
record=dict(passed=True,physical_attempt=args.physical_attempt,mapped_roms=found,source_sha256={p.relative_to(root).as_posix():sha(p)for p in inputs},scope='All12 routed ROMs: UI5+caption4+metadata1+Logo2. Independent font/text/cue/Logo sources; metadata18-bit parity preserved. Not routed functional simulation or hardware.')
(out/'summary.json').write_text(json.dumps(record,indent=2),encoding='utf8');print(json.dumps(dict(passed=True,mapped_roms=found,path=str(out)),indent=2))
