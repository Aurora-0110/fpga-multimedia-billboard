`timescale 1ns/1ps
// One persistent host, sector-atomic ownership. Each client has ONE queued slot.
// Ready drops immediately on request capture, even for a losing simultaneous
// request. Resetting a client cancels queued work and drains active work safely.
module media_sd_arbiter #(parameter integer REFILL_GRACE_CYCLES=32)(
 input clk,rst_n, bmp_reset_n,aud_reset_n,audio_urgent,
 input b_req,input [31:0] b_lba,output b_ready,b_done,b_valid,
 input a_req,input [31:0] a_lba,output a_ready,a_done,a_valid,
 output [3:0] b_error,a_error,
 output reg h_req,output reg [31:0] h_lba,
 input h_ready,h_done,h_valid,input [3:0] h_error,
 output reg active,output reg owner_audio);
 // A client cannot queue its next LBA until its just-completed sector
 // propagates through READ/NEXT/address/FAT states. Without this bounded
 // reservation, pending BMP wins that bubble even while audio is urgent,
 // defeating low-water priority at EVERY sector boundary. Never wait
 // indefinitely: mount/decode/backpressure may legitimately have no request.
 localparam GW=REFILL_GRACE_CYCLES>0?$clog2(REFILL_GRACE_CYCLES+1):1;
 reg [GW-1:0] refill_wait;
 wire reserve_audio=audio_urgent&&aud_reset_n&&refill_wait<REFILL_GRACE_CYCLES;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)refill_wait<=0;
 else if(active||!h_ready||!audio_urgent||!aud_reset_n)refill_wait<=0;
 else if(refill_wait<REFILL_GRACE_CYCLES)refill_wait<=refill_wait+1'b1;
 reg bp,ap,initialized;reg [31:0] bl,al;reg issued,discard,br,ar;
 assign b_ready=initialized&&bmp_reset_n&&!bp&&!(active&&!owner_audio);
 assign a_ready=initialized&&aud_reset_n&&!ap&&!(active&&owner_audio);
 assign b_done=br;assign a_done=ar;
 assign b_valid=h_valid&&active&&!owner_audio&&!discard&&bmp_reset_n;
 assign a_valid=h_valid&&active&&owner_audio&&!discard&&aud_reset_n;
 assign b_error=bmp_reset_n?h_error:4'd0;
 assign a_error=aud_reset_n?h_error:4'd0;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin initialized<=0;bp<=0;ap<=0;bl<=0;al<=0;active<=0;owner_audio<=0;issued<=0;discard<=0;h_req<=0;h_lba<=0;br<=0;ar<=0;end
 else begin
  h_req<=0;if(h_ready)initialized<=1;
  if(!bmp_reset_n)begin bp<=0;br<=0;end
  else if(b_req&&b_ready)begin bp<=1;bl<=b_lba;br<=0;end
  if(!aud_reset_n)begin ap<=0;ar<=0;end
  else if(a_req&&a_ready)begin ap<=1;al<=a_lba;ar<=0;end
  if(active)begin
   if(owner_audio?!aud_reset_n:!bmp_reset_n)discard<=1;
   // A host request is first seen one cycle later. Require its ready-fall
   // before accepting the sticky read_done left over from the previous sector.
   if(!h_ready)issued<=1;
   if(issued&&((h_ready&&h_done)||h_error!=0))begin
    active<=0;issued<=0;
    if(!discard)begin
     if(owner_audio&&aud_reset_n)ar<=1;
     if(!owner_audio&&bmp_reset_n)br<=1;
    end
   end
  end else if(h_ready&&h_error==0)begin
   if(ap&&aud_reset_n&&(audio_urgent||!bp||!bmp_reset_n))begin
    owner_audio<=1;ap<=0;h_lba<=al;h_req<=1;active<=1;discard<=0;issued<=0;
   end else if(bp&&bmp_reset_n&&!reserve_audio)begin
    owner_audio<=0;bp<=0;h_lba<=bl;h_req<=1;active<=1;discard<=0;issued<=0;
   end else if(ap&&aud_reset_n)begin
    owner_audio<=1;ap<=0;h_lba<=al;h_req<=1;active<=1;discard<=0;issued<=0;
   end
  end
 end
endmodule
