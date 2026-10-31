`timescale 1ns/1ps
// v089 full720p OSD + short-chord toggle; retain diagnostics for v087 variable BMP + bilinear full720p + paired transport; picture controls + double buffers + left push transition + 3-layer Alpha OSD. Four images A/B/C/D; K0 next/retry, K1 independent MANUAL/AUTO mode: real SDRAM RGB332 framebuffer, independent 720p timing.
// Reset defaults to AUTO. Five-second visible dwell; busy K0 ignored, K1 remembered. An SDRAM PLL failure must not reset video timing.
module idx_scaled_video_top #(parameter START_BITS=16, KEY_CNT=742500, UI_HOLD_CYCLES=74250000, USE_TF=1, TF_HALF_DIV=124, TF_DATA_HALF_DIV=12, TF_POWER_WAIT=4950000, PLAYLIST_ENABLE=1, PLAYLIST_IMAGES=4, AUTO_PLAY=1, AUTO_DWELL_CYCLES=247500000)(
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
 reset_release #(.RELEASE_FALLING_EDGE(1)) r0(.clk(sd),.async_n(l1),.rst_n(rs));
 reset_release #(.RELEASE_FALLING_EDGE(1)) r1(.clk(pix),.async_n(l2),.rst_n(rp));
 wire retry,mode_press;
 // Parameter edits live entirely in the pixel domain. Only human event toggles
 // cross to SD through independent two-flop synchronizers.
 wire ui_next,ui_mode,ui_osd_enabled;wire signed [7:0] ui_brightness;wire [2:0] ui_contrast;wire [1:0] ui_field;
 picture_controls_osd #(.DEBOUNCE_CYCLES(KEY_CNT),.HOLD_CYCLES(UI_HOLD_CYCLES)) controls(
 .clk(pix),.rst_n(rp),.key0_n(key0_n),.key1_n(key1_n),.next_toggle(ui_next),.mode_toggle(ui_mode),
 .brightness(ui_brightness),.contrast_q2(ui_contrast),.edit_field(ui_field),.osd_enabled(ui_osd_enabled));
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
 tf_double_playlist #(.IMAGE_COUNT(PLAYLIST_IMAGES),.AUTO_ENABLE(AUTO_PLAY),.DWELL_CYCLES(AUTO_DWELL_CYCLES)) select_image(
 .clk(sd),.rst_n(rs),.key_press(retry),.mode_press(mode_press),.init_done(init),
 .load_done(ldone),.load_error(load_error),.display_running(run),.stream_fault(fault|of),.transition_done(transition_done),
 .load_rst_n(lrst),.load_enable(len),.dest_bank(dest_bank),.file_letter(file_letter),
 .image_index(image_index),.load_index(load_index),.front_valid(fr),.transition_request(transition_request),
 .busy(playlist_busy),.failed(playlist_failed),.auto_mode(auto_mode),.error_latched(error_latched),.load_progress(1'b0));
 generate if(USE_TF)begin: tf_source
 tf_scaled_loader #(.RUNTIME_NAME(PLAYLIST_ENABLE),.HALF_DIV(TF_HALF_DIV),.DATA_HALF_DIV(TF_DATA_HALF_DIV),.POWER_WAIT_CYCLES(TF_POWER_WAIT)) loader(
 .file_letter(file_letter),.clk(sd),.rst_n(lrst),.enable(len),.miso(tf_miso),.cs_n(tf_cs_n),.sck(tf_sck),.mosi(tf_mosi),
 .req_valid(lv),.req_addr(la),.req_data(ldata),.req_ack(lack),.done(ldone),.error_code(load_error),
 .sd_init(tf_init),.mounted(tf_mount),.bmp_ok(tf_header));
 end else begin: pattern_source
 assign lv=0;assign la=0;assign ldata=0;assign ldone=0;assign load_error=0;
 assign tf_init=0;assign tf_mount=0;assign tf_header=0;
 assign tf_cs_n=1;assign tf_sck=0;assign tf_mosi=1;
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
 reg signed [7:0] active_brightness;reg [2:0] active_contrast;reg [1:0] active_field;reg active_osd_enabled;
 always @(posedge pix or negedge rp)
 if(!rp)begin active_brightness<=0;active_contrast<=4;active_field<=0;active_osd_enabled<=1;end
 else if(dd&&x_d==0&&y_d==0)begin active_brightness<=ui_brightness;active_contrast<=ui_contrast;active_field<=ui_field;active_osd_enabled<=ui_osd_enabled;end
 wire [23:0] adjusted_rgb;wire [11:0] ax,ay;wire ad,ah,av,ap;wire [1:0] ai;
 picture_adjust adjust(.clk(pix),.rst_n(rp),.rgb(screen_rgb),.x(x_d),.y(y_d),
 .de(dd),.hs(hd),.vs(vd),.picture_visible(picture_visible),.apply_pixel(win_d&&picture_visible&&dd),
 .image_index(displayed_index),.brightness(active_brightness),.contrast_q2(active_contrast),
 .rgb_out(adjusted_rgb),.x_out(ax),.y_out(ay),.de_out(ad),.hs_out(ah),.vs_out(av),.picture_visible_out(ap),.image_index_out(ai));
 wire [23:0] osd_rgb;wire [11:0] ox,oy;wire od,oh,ov,op;
 osd_layers_full720 #(.SHOW_PARAMS(1)) overlay(.clk(pix),.rst_n(rp),.x(ax),.y(ay),.rgb(adjusted_rgb),
 .de(ad),.hs(ah),.vs(av),.picture_visible(ap),.auto_mode(mode_pix[1]),.image_index(ai),
 .show_osd(active_osd_enabled),.brightness(active_brightness),.contrast_q2(active_contrast),.edit_field(active_field),
 .x_out(ox),.y_out(oy),.rgb_out(osd_rgb),.de_out(od),.hs_out(oh),.vs_out(ov),.picture_visible_out(op));
 // Independent status banner survives a framebuffer visibility fault.
 // Multi-bit TF error is diagnostic only; publish after two equal samples.
 (* ASYNC_REG="TRUE" *) reg [3:0] dbg_meta,dbg_sync;
 (* ASYNC_REG="TRUE" *) reg [7:0] err_meta,err_sync;
 reg [7:0] err_prev,dbg_error;
 always @(posedge pix or negedge rp)
 if(!rp)begin dbg_meta<=0;dbg_sync<=0;err_meta<=0;err_sync<=0;err_prev<=0;dbg_error<=0;end
 else begin
  dbg_meta<={len,rs,of,fr};dbg_sync<=dbg_meta;
  err_meta<=error_latched;err_sync<=err_meta;err_prev<=err_sync;
  if(err_sync==err_prev)dbg_error<=err_sync;
 end
 wire [23:0] diag_rgb;wire [11:0] diag_x,diag_y;wire diag_de,diag_hs,diag_vs,diag_visible;
 display_diagnostics_osd #(.FAULT_ONLY(1)) diagnostics(.clk(pix),.rst_n(rp),.x(ox),.y(oy),.rgb(osd_rgb),
 .de(od),.hs(oh),.vs(ov),.picture_visible(op),.image_index(displayed_index),
 .status({dbg_sync[3],dbg_sync[2],audio_fault,dbg_sync[1],fault,picture_visible,run,dbg_sync[0]}),
 .tf_error(dbg_error),.fifo_used(diag_fifo_used),.enable(active_osd_enabled),
 .x_out(diag_x),.y_out(diag_y),.rgb_out(diag_rgb),.de_out(diag_de),.hs_out(diag_hs),.vs_out(diag_vs),.picture_visible_out(diag_visible));
 hdmi_tx_wrap #(.INDEPENDENT_SERIAL_RESET(1),.HDMI_AUDIO_ENABLE(1),.HDMI_AUDIO_GATE_ENABLE(1)) hdmi(.clk_pix(pix),.clk_5x(s5),.rst_n(rp),.serial_async_n(l2),
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
 else begin hb<=hb+1'b1;status_meta<={auto_mode,playlist_failed,of||fault||audio_fault,run,fr,init,l1,l2};status_sync<=status_meta;end
 wire [7:0] status={status_sync[6:0],status_sync[7]?hb[24]:hb[21]};
 bist_status_595 led(.clk(clk24m),.rst_n(por_n),.data(status),.sclk(led_sclk),.dout(led_dout),.latch(led_latch));
endmodule
