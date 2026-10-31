from pathlib import Path
import importlib.util,json,time
p=Path(__file__).resolve().with_name('run_scaler_tests.py');sp=importlib.util.spec_from_file_location('scaler_test',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
t=time.monotonic();r=[m.image_case(12,1280,1024,13,9,0),m.image_case(13,1280,2,13,9,1)]
(m.EVID/'address_boundary_results.json').write_text(json.dumps({'result':'PASS','scope':'Maximum source width/height address regression, small output only; NOT full720p output','images':r,'elapsed_seconds':round(time.monotonic()-t,2)},indent=2),encoding='utf-8')
