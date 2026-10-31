"""Structural evidence only. An unchanged TD SiP mapping is NOT vendor/PVT signoff."""
from pathlib import Path
import re,json,argparse

def parse(text):
 instances={}
 for m in re.finditer(r'(?ms)^\tinstance ([^\r\n]+)\s*\{.*?^\t\}',text):
  model=re.search(r'\bmodel ([^;]+);',m[0]);attrs=dict(re.findall(r'^\s+(\w+):([^\r\n]+)',m[0],re.M))
  loc=re.search(r'\blocation ([^;]+);',m[0]);instances[m[1]]=dict(model=model[1] if model else None,attrs=attrs,location=loc[1] if loc else None)
 pins={}
 for m in re.finditer(r'(?ms)^\tnet ([^\r\n]+)\s*\{.*?^\t\}',text):
  pin_section=m[0].split('\n\t\troute')[0]
  for inst,pin in re.findall(r'^[ \t]+([^,\r\n;{}]+),[ \t]+([^;\r\n]+);',pin_section,re.M):
   pins.setdefault((inst.strip(),pin.strip()),[]).append(m[1])
 return instances,pins

def inspect(current,baseline):
 inst,pins=parse(current);ref,_=parse(baseline);fail=[]
 macros=[(n,v) for n,v in inst.items() if v['model']=='sdram_2m_32']
 if len(macros)!=1 or macros[0][0]!='u_ram':fail.append('expected exactly one native u_ram sdram_2m_32')
 def pads(items):
  out={}
  for name,v in items.items():
   sip=v['attrs'].get('SIP_INFO')
   if not sip:continue
   sig,site=sip.split('/')
   if sig in out:fail.append('duplicate SiP signal '+sig)
   out[sig]=dict(instance=name,site=site,location=v['location'],mode=v['attrs'].get('MODE'),iotype=v['attrs'].get('IOTYPE'),adc=v['attrs'].get('LOCATION'))
  return out
 pads_now,pads_ref=pads(inst),pads(ref)
 expected={*(f'dq[{i}]' for i in range(32)),*(f'addr[{i}]' for i in range(11)),*(f'ba[{i}]' for i in range(2)),*(f'dm{i}' for i in range(4)),'clk','cke','cs_n','ras_n','cas_n','we_n'}
 if set(pads_now)!=expected:fail.append('missing/extra native SiP pads: '+str(sorted(set(pads_now)^expected)))
 if len({x['site'] for x in pads_now.values()})!=len(pads_now):fail.append('duplicate internal SiP site')
 for sig,v in pads_now.items():
  old=pads_ref.get(sig)
  if not old or any(v[k]!=old[k] for k in ('site','location','mode','iotype','adc')):fail.append('mapping changed vs vendor-derived v043 reference: '+sig)
  expected_mode='BI' if sig.startswith('dq[') else 'OUT'
  if v['mode']!=expected_mode:fail.append('wrong pad direction '+sig)
  for pin in (('di','do[0]','ts') if sig.startswith('dq[') else ('do[0]',)):
   if len(pins.get((v['instance'],pin),[]))!=1:fail.append('missing/multiple net '+sig+'.'+pin)
 for i in range(32):
  v=pads_now.get(f'dq[{i}]')
  if not v:continue
  for pin,net in [('di',f'u_ctrl/dq_in[{i}]'),('do[0]',f'u_ctrl/dq_out[{i}]'),('ts','dq_oe')]:
   if pins.get((v['instance'],pin))!=[net]:fail.append('DQ lane/enable mismatch '+str(i)+'.'+pin)
 clock=pads_now.get('clk');clock_nets=pins.get((clock['instance'],'do[0]'),[]) if clock else []
 global_nets=pins.get(('u_pll/u_gclk_sd','clko'),[])
 if not clock_nets or clock_nets!=global_nets:fail.append('SDRAM clock not driven by controller global clock')
 return dict(structural_checkpoint_pass=not fail,failures=fail,macro_count=len(macros),macro_locations=[v['location'] for _,v in macros],sip_pad_count=len(pads_now),dq_lanes_checked=32,pads=pads_now,clock_net=clock_nets,scope='55 TD-expanded SiP pads and 32 DQ lane nets checked against v043 mapping; NOT proof of actual SiP voltage, speed grade, absolute legal hard-macro site or vendor timing annotation correctness',formal_macro_signoff=False)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--pnl',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 r=inspect(a.pnl.read_text(),a.baseline.read_text());a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('STRUCTURAL CHECK',r['structural_checkpoint_pass'],r['failures']);raise SystemExit(0 if r['structural_checkpoint_pass'] else 2)
