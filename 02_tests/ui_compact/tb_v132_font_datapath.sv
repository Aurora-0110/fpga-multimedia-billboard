`timescale 1ns/1ps
module tb_v132_font_datapath;
 reg clk=0;always #5 clk=~clk;
 reg rst=0;reg [15:0] oracle[0:2047];reg [1023:0] fp;
 integer g,y,x,ov,checks=0;reg expected;
 media_ui_overlay d(.clk(clk),.rst_n(rst),.x(12'd1),.y(12'd0),.rgb(24'h123456),
 .de(1'b0),.hs(1'b1),.vs(1'b1),.picture_visible(1'b1),.keys_down(2'b0),
 .brightness(8'sd0),.contrast_q2(3'd4),.volume_level(4'd10),.edit_field(2'd0),
 .auto_mode(1'b1),.overlays_enabled(1'b1),.av_enabled(1'b1),.image_index(2'd0),
 .loading(1'b0),.load_failed(1'b0),.tf_error(8'd0),.audio_error(8'd0),.audio_active(1'b0),
 .audio_select(1'b0),.audio_paused(1'b0),.ui_toggle(1'b0),.audio_choice(2'd0),.audio_status(3'd0));
 initial begin
  if(!$value$plusargs("FONT=%s",fp))$fatal(1,"FONT required");
  $readmemh(fp,oracle);#23;rst=1;
  repeat(4)@(negedge clk);
  // Only the internal FONT stage inputs are deposited by this white-box unit.
  // Full input-to-RGB latency/state is independently checked in tb_v132_ui.
  for(ov=0;ov<2;ov=ov+1)for(g=0;g<128;g=g+1)for(y=0;y<16;y=y+1)for(x=0;x<16;x=x+1)begin
   @(negedge clk);
   d.override1=ov;d.text_glyph1=ov?(g^127):g;
   d.override_glyph1=ov?g:(g^127);d.font_y1=y;d.font_x1=x;
   expected=oracle[g*16+y][15-x];
   @(posedge clk);#1;
   if(d.font_pixel2!==expected)$fatal(1,"FONT datapath g=%0d xy=%0d,%0d override=%0d pixel=%b expected=%b word=%0d bit=%0d bank=%0d",g,x,y,ov,d.font_pixel2,expected,d.font_word1,d.font_bit2,d.font_bank2);
   checks=checks+1;
  end
  if(checks!=65536)$fatal(1,"missing exhaustive checks");
  $display("PASS V132 runtime UI font datapath checks=%0d; all128x16x16 coordinates, normal+dynamic override; unchanged glyph pixels",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
