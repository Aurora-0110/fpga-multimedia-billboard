"""One-time explicit working-copy patch. Keeps V130 immutable and all UI pixels."""
from pathlib import Path
import json,re,hashlib,datetime
R=Path(__file__).resolve().parents[1];assert R.name=='v132_ui_rom_compact_20261031'and '01_versions'not in R.parts
B=Path(r'D:\FPGA_Billboard\99_archive\version_history\01_versions\v130_av_layer_ui_20261030\01_project')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rtl=R/'01_project/rtl/visual';raw=(rtl/'media_ui_zh_font_init.vh').read_text('utf8')
rows={int(a):int(b,16)for a,b in re.findall(r"font_memory\[(\d+)\]=16'h([0-9a-fA-F]+);",raw)};assert set(rows)==set(range(2048))
# Prove every removed bit is zero, never crop a painted glyph.
for g in range(128):
 for y in range(16):
  v=rows[g*16+y];assert v&0x8001==0,(g,y,v);assert y!=15 or v==0,(g,y,v)
banks=[[0]*512 for _ in range(3)]
for g in range(128):
 payload=sum(((rows[g*16+y]>>1)&0x3fff)<<(y*14)for y in range(15))
 for word in range(12):banks[word//4][g*4+word%4]=(payload>>(word*18))&0x3ffff
 for y in range(16):
  for x in range(16):
   old=(rows[g*16+y]>>(15-x))&1
   if x in[0,15]or y==15:new=0
   else:
    bit=y*14+14-x;word=bit//18;new=(banks[word//4][g*4+word%4]>>(bit%18))&1
   assert new==old,(g,y,x)
init='// V132 lossless 128x(14x15) UI payload in three512x18 native9K ROMs.\n// Original16x16 edge zeros proven by prepare_v132_ui_compact.py; OFL unchanged.\n'
for bank in range(3):init+=''.join(f"ui_font_rom{bank}[{i}]=18'h{v:05x};\n"for i,v in enumerate(banks[bank]))
(rtl/'media_ui_font_packed_v132.vh').write_text(init,encoding='utf8')
f=rtl/'media_ui_overlay.v';s=f.read_text('utf8')
s=s.replace('// v111: separate image and audio fault domains;', '// V132: lossless UI ROM packing (4->3 native9K blocks), pixel/latency unchanged.\n// v111: separate image and audio fault domains;')
s=s.replace('(* rom_style="block" *) reg [15:0] font_memory[0:2047];','''(* rom_style="block" *) reg [17:0] ui_font_rom0[0:511];
 (* rom_style="block" *) reg [17:0] ui_font_rom1[0:511];
 (* rom_style="block" *) reg [17:0] ui_font_rom2[0:511];''')
s=s.replace('`include "visual/media_ui_zh_font_init.vh"','`include "visual/media_ui_font_packed_v132.vh"')
old=''' reg [15:0] bits2;
 always @(posedge clk)begin
  text_glyph1<=text_memory[{message0,text_col0}];
  bits2<=font_memory[{(override1?override_glyph1:text_glyph1),font_y1}];
 end'''
rowcases='\n'.join(f"   4'd{y}:begin font_base_word1=4'd{(14*y)//18};font_row_bit1=5'd{(14*y)%18};end"for y in range(15))
new=''' // Three parallel512x18 ROM banks, each four words per glyph.
 // Only the all-zero edge columns x0/x15 and bottom row15 are implicit.
 // Coordinates still describe the original16x16 source and32px output cells.
 reg [3:0] font_base_word1;
 reg [4:0] font_row_bit1;
 always @*begin
  font_base_word1=0;font_row_bit1=0;
  case(font_y1)
'''+rowcases+'''
   default:begin font_base_word1=0;font_row_bit1=0;end
  endcase
 end
 wire [4:0] font_raw_bit1=font_row_bit1+5'd14-{1'b0,font_x1};
 wire font_carry1=font_raw_bit1>=18;
 wire [3:0] font_word1=font_base_word1+{3'b0,font_carry1};
 wire [4:0] font_bit1=font_carry1?font_raw_bit1-5'd18:font_raw_bit1;
 wire [6:0] font_glyph1=override1?override_glyph1:text_glyph1;
 wire [8:0] font_addr1={font_glyph1,font_word1[1:0]};
 reg [17:0] font_bits2_0,font_bits2_1,font_bits2_2;
 reg [1:0] font_bank2;
 reg [4:0] font_bit2;
 reg font_valid2;
 wire [17:0] font_bits2=font_bank2==0?font_bits2_0:(font_bank2==1?font_bits2_1:font_bits2_2);
 wire font_pixel2=font_valid2&&font_bits2[font_bit2];
 // No asynchronous reset/enable on ROM outputs: keep synchronous RAM inference.
 always @(posedge clk)begin
  text_glyph1<=text_memory[{message0,text_col0}];
  font_bits2_0<=ui_font_rom0[font_addr1];
  font_bits2_1<=ui_font_rom1[font_addr1];
  font_bits2_2<=ui_font_rom2[font_addr1];
  font_bank2<=font_word1[3:2];font_bit2<=font_bit1;
  font_valid2<=font_y1<15&&font_x1>0&&font_x1<15;
 end'''
assert old in s;s=s.replace(old,new)
assert '(glyph[2]&&bits2[15-font_x2])'in s;s=s.replace('(glyph[2]&&bits2[15-font_x2])','(glyph[2]&&font_pixel2)')
f.write_text(s,encoding='utf8')
# Preserve all old tests as historical artifacts. New raster TB keeps its independent font oracle.
tb=(R/'02_tests/ui/tb_v130_ui.sv').read_text('utf8').replace('module tb_v130_ui;','module tb_v132_ui;')
old='  for(i=0;i<2048;i++)if(d.font_memory[i]!==font_memory[i])$fatal(1,"font row differs from independent source-font raster at %0d",i);'
assert old in tb
new='''  // Reconstruct every original16x16 glyph from all compact native ROM words.
  for(i=0;i<2048;i++)begin
   for(col=0;col<16;col++)begin
    if(col==0||col==15||i%16==15)begin
     if(font_memory[i][15-col]!==1'b0)$fatal(1,"removed edge not zero %0d/%0d",i,col);
    end else begin
     row=(i%16)*14+14-col;off=row/18;row=row%18;
     case(off/4)
      0:if(d.ui_font_rom0[(i/16)*4+off%4][row]!==font_memory[i][15-col])$fatal(1,"compactROM0 mismatch %0d/%0d",i,col);
      1:if(d.ui_font_rom1[(i/16)*4+off%4][row]!==font_memory[i][15-col])$fatal(1,"compactROM1 mismatch %0d/%0d",i,col);
      2:if(d.ui_font_rom2[(i/16)*4+off%4][row]!==font_memory[i][15-col])$fatal(1,"compactROM2 mismatch %0d/%0d",i,col);
      default:$fatal(1,"bad word bank");
     endcase
    end
   end
  end'''
tb=tb.replace(old,new);(R/'02_tests/ui/tb_v132_ui.sv').write_text(tb,encoding='utf8')
run=(R/'02_tests/ui/run_v130_ui.py').read_text('utf8').replace("'v130_ui_'","'v132_ui_'").replace("'tb_v130_ui'","'tb_v132_ui'").replace("'tb_v130_ui.sv'","'tb_v132_ui.sv'").replace("{out}/v130_ui","{out}/v132_ui")
run=run.replace("'media_ui_zh_font_init.vh','media_ui_zh_text_init.vh'","'media_ui_zh_font_init.vh','media_ui_font_packed_v132.vh','media_ui_zh_text_init.vh'")
run=run.replace('"""v108:','"""V132 compact ROM + unchanged V130 independent font/pixel oracle:')
(R/'02_tests/ui/run_v132_ui.py').write_text(run,encoding='utf8')
# New affected runner explicitly binds NEW UI evidence, rather than reusing old V130 checks.
run=(R/'08_tools/run_v130_affected.py').read_text('utf8').replace("'v130_affected_'","'v132_affected_'").replace("'v130_ui_[0-9]*'","'v132_ui_[0-9]*'").replace("'02_tests/ui/run_v130_ui.py'","'02_tests/ui/run_v132_ui.py'")
run=run.replace('Fresh V130 groups including this-turn16-row UI and4-state controls.','Fresh V132 compact UI plus unchanged V130 groups; UI/media rerun on these sources.')
(R/'08_tools/run_v132_affected.py').write_text(run,encoding='utf8')
changed=[q.relative_to(R).as_posix()for q in(R/'01_project').rglob('*')if q.is_file()and(not(B/q.relative_to(R)).is_file()or sha(q)!=sha(B/q.relative_to(R)))]
assert changed==['01_project/rtl/visual/media_ui_overlay.v','01_project/rtl/visual/media_ui_font_packed_v132.vh']or set(changed)=={'01_project/rtl/visual/media_ui_overlay.v','01_project/rtl/visual/media_ui_font_packed_v132.vh'},changed
rec=dict(version=R.name,baseline=B.parent.name,scope='Existing UI ROM lossless packing only; no SHOW/CAP/runtime format or feature expansion.',changed_rtl=changed,baseline_glyph_slots=128,baseline_source_pixels_per_glyph=256,stored_pixels_per_glyph=210,zero_pixels_proven_per_glyph=46,all_source_pixels_proven=32768,original_font_bits=32768,packed_payload_bits=26880,packed_rom_allocated_bits=27648,expected_native_bram9k_before=4,expected_native_bram9k_after=3,actual_map_pending=True,fonts_labels_layout_timing_and_keys_unchanged=True,source_sha256={p.relative_to(R).as_posix():sha(p)for p in[rtl/'media_ui_overlay.v',rtl/'media_ui_font_packed_v132.vh',rtl/'media_ui_zh_font_init.vh',Path(__file__)]})
(R/'04_evidence/v132_preparation/packing.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(rec,ensure_ascii=False,indent=2))
