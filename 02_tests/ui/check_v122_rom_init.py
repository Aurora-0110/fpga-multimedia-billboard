"""Compare final routed UI/caption/Logo BRAM INIT with independent references.
This is neither routed functional simulation nor hardware readback/acceptance.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--physical-attempt', type=int, default=1)
args = parser.parse_args()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
pnl = root / f'05_td/v122_audio_visual_physical_attempt{args.physical_attempt}/physical/sdram_netlist.pnl'
raw = pnl.read_text(encoding='utf-8')
ui = sorted((root / '04_evidence').glob('v122_ui_[0-9]*/summary.json'))[-1]
media = sorted((root / '04_evidence').glob('v122_media_[0-9]*/summary.json'))[-1]
for path in (ui, media):
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data.get('passed') and data.get('complete'), str(path)

spec_path = root / '03_docs/v119_ui_font_spec.json'
spec = json.loads(spec_path.read_text(encoding='utf-8'))
ui_text = []
for n in range(64):
    message = spec['messages'][n] if n < len(spec['messages']) else ''
    ui_text.extend(spec['glyph_ids'][ch] for ch in message.ljust(16))
reference = {
    'help_ui': dict(font=[int(x, 16) for x in (ui.parent / 'font.hex').read_text().split()], text=ui_text),
    'captions': dict(font=[int(x, 16) for x in (media.parent / 'font.hex').read_text().split()],
                     text=[int(x, 16) for x in (media.parent / 'text.hex').read_text().split()]),
}
# Independent original combinational row table, NOT the optimized memory initializer.
logo_source = root / '01_project/rtl/video/official_logo.v'
original_module = logo_source.read_text(encoding='utf-8').split('endmodule', 1)[0]
logo_rows = {int(y): int(value, 16) for y, value in re.findall(r"6'd(\d+):\s*rowbits=224'h([0-9a-fA-F]+)", original_module)}
assert set(logo_rows) == set(range(56)), 'Incomplete original Logo reference'
logo_pixels = [((logo_rows[y] >> (2*x)) & 3) if x < 112 and y < 56 else 0
               for y in range(64) for x in range(128)]
# The two physical 8192x1 blocks must drive the corresponding color bit.
logo_lanes = {}
for net, block in re.findall(r'\tnet ([^\n]+)\n\t\{(.*?)\n\t\}', raw, re.S):
    lane = re.fullmatch(r'overlay/lp1\[([01])\]', net)
    if lane:
        pins = re.findall(r'(overlay/logo/[^\s,;]+),\s*doa\[0\];', block)
        assert len(pins) == 1, (net, pins)
        logo_lanes[pins[0]] = int(lane.group(1))
assert set(logo_lanes.values()) == {0, 1} and len(logo_lanes) == 2

found = []
for name, block in re.findall(r'\tinstance ([^\n]+)\n\t\{(.*?)\n\t\}', raw, re.S):
    group = name.split('/')[0]
    is_logo = name.startswith('overlay/logo/')
    if 'INIT_00' not in block or (group not in reference and not is_logo):
        continue
    init = {int(i, 16): int(value, 16) for i, value in re.findall(r"\bINIT_([0-9A-F]+)=256'h([0-9A-Fa-f]+)", block)}
    assert set(init) == set(range(32)), name
    width = int(re.search(r'DATA_WIDTH_A:(\d+)', block).group(1))
    bits = sum(init[i] << (256*i) for i in range(32))
    if is_logo:
        assert width == 1 and name in logo_lanes, (name, width)
        lane = logo_lanes[name]
        words = [(bits >> i) & 1 for i in range(8192)]
        assert words == [(value >> lane) & 1 for value in logo_pixels], (name, 'Logo INIT mismatch')
        found.append(dict(group='logo', instance=name, role='logo', words=8192,
                          physical_width=width, bit_offset=lane, matched=True))
    elif width == 9:
        words = [(bits >> (8*i)) & 255 for i in range(1024)]
        expected = reference[group]['text']
        assert words[:len(expected)] == expected, (name, 'text mismatch')
        found.append(dict(group=group, instance=name, role='text', active_words=len(expected), physical_width=width, matched=True))
    elif width == 4:
        words = [(bits >> (4*i)) & 15 for i in range(2048)]
        offsets = [offset for offset in (0, 4, 8, 12)
                   if words == [(value >> offset) & 15 for value in reference[group]['font']]]
        assert len(offsets) == 1, (name, offsets)
        found.append(dict(group=group, instance=name, role='font', words=2048,
                          physical_width=width, bit_offset=offsets[0], matched=True))
    else:
        raise AssertionError((name, width))
for group in reference:
    subset = [item for item in found if item['group'] == group]
    assert len(subset) == 5 and sum(item['role'] == 'text' for item in subset) == 1
    assert {item['bit_offset'] for item in subset if item['role'] == 'font'} == {0, 4, 8, 12}
assert len(found) == 12 and {item['bit_offset'] for item in found if item['group'] == 'logo'} == {0, 1}
inputs = [pnl, ui, media, ui.parent/'font.hex', media.parent/'font.hex', media.parent/'text.hex',
          spec_path, root/'03_docs/v107_subtitle_spec.json', Path(__file__), logo_source,
          *[root/'01_project/rtl/visual'/name for name in
            ('media_ui_overlay.v', 'subtitle_overlay.v', 'pcm_subtitle_timeline.v', 'official_logo_compact_sync.v')],
          *sorted((root/'01_project/rtl/visual').glob('media_ui_*.vh')),
          *sorted((root/'01_project/rtl/visual').glob('subtitle_*.vh'))]
out = root/'04_evidence'/('v122_rom_init_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
out.mkdir()
record = dict(passed=True,
              scope='Twelve final routed BRAM INIT blocks match independent Chinese UI/caption font-text and original 8192-coordinate Logo references; no routed-function, hardware-readback or electrical acceptance claim',
              physical_attempt=args.physical_attempt,
              source_sha256={p.relative_to(root).as_posix(): sha(p) for p in inputs}, mapped_roms=found)
(out/'summary.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(passed=True, mapped_roms=found, path=str(out)), indent=2))
