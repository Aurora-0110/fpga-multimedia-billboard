from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parents[1];rtl=r/'01_project/rtl'
p=rtl/'tf/media_sd_arbiter.v';s=p.read_text();s=s.replace('module media_sd_arbiter(','module media_sd_arbiter #(parameter integer REFILL_GRACE_CYCLES=32)(')
s=s.replace(' reg bp,ap,initialized;', ''' // A client cannot queue its next LBA until its just-completed sector
 // propagates through READ/NEXT/address/FAT states. Without this bounded
 // reservation, pending BMP wins that bubble even while audio is urgent,
 // defeating low-water priority at EVERY sector boundary. Never wait
 // indefinitely: mount/decode/backpressure may legitimately have no request.
 localparam GW=REFILL_GRACE_CYCLES>0?$clog2(REFILL_GRACE_CYCLES+1):1;
 reg [GW-1:0] refill_wait;
 wire reserve_audio=audio_urgent&&aud_reset_n&&refill_wait<REFILL_GRACE_CYCLES;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)refill_wait<=0;
 else if(active||!h_ready||!audio_urgent||!aud_reset_n)refill_wait<=0;
 else if(refill_wait<REFILL_GRACE_CYCLES)refill_wait<=refill_wait+1'b1;
 reg bp,ap,initialized;''')
s=s.replace('else if(bp&&bmp_reset_n)begin','else if(bp&&bmp_reset_n&&!reserve_audio)begin')
p.write_text(s)
p=rtl/'video/display_diagnostics_osd.v';s=p.read_text();s=s.replace('  if(tick)begin','''  // Capture FIRST audio underrun on a pixel clock, not only once per frame.
  // Keep it across source changes/UI exit. Only global reset clears it.
  if(AUDIO_DEBUG&&aflags==0&&audio_first_flags!=0)begin
   afirst<=audio_first_used;aflags<=audio_first_flags;
  end
  if(tick)begin''');s=s.replace('if(AUDIO_DEBUG)begin aq<=audio_used;amin<=audio_minimum;afirst<=audio_first_used;aflags<=audio_first_flags;end','if(AUDIO_DEBUG)begin aq<=audio_used;amin<=audio_minimum;end');p.write_text(s)
p=r/'01_project/boards/idx_audio_visual_top.v';s=p.read_text().replace('.VERSION_TENS(1),.VERSION_ONES(4)','.VERSION_TENS(1),.VERSION_ONES(6)');p.write_text(s)
prod={str(p.relative_to(r)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()for p in (r/'01_project').rglob('*')if p.is_file()}
(r/'04_evidence/v116_source_after_fix.json').write_text(json.dumps(prod,indent=2))
print('Arbiter bounded reservation and persistent first-A3 snapshot implemented.')
