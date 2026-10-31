`timescale 1ns/1ps
module tb_v116_refill_budget;
 reg sd=0,pix=0,rst=0;always #10.101 sd=~sd;always #6.734 pix=~pix;
 reg [1:0] choice=0;reg paused=0;
 wire ar,areq,ardy,adone,av,urgent;wire [31:0] al;
 wire [3:0] ae,he,be;wire hr,hd,hv,hreq;wire[31:0]hl;
 wire[8:0]hi;wire[7:0]hb;wire signed [23:0] l,r;
 wire pv,ep,playing,und,finished;wire[7:0]err;
 wire [12:0] aq,amin,firstq;wire[7:0]firsts;
 reg b_req=0;wire bready,bdone,bvalid;reg bbusy=0;integer bbytes=0,bsectors=0;
 integer nm,spc_arg,shift_arg,with_bmp,expect_under,mode,n=0,cycles=0,epochs=0;
 integer adata=0,afat=0,bmp=0,urgent_bmp=0,first_under_n=-1,play_at=-1;
 reg [2047:0]mf;reg[47:0]music[0:40000];
 tf_wav_playback #(.PIX_HZ(4640625))dut(
 .clk_sd(sd),.clk_pix(pix),.rst_n(rst),.choice(choice),.mounted(1'b1),.paused(paused),
 .root_cluster(32'd2),.data_base(32'd600),.fat_base(32'd32),.cluster_max(32'd70000),.spc(spc_arg[7:0]),.shift(shift_arg[3:0]),
 .bus_reset_n(ar),.read_req(areq),.read_lba(al),.urgent(urgent),.sd_ready(ardy),.sd_done(adone),.sd_error(ae),
 .data_valid(av),.data_index(hi),.data_byte(hb),.left(l),.right(r),.valid(pv),.epoch(ep),
 .playing(playing),.underrun(und),.error_pix(err),.finished(finished),
 .audio_used(aq),.audio_minimum(amin),.first_underflow_used(firstq),.first_underflow_flags(firsts));
 `ifdef BASELINE
 media_sd_arbiter_v114
 `else
 media_sd_arbiter
 `endif
 arb(.clk(sd),.rst_n(rst),.bmp_reset_n(rst),.aud_reset_n(ar),.audio_urgent(urgent),
 .b_req(b_req),.b_lba(32'd999999),.b_ready(bready),.b_done(bdone),.b_valid(bvalid),.b_error(be),
 .a_req(areq),.a_lba(al),.a_ready(ardy),.a_done(adone),.a_valid(av),.a_error(ae),
 .h_req(hreq),.h_lba(hl),.h_ready(hr),.h_done(hd),.h_valid(hv),.h_error(he),.active(),.owner_audio());
 v116_budget_host host(.clk(sd),.rst_n(rst),.req(hreq),.lba(hl),.ready(hr),.done(hd),.valid(hv),.index(hi),.data(hb),.error(he));
 initial begin
  if(!$value$plusargs("MUSIC=%s",mf)||!$value$plusargs("NM=%d",nm)||!$value$plusargs("SPC=%d",spc_arg)||!$value$plusargs("SHIFT=%d",shift_arg)||!$value$plusargs("BMP=%d",with_bmp)||!$value$plusargs("UNDER=%d",expect_under))$fatal(1,"args");
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  $readmemh(mf,music,0,nm-1);
  repeat(12)@(negedge pix);rst=1;repeat(20)@(negedge pix);choice=1;
  if(mode==1)begin
   wait(n>=4700);@(negedge pix);paused=1;repeat(40000)@(negedge pix);
   if(dut.wu<3584)$fatal(1,"pause refill not sustained");paused=0;
  end
 end
 always @(negedge sd)if(rst)begin
  b_req=0;
  if(with_bmp&&!bbusy&&bready)begin b_req=1;bbusy=1;bbytes=0;end
  if(bvalid)bbytes=bbytes+1;
  if(bdone&&bbusy&&bbytes==512)begin bsectors=bsectors+1;bbusy=0;end
  if(hreq)begin
   if(hl==999999)begin bmp=bmp+1;if(urgent)urgent_bmp=urgent_bmp+1;end
   else if(hl>=32&&hl<600)afat=afat+1;else adata=adata+1;
  end
 end
 always @(posedge pix)if(rst)begin
  cycles=cycles+1;
  if(playing&&play_at==-1)play_at=cycles;
  if(und&&first_under_n==-1)begin
   first_under_n=n;$display("FIRST_A3 n=%0d Q=%0d S=%02h play_cycles=%0d audio_data=%0d fat=%0d bmp=%0d urgent_bmp=%0d",n,firstq,firsts,cycles-play_at,adata,afat,bmp,urgent_bmp);
  end
  if(err!=0)$fatal(1,"reader error %h",err);
  if(pv&&{l,r}!=0)begin
   if(n>=nm||{l,r}!==music[n])$fatal(1,"PCM mismatch n=%0d",n);n=n+1;
  end
  if(pv&&ep)epochs=epochs+1;
  if(finished)begin
   if(n!=nm||und!==expect_under[0]||epochs!=1||with_bmp&&bsectors<3)$fatal(1,"result n=%0d under=%b expected=%0d epochs=%0d bmp=%0d",n,und,expect_under,epochs,bsectors);
   $display("PASS refill-budget SPC=%0d BMP=%0d samples=%0d A3=%0d first_under_n=%0d MIN=%0d audio_data=%0d FAT=%0d BMP=%0d urgent_BMP=%0d",spc_arg,with_bmp,n,und,first_under_n,amin,adata,afat,bmp,urgent_bmp);$finish;
  end
  if(cycles>14000000)$fatal(1,"timeout n=%0d state=%0d",n,dut.reader.state);
 end
endmodule
