`timescale 1ns/1ps
// End-to-end reduced frame: actual SPI host, FAT/BMP/scaler, loader, physical
// SDRAM bus model, paired async FIFO and display. No forced datapath signals.
module tb_scaled_spi_memory;
 reg sd=0,pc=0,rst=0,front=0,loader_rst=0;
 always #10.101 sd=~sd;always #6.734007 pc=~pc;
 wire miso,mosi,sck,cs_n,lv,ldone,ack;wire [18:0] la;wire [127:0] wd;wire [7:0] err;
 wire sd_init,mounted,bmp_ok,init;
 tf_scaled_loader #(.OUT_WIDTH(32),.OUT_HEIGHT(18),.HALF_DIV(2),.DATA_HALF_DIV(1),.POWER_WAIT_CYCLES(16),.INIT_GAP_CYCLES(4)) loader(
 .clk(sd),.rst_n(loader_rst),.file_letter(8'h41),.enable(init),.miso(miso),.cs_n(cs_n),.sck(sck),.mosi(mosi),
 .req_valid(lv),.req_addr(la),.req_data(wd),.req_ack(ack),.done(ldone),.error_code(err),.sd_init(sd_init),.mounted(mounted),.bmp_ok(bmp_ok));
 sd_fat_card_model card(.rst_n(loader_rst),.cs_n(cs_n),.sck(sck),.mosi(mosi),.miso(miso));
 wire [11:0] x,y;wire hs,vs,de,fs;
 video_timing #(.H_ACTIVE(32),.H_FP(8),.H_SYNC(4),.H_BP(8),.V_ACTIVE(18),.V_FP(5),.V_SYNC(5),.V_BP(20)) timing(pc,rst,x,y,hs,vs,de,fs);
 wire td,dd,hd,vd,run,fault,vis,of,cke,cs,ras,cas,we,oe;
 wire [23:0] rgb;wire [1:0] idx;wire [5:0] step;wire [10:0] ma;wire [1:0] ba;wire [3:0] dm;wire [31:0] dout;tri [31:0] dq;assign dq=oe?dout:32'bz;
 idx_pair_pipeline #(.WIDTH(32),.HEIGHT(18),.TRANSITION_STEPS(2),.PREFILL_PAIRS(16)) pipe(
 .clk_sd(sd),.clk_pix(pc),.rst_sd_n(rst),.rst_pix_n(rst),.front_valid(front),.dest_bank(1'b0),.transition_request(1'b0),.target_index(2'd0),.transition_done(td),
 .frame_start(fs),.de(de),.hs(~hs),.vs(~vs),.window(de),.load_valid(lv),.load_addr(la),.load_data(wd),.load_ack(ack),
 .rgb(rgb),.de_d(dd),.hs_d(hd),.vs_d(vd),.init_done(init),.display_running(run),.display_fault(fault),.picture_visible(vis),.overflow_fault(of),.displayed_index(idx),.displayed_step(step),
 .mem_cke(cke),.mem_cs_n(cs),.mem_ras_n(ras),.mem_cas_n(cas),.mem_we_n(we),.mem_addr(ma),.mem_ba(ba),.mem_dm(dm),.dq_out(dout),.dq_oe(oe),.dq_in(dq));
 IS42s32200 mem(.Clk(sd),.Cke(cke),.Cs_n(cs),.Ras_n(ras),.Cas_n(cas),.We_n(we),.Addr(ma),.Ba(ba),.Dqm(dm),.Dq(dq));
 reg [7:0] expected[0:575];integer expected_error,retry=0,pixels=0,writes=0,epochs=0,xx,yy;
 reg emit;string fixture;
 function [23:0] expand(input [7:0] c);begin expand={c[7:5],c[7:5],c[7:6],c[4:2],c[4:2],c[4:3],c[1:0],c[1:0],c[1:0],c[1:0]};end endfunction
 always @(posedge sd)if(rst)begin
  if(ack)writes=writes+1;
  if(ldone&&err!=0)$fatal(1,"bad scaled frame reported success");
  if(front&&!ldone)$fatal(1,"frame published before loader completed");
 end
 always @(posedge pc)if(rst&&pipe.prst)begin
  if(fault||of)$fatal(1,"scaled chain pipeline fault");
  if(!front&&vis)$fatal(1,"partial frame visible");
  emit=pipe.display.consume;xx=x;yy=y;
  #0.002;
  if(emit)begin
   if(rgb!==expand(expected[yy*32+xx])||idx!=0||step!=0||!vis)$fatal(1,"scaled SPI/memory pixel xy=%0d,%0d got=%h exp=%h",xx,yy,rgb,expand(expected[yy*32+xx]));
   pixels=pixels+1;
  end
 end
 task once;begin
  @(negedge sd);front=0;rst=0;loader_rst=0;pixels=0;writes=0;
  repeat(8)@(negedge sd);rst=1;loader_rst=1;
  wait(ldone||err!=0);
  if(err!=expected_error)$fatal(1,"scaled chain error got=%h exp=%h",err,expected_error);
  if(expected_error==0)begin
   if(writes!=36||!sd_init||!mounted||!bmp_ok)$fatal(1,"scaled chain incomplete load");
   @(negedge sd);front=1;
   wait(pixels>=576*2);@(negedge pc);
   if(!run||!vis||fault||of||pipe.ctrl.refresh_count==0)$fatal(1,"scaled chain no continuous display/refresh");
  end else begin
   repeat(300)@(negedge pc);
   if(front||run||vis||ldone)$fatal(1,"bad scaled frame published");
  end
  epochs=epochs+1;
  $display("PASS scaled_spi_memory epoch=%0d err=%h writes=%0d pixels=%0d physical_bus_model",epochs,err,writes,pixels);
 end endtask
 initial begin
  if(!$value$plusargs("FIXTURE=%s",fixture))$fatal(1,"missing fixture");
  if(!$value$plusargs("ERROR=%d",expected_error))expected_error=0;
  if(!$value$plusargs("RETRY=%d",retry))retry=0;
  $readmemh({fixture,"/indexed.hex"},expected,0,575);
  once();if(retry)once();$finish;
 end
 initial begin #20000000;$fatal(1,"scaled SPI memory watchdog");end
endmodule
