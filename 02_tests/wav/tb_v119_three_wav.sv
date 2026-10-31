`timescale 1ns/1ps
// Production4096-frame PCM FIFO and v116 shared arbiter, virtual sector transport.
module tb_v119_three_wav;
 reg sd=0,pix=0;always #10 sd=~sd;always #7 pix=~pix;
 reg rst=0,paused=0;reg[1:0]choice=0;
 wire ar,areq,ardy,adone,av,urgent;wire[31:0]al;
 reg brst=1,breq=0,bbusy=0;wire brdy,bdone,bvalid;wire[3:0]be,ae,he;
 wire hreq,hr,hd,hv;wire[31:0]hl,active_lba,transactions;wire[8:0]hi;wire[7:0]hb;
 wire signed[23:0]l,rr;wire pv,ep,playing,und,finished;wire[7:0]err;
 tf_wav_playback #(.FIFO_AW(12),.PREFILL(3072),.LOW_WATER(3584),.PIX_HZ(7425000)) dut(
 .clk_sd(sd),.clk_pix(pix),.rst_n(rst),.choice(choice),.mounted(1'b1),.paused(paused),
 .root_cluster(32'd2),.data_base(32'd600),.fat_base(32'd32),.cluster_max(32'd70000),.spc(8'd1),.shift(4'd0),
 .bus_reset_n(ar),.read_req(areq),.read_lba(al),.urgent(urgent),.sd_ready(ardy),.sd_done(adone),.sd_error(ae),
 .data_valid(av),.data_index(hi),.data_byte(hb),.left(l),.right(rr),.valid(pv),.epoch(ep),.playing(playing),
 .underrun(und),.error_pix(err),.finished(finished));
 media_sd_arbiter arb(.clk(sd),.rst_n(rst),.bmp_reset_n(brst),.aud_reset_n(ar),.audio_urgent(urgent),
 .b_req(breq),.b_lba(32'd999999),.b_ready(brdy),.b_done(bdone),.b_valid(bvalid),.b_error(be),
 .a_req(areq),.a_lba(al),.a_ready(ardy),.a_done(adone),.a_valid(av),.a_error(ae),
 .h_req(hreq),.h_lba(hl),.h_ready(hr),.h_done(hd),.h_valid(hv),.h_error(he),.active(),.owner_audio());
 wav_block_model host(.clk(sd),.rst_n(rst),.req(hreq),.lba(hl),.bad_lba(32'hffffffff),.bad_kind(2'd0),
 .ready(hr),.done(hd),.valid(hv),.index(hi),.data(hb),.error(he),.active_lba(active_lba),.transactions(transactions));
 reg[47:0]music[0:8191],ad[0:8191],extra[0:8191];reg[2047:0]mf,af,xf;
 integer mode,nm,na,nx,n=0,selected=3,epochs=0,cycles=0,last_pv=0,bcount=0,bsectors=0,pause_ticks=0;
 reg seen_epoch=0,recovered=0;reg[47:0]expected;
 task switch_to(input[1:0]c);begin
  @(negedge pix);choice=c;selected=c;n=0;seen_epoch=0;paused=0;
 end endtask
 initial begin
  if(!$value$plusargs("MODE=%d",mode)||!$value$plusargs("MUSIC=%s",mf)||!$value$plusargs("AD=%s",af)||!$value$plusargs("EXTRA=%s",xf)||!$value$plusargs("NM=%d",nm)||!$value$plusargs("NA=%d",na)||!$value$plusargs("NX=%d",nx))$fatal(1,"args");
  $readmemh(mf,music,0,nm-1);$readmemh(af,ad,0,na-1);$readmemh(xf,extra,0,nx-1);
  repeat(10)@(negedge pix);rst=1;repeat(20)@(negedge pix);
  switch_to(mode==4?1:(mode==5?2:3));
  if(mode==7)begin
   wait(n>=400);@(negedge pix);paused=1;
   repeat(400000)@(negedge pix);
   if(!dut.full||pause_ticks<20)$fatal(1,"production FIFO full/pause not exercised");
   switch_to(1);wait(n>=400);switch_to(3);
  end
  if(mode==8)begin
   repeat(40)@(negedge pix);switch_to(0);
   repeat(2)@(negedge pix);switch_to(2);
   repeat(2)@(negedge pix);switch_to(3);
  end
  if(mode==10)begin
   wait(err!=0);if(err!=8'ha1||n!=0)$fatal(1,"missing-third wrong failure %h",err);
   recovered=1;switch_to(1);
  end
 end
 always @(negedge sd)if(rst)begin
  breq=0;
  if(!bbusy&&brdy&&brst)begin breq=1;bbusy=1;bcount=0;end
  if(bvalid)bcount=bcount+1;
  if(bdone&&bbusy&&bcount==512)begin bsectors=bsectors+1;bbusy=0;end
 end
 always @(posedge pix)if(rst)begin
  cycles=cycles+1;
  if(pv)begin
   if(last_pv!=0&&cycles-last_pv!=154&&cycles-last_pv!=155)$fatal(1,"HDMI cadence gap %0d",cycles-last_pv);
   last_pv=cycles;
   if(paused)begin if({l,rr}!==48'd0)$fatal(1,"paused PCM leakage");pause_ticks=pause_ticks+1;end
   if(ep)begin if(n!=0)$fatal(1,"epoch after payload n=%0d",n);epochs=epochs+1;seen_epoch=1;end
   if({l,rr}!=0&&err==0)begin
    if(paused||!seen_epoch)$fatal(1,"PCM without accepted new-source epoch");
    case(selected)
     1:begin if(n>=nm)$fatal(1,"music length");expected=music[n];end
     2:begin if(n>=na)$fatal(1,"ad length");expected=ad[n];end
     3:begin if(n>=nx)$fatal(1,"extra length");expected=extra[n];end
     default:$fatal(1,"external PCM leaked into demo");
    endcase
    if({l,rr}!==expected)$fatal(1,"PCM mismatch mode=%0d choice=%0d n=%0d actual=%h expected=%h",mode,selected,n,{l,rr},expected);
    n=n+1;
   end
  end
  if(err!=0)begin
   if(mode==2||mode==3)begin
    if(n||epochs||und)$fatal(1,"fault leaked payload");
    if(mode==2&&err!=8'ha1)$fatal(1,"missing file expected A1 got %h",err);
    if(mode==3&&err[7:4]!=9)$fatal(1,"invalid extra WAV expected parser error got %h",err);
    $display("PASS v119 mode=%0d explicit extra-file rejection code=%h samples=%0d",mode,err,n);$finish;
   end else if(mode!=10||recovered)$fatal(1,"unexpected audio error mode=%0d code=%h",mode,err);
  end
  if(finished)begin
   if(mode==2||mode==3)$fatal(1,"missing rejection");
   if(n!=(selected==1?nm:(selected==2?na:nx))||und||err!=0||bsectors<2)$fatal(1,"finish n=%0d code=%h under=%0d bmp=%0d",n,err,und,bsectors);
   if(epochs!=(mode==7?3:1))$fatal(1,"epoch count=%0d",epochs);
   if(mode==10&&!recovered)$fatal(1,"did not recover from missing third");
   $display("PASS v119 mode=%0d choice=%0d exact_PCM_frames=%0d epochs=%0d BMP_sectors=%0d production_FIFO=4096",mode,selected,n,epochs,bsectors);$finish;
  end
  if(cycles>4500000)$fatal(1,"timeout mode=%0d n=%0d choice=%0d state=%0d error=%h",mode,n,choice,dut.reader.state,err);
 end
endmodule
