from pathlib import Path
r=Path(__file__).resolve().parents[1];t=r/'02_tests/wav'
(t/'tb_v116_arbiter_gap.sv').write_text(r'''`timescale 1ns/1ps
module tb_v116_arbiter_gap;
 reg clk=0,rst=0;always #10 clk=~clk;
 reg ar=1,br=1,urgent=1,areq=0,breq=0;
 wire ard,adone,brd,bdone,hreq,active,owner;wire[31:0]hl;
 reg hr=1,hd=0;integer hostwait=0,started=0,ended=0,gap=0,phase=0;
 integer ac=0,bc=0,phase_b=0,snapshot;reg ab=0,bb=0;
 `ifdef BASELINE
 media_sd_arbiter_v114
 `else
 media_sd_arbiter
 `endif
 dut(.clk(clk),.rst_n(rst),.bmp_reset_n(br),.aud_reset_n(ar),.audio_urgent(urgent),
 .b_req(breq),.b_lba(32'd900),.b_ready(brd),.b_done(bdone),.b_valid(),.b_error(),
 .a_req(areq),.a_lba(32'd100),.a_ready(ard),.a_done(adone),.a_valid(),.a_error(),
 .h_req(hreq),.h_lba(hl),.h_ready(hr),.h_done(hd),.h_valid(1'b0),.h_error(4'd0),.active(active),.owner_audio(owner));
 always @(posedge clk)if(rst)begin
  if(hreq)begin
   if(!hr)$fatal(1,"host overlap");hr<=0;hd<=0;hostwait<=20;
   if(owner)ac=ac+1;else begin bc=bc+1;if(phase==0)phase_b=phase_b+1;end
  end else if(!hr)begin if(hostwait==0)begin hr<=1;hd<=1;end else hostwait<=hostwait-1;end
 end
 always @(negedge clk)if(rst)begin
  areq=0;breq=0;
  if(adone&&ab)begin ab=0;ended=ended+1;gap=12;end
  if(gap>0)gap=gap-1;
  if(phase==0&&started<8&&!ab&&ard&&gap==0)begin areq=1;ab=1;started=started+1;end
  if(bdone&&bb)bb=0;
  if(!bb&&brd)begin breq=1;bb=1;end
 end
 initial begin
  repeat(4)@(negedge clk);rst=1;wait(ended==8);@(negedge clk);phase=1;
  `ifdef BASELINE
  if(phase_b==0)$fatal(1,"old scheduler gap not exposed");
  `else
  if(phase_b!=0)$fatal(1,"urgent audio sector bubble still grants BMP: %0d",phase_b);
  `endif
  snapshot=bc;repeat(130)@(negedge clk);
  if(bc<snapshot+2)$fatal(1,"bounded reservation deadlocked BMP when urgent but no audio requests");
  // A disabled/reset audio client must not reserve the bus.
  ar=0;snapshot=bc;repeat(90)@(negedge clk);
  if(bc<snapshot+3)$fatal(1,"reset audio client delayed BMP");
  $display("PASS arbiter-gap audio=%0d interposed_BMP=%0d total_BMP=%0d finite_grace_no_request_and_client_reset=PASS",ac,phase_b,bc);$finish;
 end
 initial begin #200000;$fatal(1,"unit timeout");end
endmodule
''')
(t/'tb_v116_diag_persistent.sv').write_text(r'''`timescale 1ns/1ps
module tb_v116_diag_persistent;
 reg clk=0,rst=0;always #5 clk=~clk;
 reg[12:0] used=3000,minimum=13'h1fff,first_used=0;reg[7:0]first_flags=0;
 display_diagnostics_osd #(.AUDIO_DEBUG(1))dut(.clk(clk),.rst_n(rst),.x(12'd500),.y(12'd500),.rgb(24'd0),
 .de(1'b1),.hs(1'b1),.vs(1'b1),.picture_visible(1'b1),.image_index(2'd0),.status(8'd0),.tf_error(8'd0),.fifo_used(13'd4096),.enable(1'b0),
 .audio_used(used),.audio_minimum(minimum),.audio_first_used(first_used),.audio_first_flags(first_flags),
 .x_out(),.y_out(),.rgb_out(),.de_out(),.hs_out(),.vs_out(),.picture_visible_out());
 initial begin
  repeat(4)@(negedge clk);rst=1;repeat(4)@(negedge clk);
  // A one-clock first-error report, nowhere near the video frame snapshot.
  first_used=13'd7;first_flags=8'ha2;@(negedge clk);first_used=0;first_flags=0;
  repeat(20)@(negedge clk);
  if(dut.afirst!=7||dut.aflags!=8'ha2)$fatal(1,"first A3 was lost on source reset/UI exit");
  first_used=13'd4;first_flags=8'hb2;repeat(3)@(negedge clk);
  if(dut.afirst!=7||dut.aflags!=8'ha2)$fatal(1,"second A3 overwrote first evidence");
  rst=0;@(negedge clk);first_used=0;first_flags=0;rst=1;repeat(3)@(negedge clk);
  if(dut.afirst!=0||dut.aflags!=0)$fatal(1,"global reset did not clear evidence");
  $display("PASS persistent A3 single-cycle capture, survives source-reset/UI-exit, first-only, global-reset");$finish;
 end
endmodule
''')
(t/'run_v116_units.py').write_text(r'''from pathlib import Path
import os,subprocess,json,datetime,hashlib
root=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=root/'01_project/rtl';b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin')
out=root/'04_evidence'/('v116_units_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir();env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'))
rows=[]
for label,top,sources,defines in [('old_gap','tb_v116_arbiter_gap',[t/'tb_v116_arbiter_gap.sv',t/'v114_media_sd_arbiter_reference.v'],['-DBASELINE']),('new_gap','tb_v116_arbiter_gap',[t/'tb_v116_arbiter_gap.sv',rtl/'tf/media_sd_arbiter.v'],[]),('first_error','tb_v116_diag_persistent',[t/'tb_v116_diag_persistent.sv',rtl/'video/display_diagnostics_osd.v'],[])]:
 hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources+[Path(__file__)]};exe=out/(label+'.vvp')
 c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(rtl),*defines,'-s',top,'-o',str(exe),*map(str,sources)],env=env,capture_output=True,text=True);text=c.stdout+c.stderr
 if c.returncode==0:
  c=subprocess.run([str(b/'vvp.exe'),str(exe)],env=env,capture_output=True,text=True,timeout=30);text+=c.stdout+c.stderr
 (out/(label+'.log')).write_text(text);passed=c.returncode==0 and'PASS'in text;rows.append(dict(case=label,passed=passed,source_sha256=hashes));print(label,text,flush=True)
 if not passed:break
rec=dict(passed=len(rows)==3 and all(row['passed']for row in rows),cases=rows);(out/'summary.json').write_text(json.dumps(rec,indent=2));print(out);raise SystemExit(0 if rec['passed']else 1)
''')
print('Unit tests written')
