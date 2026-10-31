"""Independently decode ALL routed initialized UI/caption/metadata/Logo ROM bits."""
from pathlib import Path
import json,re,hashlib,datetime
r=Path(__file__).resolve().parents[2];assert '01_versions'not in r.parts
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pnl=r/'05_td/v129_audio_visual_physical_attempt1/physical/sdram_netlist.pnl';raw=pnl.read_text(encoding='utf-8')
def latest(pattern):
 dirs=sorted((r/'04_evidence').glob(pattern));assert dirs,pattern
 p=dirs[-1]/'summary.json';j=json.loads(p.read_text(encoding='utf-8'));assert j.get('passed')and j.get('complete'),p
 for case in j.get('tests',[]):
  for rel,h in case['source_sha256'].items():assert sha(r/rel)==h,rel
 return p,j
ui,uj=latest('v128_ui_[0-9]*');capt,cj=latest('v129_captions_[0-9]*')
uispec=r/'03_docs/v128_ui_font_spec.json';us=json.loads(uispec.read_text(encoding='utf-8'));cspec=r/'03_docs/v129_caption_spec.json';cs=json.loads(cspec.read_text(encoding='utf-8'))
uitext=[]
for i in range(64):uitext.extend(us['glyph_ids'][c]for c in (us['messages'][i]if i<len(us['messages'])else'').ljust(16))
uirows=[int(x,16)for x in (ui.parent/'font.hex').read_text().split()]
# Independent logical12x12 pixel oracle, NOT the generated packed spec array.
logical=[int(x,16)for x in (capt.parent/'font.hex').read_text().split()];cp=[]
for gid in range(320):
 payload=sum(logical[gid*16+y]<<(12*y)for y in range(12))
 cp.extend((payload>>(18*k))&0x3ffff for k in range(8))
assert cp==cs['font_packed_words']
text=[int(x,16)for x in (capt.parent/'text.hex').read_text().split()]
meta=[int(x,16)for x in (capt.parent/'metadata.hex').read_text().split()]
logo=r/'01_project/rtl/video/official_logo.v';mod=logo.read_text(encoding='utf-8').split('endmodule',1)[0]
logorows={int(y):int(v,16)for y,v in re.findall(r"6'd(\d+):\s*rowbits=224'h([0-9a-fA-F]+)",mod)};assert set(logorows)==set(range(56))
lp=[((logorows[y]>>(2*x))&3)if x<112 and y<56 else 0 for y in range(64)for x in range(128)]
lanes={}
for name,body in re.findall(r'\tnet ([^\n]+)\n\t\{(.*?)\n\t\}',raw,re.S):
 m=re.fullmatch(r'overlay/lp1\[([01])\]',name)
 if m:
  pins=re.findall(r'(overlay/logo/[^\s,;]+),\s*doa\[0\];',body);assert len(pins)==1;lanes[pins[0]]=int(m.group(1))
assert len(lanes)==2
records=[];covered=set()
for name,body in re.findall(r'\tinstance ([^\n]+)\n\t\{(.*?)\n\t\}',raw,re.S):
 group=name.split('/')[0];islogo=name.startswith('overlay/logo/')
 if 'INIT_00'not in body or(group not in ['help_ui','captions','captions_clock']and not islogo):continue
 init={int(i,16):int(v,16)for i,v in re.findall(r"\bINIT_([0-9A-F]+)=256'h([0-9A-Fa-f]+)",body)};assert set(init)==set(range(32)),name
 ip={int(i,16):int(v,16)for i,v in re.findall(r"\bINITP_([0-9A-F]+)=256'h([0-9A-Fa-f]+)",body)};assert set(ip)==set(range(4)),name
 bits=sum(v<<(256*i)for i,v in init.items());parity=sum(v<<(256*i)for i,v in ip.items());width=int(re.search(r'DATA_WIDTH_A:(\d+)',body).group(1))
 if width==18:
  words=[((bits>>(16*i))&255)|(((parity>>(2*i))&1)<<8)|(((bits>>(16*i+8))&255)<<9)|(((parity>>(2*i+1))&1)<<17)for i in range(512)]
 elif width==9:words=[((bits>>(8*i))&255)|(((parity>>i)&1)<<8)for i in range(1024)]
 elif width in [1,2,4]:words=[(bits>>(width*i))&((1<<width)-1)for i in range(8192//width)]
 else:raise AssertionError((name,width,'unsupported physical width'))
 rec=dict(group='logo'if islogo else group,instance=name,physical_width=width,matched=True,words=len(words),parity_preserved=width in [9,18])
 if islogo:
  assert width==1 and name in lanes
  assert words==[(v>>lanes[name])&1 for v in lp],name
  rec.update(role='logo',lane=lanes[name]);key=('logo',lanes[name]);assert key not in covered;covered.add(key)
 elif group=='captions_clock':
  assert width==18 and words==meta,(name,'metadata parity/payload mismatch')
  rec.update(role='metadata');key=('meta',0);assert key not in covered;covered.add(key)
 elif group=='help_ui':
  if width==9:
   assert words==uitext,name;key=('uitext',0);rec.update(role='text')
  else:
   assert width==4
   offsets=[offset for offset in [0,4,8,12]if words==[(v>>offset)&15 for v in uirows]];assert len(offsets)==1,(name,offsets)
   key=('uifont',offsets[0]);rec.update(role='font',bit_offset=offsets[0])
  assert key not in covered;covered.add(key)
 elif group=='captions':
  # Packed glyph shape: separate2048+512 words; audit actual native banks and parity.
  # Prove each bank/lane by content including the native9th parity bits.
  if width==9 and words==text:
   key=('captext',0);rec.update(role='text')
  else:
   assert width in [9,18],(name,width)
   candidates=[]
   for bank in range(0,len(cp),len(words)):
    for offset in range(0,18,width):
     if words==[(v>>offset)&((1<<width)-1)for v in cp[bank:bank+len(words)]]:candidates.append((bank,offset))
   assert len(candidates)==1,(name,candidates,'packed glyph mismatch')
   bank,offset=candidates[0];key=('capfont',bank,offset,width);rec.update(role='packed_font',word_start=bank,bit_offset=offset)
  assert key not in covered;covered.add(key)
 records.append(rec)
assert sum(x['group']=='help_ui'for x in records)==5
assert sum(x['group']=='captions_clock'for x in records)==1
assert sum(x['group']=='logo'for x in records)==2
assert sum(x['role']=='text'and x['group']=='captions'for x in records)==1
fnt=[x for x in records if x['role']=='packed_font'];assert len(fnt)==5
# Each logical18bit word is covered exactly once, no bank/lane missing.
for word in range(2560):
 mask=0
 for rec in fnt:
  if rec['word_start']<=word<rec['word_start']+rec['words']:
   m=((1<<rec['physical_width'])-1)<<rec['bit_offset'];assert not(mask&m);mask|=m
 assert mask==0x3ffff,word
assert len(records)==14
out=r/'04_evidence'/('v129_rom_init_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
inputs=[pnl,ui,capt,uispec,cspec,logo,Path(__file__),ui.parent/'font.hex',capt.parent/'font.hex',capt.parent/'text.hex',capt.parent/'metadata.hex',*sorted((r/'01_project/rtl/visual').glob('music_caption*.vh')),*sorted((r/'01_project/rtl/visual').glob('media_ui_*.vh'))]
rec=dict(passed=True,complete=True,physical_attempt=1,mapped_roms=records,packed_logical_font_words_checked=2560,all_native_parity_bits_preserved=True,source_sha256={p.relative_to(r).as_posix():sha(p)for p in inputs},scope='All14routed UI5+caption6+metadata1+Logo2 initialized memories decoded; independent user-text/font/pixel oracle. Not dynamic routed simulation or hardware.')
(out/'summary.json').write_text(json.dumps(rec,indent=2),encoding='utf-8');print(json.dumps(dict(passed=True,mapped_roms=records,path=str(out)),indent=2))
