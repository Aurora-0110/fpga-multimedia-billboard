from pathlib import Path
r=Path(__file__).resolve().parents[1];t=r/'02_tests/audio_visual'
for f in ['build_audio_visual_synth.tcl','build_audio_visual_physical_check.tcl']:
 p=r/'01_project'/f;s=p.read_text().replace('v114','v116').replace('V114','V116');p.write_text(s)
for name in ['synth','physical']:
 p=t/f'run_v114_{name}.py';s=p.read_text().replace('v114','v116').replace('V114','V116');(t/f'run_v116_{name}.py').write_text(s)
# Dedicated short pin-protocol integration for the modified shared arbiter.
p=r/'02_tests/wav/run_v114_actual_spi_tests.py';s=p.read_text().replace("('v114_actual_spi_'","('v116_actual_spi_'")
(r/'02_tests/wav/run_v116_actual_spi_tests.py').write_text(s)
print('v116 build entrypoints prepared; ADC, SDC, clocks, FIFO size and sample format unchanged')
