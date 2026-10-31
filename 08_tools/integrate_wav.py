from pathlib import Path
r=Path(r'D:\FPGA_Billboard\work\v108_tf_wav_20261026')
p=r/'01_project/rtl/audio/audio_choice_cdc.v';s=p.read_text().replace('output reg [1:0] sd_choice,output reg changed);','output reg [1:0] sd_choice,output reg changed,output pending);').replace(' reg [1:0] payload;reg request,ack;',' reg [1:0] payload;reg request,ack;\n assign pending=choice!=payload||request!=ak[1];');p.write_text(s)
p=r/'01_project/rtl/audio/tf_wav_reader.v';s=p.read_text().replace('.rst_n(rst_n&&(state==FILE_START||state==FILE_PLAY)),','.rst_n(rst_n&&(state==FILE_START||state==FILE_PLAY||(state==HALT&&eof))),');p.write_text(s)
p=r/'01_project/rtl/audio/tf_wav_playback.v';s=p.read_text().replace('wire [1:0] cmd;wire changed;', 'wire [1:0] cmd;wire changed,command_pending;').replace('.changed(changed));', '.changed(changed),.pending(command_pending));')
a=s.index(' // Also assert on');b=s.index(' wire sr,pr;',a)
s=s[:a]+''' // Assert immediately for a new request and hold until the destination
 // acknowledges the mailbox, then wait for the SD reset counter too.
 wire fifo_async_n=rst_n&&(reset_count==15)&&!command_pending&&(choice!=0);
'''+s[b:]
s=s.replace(' reg first_sample;reg pop_delay;', ''' wire sample_tick=sum>=PIX_HZ;
 reg first_sample;reg pop_delay;
 // Keep48k HDMI/ACR cadence running with explicit zero samples during mount,
 // rebuffer, switch, EOF and faults. Only accepted real samples drive epoch.
 always @(posedge clk_pix or negedge rst_n)
 if(!rst_n)begin acc<=0;left<=0;right<=0;valid<=0;epoch<=0;end
 else begin
  valid<=0;epoch<=0;
  if(sample_tick)begin
   acc<=sum-PIX_HZ;valid<=1;left<=0;right<=0;
   if(pr&&playing&&have&&error_pix==0)begin left<=held[47:24];right<=held[23:0];epoch<=first_sample;end
  end else acc<=sum[26:0];
 end''')
s=s.replace('begin left<=0;right<=0;valid<=0;epoch<=0;playing<=0;', 'begin playing<=0;').replace('finished<=0;acc<=0;pop<=0;', 'finished<=0;pop<=0;')
s=s.replace('  valid<=0;epoch<=0;pop<=0;', '  pop<=0;').replace('   acc<=0;\n','')
s=s.replace('end else if(sum>=PIX_HZ)begin\n   acc<=sum-PIX_HZ;', 'end else if(sample_tick)begin')
s=s.replace('if(have)begin left<=held[47:24];right<=held[23:0];valid<=1;epoch<=first_sample;first_sample<=0;have<=0;end','if(have)begin first_sample<=0;have<=0;end')
s=s.replace('playing<=0;left<=0;right<=0;','playing<=0;').replace('  end else acc<=sum[26:0];','  end') # careful global replacement also affects outer else accumulator!
# Restore cadence accumulator else in its own always.
s=s.replace('epoch<=first_sample;end\n  end\n end\n always', 'epoch<=first_sample;end\n  end else acc<=sum[26:0];\n end\n always')
p.write_text(s)
# Top shares the persistent SD host; mount geometry latched once per global reset.
p=r/'01_project/boards/idx_audio_visual_top.v';s=p.read_text()
s=s.replace('// v107: long single-key media/UI gestures and sample-clock demo subtitles; no TF WAV reader yet.','// v108: sector-arbitrated TF WAV playback. Existing demo choice0 retained;1 MUSIC,2 ADVOICE.')
s=s.replace('TF_DATA_HALF_DIV=12','TF_DATA_HALF_DIV=4')
s=s.replace(' wire [7:0] load_error;wire tf_init,tf_mount,tf_header;',''' wire [7:0] load_error;wire tf_init,tf_mount,tf_header;
 wire signed [23:0] wav_l,wav_r;wire wav_valid,wav_epoch,wav_playing,wav_under,wav_finished;wire [7:0] wav_error;''')
a=s.index(' generate if(USE_TF)');b=s.index(' idx_pair_pipeline pipe',a)
print(s[a:b])
s=s[:a]+''' generate if(USE_TF)begin: real_tf
 wire b_req,b_ready,b_done,bv,a_req,a_ready,a_done,av,ar,urgent;
 wire [31:0] bl,al,mb,mf,mm,mr;wire [7:0] ms;wire [3:0] msh,be,ae;
 wire hr,hd,hv,hreq;wire [31:0] hl;wire [3:0] he;wire [8:0] hi;wire [7:0] hb;
 reg mount_valid;reg [31:0] base,fat,mx,root;reg [7:0] spc;reg [3:0] shift;
 always @(posedge sd or negedge rs)
 if(!rs)begin mount_valid<=0;base<=0;fat<=0;mx<=0;root<=0;spc<=0;shift<=0;end
 else if(tf_mount&&!mount_valid)begin mount_valid<=1;base<=mb;fat<=mf;mx<=mm;root<=mr;spc<=ms;shift<=msh;end
 sd_spi_reader #(.HALF_DIV(TF_HALF_DIV),.DATA_HALF_DIV(TF_DATA_HALF_DIV),.POWER_WAIT_CYCLES(TF_POWER_WAIT)) card(
 .clk(sd),.rst_n(rs),.miso(tf_miso),.sck(tf_sck),.mosi(tf_mosi),.cs_n(tf_cs_n),
 .read_req(hreq),.read_lba(hl),.ready(hr),.init_done(tf_init),.read_done(hd),.signature_ok(),.error_code(he),
 .high_capacity(),.data_crc(),.received_crc(),.data_sum(),.last_r1(),.last_cmd(),.data_valid(hv),.data_index(hi),.data_byte(hb));
 media_sd_arbiter arbiter(.clk(sd),.rst_n(rs),.bmp_reset_n(lrst),.aud_reset_n(ar),.audio_urgent(urgent),
 .b_req(b_req),.b_lba(bl),.b_ready(b_ready),.b_done(b_done),.b_valid(bv),.b_error(be),
 .a_req(a_req),.a_lba(al),.a_ready(a_ready),.a_done(a_done),.a_valid(av),.a_error(ae),
 .h_req(hreq),.h_lba(hl),.h_ready(hr),.h_done(hd),.h_valid(hv),.h_error(he),.active(),.owner_audio());
 tf_bus_scaled_loader #(.HALF_DIV(TF_HALF_DIV),.DATA_HALF_DIV(TF_DATA_HALF_DIV),.POWER_WAIT_CYCLES(TF_POWER_WAIT),
 .MAX_WIDTH(MAX_SOURCE_WIDTH),.MAX_HEIGHT(MAX_SOURCE_HEIGHT),.DITHER_ENABLE(DITHER_ENABLE)) loader(
 .clk(sd),.rst_n(lrst),.file_letter(file_letter),.enable(len),.ready(b_ready),.read_done(b_done),.dv(bv),.se(be),.di(hi),.db(hb),
 .read_req(b_req),.read_lba(bl),.mount_base(mb),.mount_fat(mf),.mount_max(mm),.mount_root(mr),.mount_spc(ms),.mount_shift(msh),
 .req_valid(lv),.req_addr(la),.req_data(ldata),.req_ack(lack),.done(ldone),.error_code(load_error),
 .mounted(tf_mount),.bmp_ok(tf_header));
 tf_wav_playback wav(.clk_sd(sd),.clk_pix(pix),.rst_n(rs&&rp),.choice(ui_audio_choice),.mounted(mount_valid),
 .root_cluster(root),.data_base(base),.fat_base(fat),.cluster_max(mx),.spc(spc),.shift(shift),
 .bus_reset_n(ar),.read_req(a_req),.read_lba(al),.urgent(urgent),.sd_ready(a_ready),.sd_done(a_done),.sd_error(ae),
 .data_valid(av),.data_index(hi),.data_byte(hb),.left(wav_l),.right(wav_r),.valid(wav_valid),.epoch(wav_epoch),
 .playing(wav_playing),.underrun(wav_under),.error_pix(wav_error),.finished(wav_finished));
 end else begin: pattern_source
 assign lv=0;assign la=0;assign ldata=0;assign ldone=0;assign load_error=0;
 assign tf_init=0;assign tf_mount=0;assign tf_header=0;
 assign tf_cs_n=1;assign tf_sck=0;assign tf_mosi=1;
 assign wav_l=0;assign wav_r=0;assign wav_valid=0;assign wav_epoch=0;assign wav_playing=0;assign wav_under=0;assign wav_error=0;assign wav_finished=0;
 end endgenerate
'''+s[b:]
s=s.replace('.use_external(1\'b0),\n .external_l(24\'sd0),.external_r(24\'sd0),.external_valid(1\'b0),.external_epoch(1\'b0),', ".use_external(USE_TF&&ui_audio_choice!=0),\n .external_l(wav_l),.external_r(wav_r),.external_valid(wav_valid),.external_epoch(wav_epoch),")
# No16-second demo transcript/progress on actual music/advertisement.
s=s.replace('.enable(active_osd_enabled),\n .started(subtitle_started)', '.enable(active_osd_enabled&&ui_audio_choice==0),\n .started(subtitle_started)')
# Non-hideable audio file errors / rebuffer latch, separated from image error display.
s=s.replace(' wire diagnostic_enable=active_osd_enabled||fault||audio_fault||dbg_sync[1]||(|dbg_error);', ''' wire [7:0] visible_error=wav_error!=0?wav_error:(wav_under?8'ha3:dbg_error);
 wire diagnostic_enable=active_osd_enabled||fault||audio_fault||wav_under||(|visible_error)||dbg_sync[1];''')
s=s.replace('.tf_error(dbg_error),.audio_active(pcm_sound_active)', '.tf_error(wav_error!=0?wav_error:(wav_under?8\'ha3:dbg_error)),.audio_active(pcm_sound_active)')
s=s.replace('.VERSION_ONES(7)', '.VERSION_ONES(8)').replace('.tf_error(dbg_error),.fifo_used', '.tf_error(visible_error),.fifo_used')
s=s.replace('of||fault||audio_fault,run', 'of||fault||audio_fault||wav_under,run').replace('auto_mode,playlist_failed,', 'auto_mode,playlist_failed||(|wav_error),')
p.write_text(s,encoding='utf-8')
p=r/'01_project/build_audio_visual_synth.tcl';s=p.read_text().replace('v107','v108').replace('V107','V108')
s=s.replace('tf/spi_byte.v', 'tf/media_bmp_probe.v tf/tf_bus_bmp_source.v tf/tf_bus_bmp_scaled_source.v tf/tf_bus_scaled_loader.v tf/media_sd_arbiter.v tf/fat32_byte_stream.v audio/wav_pcm_decode.v audio/tf_wav_reader.v audio/audio_choice_cdc.v audio/tf_wav_playback.v tf/spi_byte.v')
p.write_text(s)
for name in ['synth','physical','bitgen']:
 p=r/f'02_tests/audio_visual/run_v107_{name}.py'
 (p.with_name(f'run_v108_{name}.py')).write_text(p.read_text().replace('v107','v108').replace('V107','V108'))
