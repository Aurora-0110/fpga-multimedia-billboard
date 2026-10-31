"""Sparse synthetic FAT32 images. Independent Python little-endian builder.
Only requested sectors exist; payload size fields do NOT imply a real full BMP image.
No hardware card is opened or written by this fixture generator.
"""
from pathlib import Path
import struct,json
R=Path(__file__).resolve().parents[1]
O=R/'02_tests/fixtures';O.mkdir(exist_ok=True)
def u16(b,o,v):struct.pack_into('<H',b,o,v)
def u32(b,o,v):struct.pack_into('<I',b,o,v&0xffffffff)
def entry(cluster=4,size=921654,name=b'A       BMP',attr=0x20):
 b=bytearray(32);b[:11]=name;b[11]=attr;u16(b,20,cluster>>16);u16(b,26,cluster&65535);u32(b,28,size);return b
def root_empty():
 b=bytearray(512)
 for i in range(16):b[32*i]=0xe5
 return b
def bmp():
 b=bytearray(512);b[:2]=b'BM';u32(b,2,921654);u32(b,10,54);u32(b,14,40);u32(b,18,640);u32(b,22,480);u16(b,26,1);u16(b,28,24);u32(b,34,921600);return b
configs=[('mbr_ok',{}),('superfloppy',{'super':1}),('sdsc',{}),('partition_slot2',{'slot':2,'type':0x0b}),
 ('root_second_sector',{'spc':2,'second':1,'total':200000}),('root_fat_chain',{'chain':1}),('active_fat1',{'chain':1,'active':1}),
 ('root_high_cluster',{'chain':1,'root':130,'file':300}),('spc128',{'spc':128,'total':12800000}),
 ('file_cluster_high16',{'file':65540}),('top_down',{'height':-480}),('image_size_zero',{'image0':1}),('filters',{'filters':1}),('dib124',{'dib':124,'offset':138,'size':921738}),
 ('no_file',{'missing':1,'err':5}),('root_eoc',{'chain':'eoc','err':5}),('root_bad',{'chain':'bad','err':6}),
 ('root_free',{'chain':'free','err':6}),('root_reserved',{'chain':'reserved','err':6}),('root_cycle',{'chain':'cycle','err':7}),
 ('boot_signature',{'bootsig':0,'err':2}),('mbr_type',{'type':0xee,'err':2}),('partition_overflow',{'part':0xffff0000,'err':2}),
 ('vbr_signature',{'vbrsig':0,'err':2}),('bps1024',{'bps':1024,'err':3}),('spc3',{'spc':3,'err':3}),
 ('nfats3',{'nfats':3,'err':3}),('fat16_fields',{'fat16':5,'err':3}),('fs_version',{'fsver':1,'err':3}),
 ('bad_active_fat',{'flags':0x82,'err':3}),('small_volume',{'total':50000,'err':4}),('short_fat',{'fatsz':10,'err':4}),
 ('partition_short',{'part_size':90000,'err':4}),('root_cluster_bad',{'root':1,'err':4}),
 ('file_cluster_bad',{'file':1,'err':8}),('file_short',{'size':53,'err':8}),
 ('bmp_signature',{'bmpsig':0,'err':9}),('bmp_bpp',{'bpp':16,'err':10}),('bmp_compressed',{'compression':1,'err':10}),
 ('bmp_dib',{'dib':12,'err':10}),('bmp_planes',{'planes':2,'err':10}),
 ('bmp_width',{'width':320,'err':11}),('bmp_height',{'height':240,'err':11}),
 ('bmp_offset',{'offset':40,'err':12}),('bmp_truncated',{'size':900000,'err':12}),
 ('bmp_size_mismatch',{'bfsize':921655,'err':12}),('bmp_offset_overflow',{'offset':0xfffffff0,'err':12}),
 ('bmp_dib_overflow',{'dib':0xfffffff0,'err':12}),('bmp_image_size',{'imgsize':1,'err':12}),
 ('root_zero_before_match',{'zero_first':1,'err':5}),
 ('crc_boot',{'crc_read':1,'err':1}),('crc_vbr',{'crc_read':2,'err':1}),
 ('crc_root',{'crc_read':3,'err':1}),('crc_bmp',{'crc_read':4,'err':1}),
 ('timeout_init',{'stall':1,'err':13}),('timeout_accept',{'stall':2,'err':13}),('timeout_read',{'stall':3,'err':13}),
 ('sd_init_error',{'sd_init_error':1,'err':1})]
cases=[]
for name,c in configs:
 part=0 if c.get('super') else c.get('part',2048);spc=c.get('spc',1);nf=c.get('nfats',2);fs=c.get('fatsz',800);total=c.get('total',100000);rcl=c.get('root',2);fcl=c.get('file',4);flags=c.get('flags',0x81 if c.get('active') else 0)
 data=part+32+nf*fs;rlba=data+(rcl-2)*spc;flba=data+(fcl-2)*spc;fatbase=part+32+(fs if c.get('active') else 0);fatlba=fatbase+(rcl>>7)
 v=bytearray(512);v[:3]=b'\xeb\x58\x90';u16(v,11,c.get('bps',512));v[13]=spc;u16(v,14,32);v[16]=nf;u32(v,32,total);u16(v,22,c.get('fat16',0));u32(v,36,fs);u16(v,40,flags);u16(v,42,c.get('fsver',0));u32(v,44,rcl);v[510:512]=b'\x55\xaa' if c.get('vbrsig',1) else b'\0\0'
 disk={};seq=[]
 if part:
  m=bytearray(512);base=446+c.get('slot',0)*16;m[base+4]=c.get('type',0x0c);u32(m,base+8,part);u32(m,base+12,c.get('part_size',total));m[510:]=b'\x55\xaa' if c.get('bootsig',1) else b'\0\0';disk[0]=m
 disk[part]=v
 root=root_empty() if (c.get('chain') or c.get('second')) else bytearray(512)
 if not c.get('chain') and not c.get('second') and not c.get('missing'):
  k=0
  if c.get('filters'):
   root[0:32]=entry(fcl,attr=0x0f);root[32:64]=entry(fcl,attr=0x08);root[64:96]=entry(fcl,attr=0x10);root[96:128]=entry(fcl);root[96]=0xe5;k=128
  if c.get('zero_first'):k=32
  root[k:k+32]=entry(fcl,c.get('size',921654))
 disk[rlba]=root
 if c.get('second'):
  root2=bytearray(512);root2[:32]=entry(fcl,c.get('size',921654));disk[rlba+1]=root2
 chain=c.get('chain');fat=bytearray(512)
 nxt={'eoc':0x0fffffff,'bad':0x0ffffff7,'free':0,'reserved':0x0ffffff0,'cycle':rcl}.get(chain,3)
 if chain:
  u32(fat,(rcl&127)*4,nxt);disk[fatlba]=fat
  if chain==1:
   nextroot=bytearray(512);nextroot[:32]=entry(fcl,c.get('size',921654));disk[data+(nxt-2)*spc]=nextroot
 b=bmp()
 if not c.get('bmpsig',1):b[0]=0
 for key,off,default in [('width',18,640),('height',22,480),('dib',14,40),('offset',10,54),('bfsize',2,c.get('size',921654)),('compression',30,0),('imgsize',34,0 if c.get('image0') else 921600)]:u32(b,off,c.get(key,default))
 u16(b,26,c.get('planes',1));u16(b,28,c.get('bpp',24));disk[flba]=b
 # Expected request trace, independently derived from the scenario boundary being exercised.
 err=c.get('err',0);mount=found=ok=0
 if not c.get('stall') and not c.get('sd_init_error'):
  seq=[0]
  if name not in ['boot_signature','mbr_type','partition_overflow','crc_boot']:
   if part:seq.append(part)
   if err not in [2,3,4] and name!='crc_vbr':
    mount=1;seq.append(rlba)
    if name!='crc_root':
     if c.get('second'):seq.append(rlba+1)
     if chain:
      if chain=='cycle':seq += [fatlba,rlba]*3
      else:
       seq.append(fatlba)
       if chain==1:seq.append(data+spc)
     if err not in [5,6,7,8]:found=1;seq.append(flba)
     if err==0:ok=1
 elif c.get('stall') in [2,3]:seq=[0]
 if name=='crc_bmp':found=1
 # Preserve first occurrence of each sparse sector, using a separate repeated-request trace.
 lbas=list(dict.fromkeys(seq))
 # Stall/error-in-init cases still have a legal image for model setup.
 if not lbas:lbas=[0]
 # Always put actual expected sector bytes in fixture order; no implicit image generation in Verilog.
 if any(l not in disk for l in lbas):raise AssertionError((name,lbas,list(disk)))
 d=O/name;d.mkdir(exist_ok=True)
 (d/'lbas.hex').write_text(''.join(f'{l&0xffffffff:08x}\n' for l in lbas))
 (d/'data.hex').write_text(''.join(f'{byte:02x}\n' for l in lbas for byte in disk[l]))
 (d/'requests.hex').write_text(''.join(f'{l&0xffffffff:08x}\n' for l in seq) or '00000000\n')
 cases.append(dict(name=name,blocks=len(lbas),requests=len(seq),error=err,mounted=mount,found=found,bmp_ok=ok,top_down=int(c.get('height',480)<0),sdsc=int(name=='sdsc'),crc_read=c.get('crc_read',0),stall=c.get('stall',0),sd_init_error=c.get('sd_init_error',0),file_cluster=fcl,offset=c.get('offset',54),size=c.get('size',921654)))
(O/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
print('Built',len(cases),'sparse fixtures (no physical card access).')
