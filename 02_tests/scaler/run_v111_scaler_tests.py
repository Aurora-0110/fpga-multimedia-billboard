"""Independent integer oracle + Icarus regression; no third-party Python packages.
Run with Python 3.9+: python -X utf8 -B run_scaler_tests.py [--quick]
Generated caches go to 02_tests/scaler/build (excluded from archive).
PASS evidence, seed, source SHA256 and tool version are kept outside build.
"""
from pathlib import Path
import argparse, hashlib, json, random, subprocess, time, os
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RTL=ROOT/'01_project/rtl/scale'
TOOLS=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
BUILD=HERE/'build'; BUILD.mkdir(exist_ok=True)
EVID=ROOT/'04_evidence/v111_scaler_units'; EVID.mkdir(parents=True,exist_ok=True)
SEED=0xB1832026

def run(args,cwd,timeout=240):
    env=dict(os.environ);env["PATH"]=str(TOOLS)+os.pathsep+env.get("PATH", "")
    p=subprocess.run([str(x) for x in args],cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
    text=p.stdout+p.stderr
    if p.returncode or 'FATAL' in text or 'ERROR' in text:
        raise RuntimeError(f"returncode={p.returncode} command={args}\n{text}")
    return text

def blend(p,fx,fy):
    # Reference directly weights four corners; does NOT duplicate the RTL's
    # signed difference / horizontal-then-vertical implementation.
    weights=((256-fx)*(256-fy),fx*(256-fy),(256-fx)*fy,fx*fy)
    out=0
    for shift in (0,8,16):
        v=(sum(((p[i]>>shift)&255)*weights[i] for i in range(4))+32768)//65536
        assert 0<=v<=255
        out |= v<<shift
    return out

def pattern(x,y):
    # Asymmetric channels and sharp edges catch transposes, stale rows and swaps.
    return (((x*37+y*13+(255 if (x//3+y//5)%2 else 0))&255)<<16 |
            ((x*7+y*53+(x*y)%251)&255)<<8 |
            ((x*91+y*19+67)&255))

def kernel():
    d=BUILD/'kernel';d.mkdir(exist_ok=True)
    rng=random.Random(SEED);n=0
    with (d/'kernel_vectors.hex').open('w',encoding='ascii') as f:
        presets=((0,0xffffff,0xffffff,0), (0xffffff,0,0,0xffffff),
                 (0x102030,0x102030,0x102030,0x102030),
                 (0xff0000,0x00ff00,0x0000ff,0xffffff))
        def emit(p,fx,fy):
            nonlocal n
            f.write(''.join(f'{v:06x}' for v in p)+f'{fx:02x}{fy:02x}{blend(p,fx,fy):06x}\n');n+=1
        for fx in range(256):
            for fy in range(256):emit(presets[(fx+fy)%len(presets)],fx,fy)
        for _ in range(20000):emit(tuple(rng.randrange(1<<24) for _ in range(4)),rng.randrange(256),rng.randrange(256))
    log=run([TOOLS/'iverilog.exe','-g2012','-Wall','-s','tb_bilinear_rgb888','-o',d/'test.vvp',RTL/'bilinear_rgb888.v',HERE/'tb_bilinear_rgb888.v'],d)
    log+=run([TOOLS/'vvp.exe',d/'test.vvp',f'+N={n}'],d)
    (EVID/'kernel.log').write_text(log,encoding='utf-8'); print(log.strip(),flush=True)
    return {'vectors':n,'all_fraction_pairs':65536,'result':'PASS','log':log.strip()}

def image_case(idx,w,h,ow,oh,td,maxw=1280,maxh=1024):
    d=BUILD/f'case_{idx:02d}';d.mkdir(exist_ok=True)
    # Generate logical top-down test content; serialize file order explicitly.
    with (d/'source.hex').open('w',encoding='ascii') as f:
        for r in range(h):
            y=r if td else h-1-r
            for x in range(w):f.write(f'{pattern(x,y):06x}\n')
    def pixel(x,r):return pattern(x,r if td else h-1-r)
    with (d/'expected.hex').open('w',encoding='ascii') as f:
        for dy in range(oh):
            sy,ry=divmod(dy*(h-1),oh-1); y1=min(sy+1,h-1);fy=(ry*256)//(oh-1)
            for dx in range(ow):
                sx,rx=divmod(dx*(w-1),ow-1); x1=min(sx+1,w-1);fx=(rx*256)//(ow-1)
                p=(pixel(sx,sy),pixel(x1,sy),pixel(sx,y1),pixel(x1,y1))
                f.write(f'{blend(p,fx,fy):06x}\n')
    log=run([TOOLS/'iverilog.exe','-g2012','-Wall','-s','tb_bilinear_stream_scaler',
             f'-Ptb_bilinear_stream_scaler.OW={ow}',f'-Ptb_bilinear_stream_scaler.OH={oh}',f'-Ptb_bilinear_stream_scaler.MW={maxw}',f'-Ptb_bilinear_stream_scaler.MH={maxh}',
             '-o',d/'test.vvp',RTL/'bilinear_rgb888.v',RTL/'bilinear_stream_scaler.v',HERE/'tb_bilinear_stream_scaler.v'],d)
    log+=run([TOOLS/'vvp.exe',d/'test.vvp',f'+W={w}',f'+H={h}',f'+TD={td}'],d,timeout=1200)
    (EVID/f'case_{idx:02d}.log').write_text(log,encoding='utf-8'); print(log.strip(),flush=True)
    return {'src':[w,h],'dst':[ow,oh],'top_down':bool(td),'pixels':ow*oh,'result':'PASS','log':log.strip()}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');args=ap.parse_args()
    t=time.time();results={'seed':SEED,'scope':'Standalone RGB888 scaler only; NOT connected to TF/SDRAM/HDMI top; NOT TD/bit/hardware acceptance.'}
    results['kernel']=kernel()
    cases=[(1,1,13,9,0),(1,1,13,9,1),(1,9,13,9,0),(7,1,13,9,1),
           (2,2,13,9,0),(3,5,13,9,1),(13,9,13,9,0),(13,9,13,9,1),
           (29,23,13,9,0),(29,23,13,9,1),(31,27,7,5,0),(15,19,6,4,1)]
    if not args.quick:cases += [(1280,1024,13,9,0),(640,480,1280,720,1),(17,11,1280,720,0)]
    # Keep small cases sequential; independent full720p cases run in two
    # processes to bound elapsed time without weakening per-pixel checks.
    small=cases if args.quick else cases[:13]
    results['images']=[image_case(i,*case) for i,case in enumerate(small)]
    if not args.quick:
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(image_case,i,*cases[i]) for i in (13,14)]
            results['images'] += [job.result() for job in jobs]
    files=sorted(RTL.glob('*.v'))+sorted(HERE.glob('*.v'))+[Path(__file__).resolve()]
    results['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    results['elapsed_seconds']=round(time.time()-t,2)
    results['tool_version']=run([TOOLS/'iverilog.exe','-V'],BUILD).splitlines()[0]
    results['full_suite']=not args.quick;results['total_image_pixels']=sum(x['pixels'] for x in results['images'])
    results['result']='PASS'
    (EVID/('quick_results.json' if args.quick else 'results.json')).write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f"PASS {'quick' if args.quick else 'full'}: {len(cases)} images, {results['total_image_pixels']} pixels, elapsed {results['elapsed_seconds']}s",flush=True)
if __name__=='__main__':main()

