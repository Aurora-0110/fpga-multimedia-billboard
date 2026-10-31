from pathlib import Path
import importlib.util,json,time,hashlib
p=Path(__file__).resolve().with_name('run_v111_scaler_tests.py');sp=importlib.util.spec_from_file_location('scaler_test',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
files=[p,Path(__file__),m.RTL/'bilinear_stream_scaler.v',m.RTL/'bilinear_rgb888.v',m.HERE/'tb_bilinear_stream_scaler.v']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={x.relative_to(m.ROOT).as_posix():sha(x) for x in files}
t=time.monotonic();r=[m.image_case(20,2048,2048,13,9,0,2048,2048),m.image_case(21,2048,2,13,9,1,2048,2048),m.image_case(22,1,2048,13,9,1,2048,2048)]
unchanged=all(sha(m.ROOT/k)==v for k,v in before.items())
(m.EVID/'address_boundary_results.json').write_text(json.dumps({'result':'PASS' if unchanged else 'FAIL','scope':'2048x2048 maximum source address regression, small output only; NOT full720p output','images':r,'elapsed_seconds':round(time.monotonic()-t,2),'source_sha256':before,'sources_unchanged_during_run':unchanged},indent=2),encoding='utf-8')
assert unchanged
