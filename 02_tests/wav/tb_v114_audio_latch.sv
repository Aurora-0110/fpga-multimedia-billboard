`timescale 1ns/1ps
// Deliberately accelerated consumer cadence; sector-transport abstraction,
// NOT an SD electrical, 720p whole-system or PVT test.
module tb_v114_audio_latch;
 reg sd=0,pix=0,rst=0;always #6.734 sd=~sd;always #5 pix=~pix;
 reg [1:0] choice=0;reg paused=0,stall=0;
 wire ar,areq,ardy,adone,av,urgent;wire [31:0] al;
 wire [3:0] ae,he,be;wire hr,hd,hv,hreq;wire[31:0]hl,active_lba,transactions;
 wire[8:0]hi;wire[7:0]hb;wire signed [23:0] l,r;
 wire pv,ep,playing,und,finished;wire[7:0]err;
 reg b_req=0;wire bready,bdone,bvalid;reg bbusy=0;integer bbytes=0,bsectors=0;
 integer mode,n=0,nm,na,cycles=0,ticks=0,epochs=0,overlaps=0,max_used=0,checked=0;
 reg[2047:0]mf,af;reg[47:0]music[0:16383];reg[47:0]ad[0:16383];
 reg[31:0]bad_lba=32'hffffffff;reg[1:0]bad_kind=0;
 reg expect_under=0;reg under_while_stall=0;integer stall_ticks=0,min_stall_used=100000,selected=1;
 `ifdef BASELINE
 localparam AW=11,PRE=1024,LOW=1536,TARGET=1850;
 `else
 localparam AW=12,PRE=3072,LOW=3584,TARGET=3500;
 `endif
 tf_wav_playback #(.FIFO_AW(AW),.PREFILL(PRE),.LOW_WATER(LOW),.PIX_HZ(14850000))dut(
 .clk_sd(sd),.clk_pix(pix),.rst_n(rst),.choice(choice),.mounted(1'b1),.paused(paused),
 .root_cluster(32'd2),.data_base(32'd600),.fat_base(32'd32),.cluster_max(32'd70000),.spc(8'd1),.shift(4'd0),
 .bus_reset_n(ar),.read_req(areq),.read_lba(al),.urgent(urgent),.sd_ready(ardy),.sd_done(adone),.sd_error(ae),
 .data_valid(av),.data_index(hi),.data_byte(hb),.left(l),.right(r),.valid(pv),.epoch(ep),.playing(playing),.underrun(und),.error_pix(err),.finished(finished));
 media_sd_arbiter arb(.clk(sd),.rst_n(rst),.bmp_reset_n(rst),.aud_reset_n(ar),.audio_urgent(urgent),
 .b_req(b_req),.b_lba(32'd999999),.b_ready(bready),.b_done(bdone),.b_valid(bvalid),.b_error(be),
 .a_req(areq),.a_lba(al),.a_ready(ardy),.a_done(adone),.a_valid(av),.a_error(ae),
 .h_req(hreq),.h_lba(hl),.h_ready(hr),.h_done(hd),.h_valid(hv),.h_error(he),.active(),.owner_audio());
 wav_block_stall_model host(.clk(sd),.rst_n(rst),.stall(stall),.req(hreq),.lba(hl),.bad_lba(bad_lba),.bad_kind(bad_kind),
 .ready(hr),.done(hd),.valid(hv),.index(hi),.data(hb),.error(he),.active_lba(active_lba),.transactions(transactions));
 initial begin
  if(!$value$plusargs("MODE=%d",mode)||!$value$plusargs("MUSIC=%s",mf)||!$value$plusargs("AD=%s",af)||!$value$plusargs("NM=%d",nm)||!$value$plusargs("NA=%d",na))$fatal(1,"args");
  $readmemh(mf,music,0,nm-1);$readmemh(af,ad,0,na-1);
  expect_under=(mode==2);
  `ifdef BASELINE
  if(mode==1)expect_under=1;
  `endif
  if(mode==1||mode==2)paused=1;
  repeat(12)@(negedge pix);rst=1;repeat(20)@(negedge pix);choice=1;
  if(mode==1||mode==2)begin
   wait(dut.full);@(negedge pix);paused=0;
   wait(n>=700);@(negedge sd);stall=1;
   repeat(mode==1?2640:5200)begin @(negedge pix);while(!pv)@(negedge pix);stall_ticks=stall_ticks+1;end
   @(negedge sd);stall=0;
  end
  if(mode==3)begin
   wait(n>=700);@(negedge pix);paused=1;repeat(700000)@(negedge pix);
   if(!dut.full)$fatal(1,"did not fill PCM FIFO on pause");
   `ifndef BASELINE
   if(dut.reader.stream.queued!=3)$fatal(1,"did not fill all three sector banks");
   `endif
   paused=0;
  end
  if(mode==4)begin
   wait(n>=700);@(negedge pix);paused=1;repeat(700000)@(negedge pix);
   choice=2;selected=2;n=0;paused=0;
  end
 end
 always @(negedge sd)if(rst)begin
  b_req=0;
  if(!bbusy&&bready)begin b_req=1;bbusy=1;bbytes=0;end
  if(bvalid)bbytes=bbytes+1;
  if(bdone&&bbusy&&bbytes==512)begin bsectors=bsectors+1;bbusy=0;end
  if(dut.wu>max_used)max_used=dut.wu;
  `ifndef BASELINE
  if(host.active&&arb.owner_audio&&dut.reader.stream.byte_valid&&dut.reader.stream.byte_ready)overlaps=overlaps+1;
  if(dut.reader.stream.queued>3)$fatal(1,"sector queue overflow");
  if(dut.reader.stream.state==8&&!dut.reader.stream.kind_fat&&dut.reader.stream.queued==3)$fatal(1,"write into full queue");
  `endif
 end
 integer last_tick=0;
 always @(posedge pix)if(rst)begin
  cycles=cycles+1;
  if(stall&&und)under_while_stall=1;
  if(pv)begin
   ticks=ticks+1;
   if(last_tick!=0&&cycles-last_tick!=309&&cycles-last_tick!=310)$fatal(1,"48k cadence broken");
   last_tick=cycles;
   if(stall&&dut.ru<min_stall_used)min_stall_used=dut.ru;
   if(paused&&{l,r}!==48'd0)$fatal(1,"nonzero PCM in pause");
   if(ep)begin epochs=epochs+1;if(n!=0)$fatal(1,"epoch midtrack");end
   if({l,r}!=0&&err==0)begin
    if(selected==1)begin if(n>=nm||{l,r}!==music[n])$fatal(1,"music mismatch n=%0d got=%h",n,{l,r});end
    else if(n>=na||{l,r}!==ad[n])$fatal(1,"AD mismatch n=%0d got=%h",n,{l,r});
    n=n+1;checked=checked+1;
   end
  end
  if(err!=0)$fatal(1,"reader fault %h",err);
  if(und&&!expect_under)$fatal(1,"unexpected underrun n=%0d wu=%0d stall_ticks=%0d",n,dut.wu,stall_ticks);
  if(und)begin
   if(dut.first_underflow_used!==13'd0||dut.first_underflow_flags!==8'ha2||dut.audio_minimum!==13'd0)
    $fatal(1,"first underflow evidence changed used=%h flags=%h min=%h",dut.first_underflow_used,dut.first_underflow_flags,dut.audio_minimum);
  end
  if(finished)begin
   if((mode==1||mode==2)&&stall_ticks!=(mode==1?2640:5200))$fatal(1,"stall injection did not complete");
   if((mode==1||mode==2)&&under_while_stall!==expect_under)$fatal(1,"gap-fault timing mismatch under_in_gap=%b expected=%b",under_while_stall,expect_under);
   if(n!=(selected==1?nm:na)||und!==expect_under||bsectors<3||epochs!=(mode==4?2:1))$fatal(1,"result n=%0d under=%b expect=%b BMP=%0d epochs=%0d",n,und,expect_under,bsectors,epochs);
   `ifndef BASELINE
   // Explicit overlap is required by the separate prefetch byte-level test.
   // A particular PCM/backpressure workload is allowed not to overlap.
   `endif
   $display("PASS first-A3 snapshot/rebuffer sticky audit mode=%0d AW=%0d checked=%0d under=%0d stall_ticks=%0d min_stall_used=%0d max_used=%0d overlaps=%0d bmp=%0d",mode,AW,checked,und,stall_ticks,min_stall_used,max_used,overlaps,bsectors);$finish;
  end
  if(cycles>14000000)$fatal(1,"timeout n=%0d queued=%0d",n,dut.wu);
 end
endmodule