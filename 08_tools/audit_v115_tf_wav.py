"""Read-only comparison/decode of supplied TF-card WAV files; results on D only."""
from pathlib import Path
from datetime import datetime
import argparse, hashlib, json, sys
from audit_audio_files import inspect_bytes, selftest, full_decode, sha, DEFAULT_FFMPEG

root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser()
ap.add_argument('--input-root', type=Path, default=Path('E:/'))
ap.add_argument('--out',type=Path)
a=ap.parse_args()
out=a.out or root/'04_evidence'/('v115_tf_wav_audit_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
assert out.resolve().drive.upper()=='D:', 'Results must be on D'
assert not out.exists(), 'Preserve previous audit evidence'
out.mkdir(parents=True)
manifest_path=root/'06_test_media/audio/audio_manifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
expected={Path(x['file']).name.upper():x for x in manifest['media']}
report=dict(version='v115_tf_wav_audit_20261027', recorded_at=datetime.now().astimezone().isoformat(),
 scope='Read-only supplied E-drive WAV bytes/headers/full decode compared with original prepared WAV; no FPGA or real-time SPI/card latency test',
 input_root=str(a.input_root.resolve()), input_files_modified=False, flash_modified=False,
 new_rtl=False,new_bitstream=False,hardware_test=False,a3_root_cause_closed=False,
 source_sha256={'08_tools/audit_v115_tf_wav.py':sha(Path(__file__)),'08_tools/audit_audio_files.py':sha(root/'08_tools/audit_audio_files.py'),'06_test_media/audio/audio_manifest.json':sha(manifest_path)},
 decoder=dict(path=str(DEFAULT_FFMPEG),sha256=sha(DEFAULT_FFMPEG)),
 selftests=selftest(),files=[],
 limits=['Byte equality excludes alteration of the supplied files relative to prepared originals, not physical card response/latency/SPI integrity.',
 'WAV PCM accepts arbitrary sample bytes; decode alone cannot prove the source signal. Full-file SHA and direct byte comparison are independent checks.',
 'All audio outputs are discarded after strict decoding; no listening, FPGA programming, card repair or formatting is performed.'])

def byte_compare(left,right):
 offset=0
 with left.open('rb') as f,right.open('rb') as g:
  while True:
   x=f.read(1024*1024);y=g.read(1024*1024)
   if x!=y:
    n=min(len(x),len(y))
    i=next((i for i in range(n) if x[i]!=y[i]),n)
    return False,offset+i
   if not x:return True,None
   offset+=len(x)

for name in ('ADVOICE.WAV','MUSIC.WAV'):
 path=a.input_root/name
 entry=dict(path=str(path.resolve()),pass_all=False)
 try:
  before=path.stat()
  info=inspect_bytes(path.read_bytes());entry.update(info)
  gold=root/expected[name]['file']
  gold_info=inspect_bytes(gold.read_bytes())
  expected_sha=expected[name]['sha256']
  entry.update(expected_sha256=expected_sha,prepared_path=str(gold),prepared_sha256=gold_info['sha256'],
   prepared_manifest_matches=gold_info['sha256']==expected_sha,
   matches_original_sha256=info['sha256']==expected_sha,
   pcm_sha_matches_prepared=info['data_sha256']==gold_info['data_sha256'])
  equal,diff=byte_compare(path,gold)
  entry.update(byte_for_byte_equal=equal,first_differing_byte=diff)
  entry['full_decode']=full_decode(DEFAULT_FFMPEG,path,out/(name+'_strict_decode.log'))
  entry['sha256_after_checks']=sha(path)
  after=path.stat()
  entry['stable_during_read']=before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns and info['sha256']==entry['sha256_after_checks']
  entry['pass_all']=all((entry['prepared_manifest_matches'],entry['matches_original_sha256'],entry['pcm_sha_matches_prepared'],equal,
   entry['full_decode']['pass'],entry['full_decode']['stderr_empty'],entry['stable_during_read']))
 except Exception as e:
  entry['error']=type(e).__name__+': '+str(e)
 report['files'].append(entry)
report['passed']=all(c['pass']for c in report['selftests']) and len(report['files'])==2 and all(c['pass_all']for c in report['files'])
report_path=out/'summary.json'
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(report=str(report_path),passed=report['passed'],selftests_passed=sum(c['pass']for c in report['selftests']),files=[{k:x.get(k)for k in ('path','file_bytes','sample_rate_hz','bits_per_sample','channels','sample_frames','duration_seconds','sha256','byte_for_byte_equal','stable_during_read','full_decode','pass_all','error')}for x in report['files']]),ensure_ascii=False,indent=2),flush=True)
sys.exit(0 if report['passed']else 1)
