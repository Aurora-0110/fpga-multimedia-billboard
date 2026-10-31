`timescale 1ns/1ps
module tb_v114_ui_audio;
 reg sd=0,pix=0;always #10 sd=~sd;always #7 pix=~pix;
 wire paused;reg rst=0;wire [1:0]choice;reg key0=1,key1=1;wire ui,select_audio;wire nt,mt;reg brst=1;reg b_req=0;wire ar,areq,ardy,adone,av,urgent;
 wire bready,bdone,bvalid;wire [3:0]be,ae,he;
 wire hreq,hr,hd,hv;wire [31:0]hl,al,active_lba,transactions;wire[8:0]hi;wire[7:0]hb;
 wire signed[23:0]l,rr;wire pv,ep,playing,und,finished;wire[7:0]err;
 integer mode;reg[31:0]bad_lba=32'hffffffff;reg[1:0]bad_kind=0;
 reg [47:0] music[0:4095],ad[0:4095];integer nm,na;reg[2047:0]mf,af;
 tf_wav_playback #(.FIFO_AW(11),.PREFILL(1024),.LOW_WATER(1536),.PIX_HZ(7425000)) dut(
 .clk_sd(sd),.clk_pix(pix),.rst_n(rst),.choice(choice),.mounted(1'b1),.paused(paused),.root_cluster(32'd2),.data_base(32'd600),.fat_base(32'd32),.cluster_max(32'd70000),.spc(8'd1),.shift(4'd0),
 .bus_reset_n(ar),.read_req(areq),.read_lba(al),.urgent(urgent),.sd_ready(ardy),.sd_done(adone),.sd_error(ae),.data_valid(av),.data_index(hi),.data_byte(hb),
 .left(l),.right(rr),.valid(pv),.epoch(ep),.playing(playing),.underrun(und),.error_pix(err),.finished(finished));
 media_sd_arbiter arb(.clk(sd),.rst_n(rst),.bmp_reset_n(brst),.aud_reset_n(ar),.audio_urgent(urgent),
 .b_req(b_req),.b_lba(32'd999999),.b_ready(bready),.b_done(bdone),.b_valid(bvalid),.b_error(be),
 .a_req(areq),.a_lba(al),.a_ready(ardy),.a_done(adone),.a_valid(av),.a_error(ae),
 .h_req(hreq),.h_lba(hl),.h_ready(hr),.h_done(hd),.h_valid(hv),.h_error(he),.active(),.owner_audio());
 wav_block_model host(.clk(sd),.rst_n(rst),.req(hreq),.lba(hl),.bad_lba(bad_lba),.bad_kind(bad_kind),
 .ready(hr),.done(hd),.valid(hv),.index(hi),.data(hb),.error(he),.active_lba(active_lba),.transactions(transactions));
 media_controls #(.DEBOUNCE_CYCLES(3),.HOLD_CYCLES(64)) controls(
 .clk(pix),.rst_n(rst),.key0_n(key0),.key1_n(key1),.next_toggle(nt),.mode_toggle(mt),
 .brightness(),.contrast_q2(),.edit_field(),.osd_enabled(),.keys_down(),
 .audio_select(select_audio),.audio_choice(choice),.ui_toggle(ui),.audio_paused(paused));
 task waitpix(input integer n);repeat(n)@(negedge pix);endtask
 task gesture(input integer key,input integer duration);begin
  if(key==0)key0=0;else key1=0;waitpix(duration);
  key0=1;key1=1;waitpix(16);
 end endtask
 integer toggles=0;reg last_ui=0;reg expect_ui_only=0;
 always @(posedge pix)if(rst)begin
  if(ui!=last_ui)begin toggles=toggles+1;last_ui=ui;end
  if(nt||mt)$fatal(1,"audio controls leaked image action");
  if(expect_ui_only&&(choice!=1||paused))$fatal(1,"UI gesture changed audio state");
  if(dut.staged>3||dut.staged+dut.pending>3)$fatal(1,"sample queue capacity");
 end
 integer pause_samples=0,pause_n=-1;
 integer n=0,epochs=0,selected=1,stage=0,cycles=0,bsectors=0,bcount=0;reg bbusy=0,seen_epoch=0;integer last_pv=0;
 initial begin
  if(!$value$plusargs("MODE=%d",mode)||!$value$plusargs("MUSIC=%s",mf)||!$value$plusargs("AD=%s",af)||!$value$plusargs("NM=%d",nm)||!$value$plusargs("NA=%d",na))$fatal(1,"args");
  $readmemh(mf,music,0,nm-1);$readmemh(af,ad,0,na-1);
  if(mode!=1)$fatal(1,"single integration mode required");
  waitpix(10);rst=1;waitpix(24);
  gesture(0,80);if(!select_audio)$fatal(1,"audio mode entry");
  gesture(1,12);if(choice!=1)$fatal(1,"music choice");
  wait(n>=100);expect_ui_only=1;
  repeat(6)gesture(1,80); // independent UI toggles during continuous PCM
  gesture(0,80);if(select_audio)$fatal(1,"mode exit");
  gesture(1,80); // independent UI remains available outside audio controls
  gesture(0,80);if(!select_audio)$fatal(1,"mode reentry");
  expect_ui_only=0;
  gesture(0,12);if(!paused)$fatal(1,"pause");
  gesture(1,80);if(!paused||choice!=1)$fatal(1,"UI unpaused/changed source");
  waitpix(400000);if(!dut.full)$fatal(1,"paused FIFO not filled");
  gesture(0,12);if(paused)$fatal(1,"resume");
  wait(n>=700);
  fork
   gesture(1,12);
   begin wait(choice==2);selected=2;n=0;seen_epoch=0;stage=1;end
  join
  if(toggles!=8)$fatal(1,"missing UI toggles %0d",toggles);
 end

 // Independent BMP-like client continuously asks for sectors. Cancel one in
 // flight to prove its reset never resets/corrupts the shared card host.
 always @(negedge sd)if(rst)begin
  b_req=0;
  if(!bbusy&&bready&&brst)begin b_req=1;bbusy=1;bcount=0;end
  if(bvalid)bcount=bcount+1;
  if(bdone&&bbusy&&bcount==512)begin bsectors=bsectors+1;bbusy=0;end
  if(transactions==5&&brst)begin brst=0;bbusy=0;end
  if(transactions>=6)brst=1;
 end
 always @(posedge pix)if(rst)begin
  cycles=cycles+1;
  if(pv)begin
   if(paused)begin
    if({l,rr}!==48'd0)$fatal(1,"nonzero PCM during pause");
    if(pause_n>=0&&n!=pause_n)$fatal(1,"pause consumed sample index");
    pause_n=n;pause_samples=pause_samples+1;
   end else pause_n=-1;
   // Accumulator runs across all source resets, no packet/ACR cadence gap.
   if(last_pv!=0&&cycles-last_pv!=154&&cycles-last_pv!=155)$fatal(1,"cadence %0d",cycles-last_pv);
   last_pv=cycles;
   if(ep)begin epochs=epochs+1;seen_epoch=1;if(n!=0)$fatal(1,"unexpected epoch n=%0d",n);end
   if({l,rr}!=48'd0&&err==0)begin
    if(!seen_epoch)$fatal(1,"sample before epoch");
    if(selected==1)begin if(n>=nm||{l,rr}!==music[n])$fatal(1,"music mismatch n=%0d got=%h exp=%h",n,{l,rr},music[n]);end
    else begin if(n>=na||{l,rr}!==ad[n])$fatal(1,"AD mismatch n=%0d got=%h exp=%h",n,{l,rr},ad[n]);end
    n=n+1;
   end
  end
  if((mode==2||mode==3)&&err!=0)begin
   if(n!=0)$fatal(1,"CRC/index failed sector leaked PCM count=%0d",n);
   $display("PASS transport rejection mode=%0d code=%h bmp_sectors=%0d",mode,err,bsectors);$finish;
  end
  if(finished)begin
   if(mode==2||mode==3)$fatal(1,"missing fault");
   if(n!=(selected==1?nm:na)||und||err!=0||bsectors<2||epochs!=((mode==1||mode==6)?2:1))$fatal(1,"end n=%0d und=%0d err=%h bmp=%0d epochs=%0d",n,und,err,bsectors,epochs);
   if(mode>=4&&pause_samples<20)$fatal(1,"missing pause evidence");
   $display("PASS UI+audio gestures mode=%0d samples=%0d epochs=%0d BMP sectors=%0d transactions=%0d",mode,n,epochs,bsectors,transactions);$finish;
  end
  if(cycles>3000000)$fatal(1,"timeout n=%0d readerstate=%0d bytestate=%0d err=%h",n,dut.reader.state,dut.reader.stream.state,err);
 end
endmodule
