from pathlib import Path
import os,re,json,hashlib,subprocess,datetime
root=Path(__file__).resolve().parents[2];rtl=root/'01_project/rtl';t=Path(__file__).resolve().parent
out=root/'04_evidence'/('v114_audio_diag_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
font={m[0]:[int(x,2) for x in m[1].split('_')] for m in re.findall(r'"(.)":bits=35\'b([01_]+);',(rtl/'video/osd_font.vh').read_text())}
font['Q']=[14,17,17,17,21,18,13];font['=']=[0,0,31,0,31,0,0]
(out/'font.hex').write_text(''.join(f'{v:02x}\n' for c in range(256)for v in font.get(chr(c),[0]*7)+[0]))
(out/'text.hex').write_text(''.join(f'{ord(c):02x}\n' for c in 'AUD Q=12AB MIN=0034 A3Q=0000 S=A2 B=3'.ljust(56)))
src=[t/'tb_v114_audio_diag.sv',rtl/'video/display_diagnostics_osd.v'];deps=src+[rtl/'video/osd_font.vh',Path(__file__)]
bound={p.relative_to(root).as_posix():sha(p)for p in deps}
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'))
exe=out/'diag.vvp';c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(rtl),'-s','tb_v114_audio_diag','-o',str(exe),*map(str,src)],env=env,capture_output=True,text=True);text=c.stdout+c.stderr;rc=None
if c.returncode==0:
 c2=subprocess.run([str(b/'vvp.exe'),str(exe),f'+FONT={out}/font.hex',f'+TEXT={out}/text.hex'],env=env,capture_output=True,text=True,timeout=60);text+=c2.stdout+c2.stderr;rc=c2.returncode
(out/'run.log').write_text(text,encoding='utf8')
rec=dict(passed=c.returncode==0 and rc==0 and 'PASS' in text and 'FATAL' not in text,source_sha256=bound,scope='Independent diagnostic third-line raster oracle, known hex fields,frame snapshot, hidden sticky fault and3-cycle all control/RGB alignment; no hardware')
(out/'summary.json').write_text(json.dumps(rec,indent=2),encoding='utf8');print(text[-2500:]);print(out);raise SystemExit(0 if rec['passed']else 1)
