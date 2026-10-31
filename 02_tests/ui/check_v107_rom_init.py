"""Check final routed INIT bits against independent UI/subtitle font references.
Not a routed functional simulation, readback, or electrical acceptance.
"""
from pathlib import Path
import re,json,hashlib,datetime,argparse
r=Path(__file__).resolve().parents[2];ap=argparse.ArgumentParser();ap.add_argument('--physical-attempt',type=int,default=1);args=ap.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pnl=r/f'05_td/v107_audio_visual_physical_attempt{args.physical_attempt}/physical/sdram_netlist.pnl';raw=pnl.read_text(encoding='utf8')
ui=sorted((r/'04_evidence').glob('v107_ui_*/summary.json'))[-1];media=sorted((r/'04_evidence').glob('v107_media_*/summary.json'))[-1]
for f in [ui,media]:d=json.loads(f.read_text(encoding='utf8'));assert d.get('passed') and d.get('complete'),str(f)
specp=r/'03_docs/v107_ui_font_spec.json';spec=json.loads(specp.read_text(encoding='utf8'));ui_text=[]
for n in range(64):ui_text.extend(spec['glyph_ids'][ch] for ch in (spec['messages'][n] if n<len(spec['messages']) else '').ljust(16))
ref={
 'help_ui':dict(font=[int(x,16) for x in (ui.parent/'font.hex').read_text().split()],text=ui_text),
 'captions':dict(font=[int(x,16) for x in (media.parent/'font.hex').read_text().split()],text=[int(x,16) for x in (media.parent/'text.hex').read_text().split()])}
found=[]
for name,block in re.findall(r'\tinstance ([^\n]+)\n\t\{(.*?)\n\t\}',raw,re.S):
 group=name.split('/')[0]
 if group not in ref or 'INIT_00' not in block:continue
 init={int(i,16):int(v,16) for i,v in re.findall(r"\bINIT_([0-9A-F]+)=256'h([0-9A-Fa-f]+)",block)};assert set(init)==set(range(32)),name
 width=int(re.search(r'DATA_WIDTH_A:(\d+)',block).group(1));bits=sum(init[i]<<(256*i) for i in range(32))
 if width==9:
  words=[(bits>>(8*i))&255 for i in range(1024)];expect=ref[group]['text'];assert words[:len(expect)]==expect,(name,'text mismatch')
  found.append(dict(group=group,instance=name,role='text',active_words=len(expect),physical_width=width,matched=True))
 elif width==4:
  words=[(bits>>(4*i))&15 for i in range(2048)];offsets=[n for n in [0,4,8,12] if words==[(v>>n)&15 for v in ref[group]['font']]];assert len(offsets)==1,(name,offsets)
  found.append(dict(group=group,instance=name,role='font',words=2048,physical_width=width,bit_offset=offsets[0],matched=True))
 else:raise AssertionError((name,width))
for group in ref:
 subset=[x for x in found if x['group']==group];assert len(subset)==5 and sum(x['role']=='text' for x in subset)==1
 assert {x['bit_offset'] for x in subset if x['role']=='font'}=={0,4,8,12}
inputs=[pnl,ui,media,ui.parent/'font.hex',media.parent/'font.hex',media.parent/'text.hex',specp,r/'03_docs/v107_subtitle_spec.json',Path(__file__),*[r/'01_project/rtl/visual'/f for f in ['media_ui_overlay.v','subtitle_overlay.v','pcm_subtitle_timeline.v']],*sorted((r/'01_project/rtl/visual').glob('media_ui_*.vh')),*sorted((r/'01_project/rtl/visual').glob('subtitle_*.vh'))]
out=r/'04_evidence'/('v107_rom_init_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
rec=dict(passed=True,scope='Ten final routed BRAM INIT blocks match new UI and caption text/font references, no hardware readback or physical-function claim',source_sha256={p.relative_to(r).as_posix():sha(p) for p in inputs},mapped_roms=found)
(out/'summary.json').write_text(json.dumps(rec,indent=2),encoding='utf8');print(json.dumps(dict(passed=True,mapped_roms=found,path=str(out)),indent=2))
