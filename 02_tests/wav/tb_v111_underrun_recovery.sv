`timescale 1ns/1ps
module tb_v111_underrun_recovery;
 reg sd=0,pix=0;always #10 sd=~sd;always #7 pix=~pix;
 reg paused=0;reg rst=0;reg [1:0]choice=0;reg brst=1;reg b_req=0;wire ar,areq,ardy,adone,av,urgent;
 wire bready,bdone,bvalid;wire [3:0]be,ae,he;
 wire hreq,hr,hd,hv;wire [31:0]hl,al,active_lba,transactions;wire[8:0]hi;wire[7:0]hb;
 wire signed[23:0]l,rr;wire pv,ep,playing,und,finished;wire[7:0]err;
 integer mode;reg stall=0;integer underrun_edges=0;reg prev_under=0;reg[31:0]bad_lba=32'hffffffff;reg[1:0]bad_kind=0;
 reg [47:0] music[0:4095],ad[0:4095];integer nm,na;reg[2047:0]mf,af;
 tf_wav_playback #(.FIFO_AW(11),.PREFILL(1024),.LOW_WATER(1536),.PIX_HZ(7425000)) dut(
 .clk_sd(sd),.clk_pix(pix),.rst_n(rst),.choice(choice),.mounted(1'b1),.paused(paused),.root_cluster(32'd2),.data_base(32'd600),.fat_base(32'd32),.cluster_max(32'd70000),.spc(8'd1),.shift(4'd0),
 .bus_reset_n(ar),.read_req(areq),.read_lba(al),.urgent(urgent),.sd_ready(ardy),.sd_done(adone),.sd_error(ae),.data_valid(av),.data_index(hi),.data_byte(hb),
 .left(l),.right(rr),.valid(pv),.epoch(ep),.playing(playing),.underrun(und),.error_pix(err),.finished(finished));
 media_sd_arbiter arb(.clk(sd),.rst_n(rst),.bmp_reset_n(brst),.aud_reset_n(ar),.audio_urgent(urgent),
 .b_req(b_req),.b_lba(32'd999999),.b_ready(bready),.b_done(bdone),.b_valid(bvalid),.b_error(be),
 .a_req(areq),.a_lba(al),.a_ready(ardy),.a_done(adone),.a_valid(av),.a_error(ae),
 .h_req(hreq),.h_lba(hl),.h_ready(hr),.h_done(hd),.h_valid(hv),.h_error(he),.active(),.owner_audio());
 wav_block_stall_model host(.clk(sd),.rst_n(rst),.stall(stall),.req(hreq),.lba(hl),.bad_lba(bad_lba),.bad_kind(bad_kind),
 .ready(hr),.done(hd),.valid(hv),.index(hi),.data(hb),.error(he),.active_lba(active_lba),.transactions(transactions));
 integer pause_samples=0,pause_n=-1;
 integer n=0,epochs=0,selected=1,stage=0,cycles=0,bsectors=0,bcount=0;reg bbusy=0,seen_epoch=0;integer last_pv=0;
 initial begin
  if(!$value$plusargs("MODE=%d",mode)||!$value$plusargs("MUSIC=%s",mf)||!$value$plusargs("AD=%s",af)||!$value$plusargs("NM=%d",nm)||!$value$plusargs("NA=%d",na))$fatal(1,"args");
  $readmemh(mf,music,0,nm-1);$readmemh(af,ad,0,na-1);
  if(mode==2)begin bad_kind=1;bad_lba=603;end
  if(mode==3)begin bad_kind=2;bad_lba=603;end
  repeat(10)@(negedge pix);rst=1;repeat(20)@(negedge pix);choice=1;
  if(mode==8)begin
   wait(n>=125);@(negedge sd);stall=1;
   wait(und);repeat(100)@(negedge sd);
   stall=0;
  end
  if(mode==4)begin
   wait(n>=125);@(negedge pix);paused=1;repeat(400000)@(negedge pix);
   if(!dut.full)$fatal(1,"pause did not exercise FIFO backpressure");
   paused=0;wait(n>=1500);@(negedge pix);paused=1;repeat(4000)@(negedge pix);paused=0;
  end
  if(mode==5)begin
   wait(n>=1);@(negedge pix);paused=1;repeat(400000)@(negedge pix);paused=0;
  end
  if(mode==7)begin
   wait(n>=nm-1);@(negedge pix);paused=1;repeat(40000)@(negedge pix);paused=0;
  end
  if(mode==1||mode==6)begin
   wait(n>=700);@(negedge pix);if(mode==6)begin paused=1;repeat(40000)@(negedge pix);end
   choice=2;paused=0;selected=2;n=0;seen_epoch=0;stage=1;
  end
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
  if(und&&!prev_under)underrun_edges=underrun_edges+1;
  prev_under=und;
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
   if(n!=(selected==1?nm:na)||(mode==8?(!und||underrun_edges!=1):und)||err!=0||bsectors<2||epochs!=((mode==1||mode==6)?2:1))$fatal(1,"end n=%0d und=%0d err=%h bmp=%0d epochs=%0d",n,und,err,bsectors,epochs);
   if(mode>=4&&mode<=7&&pause_samples<20)$fatal(1,"missing pause evidence");
   $display("PASS underrun/recovery mode=%0d samples=%0d epochs=%0d BMP sectors=%0d transactions=%0d",mode,n,epochs,bsectors,transactions);$finish;
  end
  if(cycles>3000000)$fatal(1,"timeout n=%0d readerstate=%0d bytestate=%0d err=%h",n,dut.reader.state,dut.reader.stream.state,err);
 end
endmodule
