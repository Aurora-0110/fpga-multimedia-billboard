"""Read-only WAV/card-content audit; never formats, repairs or writes a TF card.
All new results go under the D-drive project evidence directory.
A successful local-file audit is NOT a card or FPGA playback acceptance.
"""
from pathlib import Path
from datetime import datetime
import argparse, hashlib, json, struct, subprocess, sys

DEFAULT_FFMPEG=Path(r'D:\FPGA_Billboard\90_tools\media\python_packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe')

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def inspect_bytes(s):
 if len(s)<12 or s[:4]!=b'RIFF' or s[8:12]!=b'WAVE': raise ValueError('Not RIFF/WAVE')
 end=struct.unpack_from('<I',s,4)[0]+8
 if end!=len(s): raise ValueError('RIFF length differs from actual file size')
 pos=12;fmt=None;pcm=None;chunks=[]
 while pos<end:
  if pos+8>end: raise ValueError('Truncated chunk header')
  tag=s[pos:pos+4];n=struct.unpack_from('<I',s,pos+4)[0];start=pos+8;following=start+n+(n&1)
  if following>end: raise ValueError('Chunk exceeds RIFF/file bounds')
  chunks.append({'id':tag.decode('ascii','backslashreplace'),'bytes':n,'offset':start})
  if tag==b'fmt ':
   if fmt is not None or n<16: raise ValueError('Duplicate/short fmt chunk')
   fmt=struct.unpack_from('<HHIIHH',s,start)
  if tag==b'data':
   if pcm is not None or fmt is None: raise ValueError('Duplicate data or data before fmt')
   pcm=s[start:start+n]
  pos=following
 if fmt is None or pcm is None or not pcm: raise ValueError('Missing/empty fmt or data')
 tag,ch,hz,rate,align,bits=fmt
 if tag!=1 or ch not in (1,2) or hz!=48000 or bits not in (16,24): raise ValueError('Outside FPGA WAV format contract')
 if align!=ch*bits//8 or rate!=hz*align or len(pcm)%align: raise ValueError('Bad byte rate, block alignment or incomplete PCM frame')
 return {'format_tag':tag,'sample_rate_hz':hz,'bits_per_sample':bits,'channels':ch,'block_align':align,'byte_rate':rate,
 'file_bytes':len(s),'data_bytes':len(pcm),'sample_frames':len(pcm)//align,'duration_seconds':len(pcm)/rate,
 'data_md5':hashlib.md5(pcm).hexdigest(),'data_sha256':hashlib.sha256(pcm).hexdigest(),'sha256':hashlib.sha256(s).hexdigest(),
 'chunks':chunks,'checks_passed':True}

def canonical(payload=bytes(60)):
 fmt=struct.pack('<HHIIHH',1,2,48000,288000,6,24)
 body=b'WAVEfmt '+struct.pack('<I',16)+fmt+b'data'+struct.pack('<I',len(payload))+payload
 return b'RIFF'+struct.pack('<I',len(body))+body

def selftest():
 good=canonical();cases=[('valid',good,True),('not_wave',b'bad',False),('truncated_payload',good[:-1],False)]
 def patch(offset,value):
  s=bytearray(good);s[offset:offset+len(value)]=value;return bytes(s)
 cases += [('riff_oversize',patch(4,struct.pack('<I',len(good))),False),('compressed',patch(20,struct.pack('<H',3)),False),
 ('44100',patch(24,struct.pack('<I',44100)),False),('wrong_byterate',patch(28,struct.pack('<I',1)),False),
 ('wrong_alignment',patch(32,struct.pack('<H',4)),False),('invalid_bits',patch(34,struct.pack('<H',32)),False),
 ('oversized_data',patch(40,struct.pack('<I',120)),False),('incomplete_pcm_frame',canonical(bytes(58)),False),('empty_data',canonical(b''),False)]
 results=[]
 for name,data,expected in cases:
  try: inspect_bytes(data);accepted=True;error=None
  except ValueError as e: accepted=False;error=str(e)
  results.append({'name':name,'expected_accept':expected,'accepted':accepted,'pass':accepted==expected,'error':error})
 assert all(c['pass'] for c in results)
 return results

def full_decode(ffmpeg,path,log):
 cmd=[str(ffmpeg),'-hide_banner','-nostdin','-v','error','-xerror','-err_detect','explode','-i',str(path),'-map','0:a:0','-f','null','-']
 r=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=120)
 text=r.stderr.decode('utf-8','replace');log.write_text(text,encoding='utf-8')
 return {'command':cmd,'returncode':r.returncode,'stderr_empty':not text.strip(),'stderr_log':str(log),'pass':r.returncode==0}

def flac_streaminfo(path):
 with path.open('rb') as f:
  if f.read(4)!=b'fLaC': raise ValueError('No native FLAC signature')
  while True:
   header=f.read(4)
   if len(header)!=4:raise ValueError('No STREAMINFO')
   payload=f.read(int.from_bytes(header[1:4],'big'))
   if header[0]&0x7f==0:
    if len(payload)!=34:raise ValueError('Invalid STREAMINFO')
    packed=int.from_bytes(payload[10:18],'big')
    return {'sample_frames':packed&((1<<36)-1),'sample_rate_hz':packed>>44,'channels':((packed>>41)&7)+1,
      'bits_per_sample':((packed>>36)&31)+1,'stored_pcm_md5':payload[18:34].hex()}
   if header[0]&0x80:raise ValueError('No STREAMINFO')

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--project-dir',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--ffmpeg',type=Path,default=DEFAULT_FFMPEG)
 ap.add_argument('--card-root',type=Path);ap.add_argument('--out',type=Path)
 a=ap.parse_args();base=a.project_dir.resolve();out=(a.out or base/'04_evidence/v113_audio_file_audit').resolve()
 if out.drive.upper()!='D:':raise ValueError('Write evidence only on D:')
 if a.card_root and out.is_relative_to(a.card_root.resolve()):raise ValueError('Do not place results on TF card')
 out.mkdir(parents=True,exist_ok=True)
 report={'version':'v113_audio_file_audit_20261027','recorded_at':datetime.now().astimezone().isoformat(),
 'hardware_baseline':'v112_audio_pingpong_20261027','readonly_audio_audit':True,'card_contents_modified':False,
 'fpga_modified':False,'new_bitstream':False,'selftests':selftest(),'prepared_files':[],'tf_card_audited':False,'card_files':[],
 'user_feedback':{'other_functions':'user reports normal','audio':'A3 persists','L6':'on during fault','hardware_pass':False}}
 manifest=json.loads((base/'06_test_media/audio/audio_manifest.json').read_text(encoding='utf-8-sig'))
 byname={}
 for item in manifest['media']:
  path=base/item['file'];entry=inspect_bytes(path.read_bytes());entry['path']=str(path);entry['expected_sha256']=item['sha256']
  entry['matches_prepared_manifest']=entry['sha256']==item['sha256'];source=Path(item['source'])
  entry['source_copy_sha256']=sha(source);entry['matches_source_copy']=entry['sha256']==entry['source_copy_sha256']
  entry['full_decode']=full_decode(a.ffmpeg,path,out/(path.name+'_ffmpeg.log'))
  entry['pass']=entry['matches_prepared_manifest'] and entry['matches_source_copy'] and entry['full_decode']['pass']
  report['prepared_files'].append(entry);byname[path.name.upper()]=entry
 music_source=Path(r'D:\FPGA_Billboard\media\music_natianxiayule_20261026\01_originals\周杰伦,周杰伦- - 那天下雨了.flac')
 original=Path(r'D:\CloudMusic\周杰伦,周杰伦- - 那天下雨了.flac')
 si=flac_streaminfo(music_source);si.update(path=str(music_source),sha256=sha(music_source),user_source_sha256=sha(original))
 si['matches_user_source']=si['sha256']==si['user_source_sha256']
 si['wav_pcm_matches_flac_stored_md5']=byname['MUSIC.WAV']['data_md5']==si['stored_pcm_md5']
 si['wav_sample_count_matches_streaminfo']=byname['MUSIC.WAV']['sample_frames']==si['sample_frames']
 si['fresh_strict_flac_decode']=full_decode(a.ffmpeg,music_source,out/'source_FLAC_ffmpeg.log')
 si['warning']='Original FLAC strict decoder errors must remain recorded. Matching decoded-PCM MD5/sample count and a valid final WAV do not establish the original FLAC is clean.'
 report['music_source']=si
 if a.card_root:
  root=a.card_root.resolve();report['tf_card_root']=str(root)
  for name,local in byname.items():
   path=root/name
   try:
    entry=inspect_bytes(path.read_bytes());entry.update(path=str(path),matches_prepared_wav=entry['sha256']==local['sha256'])
    entry['full_decode']=full_decode(a.ffmpeg,path,out/('card_'+name+'_ffmpeg.log'));entry['pass']=entry['matches_prepared_wav'] and entry['full_decode']['pass']
   except (OSError,ValueError) as e:entry={'path':str(path),'pass':False,'error':str(e)}
   report['card_files'].append(entry)
  report['tf_card_audited']=True
 report['local_wav_checks_passed']=all(x['pass'] for x in report['prepared_files']) and si['matches_user_source'] and si['wav_pcm_matches_flac_stored_md5'] and si['wav_sample_count_matches_streaminfo']
 report['actual_card_corruption_excluded']=report['tf_card_audited'] and all(x['pass'] for x in report['card_files'])
 report['a3_root_cause_closed']=False
 report['limits']=['PCM WAV has no intrinsic sample checksum; successful WAV decoding alone does not prove original samples. SHA comparison and FLAC-stored PCM MD5 are separate evidence.',
 'No TF card available is NOT a pass. File equality does not prove SPI link, card latency, FAT traversal or sector arbitration.',
 'A3 is a latched PCM starvation flag, not a standalone file-corruption detector; source FLAC is not the FPGA playback file.',
 'No RTL change, new simulation, TD build, new bitstream, programming, listening or Flash acceptance in this diagnostic node.']
 (out/'audio_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'report':str(out/'audio_audit.json'),'selftests_passed':len(report['selftests']),
 'local_wav_checks_passed':report['local_wav_checks_passed'],'files':[{k:x[k] for k in ('path','sha256','duration_seconds','full_decode','pass')} for x in report['prepared_files']],
 'source_flac_strict_decode_pass':si['fresh_strict_flac_decode']['pass'],'wav_pcm_matches_source_flac_stored_md5':si['wav_pcm_matches_flac_stored_md5'],
 'tf_card_audited':report['tf_card_audited'],'actual_card_corruption_excluded':report['actual_card_corruption_excluded'],'a3_root_cause_closed':False},ensure_ascii=False,indent=2))
 return 0 if report['local_wav_checks_passed'] and (not report['tf_card_audited'] or report['actual_card_corruption_excluded']) else 1

if __name__=='__main__':sys.exit(main())
