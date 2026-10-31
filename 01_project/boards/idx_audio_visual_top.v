`timescale 1ns/1ps
// v114 triple-sector + triple-slot sample prefetch, current/first-fault audio telemetry; v111: image/audio UI faults are independent; A3 remains an observable audio underrun.
// v109: sector-arbitrated TF WAV playback. Existing demo choice0 retained;1 MUSIC,2 ADVOICE,3 first extra WAV.
// v103 bounded TF inactivity/retry and non-hideable fault banner; v102 hidden parameter/key/status UI; v101: 1..2048 source dimensions, 720p bilinear and optional stationary RGB332 dither.
// v105 centered rounded Chinese glass UI and64 rainbow display bars from16 real DFT bands; v089 full720p OSD + short-chord toggle; retain diagnostics for v087 variable BMP + bilinear full720p + paired transport; picture controls + double buffers + left push transition + 3-layer Alpha OSD. Four images A/B/C/D; K0 next/retry, K1 independent MANUAL/AUTO mode: real SDRAM RGB332 framebuffer, independent 720p timing.
// Reset defaults to AUTO. Five-second visible dwell; busy K0 ignored, K1 remembered. An SDRAM PLL failure must not reset video timing.
module idx_audio_visual_top #(parameter START_BITS=16, KEY_CNT=742500, UI_HOLD_CYCLES=74250000, USE_TF=1, TF_HALF_DIV=124, TF_DATA_HALF_DIV=4, TF_POWER_WAIT=4950000, PLAYLIST_ENABLE=1, PLAYLIST_IMAGES=4, AUTO_PLAY=1, AUTO_DWELL_CYCLES=247500000, MAX_SOURCE_WIDTH=2048, MAX_SOURCE_HEIGHT=2048, DITHER_ENABLE=1, UI_TIMEOUT_FRAMES=360, LOAD_TIMEOUT_CYCLES=495000000, LOAD_AUTO_RETRIES=2, LOAD_RETRY_DELAY_CYCLES=49500000)(
 input wire clk24m,key0_n,key1_n,tf_miso,
 output wire tf_cs_n,tf_sck,tf_mosi,
 output wire led_sclk,led_dout,led_latch,hdmi_clk_p,
 output wire [2:0] hdmi_d_p);
 reg [START_BITS-1:0] startup=0;
 wire por_n=&startup;
 always @(posedge clk24m) if(!por_n) startup<=startup+1'b1;
 wire sd,pix,s5,l1,l2;
 pll_sdram u_pll_sd(.clk_in(clk24m),.rst_n(por_n),.clk_sd(sd),.clk_24(),.locked(l1));
 pll_video720 u_pll_vid(.clk_in(clk24m),.rst_n(por_n),.clk_pix(pix),.clk_5x(s5),.clk_sd(),.clk_sdram(),.locked(l2));
 wire rs,rp;
 // The shared bus uses rs as ordinary enable logic as well as async reset.
 // Release it on the positive edge: the prior falling release created a real
 // half-cycle rs->arbiter.dv->BMP CE path (-2.067ns at routed attempt3).
 // No clock/exception relaxation; async assertion and4-stage release retained.
 reset_release #(.RELEASE_FALLING_EDGE(0)) r0(.clk(sd),.async_n(l1),.rst_n(rs));
 reset_release #(.RELEASE_FALLING_EDGE(1)) r1(.clk(pix),.async_n(l2),.rst_n(rp));
 wire retry,mode_press;
 // Parameter edits live entirely in the pixel domain. Only human event toggles
 // cross to SD through independent two-flop synchronizers.
 wire [3:0] ui_volume;
 wire ui_av_enabled;wire ui_audio_select,ui_toggle,ui_audio_paused;wire [1:0] ui_audio_choice;wire [1:0] ui_keys_down;wire ui_next,ui_mode,ui_osd_enabled;wire signed [7:0] ui_brightness;wire [2:0] ui_contrast;wire [1:0] ui_field;
 media_controls #(.DEBOUNCE_CYCLES(KEY_CNT),.HOLD_CYCLES(UI_HOLD_CYCLES)) controls(
 .clk(pix),.rst_n(rp),.key0_n(key0_n),.key1_n(key1_n),.next_toggle(ui_next),.mode_toggle(ui_mode),
 .brightness(ui_brightness),.contrast_q2(ui_contrast),.edit_field(ui_field),.osd_enabled(ui_osd_enabled),.keys_down(ui_keys_down),.av_enabled(ui_av_enabled),.volume_level(ui_volume),.audio_select(ui_audio_select),.audio_choice(ui_audio_choice),.ui_toggle(ui_toggle),.audio_paused(ui_audio_paused));
 (* ASYNC_REG="TRUE" *) reg [1:0] next_sd,mode_sd;
 reg next_prev,mode_prev;reg [2:0] event_ready;
 // Either domain losing lock invalidates the event epoch. After recovery,
 // prime both synchronizers and their previous values before detecting edges.
 // A pre-reset toggle value of 1 must NOT be replayed as a new key action.
 wire event_reset_n=rs&&rp;
 always @(posedge sd or negedge event_reset_n)
 if(!event_reset_n)begin next_sd<=0;mode_sd<=0;next_prev<=0;mode_prev<=0;event_ready<=0;end
 else begin
  next_sd<={next_sd[0],ui_next};mode_sd<={mode_sd[0],ui_mode};
  next_prev<=next_sd[1];mode_prev<=mode_sd[1];event_ready<={event_ready[1:0],1'b1};
 end
 assign retry=event_ready[2]&&(next_sd[1]^next_prev);
 assign mode_press=event_ready[2]&&(mode_sd[1]^mode_prev);
 wire [11:0] x,y;wire hs,vs,de,fs;
 video_timing #(.H_ACTIVE(1280),.H_FP(110),.H_SYNC(40),.H_BP(220),
 .V_ACTIVE(720),.V_FP(5),.V_SYNC(5),.V_BP(20)) timing(.clk(pix),.rst_n(rp),
 .x(x),.y(y),.hs(hs),.vs(vs),.de(de),.frame_start(fs));
 wire window=de; // Entire effective 1280x720 picture, not a centered 640x480 window.
 wire [12:0] diag_fifo_used;
 wire [23:0] rgb;wire dd,hd,vd,init,fr,ren,run,fault,of,picture_visible;wire [1:0] phase;
 wire cke,cs,ras,cas,we,oe;wire [10:0] ma;wire [1:0] ba;wire [3:0] dm;
 wire [31:0] dout;tri [31:0] dq;assign dq=oe?dout:32'bz;
 wire lv,ldone,lack,lrst,len;wire [18:0] la;wire [127:0] ldata;
 wire [1:0] image_index,load_index,displayed_index;wire [5:0] displayed_step;
 wire [7:0] file_letter,error_latched;
 wire playlist_busy,playlist_failed,auto_mode,dest_bank,transition_request,transition_done;
 wire [7:0] load_error;wire tf_init,tf_mount,tf_header;
 wire signed [23:0] wav_l,wav_r;wire wav_valid,wav_epoch,wav_playing,wav_under,wav_finished;wire [7:0] wav_error;
 wire [12:0] wav_used,wav_min,wav_first_used;wire [7:0] wav_first_flags;
 tf_double_playlist #(.IMAGE_COUNT(PLAYLIST_IMAGES),.AUTO_ENABLE(AUTO_PLAY),.DWELL_CYCLES(AUTO_DWELL_CYCLES),
 .LOAD_TIMEOUT_CYCLES(LOAD_TIMEOUT_CYCLES),.AUTO_RETRIES(LOAD_AUTO_RETRIES),.RETRY_DELAY_CYCLES(LOAD_RETRY_DELAY_CYCLES)) select_image(
 .clk(sd),.rst_n(rs),.key_press(retry),.mode_press(mode_press),.init_done(init),
 .load_done(ldone),.load_error(load_error),.display_running(run),.stream_fault(fault|of),.transition_done(transition_done),
 .load_rst_n(lrst),.load_enable(len),.dest_bank(dest_bank),.file_letter(file_letter),
 .image_index(image_index),.load_index(load_index),.front_valid(fr),.transition_request(transition_request),
 .busy(playlist_busy),.failed(playlist_failed),.auto_mode(auto_mode),.error_latched(error_latched),.load_progress(lack));
 wire wav_consumed,wav_session_ready;
 generate if(USE_TF)begin: real_tf
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
 tf_wav_playback wav(.sample_consumed(wav_consumed),.session_ready(wav_session_ready),.clk_sd(sd),.clk_pix(pix),.rst_n(rs&&rp),.choice(ui_audio_choice),.mounted(mount_valid),.paused(ui_audio_paused),
 .root_cluster(root),.data_base(base),.fat_base(fat),.cluster_max(mx),.spc(spc),.shift(shift),
 .bus_reset_n(ar),.read_req(a_req),.read_lba(al),.urgent(urgent),.sd_ready(a_ready),.sd_done(a_done),.sd_error(ae),
 .data_valid(av),.data_index(hi),.data_byte(hb),.left(wav_l),.right(wav_r),.valid(wav_valid),.epoch(wav_epoch),
 .playing(wav_playing),.underrun(wav_under),.error_pix(wav_error),.finished(wav_finished),.audio_used(wav_used),.audio_minimum(wav_min),.first_underflow_used(wav_first_used),.first_underflow_flags(wav_first_flags));
 end else begin: pattern_source
 assign lv=0;assign la=0;assign ldata=0;assign ldone=0;assign load_error=0;
 assign tf_init=0;assign tf_mount=0;assign tf_header=0;
 assign tf_cs_n=1;assign tf_sck=0;assign tf_mosi=1;
 assign wav_consumed=0;assign wav_session_ready=0;
 assign wav_l=0;assign wav_r=0;assign wav_valid=0;assign wav_epoch=0;assign wav_playing=0;assign wav_under=0;assign wav_error=0;assign wav_finished=0;assign wav_used=0;assign wav_min=0;assign wav_first_used=0;assign wav_first_flags=0;
 end endgenerate
 idx_pair_pipeline pipe(.clk_sd(sd),.clk_pix(pix),.rst_sd_n(rs),.rst_pix_n(rp),.front_valid(fr),.dest_bank(dest_bank),
 .transition_request(transition_request),.target_index(load_index),.transition_done(transition_done),
 .load_valid(lv),.load_addr(la),.load_data(ldata),.load_ack(lack),
 .frame_start(fs),.de(de),.hs(~hs),.vs(~vs),.window(window),.rgb(rgb),.de_d(dd),.hs_d(hd),.vs_d(vd),
 .fifo_used_pairs(diag_fifo_used),.init_done(init),.display_running(run),.display_fault(fault),.picture_visible(picture_visible),.overflow_fault(of),
 .displayed_index(displayed_index),.displayed_step(displayed_step),
 .mem_cke(cke),.mem_cs_n(cs),.mem_ras_n(ras),.mem_cas_n(cas),.mem_we_n(we),.mem_addr(ma),.mem_ba(ba),.mem_dm(dm),
 .dq_out(dout),.dq_oe(oe),.dq_in(dq));
 EG_PHY_SDRAM_2M_32 u_ram(.clk(sd),.ras_n(ras),.cas_n(cas),.we_n(we),.addr(ma),.ba(ba),.dq(dq),
 .cs_n(cs),.dm0(dm[0]),.dm1(dm[1]),.dm2(dm[2]),.dm3(dm[3]),.cke(cke));
 // Match idx_display's one-cycle control/data latency. This marker deliberately
 // bypasses memory: visible border/background is NOT an SDRAM test PASS.
 reg win_d,edge_d;
 reg [11:0] x_d,y_d;wire audio_fault;
 always @(posedge pix or negedge rp)
 if(!rp)begin win_d<=0;edge_d<=0;x_d<=0;y_d<=0;end
 else begin
  win_d<=window;x_d<=x;y_d<=y;
  edge_d<=de&&(x<4||x>=1276||y<4||y>=716);
 end
 wire [23:0] screen_rgb=edge_d?24'hffffff:(win_d?(picture_visible?rgb:24'h0):24'h081830);
 // One-bit mode CDC; image/step metadata travels with each framebuffer pixel.
 (* ASYNC_REG="TRUE" *) reg [1:0] mode_pix;
 always @(posedge pix or negedge rp)if(!rp)mode_pix<=0;else mode_pix<={mode_pix[0],auto_mode};
 // Commit all user parameters together at the first active pixel of a frame.
 reg signed [7:0] active_brightness;reg [2:0] active_contrast;reg [1:0] active_field;reg active_osd_enabled,active_av_enabled;
 always @(posedge pix or negedge rp)
 if(!rp)begin active_brightness<=0;active_contrast<=4;active_field<=0;active_osd_enabled<=1;active_av_enabled<=1;end
 else if(dd&&x_d==0&&y_d==0)begin active_brightness<=ui_brightness;active_contrast<=ui_contrast;active_field<=ui_field;active_osd_enabled<=ui_osd_enabled;active_av_enabled<=ui_av_enabled;end
 wire [23:0] adjusted_rgb;wire [11:0] ax,ay;wire ad,ah,av,ap;wire [1:0] ai;
 picture_adjust adjust(.clk(pix),.rst_n(rp),.rgb(screen_rgb),.x(x_d),.y(y_d),
 .de(dd),.hs(hd),.vs(vd),.picture_visible(picture_visible),.apply_pixel(win_d&&picture_visible&&dd),
 .image_index(displayed_index),.brightness(active_brightness),.contrast_q2(active_contrast),
 .rgb_out(adjusted_rgb),.x_out(ax),.y_out(ay),.de_out(ad),.hs_out(ah),.vs_out(av),.picture_visible_out(ap),.image_index_out(ai));
 wire [23:0] osd_rgb;wire [11:0] ox,oy;wire od,oh,ov,op;
 osd_layers_visual #(.SHOW_PARAMS(1)) overlay(.clk(pix),.rst_n(rp),.x(ax),.y(ay),.rgb(adjusted_rgb),
 .de(ad),.hs(ah),.vs(av),.picture_visible(ap),.auto_mode(mode_pix[1]),.image_index(ai),
 .show_osd(active_osd_enabled),.brightness(active_brightness),.contrast_q2(active_contrast),.edit_field(active_field),
 .x_out(ox),.y_out(oy),.rgb_out(osd_rgb),.de_out(od),.hs_out(oh),.vs_out(ov),.picture_visible_out(op));
 // Select demo timbre once per visible frame, not on per-pixel mixed-slide
 // image metadata. The frontend publishes the epoch at a stereo boundary.
 reg [1:0]demo_track;
 always @(posedge pix or negedge rp)
 if(!rp)demo_track<=0;
 else if(ad&&ax==0&&ay==0&&ap)demo_track<=ai;
 wire [1:0] selected_demo_track=ui_audio_choice==0?demo_track:(ui_audio_choice==1?2'd1:2'd3);
 wire signed[23:0]pcm_left,pcm_right;wire pcm_valid,pcm_epoch;
 audio_pcm_frontend #(.VOLUME_ENABLE(1)) pcm_source(.volume_level(ui_volume),.clk_pix(pix),.rst_n(rp),.demo_track(selected_demo_track),.paused(ui_audio_paused),.use_external(USE_TF&&ui_audio_choice!=0),
 .external_l(wav_l),.external_r(wav_r),.external_valid(wav_valid),.external_epoch(wav_epoch),
 .pcm_l(pcm_left),.pcm_r(pcm_right),.pcm_valid(pcm_valid),.pcm_epoch(pcm_epoch),.bclk(),.lrclk(),.sdata());
 wire pcm_sound_active;
 pcm_activity_gate activity(.clk(pix),.rst_n(rp),.pcm_l(pcm_left),.pcm_r(pcm_right),
  .pcm_valid(pcm_valid),.stream_active(op),.track_change(pcm_epoch),.sound_active(pcm_sound_active));
 wire [127:0]spectrum_levels;wire spectrum_valid,spectrum_overrun;
 pcm_spectrum_dft analyze(.clk(pix),.rst_n(rp),.pcm_l(pcm_left),.pcm_r(pcm_right),
 .pcm_valid(pcm_valid),.stream_active(op),.track_change(pcm_epoch),
 .levels(spectrum_levels),.levels_valid(spectrum_valid),.overrun(spectrum_overrun),
 .bin_valid(),.bin_index(),.bin_energy());
 wire [23:0]visual_rgb;wire [11:0]vx,vy;wire vde,vhs,vvs,vpic;
 spectrum_overlay spectrum(.clk(pix),.rst_n(rp),.x(ox),.y(oy),.rgb(osd_rgb),
 .de(od),.hs(oh),.vs(ov),.picture_visible(op),.enable(active_av_enabled),
 .levels(spectrum_levels),.levels_valid(spectrum_valid),.track_change(pcm_epoch),.sound_active(pcm_sound_active),
 .x_out(vx),.y_out(vy),.rgb_out(visual_rgb),.de_out(vde),.hs_out(vhs),.vs_out(vvs),.picture_visible_out(vpic));
 // Actual WAV sample-consumption events delayed with the two-stage gain path.
 // Never count HDMI keepalive zeros; pause does not restart captions; mute advances.
 reg [1:0] caption_real_pipe,caption_first_pipe;
 always @(posedge pix or negedge rp)
 if(!rp)begin caption_real_pipe<=0;caption_first_pipe<=0;end
 else begin caption_real_pipe<={caption_real_pipe[0],wav_consumed};caption_first_pipe<={caption_first_pipe[0],wav_epoch};end
 wire [31:0] caption_samples;wire [10:0] caption_offset;wire [4:0] caption_length;
 wire subtitle_active;wire [5:0] subtitle_index;
 pcm_caption_player captions_clock(.clk(pix),.rst_n(rp),.choice(ui_audio_choice),
 .session_ready(wav_session_ready),.sample_consumed(caption_real_pipe[1]),.first_sample(caption_first_pipe[1]),
 .finished(wav_finished),.error_code(wav_error),.sample_position(caption_samples),
 .cue_active(subtitle_active),.text_offset(caption_offset),.text_length(caption_length),.cue_index(subtitle_index));
 wire [23:0]caption_rgb;wire [11:0]caption_x,caption_y;wire caption_de,caption_hs,caption_vs,caption_pic;
 subtitle_overlay captions(.clk(pix),.rst_n(rp),.x(vx),.y(vy),.rgb(visual_rgb),
 .de(vde),.hs(vhs),.vs(vvs),.picture_visible(vpic),.enable(active_av_enabled&&(ui_audio_choice==1||ui_audio_choice==3)),
 .text_offset(caption_offset),.text_length(caption_length),.cue_active(subtitle_active),
 .x_out(caption_x),.y_out(caption_y),.rgb_out(caption_rgb),.de_out(caption_de),.hs_out(caption_hs),.vs_out(caption_vs),.picture_visible_out(caption_pic));
 // Independent status banner survives a framebuffer visibility fault.
 // Multi-bit TF error is diagnostic only; publish after two equal samples.
 (* ASYNC_REG="TRUE" *) reg [3:0] dbg_meta,dbg_sync;
 (* ASYNC_REG="TRUE" *) reg [7:0] err_meta,err_sync;
 reg [7:0] err_prev,dbg_error;
 (* ASYNC_REG="TRUE" *) reg [1:0] help_meta,help_sync;
 always @(posedge pix or negedge rp)
 if(!rp)begin dbg_meta<=0;dbg_sync<=0;err_meta<=0;err_sync<=0;err_prev<=0;dbg_error<=0;help_meta<=0;help_sync<=0;end
 else begin
  dbg_meta<={len,rs,of,fr};dbg_sync<=dbg_meta;
   help_meta<={playlist_failed,playlist_busy};help_sync<=help_meta;
  err_meta<=error_latched;err_sync<=err_meta;err_prev<=err_sync;
  if(err_sync==err_prev)dbg_error<=err_sync;
 end
 wire [7:0] ui_audio_error=wav_error!=0?wav_error:(wav_under?8'ha3:8'd0);
 wire [23:0] help_rgb;wire [11:0] help_x,help_y;wire help_de,help_hs,help_vs,help_picture,help_visible;
 media_ui_overlay #(.TIMEOUT_FRAMES(UI_TIMEOUT_FRAMES)) help_ui(
 .clk(pix),.rst_n(rp),.x(caption_x),.y(caption_y),.rgb(caption_rgb),.de(caption_de),.hs(caption_hs),.vs(caption_vs),.picture_visible(caption_pic),
 .volume_level(ui_volume),.keys_down(ui_keys_down),.brightness(active_brightness),.contrast_q2(active_contrast),.edit_field(active_field),
 .auto_mode(mode_pix[1]),.overlays_enabled(active_osd_enabled),.av_enabled(active_av_enabled),.image_index(demo_track),
 .loading(help_sync[0]),.load_failed(help_sync[1]),.tf_error(dbg_error),.audio_error(ui_audio_error),.audio_active(pcm_sound_active),.audio_select(ui_audio_select),.audio_paused(ui_audio_paused),.audio_choice(ui_audio_choice),.ui_toggle(ui_toggle),
 .audio_status(wav_error!=0||wav_under?3'd4:(ui_audio_paused?3'd1:(ui_audio_choice!=0?(wav_finished?3'd3:(wav_playing?3'd0:3'd2)):3'd0))),
 .x_out(help_x),.y_out(help_y),.rgb_out(help_rgb),.de_out(help_de),.hs_out(help_hs),.vs_out(help_vs),
 .picture_visible_out(help_picture),.ui_visible(help_visible));
 // v103: decorative UI may be hidden, never a live display/audio/TF fault.
 wire [7:0] visible_error=ui_audio_error!=0?ui_audio_error:dbg_error;
 wire diagnostic_enable=active_osd_enabled||fault||audio_fault||wav_under||(|visible_error)||dbg_sync[1];
 wire [23:0] diag_rgb;wire [11:0] diag_x,diag_y;wire diag_de,diag_hs,diag_vs,diag_visible;
 display_diagnostics_osd #(.FAULT_ONLY(1),.VERSION_MAJOR(1),.VERSION_TENS(2),.VERSION_ONES(5),.ALWAYS_SHOW_FAULTS(1),.AUDIO_DEBUG(1)) diagnostics(.clk(pix),.rst_n(rp),.x(help_x),.y(help_y),.rgb(help_rgb),
 .de(help_de),.hs(help_hs),.vs(help_vs),.picture_visible(help_picture),.image_index(displayed_index),
 .status({dbg_sync[3],dbg_sync[2],audio_fault,dbg_sync[1],fault,picture_visible,run,dbg_sync[0]}),
 .tf_error(visible_error),.fifo_used(diag_fifo_used),.enable(diagnostic_enable),
 .audio_used(wav_used),.audio_minimum(wav_min),.audio_first_used(wav_first_used),.audio_first_flags(wav_first_flags),
 .x_out(diag_x),.y_out(diag_y),.rgb_out(diag_rgb),.de_out(diag_de),.hs_out(diag_hs),.vs_out(diag_vs),.picture_visible_out(diag_visible));
 hdmi_visual_wrap #(.INDEPENDENT_SERIAL_RESET(1),.HDMI_AUDIO_ENABLE(1),.HDMI_AUDIO_GATE_ENABLE(1)) hdmi(.clk_pix(pix),.clk_5x(s5),.rst_n(rp),.serial_async_n(l2),
 .pcm_l(pcm_left),.pcm_r(pcm_right),.pcm_valid(pcm_valid),
 .cx(diag_x),.cy(diag_y),.audio_fault(audio_fault),.picture_visible(diag_visible),
 .r(diag_rgb[23:16]),.g(diag_rgb[15:8]),.b(diag_rgb[7:0]),
 .de(diag_de),.hs(diag_hs),.vs(diag_vs),.tmds_clk_p(hdmi_clk_p),.tmds_clk_n(),.tmds_d_p(hdmi_d_p),.tmds_d_n());
 // LED controller runs on the crystal, so PLL loss cannot hide diagnostics.
 // L0 slow blink=AUTO (~1.40s period), fast blink=MANUAL (~0.175s); L1 video lock; L2 memory lock; L3 init; L4 frame written;
 // L5 display running (NOT comparison PASS); L6 underflow/overflow/audio FIFO fault; L7 TF load error.
 reg [24:0] hb;
 reg [7:0] status_meta,status_sync;
 always @(posedge clk24m or negedge por_n)
 if(!por_n)begin hb<=0;status_meta<=0;status_sync<=0;end
 else begin hb<=hb+1'b1;status_meta<={auto_mode,playlist_failed||(|wav_error),of||fault||audio_fault||wav_under,run,fr,init,l1,l2};status_sync<=status_meta;end
 wire [7:0] status={status_sync[6:0],status_sync[7]?hb[24]:hb[21]};
 bist_status_595 led(.clk(clk24m),.rst_n(por_n),.data(status),.sclk(led_sclk),.dout(led_dout),.latch(led_latch));
endmodule


