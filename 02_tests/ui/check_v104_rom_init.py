"""Read final routed PNL and verify all Chinese text/font BRAM initialization bits.
This guards against accidentally losing embedded ROM initializers in synthesis.
Not a routed functional/electrical simulation or bitstream read-back.
"""
from pathlib import Path
import argparse,re,json,hashlib,datetime
r=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser();ap.add_argument('--physical-attempt',type=int,default=1);args=ap.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pnl=r/f'05_td/v104_audio_visual_physical_attempt{args.physical_attempt}/physical/sdram_netlist.pnl'
uip=sorted((r/'04_evidence').glob('v104_ui_*/summary.json'))[-1];ui=json.loads(uip.read_text(encoding='utf8'));assert ui.get('passed') and ui.get('complete')
font_ref=uip.parent/'font.hex';font_rows=[int(x,16) for x in font_ref.read_text().split()];assert len(font_rows)==2048
specp=r/'03_docs/v104_ui_font_spec.json';spec=json.loads(specp.read_text(encoding='utf8'));text=[]
for n in range(64):
 msg=spec['messages'][n] if n<len(spec['messages']) else ''
 text.extend(spec['glyph_ids'][ch] for ch in msg.ljust(16))
found=[]
for name,block in re.findall(r'\tinstance ([^\n]+)\n\t\{(.*?)\n\t\}',pnl.read_text(encoding='utf8'),re.S):
 if not name.startswith('help_ui/') or 'INIT_00' not in block:continue
 init={int(i,16):int(raw,16) for i,raw in re.findall(r"\bINIT_([0-9A-F]+)=256'h([0-9A-Fa-f]+)",block)}
 assert set(init)==set(range(32)),name
 width=int(re.search(r'DATA_WIDTH_A:(\d+)',block).group(1));bits=sum(init[i]<<(i*256) for i in range(32))
 if width==9:
  words=[(bits>>(8*i))&255 for i in range(1024)];assert words==text,'text ROM init mismatch'
  found.append({'instance':name,'role':'text','words':1024,'physical_width':9,'matched':True})
 elif width==4:
  words=[(bits>>(4*i))&15 for i in range(2048)]
  offsets=[n for n in [0,4,8,12] if words==[(v>>n)&15 for v in font_rows]]
  assert len(offsets)==1,(name,offsets)
  found.append({'instance':name,'role':'font','words':2048,'physical_width':4,'bit_offset':offsets[0],'matched':True})
 else:raise AssertionError((name,width))
assert len(found)==5 and sum(x['role']=='text' for x in found)==1
assert {x['bit_offset'] for x in found if x['role']=='font'}=={0,4,8,12}
inputs=[pnl,font_ref,specp,Path(__file__),r/'01_project/rtl/visual/ui_help_overlay.v',*[r/'01_project/rtl/visual'/x for x in ['ui_zh_glyph_ids.vh','ui_zh_font_init.vh','ui_zh_text_init.vh']]]
out=r/'04_evidence'/('v104_rom_init_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
rec={'passed':True,'scope':'Final routed PNL INIT bits exactly match1024 text IDs and2048x16 independently font-rasterized rows; not hardware readback','source_sha256':{p.relative_to(r).as_posix():sha(p) for p in inputs},'ui_report':uip.relative_to(r).as_posix(),'ui_report_sha256':sha(uip),'mapped_roms':found}
(out/'summary.json').write_text(json.dumps(rec,indent=2),encoding='utf8');print(json.dumps({'passed':True,'mapped_roms':found,'path':str(out)},indent=2))
