`timescale 1ns/1ps
// v114: three verified SD sectors -> 4096-frame asynchronous BRAM FIFO
// -> three-slot pixel-domain read-ahead with same-edge arrival forwarding -> exact48k
// pixel-domain cadence. Source reset is asserted to BOTH domains immediately
// on a selection change; each domain then synchronously releases after8 cycles.
// Selection never resets the physical SD host or the HDMI clock/packet engine.
// EOF drains cleanly and stops (not gapless looping in this first WAV release).
module tf_wav_playback #(parameter FIFO_AW=12,PREFILL=3072,LOW_WATER=3584,PIX_HZ=74250000,SAMPLE_HZ=48000)(
 input clk_sd,clk_pix,rst_n,input [1:0] choice,input mounted,input paused,
 input [31:0] root_cluster,data_base,fat_base,cluster_max,input [7:0] spc,input [3:0] shift,
 output bus_reset_n,output read_req,output [31:0] read_lba,output urgent,
 input sd_ready,sd_done,input [3:0] sd_error,input data_valid,input [8:0] data_index,input [7:0] data_byte,
 output reg signed [23:0] left,right,output reg valid,epoch,output reg playing,
 output reg sample_consumed,output wire session_ready,
 output reg underrun,output reg [7:0] error_pix,output reg finished,
 output wire [12:0] audio_used,output reg [12:0] audio_minimum,
 output reg [12:0] first_underflow_used,output reg [7:0] first_underflow_flags);
 wire [1:0] cmd;wire changed,command_pending;
 audio_choice_cdc command(.pclk(clk_pix),.sclk(clk_sd),.rst_n(rst_n),.choice(choice),.sd_choice(cmd),.changed(changed),.pending(command_pending));
 reg [3:0] reset_count;
 always @(posedge clk_sd or negedge rst_n)
 if(!rst_n)reset_count<=0;else if(changed||cmd==0)reset_count<=0;else if(reset_count!=15)reset_count<=reset_count+1'b1;
 // Assert immediately for a new request and hold until the destination
 // acknowledges the mailbox, then wait for the SD reset counter too.
 wire fifo_async_n=rst_n&&(reset_count==15)&&!command_pending&&(choice!=0);
 wire sr,pr;
 assign session_ready=pr;
 reset_release #(.RELEASE_FALLING_EDGE(0)) srst(.clk(clk_sd),.async_n(fifo_async_n),.rst_n(sr));
 reset_release #(.RELEASE_FALLING_EDGE(0)) prst(.clk(clk_pix),.async_n(fifo_async_n),.rst_n(pr));
 wire signed [23:0] sl,srr;wire sv,full,empty;wire [FIFO_AW:0] wu,ru;
 wire [47:0] rd;wire eof,header;wire [7:0] er;wire [31:0] data_size;
 tf_wav_reader reader(.clk(clk_sd),.rst_n(sr),.enable(cmd!=0),.choice(cmd),.mounted(mounted),
 .root_cluster(root_cluster),.data_base(data_base),.fat_base(fat_base),.cluster_max(cluster_max),.spc(spc),.shift(shift),
 .bus_reset_n(bus_reset_n),.read_req(read_req),.read_lba(read_lba),.sd_ready(sd_ready),.sd_done(sd_done),.sd_error(sd_error),
 .data_valid(data_valid),.data_index(data_index),.data_byte(data_byte),.left(sl),.right(srr),.pcm_valid(sv),.pcm_ready(!full),
 .eof(eof),.error_code(er),.header_ok(header),.data_size(data_size));
 // UI pause stops consumption only; it must not revoke low-water refill.
 assign urgent=cmd!=0&&wu<LOW_WATER&&!eof&&er==0;
 // Reserve capacity for the one-cycle synchronous BRAM read response.
 // Three staging slots keep prefetch independent of the 48k sample tick.
 reg [47:0] stage0,stage1,stage2;reg [1:0] staged;
 reg pending;
 wire pop=pr&&error_pix==0&&!empty&&({1'b0,staged}+pending<3);
 wire have=(staged!=0)||pending;
 // If the response arrives at the exact sample edge, consume it directly.
 // The old have register would still be zero on that edge and raised A3.
 wire [47:0] held=staged!=0?stage0:rd;
 reg [26:0] acc;wire [27:0] sum={1'b0,acc}+SAMPLE_HZ;
 wire sample_tick=sum>=PIX_HZ;
 wire consume=sample_tick&&!paused&&playing&&error_pix==0&&have;
 assign audio_used=ru;
 async_fifo #(.WIDTH(48),.AW(FIFO_AW)) samples(.wclk(clk_sd),.wrst_n(sr),.wr_en(sv&&!full&&er==0),.wdata({sl,srr}),.wfull(full),.wused(wu),
 .rclk(clk_pix),.rrst_n(pr),.rd_en(pop),.rdata(rd),.rempty(empty),.rused(ru));
 (* ASYNC_REG="TRUE" *) reg [1:0] ep,hp;reg [7:0] e0,e1,elast;
 reg first_sample;
 // Keep48k HDMI/ACR cadence running with explicit zero samples during mount,
 // rebuffer, switch, EOF and faults. Only accepted real samples drive epoch.
 always @(posedge clk_pix or negedge rst_n)
 if(!rst_n)begin acc<=0;left<=0;right<=0;valid<=0;epoch<=0;sample_consumed<=0;end
 else begin
  valid<=0;epoch<=0;sample_consumed<=0;
  if(sample_tick)begin
   acc<=sum-PIX_HZ;valid<=1;left<=0;right<=0;
   if(pr&&!paused&&playing&&have&&error_pix==0)begin left<=held[47:24];right<=held[23:0];epoch<=first_sample;sample_consumed<=1;end
  end else acc<=sum[26:0];
 end
 always @(posedge clk_pix or negedge pr)
 if(!pr)begin ep<=0;hp<=0;e0<=0;e1<=0;elast<=0;error_pix<=0;end
 else begin ep<={ep[0],eof};hp<={hp[0],header};e0<=er;e1<=e0;elast<=e1;if(e1==elast)error_pix<=e1;end
 // FIFO data is registered on the pop edge; pending qualifies it on the
 // following edge. Pending+staged is bounded by three, including backpressure.
 always @(posedge clk_pix or negedge pr)
 if(!pr)begin pending<=0;staged<=0;stage0<=0;stage1<=0;stage2<=0;end
 else begin
  pending<=pop;
  case({pending,consume})
   2'b10:begin
    case(staged)0:stage0<=rd;1:stage1<=rd;2:stage2<=rd;default:begin end endcase
    staged<=staged+1'b1;
   end
   2'b01:begin stage0<=stage1;stage1<=stage2;staged<=staged-1'b1;end
   2'b11:begin
    case(staged)
     0:begin end // directly forwarded response, not queued twice
     1:stage0<=rd;
     2:begin stage0<=stage1;stage1<=rd;end
     3:begin stage0<=stage1;stage1<=stage2;stage2<=rd;end
    endcase
   end
   default:begin end
  endcase
 end
 always @(posedge clk_pix or negedge pr)
 if(!pr)begin
  playing<=0;underrun<=0;finished<=0;first_sample<=1;
  audio_minimum<=13'h1fff;first_underflow_used<=0;first_underflow_flags<=0;
 end else begin
  if(playing&&sample_tick&&!paused&&ru<audio_minimum)audio_minimum<=ru;
  if(error_pix!=0)playing<=0;
  else if(!playing)begin
   // Require a genuinely available head sample, not merely a nonempty FIFO.
   if(!finished&&hp[1]&&(ru>=PREFILL||ep[1])&&have)playing<=1;
   if(ep[1]&&empty&&!pending&&staged==0)finished<=1;
  end else if(sample_tick&&!paused)begin
   if(have)first_sample<=0;
   else begin
    playing<=0;
    if(ep[1]&&empty&&!pending)finished<=1;
    else begin
     underrun<=1;
     if(!underrun)begin
      first_underflow_used<=ru;
      first_underflow_flags<={hp[1],ep[1],empty,pending,(staged!=0),paused,playing,command_pending};
     end
    end
   end
  end
 end
endmodule
