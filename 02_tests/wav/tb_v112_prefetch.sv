`timescale 1ns/1ps
module tb_v112_prefetch;
 `include "prefetch_meta.vh"
 reg clk=0,rst=0,start=0;always #5 clk=~clk;
 wire req,ready,sdone,dv,bv,done;wire[31:0]lba,pos,active_lba,transactions;
 wire[3:0]se,err;wire[8:0]di;wire[7:0]db,bd;
 reg br=0;integer ticks=0,n=0,overlap=0,full_banks=0;reg[31:0]rng=32'hbc89321;
 reg[7:0]gold[0:GOLDN-1];initial $readmemh("gold.hex",gold);
 fat32_audio_prefetch #(.TIMEOUT(20000))dut(.clk(clk),.rst_n(rst),.start(start),.directory_mode(DIR),
 .start_cluster(CL),.file_size(FS),.data_base(BASE),.fat_base(32'd32),.cluster_max(32'd70000),.spc(SPC),.shift(SHIFT),
 .read_req(req),.read_lba(lba),.sd_ready(ready),.sd_done(sdone),.sd_error(se),.data_valid(dv),.data_index(di),.data_byte(db),
 .byte_valid(bv),.byte_ready(br),.byte_data(bd),.position(pos),.done(done),.error_code(err));
 wav_block_stall_model #(.GAP(2))host(.clk(clk),.rst_n(rst),.req(req),.stall(1'b0),.lba(lba),.bad_lba(BADLBA),.bad_kind(BADKIND),
 .ready(ready),.done(sdone),.valid(dv),.index(di),.data(db),.error(se),.active_lba(active_lba),.transactions(transactions));
 initial begin repeat(10)@(negedge clk);rst=1;start=1;end
 always @(negedge clk)begin
  rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
  // Long initial hold fills BOTH banks before consumption begins.
  br=(ticks>6000)&&(rng[2:0]!=0);
 end
 reg prev_stall=0;reg[7:0]last_data;reg[31:0]last_pos;
 always @(posedge clk)if(rst)begin
  ticks=ticks+1;
  if(prev_stall&&!done&&(bd!==last_data||pos!==last_pos))$fatal(1,"byte not stable under backpressure");
  prev_stall=bv&&!br;last_data=bd;last_pos=pos;
  if(dut.queued==2)full_banks=full_banks+1;
  if(dut.queued>2)$fatal(1,"queue overflow");
  if(dut.state==8&&!dut.kind_fat&&dut.queued==2)$fatal(1,"bank overwrite");
  if(bv&&br)begin
   if(n>=GOLDN||bd!==gold[n]||pos!=n)$fatal(1,"data n=%0d pos=%0d got=%h expected=%h",n,pos,bd,gold[n]);
   n=n+1;
   if(host.active)overlap=overlap+1;
  end
  if(done)begin
   if(err!==EXPECT||n>MAXN||(EXPECT==0&&n!=MAXN))$fatal(1,"end err=%h expect=%h n=%0d max=%0d",err,EXPECT,n,MAXN);
   if(EXPECT==0&&MAXN>1024&&overlap==0)$fatal(1,"no overlap");
   $display("PASS prefetch bytes=%0d error=%h overlap=%0d full=%0d sectors=%0d",n,err,overlap,full_banks,transactions);$finish;
  end
  if(ticks>3000000)$fatal(1,"timeout n=%0d state=%0d",n,dut.state);
 end
endmodule