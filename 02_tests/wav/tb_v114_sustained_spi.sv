`timescale 1ns/1ps
module tb_wav_actual_spi;
 reg clk=0,pix=0,rst=0,brst=0;
 `ifdef PRODUCTION_SPI
 always #10.101010 clk=~clk;always #6.734007 pix=~pix;
 localparam SD_DIV=4;
 `else
 always #10 clk=~clk;always #6.667 pix=~pix;
 localparam SD_DIV=1;
 `endif
 reg paused=0;reg [7:0]letter=8'h41;reg [1:0]choice=1;
 wire miso,mosi,sck,cs;wire hr,hd,hv,hreq;wire[31:0]hl;wire[3:0]he;wire[8:0]hi;wire[7:0]hb;
 wire b_req,b_ready,b_done,bv,ar,a_req,a_ready,a_done,av,urgent;wire[31:0]bl,al;
 wire [3:0]be,ae;wire sdinit,mounted,bmpok;wire[31:0]mb,mf,mm,mr;wire[7:0]ms;wire[3:0]msh;
 reg mount_valid=0;reg[31:0]base,fat,mx,root;reg[7:0]spc;reg[3:0]shift;
 always @(posedge clk)if(!rst)mount_valid<=0;else if(mounted&&!mount_valid)begin mount_valid<=1;base<=mb;fat<=mf;mx<=mm;root<=mr;spc<=ms;shift<=msh;end
 sd_spi_reader #(.HALF_DIV(3),.DATA_HALF_DIV(SD_DIV),.POWER_WAIT_CYCLES(64),.INIT_GAP_CYCLES(16)) cardhost(
 .clk(clk),.rst_n(rst),.miso(miso),.sck(sck),.mosi(mosi),.cs_n(cs),.read_req(hreq),.read_lba(hl),.ready(hr),.init_done(sdinit),.read_done(hd),.error_code(he),.data_valid(hv),.data_index(hi),.data_byte(hb));
 sd_fat_card_model #(.FIXTURE_BLOCKS(256)) card(.rst_n(rst),.cs_n(cs),.sck(sck),.mosi(mosi),.miso(miso));
 media_sd_arbiter arb(.clk(clk),.rst_n(rst),.bmp_reset_n(brst),.aud_reset_n(ar),.audio_urgent(urgent),
 .b_req(b_req),.b_lba(bl),.b_ready(b_ready),.b_done(b_done),.b_valid(bv),.b_error(be),
 .a_req(a_req),.a_lba(al),.a_ready(a_ready),.a_done(a_done),.a_valid(av),.a_error(ae),
 .h_req(hreq),.h_lba(hl),.h_ready(hr),.h_done(hd),.h_valid(hv),.h_error(he),.active(),.owner_audio());
 wire req,done;wire[18:0]addr;wire[127:0]data;reg ack=0;wire[7:0]image_error;
 tf_bus_scaled_loader #(.OUT_WIDTH(32),.OUT_HEIGHT(18),.MAX_WIDTH(2048),.MAX_HEIGHT(2048),.DITHER_ENABLE(1)) image(
 .clk(clk),.rst_n(brst),.file_letter(letter),.enable(1'b1),.ready(b_ready),.read_done(b_done),.dv(bv),.se(be),.di(hi),.db(hb),
 .read_req(b_req),.read_lba(bl),.mount_base(mb),.mount_fat(mf),.mount_max(mm),.mount_root(mr),.mount_spc(ms),.mount_shift(msh),
 .req_valid(req),.req_addr(addr),.req_data(data),.req_ack(ack),.done(done),.error_code(image_error),.mounted(mounted),.bmp_ok(bmpok));
 wire signed[23:0]l,rr;wire pv,ep,playing,und,finished;wire[7:0]aerr;
 `ifdef SHORT_SPI
 localparam FAW=9,PRE=384,LOW=480,SWITCH_AT=128,PHZ=74250000;
 `else
 `ifdef PRODUCTION_SPI
 localparam FAW=12,PRE=3072,LOW=3584,SWITCH_AT=400,PHZ=74250000;
 `else
 localparam FAW=12,PRE=3072,LOW=3584,SWITCH_AT=400,PHZ=18562500;
 `endif
 `endif
 // Short protocol matrix reduces ONLY fixture/FIFO size, keeps wrapping.
 // Default path remains the actual 4096-frame design; accelerated sample
 // cadence is confined to this pin-level TB, not the board implementation.
 tf_wav_playback #(.FIFO_AW(FAW),.PREFILL(PRE),.LOW_WATER(LOW),.PIX_HZ(PHZ)) audio(.clk_sd(clk),.clk_pix(pix),.rst_n(rst),.choice(choice),.mounted(mount_valid),.paused(paused),
 .root_cluster(root),.data_base(base),.fat_base(fat),.cluster_max(mx),.spc(spc),.shift(shift),
 .bus_reset_n(ar),.read_req(a_req),.read_lba(al),.urgent(urgent),.sd_ready(a_ready),.sd_done(a_done),.sd_error(ae),
 .data_valid(av),.data_index(hi),.data_byte(hb),.left(l),.right(rr),.valid(pv),.epoch(ep),.playing(playing),.underrun(und),.error_pix(aerr),.finished(finished));
 reg[7:0] gold_a[0:575],gold_b[0:575];reg[47:0]gold_m[0:8191],gold_ad[0:8191];integer nm,na,mode;
 reg[2047:0]path;integer count=0,epochs=0,writes=0,frames=0,lane,commands;
 reg[35:0]seen=0;reg pending=0;integer delay_ack=0,selected=1;
 initial begin
  if(!$value$plusargs("FIXTURE=%s",path)||!$value$plusargs("NM=%d",nm)||!$value$plusargs("NA=%d",na))$fatal(1,"args");
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  $readmemh({path,"/indexed_a.hex"},gold_a);$readmemh({path,"/indexed_b.hex"},gold_b);
  $readmemh({path,"/music.hex"},gold_m,0,nm-1);$readmemh({path,"/ad.hex"},gold_ad,0,na-1);
  repeat(10)@(negedge clk);rst=1;brst=1;
  if(mode>=2)begin
   wait(count>=SWITCH_AT);@(negedge pix);paused=1;
   begin: pause_evidence
    integer old_count,old_frames,old_cmd0;old_count=count;old_frames=frames;old_cmd0=card.cmd0_count;
    wait(frames>=old_frames+2);repeat(5000)@(negedge pix);
    if(count!=old_count||card.cmd0_count!=old_cmd0||audio.underrun)$fatal(1,"pause consumed audio/reinitialized host/starved BMP");
    if(mode==3)begin choice=2;selected=2;count=0;end
    paused=0;
   end
  end
  if(mode==1)begin wait(count>=SWITCH_AT);@(negedge pix);choice=2;selected=2;count=0;end
 end
 always @(posedge clk)begin
  if(!brst)begin ack<=0;seen<=0;writes<=0;pending<=0;end
  else begin
   if(image_error!=0)$fatal(1,"BMP error %h",image_error);
   if(ack)begin ack<=0;pending<=0;end
   else if(pending)begin if(delay_ack==0)ack<=1;else delay_ack<=delay_ack-1;end
   else if(req)begin
    if(addr>=36||seen[addr])$fatal(1,"duplicate burst %0d",addr);
    for(lane=0;lane<16;lane=lane+1)
     if(data[lane*8+:8]!==((letter==8'h41)?gold_a[addr*16+lane]:gold_b[addr*16+lane]))$fatal(1,"scaled BMP burst mismatch addr=%0d lane=%0d",addr,lane);
    seen[addr]<=1;writes<=writes+1;pending<=1;delay_ack<=writes%11;
   end
  end
 end
 // Repeatedly restart/remount BMP clients without reinitializing the card.
 initial begin
  wait(rst);forever begin wait(done);@(negedge clk);
   if(writes!=36||seen!=36'hfffffffff)$fatal(1,"incomplete BMP writes=%0d",writes);
   frames=frames+1;brst=0;letter=(letter==8'h41)?8'h42:8'h41;
   repeat(8)@(negedge clk);brst=1;
  end
 end
 always @(posedge pix)if(rst)begin
  if(aerr!=0||he!=0)$fatal(1,"audio/host error %h/%h",aerr,he);
  if(pv&&ep)begin epochs=epochs+1;if(count!=0)$fatal(1,"epoch mismatch");end
  if(pv&&paused&&{l,rr}!=0)$fatal(1,"nonzero pin-level paused PCM");
  if(pv&&{l,rr}!=0)begin
   if(selected==1)begin if(count>=nm||{l,rr}!==gold_m[count])$fatal(1,"SPI music mismatch n=%0d",count);end
   else if(count>=na||{l,rr}!==gold_ad[count])$fatal(1,"SPI AD mismatch n=%0d",count);
   count=count+1;
  end
  if(finished)begin
   if(count!=(selected==1?nm:na)||und||frames<2||epochs!=((mode==1||mode==3)?2:1))$fatal(1,"result count=%0d und=%d images=%0d epochs=%0d",count,und,frames,epochs);
   if(card.cmd0_count!=1)$fatal(1,"card was reinitialized during playback");
   $display("PASS actual SPI SDHC/SDSC+fragmented FAT+WAV+BMP bilinear/RGB332:mode=%0d samples=%0d epochs=%0d image_frames=%0d CMD17=%0d CMD0=%0d",mode,count,epochs,frames,card.read_count,card.cmd0_count);$finish;
  end
 end
 initial begin
  $display("SIM init");#100;$display("SIM time100 rst=%b",rst);#1000;$display("SIM time1100");
  repeat(200)begin #1000000;
   $display("SPI progress t=%0t count=%0d frames=%0d cmd17=%0d host=%0d arb=%b owner=%b bmp=%0d wav=%0d err=%h",$time,count,frames,card.read_count,cardhost.state,arb.active,arb.owner_audio,image.source.source.probe.state,audio.reader.state,aerr);
  end
 end
 initial begin #300000000;$fatal(1,"SPI timeout");end
endmodule
