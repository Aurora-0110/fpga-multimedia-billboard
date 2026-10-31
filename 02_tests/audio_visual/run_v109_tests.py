"""Independent PCM numeric/reference/720p tests. No programming or TF changes."""
from pathlib import Path
import argparse,os,subprocess,json,hashlib,datetime,math,random,re,time,concurrent.futures
ap=argparse.ArgumentParser();ap.add_argument('--only',nargs='*');args=ap.parse_args()
root=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env['PATH']=str(b)+os.pathsep+env.get('PATH','')
temp_dir=root/'00_tmp';temp_dir.mkdir(exist_ok=True)
env.update(TEMP=str(temp_dir),TMP=str(temp_dir),TMPDIR=str(temp_dir),PYTHONDONTWRITEBYTECODE='1')
out=root/'04_evidence'/('v109_visual_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
coeff=[round(1024*math.cos(2*math.pi*n/256)) for n in range(256)]
bins=[1,2,3,4,5,6,8,10,13,17,22,29,38,50,66,90]
cases=[]
def add(name,l,r=None):cases.append((name,list(l),list(l if r is None else r)))
add('silence',[0]*256);add('positive_dc',[8388607]*256);add('negative_dc',[-8388608]*256)
for k in bins:add('coherent_tone_bin'+str(k),[round(2100000*math.sin(2*math.pi*k*n/256)) for n in range(256)])
add('off_bin_5p5',[round(1300000*math.sin(2*math.pi*5.5*n/256)) for n in range(256)])
add('three_tones',[round(900000*math.sin(2*math.pi*4*n/256)+600000*math.sin(2*math.pi*13*n/256)+200000*math.sin(2*math.pi*38*n/256)) for n in range(256)])
a=[round(2000000*math.sin(2*math.pi*6*n/256)) for n in range(256)];add('stereo_cancel',a,[-v for v in a])
add('fullscale_alternating',[-8388608 if n%2 else 8388607 for n in range(256)])
add('low24_bits_only',[round(77*math.sin(2*math.pi*8*n/256)) for n in range(256)])
add('odd_negative_average',[-4097]*256,[-4096]*256)
for amp in [1048576,524288,262144,131072]:add('amplitude_'+str(amp),[round(amp*math.sin(2*math.pi*4*n/256)) for n in range(256)])
rng=random.Random(91025);add('random_full24',[rng.randint(-8388608,8388607) for _ in range(256)],[rng.randint(-8388608,8388607) for _ in range(256)])
energy=[];levels=[];stim=[];report=[]
for name,l,r in cases:
 mono=[(a+b)//2 for a,b in zip(l,r)];ee=[];ll=[]
 for k in bins:
  rr=sum(s*coeff[(n*k)%256] for n,s in enumerate(mono))//(1<<24)
  ii=sum(s*coeff[(n*k+64)%256] for n,s in enumerate(mono))//(1<<24)
  power=rr*rr+ii*ii;ee.append(power)
  m=power.bit_length()-1;ll.append(0 if power<256 else min(144,(m-8)*6+((power>>(m-2))&3)))
 energy.extend(ee);levels.append(sum(v<<(i*8) for i,v in enumerate(ll)))
 stim.extend(((b&0xffffff)<<24)|(a&0xffffff) for a,b in zip(l,r))
 report.append({'name':name,'bins':bins,'energy':ee,'levels':ll})
(out/'samples.hex').write_text(''.join(f'{v:012x}\n' for v in stim));(out/'energy.hex').write_text(''.join(f'{v:010x}\n' for v in energy));(out/'levels.hex').write_text(''.join(f'{v:032x}\n' for v in levels))
(out/'integer_oracle.json').write_text(json.dumps({'method':'Independent Python signed-integer DFT, roundcosQ10; no DUT state read for energy','cases':report},indent=2))
native=out/'native';native.mkdir();provenance=[]
td=Path(r'C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\sim_release\eg4')
for filename,mod in [('eg_logic_io.v','EG_LOGIC_ODDR'),('eg_phy_glbl.v','glbl')]:
 src=td/filename;raw=src.read_text(encoding='utf8');head=raw[:raw.index('`timescale')];match=re.search(r'\bmodule\s+'+mod+r'\s*\(.*?\bendmodule',raw,re.S);assert match
 dest=native/(mod+'.v');dest.write_text(head+'\n`timescale 1ns/1ps\n'+match[0]+'\n',encoding='utf8');provenance.append({'original':str(src),'original_sha256':sha(src),'module':mod,'excerpt_sha256':sha(dest)})
(out/'native_provenance.json').write_text(json.dumps(provenance,indent=2))
common=[rtl/'video/osd_font.vh',*sorted((rtl/'visual').glob('*.vh'))]
jobs=[('activity','tb_v099_activity',[t/'tb_v099_activity.sv',rtl/'visual/pcm_activity_gate.v'],[],[]),('power_level','tb_power_level',[t/'tb_power_level.sv',rtl/'visual/spectrum_power_level.v'],[],[]),('logo','tb_logo',[t/'tb_logo.sv',rtl/'video/official_logo.v',rtl/'visual/official_logo_compact_sync.v'],[],[]),
 ('dft','tb_dft',[t/'tb_dft.sv',rtl/'visual/pcm_spectrum_dft.v',rtl/'visual/spectrum_power_level.v'],[],[f'+DATA={out}/samples.hex',f'+ENERGY={out}/energy.hex',f'+LEVEL={out}/levels.hex',f'+CASES={len(cases)}']),
 ('overlay','tb_v107_overlay',[t/'tb_v107_overlay.sv',rtl/'visual/spectrum_overlay.v'],[],[f'+PREVIEW={out}/v109_active_spectrum.ppm']),
 ('osd','tb_visual_osd',[t/'tb_visual_osd.sv',rtl/'visual/osd_layers_visual.v',rtl/'visual/official_logo_compact_sync.v',rtl/'video/official_logo.v'],[],[])]
sources=[*sorted((rtl/'audio').glob('*.v')),*sorted((rtl/'tf').glob('*.v')),*sorted((rtl/'scale').glob('*.v')),*sorted((rtl/'visual').glob('*.v')),*[rtl/s for s in ['ip/pll_video720.v','ip/hdmi_tx_wrap.v','ip/hdmi_visual_wrap.v','mem/sdram_ctrl.v','mem/async_fifo.v','video/idx_writer.v','video/idx_reader.v','video/idx_display.v','video/idx_pipeline.v','video/idx_dual_pipeline.v','video/idx_pair_reader.v','video/idx_pair_pipeline.v','video/idx_pair_display.v','video/idx_slide_reader.v','video/official_logo.v','video/osd_layers.v','video/osd_layers_full720.v','video/display_diagnostics.v','video/display_diagnostics_osd.v','video/picture_adjust.v','common/picture_controls.v','common/picture_controls_osd.v','common/media_controls.v','video/fb_session_ctrl.v','video/video_timing.v','video/tmds_encoder.v','video/tmds_serializer.v','common/reset_release.v','common/key_debounce.v','common/bist_status_595.v']]]
jobs.append(('top','tb_visual_top',[t/'tb_v107_top.sv',root/'01_project/boards/idx_audio_visual_top.v',native/'EG_LOGIC_ODDR.v',native/'glbl.v',*sources],['-DSIM_PLL_BEHAV','-s','glbl'],[]))
if (t/'tb_audio_pcm.sv').exists():jobs.append(('audio_pcm','tb_audio_pcm',[t/'tb_audio_pcm.sv',rtl/'visual/audio_pcm_frontend.v',rtl/'audio/i2s_test_tone.v',rtl/'audio/hdmi_audio_packets.v',rtl/'video/video_timing.v'],[],[]))
jobs.append(('tmds','tb_v100_tmds',[t/'tb_v100_tmds.sv',rtl/'video/tmds_encoder.v'],[],[]))
if args.only:jobs=[j for j in jobs if j[0] in args.only]
def run(job):
 name,top,src,extra,plus=job;start=time.monotonic();exe=out/(name+'.vvp');src=list(dict.fromkeys(list(src)+[rtl/'tf/media_bmp_probe.v',rtl/'tf/tf_bus_bmp_source.v',rtl/'tf/tf_bus_bmp_scaled_source.v',rtl/'tf/tf_bus_scaled_loader.v',rtl/'tf/media_sd_arbiter.v',rtl/'tf/fat32_byte_stream.v',rtl/'audio/wav_pcm_decode.v',rtl/'audio/tf_wav_reader.v',rtl/'audio/audio_choice_cdc.v',rtl/'audio/tf_wav_playback.v',rtl/'common/media_controls.v',rtl/'visual/media_ui_overlay.v',rtl/'visual/pcm_subtitle_timeline.v',rtl/'visual/subtitle_overlay.v']));cmd=[str(b/'iverilog.exe'),'-g2012','-Wall','-I',str(rtl),'-s',top,*extra,'-o',str(exe),*map(str,src)]
 before={s.relative_to(root).as_posix():sha(s) for s in src+common}
 c=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=40);text=c.stdout+c.stderr;rc=None
 if c.returncode==0:
  try:
   v=subprocess.run([str(b/'vvp.exe'),str(exe),*plus],env=env,capture_output=True,text=True,timeout=600);text+=v.stdout+v.stderr;rc=v.returncode
  except subprocess.TimeoutExpired:text+='\nTIMEOUT\n'
 (out/(name+'.log')).write_text(text,encoding='utf8');row={'name':name,'compile_rc':c.returncode,'sim_rc':rc,'passed':c.returncode==0 and rc==0 and 'PASS' in text and 'FATAL' not in text and 'ERROR' not in text and all(sha(root/k)==v for k,v in before.items()),'source_sha256':before,'sources_unchanged_during_run':all(sha(root/k)==v for k,v in before.items()),'elapsed_seconds':round(time.monotonic()-start,3),'results':[s for s in text.splitlines() if s.startswith(('PASS','FATAL','ERROR'))]}
 print(name,row['passed'],row['results'],flush=True)
 if not row['passed']:print(text[-4000:],flush=True)
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(run,jobs))
summary={'passed':all(x['passed'] for x in rows),'complete':len(rows)==len(jobs),'tests':rows,'scope':'v109: exhaustive TMDS and post-gain stereo activity/exact400ms release, exact DFT integer reference, transparent full720p blend/control/epochs and actual top with injected memory; no hardware acceptance','fixture_sha256':{f.name:sha(f) for f in [out/'samples.hex',out/'energy.hex',out/'levels.hex',out/'integer_oracle.json']}}
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(out,flush=True)
raise SystemExit(0 if summary['passed'] else 1)


