`timescale 1ns/1ps
// v105: centered Chinese two-column rounded translucent 720p UI.
// Lightweight glass tint/highlights only: no blur/refraction/framebuffer or new CPU.
// Compact synchronous text/font ROMs; no runtime filesystem or external processor.
// No raw-key sampling here: keys_down is debounced in picture_controls_osd.
// Four fully aligned video stages; showing this UI never raises picture_visible.
module ui_help_overlay #(parameter TIMEOUT_FRAMES=360)(
 input wire clk,rst_n,input wire [11:0] x,y,input wire [23:0] rgb,
 input wire de,hs,vs,picture_visible,input wire [1:0] keys_down,
 input wire signed [7:0] brightness,input wire [2:0] contrast_q2,
 input wire [1:0] edit_field,input wire auto_mode,overlays_enabled,
 input wire [1:0] image_index,input wire loading,load_failed,
 input wire [7:0] tf_error,input wire audio_active,
 output reg [11:0] x_out,y_out,output reg [23:0] rgb_out,
 output reg de_out,hs_out,vs_out,picture_visible_out,output reg ui_visible);
 localparam CW=TIMEOUT_FRAMES>1?$clog2(TIMEOUT_FRAMES+1):1;
 wire tick=de&&x==0&&y==0;
 reg [CW-1:0] remaining;
 reg pending;
 reg [1:0] previous_keys,last_key;
 reg signed [7:0] previous_brightness;
 reg [2:0] previous_contrast;
 reg [1:0] previous_field;
 reg previous_overlays,previous_auto;
 wire key_change=keys_down!=previous_keys;
 wire action=key_change || brightness!=previous_brightness || contrast_q2!=previous_contrast ||
             edit_field!=previous_field || overlays_enabled!=previous_overlays || auto_mode!=previous_auto;
 reg signed [7:0] shown_brightness;
 reg [2:0] shown_contrast;
 reg [1:0] shown_field,shown_keys,shown_last,shown_image;
 reg shown_auto,shown_overlays,shown_loading,shown_failed,shown_video,shown_audio;
 reg [7:0] shown_error;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  remaining<=TIMEOUT_FRAMES;pending<=0;ui_visible<=1;
  previous_keys<=0;last_key<=0;previous_brightness<=0;previous_contrast<=4;
  previous_field<=0;previous_overlays<=1;previous_auto<=1;
  shown_brightness<=0;shown_contrast<=4;shown_field<=0;shown_keys<=0;shown_last<=0;shown_image<=0;
  shown_auto<=1;shown_overlays<=1;shown_loading<=1;shown_failed<=0;shown_error<=0;shown_video<=0;shown_audio<=0;
 end else begin
  previous_keys<=keys_down;previous_brightness<=brightness;previous_contrast<=contrast_q2;
  previous_field<=edit_field;previous_overlays<=overlays_enabled;previous_auto<=auto_mode;
  if(key_change&&keys_down!=0&&(previous_keys==0||keys_down==3))last_key<=keys_down;
  if(action)pending<=1;
  if(tick)begin
   // Snapshot all rows only once per frame. Auto slide changes do not wake UI.
   shown_brightness<=brightness;shown_contrast<=contrast_q2;shown_field<=edit_field;
   shown_keys<=keys_down;shown_last<=(key_change&&keys_down!=0&&(previous_keys==0||keys_down==3))?keys_down:last_key;
   shown_image<=image_index;shown_auto<=auto_mode;shown_overlays<=overlays_enabled;
   shown_loading<=loading;shown_failed<=load_failed||(tf_error!=0);shown_error<=tf_error;
   shown_video<=picture_visible;shown_audio<=audio_active;
   pending<=0;
   if(pending||action||keys_down!=0||edit_field!=0||load_failed||tf_error!=0)begin
    remaining<=TIMEOUT_FRAMES;ui_visible<=1;
   end else if(remaining>1)begin remaining<=remaining-1'b1;ui_visible<=1;end
   else begin remaining<=0;ui_visible<=0;end
  end
 end

 `include "visual/ui_zh_glyph_ids.vh"
 // Both ROM ports are synchronous and intentionally have no asynchronous reset.
 // Valid/control tags are reset in the video pipeline, so unknown startup ROM
 // output cannot leak onto the output. Embedded initializers avoid cwd paths.
 (* rom_style="block" *) reg [6:0] text_memory[0:1023];
 (* rom_style="block" *) reg [15:0] font_memory[0:2047];
 initial begin
  `include "visual/ui_zh_text_init.vh"
 end
 initial begin
  `include "visual/ui_zh_font_init.vh"
 end
 function [6:0] digit_glyph;input [3:0] v;begin
  digit_glyph=v<10?G_0030+v:G_003F;
 end endfunction
 function [6:0] hex_glyph;input [3:0] v;begin
  hex_glyph=v<10?G_0030+v:G_0041+v-10;
 end endfunction
 function [6:0] bright_tens;input signed [7:0] v;reg [7:0] m;begin
  m=v[7]?-v:v;case(m)
   0:bright_tens=G_0030;16:bright_tens=G_0031;32:bright_tens=G_0033;
   48:bright_tens=G_0034;64:bright_tens=G_0036;default:bright_tens=G_003F;
  endcase
 end endfunction
 function [6:0] bright_ones;input signed [7:0] v;reg [7:0] m;begin
  m=v[7]?-v:v;case(m)
   0:bright_ones=G_0030;16:bright_ones=G_0036;32:bright_ones=G_0032;
   48:bright_ones=G_0038;64:bright_ones=G_0034;default:bright_ones=G_003F;
  endcase
 end endfunction
 function [6:0] label_message;input [3:0] row;begin
  case(row)
   0:label_message=1;1:label_message=3;2:label_message=5;
   3:label_message=8;4:label_message=10;5:label_message=15;
   6:label_message=19;7:label_message=21;8:label_message=23;
   9:label_message=26;10:label_message=29;11:label_message=34;
   12:label_message=38;13:label_message=42;default:label_message=0;
  endcase
 end endfunction
 function [5:0] state_message;input [3:0] row;begin
  case(row)
   0:state_message=2;1:state_message=4;2:state_message=shown_auto?6:7;
   3:state_message=9;
   4:state_message=shown_failed?14:(shown_loading?11:(shown_video?12:13));
   5:state_message=shown_field==0?16:(shown_field==1?17:(shown_field==2?18:45));
   6:state_message=20;
   7:state_message=(shown_contrast>=2&&shown_contrast<=6)?22:45;
   8:state_message=shown_overlays?24:25;9:state_message=shown_audio?27:28;
   10:state_message=shown_keys==0?30:(shown_keys==1?31:(shown_keys==2?32:33));
   11:state_message=shown_field==0?(shown_failed?44:35):(shown_field==1?36:(shown_field==2?37:45));
   12:state_message=shown_field==0?39:(shown_field==1?40:(shown_field==2?41:45));
   13:state_message=43;default:state_message=0;
  endcase
 end endfunction
 // Fixed-radius pixel-center circle lookup; no per-pixel multiply/divide.
 function [3:0] message_length;input [5:0] msg;begin
  case(msg)
   6'd0:message_length=4'd0;
   6'd1:message_length=4'd4;
   6'd2:message_length=4'd4;
   6'd3:message_length=4'd2;
   6'd4:message_length=4'd2;
   6'd5:message_length=4'd4;
   6'd6:message_length=4'd4;
   6'd7:message_length=4'd4;
   6'd8:message_length=4'd4;
   6'd9:message_length=4'd5;
   6'd10:message_length=4'd4;
   6'd11:message_length=4'd3;
   6'd12:message_length=4'd3;
   6'd13:message_length=4'd3;
   6'd14:message_length=4'd5;
   6'd15:message_length=4'd4;
   6'd16:message_length=4'd4;
   6'd17:message_length=4'd4;
   6'd18:message_length=4'd5;
   6'd19:message_length=4'd2;
   6'd20:message_length=4'd3;
   6'd21:message_length=4'd3;
   6'd22:message_length=4'd4;
   6'd23:message_length=4'd4;
   6'd24:message_length=4'd3;
   6'd25:message_length=4'd3;
   6'd26:message_length=4'd4;
   6'd27:message_length=4'd4;
   6'd28:message_length=4'd4;
   6'd29:message_length=4'd4;
   6'd30:message_length=4'd3;
   6'd31:message_length=4'd4;
   6'd32:message_length=4'd4;
   6'd33:message_length=4'd4;
   6'd34:message_length=4'd4;
   6'd35:message_length=4'd3;
   6'd36:message_length=4'd3;
   6'd37:message_length=4'd4;
   6'd38:message_length=4'd4;
   6'd39:message_length=4'd5;
   6'd40:message_length=4'd3;
   6'd41:message_length=4'd4;
   6'd42:message_length=4'd4;
   6'd43:message_length=4'd9;
   6'd44:message_length=4'd4;
   6'd45:message_length=4'd4;
   default:message_length=0;
  endcase
 end endfunction
 function [4:0] corner24;input [4:0] v;begin
  case(v)
   5'd0:corner24=5'd19;
   5'd1:corner24=5'd16;
   5'd2:corner24=5'd13;
   5'd3:corner24=5'd12;
   5'd4:corner24=5'd10;
   5'd5:corner24=5'd9;
   5'd6:corner24=5'd8;
   5'd7:corner24=5'd7;
   5'd8:corner24=5'd6;
   5'd9:corner24=5'd5;
   5'd10:corner24=5'd4;
   5'd11:corner24=5'd4;
   5'd12:corner24=5'd3;
   5'd13:corner24=5'd2;
   5'd14:corner24=5'd2;
   5'd15:corner24=5'd2;
   5'd16:corner24=5'd1;
   5'd17:corner24=5'd1;
   5'd18:corner24=5'd1;
   5'd19:corner24=5'd0;
   5'd20:corner24=5'd0;
   5'd21:corner24=5'd0;
   5'd22:corner24=5'd0;
   5'd23:corner24=5'd0;
   default:corner24=0;
  endcase
 end endfunction
 function [4:0] corner22;input [4:0] v;begin
  case(v)
   5'd0:corner22=5'd17;
   5'd1:corner22=5'd14;
   5'd2:corner22=5'd12;
   5'd3:corner22=5'd10;
   5'd4:corner22=5'd9;
   5'd5:corner22=5'd7;
   5'd6:corner22=5'd6;
   5'd7:corner22=5'd5;
   5'd8:corner22=5'd5;
   5'd9:corner22=5'd4;
   5'd10:corner22=5'd3;
   5'd11:corner22=5'd3;
   5'd12:corner22=5'd2;
   5'd13:corner22=5'd2;
   5'd14:corner22=5'd1;
   5'd15:corner22=5'd1;
   5'd16:corner22=5'd1;
   5'd17:corner22=5'd0;
   5'd18:corner22=5'd0;
   5'd19:corner22=5'd0;
   5'd20:corner22=5'd0;
   5'd21:corner22=5'd0;
   default:corner22=0;
  endcase
 end endfunction
 function [23:0] tint;input [23:0] d,s;reg [9:0] a,b,c;begin
  a={2'b0,d[23:16]}+{2'b0,s[23:16]}+{1'b0,s[23:16],1'b0}+10'd2;
  b={2'b0,d[15:8]}+{2'b0,s[15:8]}+{1'b0,s[15:8],1'b0}+10'd2;
  c={2'b0,d[7:0]}+{2'b0,s[7:0]}+{1'b0,s[7:0],1'b0}+10'd2;
  tint={a[9:2],b[9:2],c[9:2]};
 end endfunction
 function [7:0] shadow_channel;input [7:0] d,s;reg [10:0] v;begin
  v={d,3'b0}-{3'b0,d}+{3'b0,s}+11'd4;shadow_channel=v[10:3];
 end endfunction
 function [23:0] drop_shadow;input [23:0] d;begin
  drop_shadow={shadow_channel(d[23:16],8'd128),shadow_channel(d[15:8],8'd152),shadow_channel(d[7:0],8'd172)};
 end endfunction
 wire [4:0] outer_inset=y<88?corner24(y-12'd64):(y>=632?corner24(12'd655-y):5'd0);
 wire [4:0] inner_inset=y<88?corner22(y-12'd66):(y>=632?corner22(12'd653-y):5'd0);
 wire [4:0] shadow_inset=y<96?corner24(y-12'd72):(y>=640?corner24(12'd663-y):5'd0);
 wire in_panel=y>=64&&y<656&&x>=(12'd288+outer_inset)&&x<(12'd992-outer_inset);
 wire in_inner=y>=66&&y<654&&x>=(12'd290+inner_inset)&&x<(12'd990-inner_inset);
 wire in_shadow=y>=72&&y<664&&x>=(12'd294+shadow_inset)&&x<(12'd998-shadow_inset);
 reg [3:0] row_now,font_y_now;
 reg glyph_y_now;
 // Constant range decoders avoid a pixel-clock division by the 40px row pitch.
 always @* begin
  row_now=15;font_y_now=0;glyph_y_now=0;
  if(y>=12'd80&&y<12'd120)begin row_now=4'd0;font_y_now=(y-12'd80)>>1;glyph_y_now=y<12'd112;end
  else if(y>=12'd120&&y<12'd160)begin row_now=4'd1;font_y_now=(y-12'd120)>>1;glyph_y_now=y<12'd152;end
  else if(y>=12'd160&&y<12'd200)begin row_now=4'd2;font_y_now=(y-12'd160)>>1;glyph_y_now=y<12'd192;end
  else if(y>=12'd200&&y<12'd240)begin row_now=4'd3;font_y_now=(y-12'd200)>>1;glyph_y_now=y<12'd232;end
  else if(y>=12'd240&&y<12'd280)begin row_now=4'd4;font_y_now=(y-12'd240)>>1;glyph_y_now=y<12'd272;end
  else if(y>=12'd280&&y<12'd320)begin row_now=4'd5;font_y_now=(y-12'd280)>>1;glyph_y_now=y<12'd312;end
  else if(y>=12'd320&&y<12'd360)begin row_now=4'd6;font_y_now=(y-12'd320)>>1;glyph_y_now=y<12'd352;end
  else if(y>=12'd360&&y<12'd400)begin row_now=4'd7;font_y_now=(y-12'd360)>>1;glyph_y_now=y<12'd392;end
  else if(y>=12'd400&&y<12'd440)begin row_now=4'd8;font_y_now=(y-12'd400)>>1;glyph_y_now=y<12'd432;end
  else if(y>=12'd440&&y<12'd480)begin row_now=4'd9;font_y_now=(y-12'd440)>>1;glyph_y_now=y<12'd472;end
  else if(y>=12'd480&&y<12'd520)begin row_now=4'd10;font_y_now=(y-12'd480)>>1;glyph_y_now=y<12'd512;end
  else if(y>=12'd520&&y<12'd560)begin row_now=4'd11;font_y_now=(y-12'd520)>>1;glyph_y_now=y<12'd552;end
  else if(y>=12'd560&&y<12'd600)begin row_now=4'd12;font_y_now=(y-12'd560)>>1;glyph_y_now=y<12'd592;end
  else if(y>=12'd600&&y<12'd640)begin row_now=4'd13;font_y_now=(y-12'd600)>>1;glyph_y_now=y<12'd632;end

 end
 // Frame-only three-step layout preparation: message -> length -> bounds.
 // Pixel path never computes a message length or derives centering from state.
 reg [5:0] state_msg_cache[0:15],state_start_cache[0:15],state_end_cache[0:15];
 reg layout_busy,layout_ready;reg [3:0] layout_row;reg [1:0] layout_phase;
 reg [5:0] layout_message;reg [3:0] layout_length;integer lr;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  layout_busy<=0;layout_ready<=0;layout_row<=0;layout_phase<=0;layout_message<=0;layout_length<=0;
  for(lr=0;lr<16;lr=lr+1)begin state_msg_cache[lr]<=0;state_start_cache[lr]<=0;state_end_cache[lr]<=0;end
 end else if(tick)begin
  layout_busy<=1;layout_ready<=0;layout_row<=0;layout_phase<=0;
 end else if(layout_busy)begin
  case(layout_phase)
   0:begin layout_message<=state_message(layout_row);layout_phase<=1;end
   1:begin layout_length<=message_length(layout_message);layout_phase<=2;end
   2:begin
    state_msg_cache[layout_row]<=layout_message;
    state_start_cache[layout_row]<=6'd48-{2'b0,layout_length};
    state_end_cache[layout_row]<=6'd48+{2'b0,layout_length};
    if(layout_row==13)begin layout_busy<=0;layout_ready<=1;end
    else begin layout_row<=layout_row+1'b1;layout_phase<=0;end
   end
  endcase
 end
 wire [5:0] label_now=label_message(row_now),state_now=state_msg_cache[row_now];
 wire [5:0] left_units=(row_now==1||row_now==6)?6'd26:(row_now==7?6'd25:6'd24);
 wire [5:0] left_end=(row_now==1||row_now==6)?6'd30:(row_now==7?6'd31:6'd32);
 wire is_right=x>=576;
 wire label_hit=x[11:4]>={2'b0,left_units}&&x[11:4]<{2'b0,left_end};
 wire state_hit=x[11:4]>={2'b0,state_start_cache[row_now]}&&x[11:4]<{2'b0,state_end_cache[row_now]};
 wire [5:0] start_units=is_right?state_start_cache[row_now]:left_units;
 wire [11:0] local_x=x-{2'b0,start_units,4'b0};
 wire [4:0] value_col_now={1'b0,local_x[8:5]};
 reg [3:0] row0;reg [4:0] value_col0;reg right0;
 reg override_now;reg [6:0] override_glyph_now;
 always @* begin
  override_now=0;override_glyph_now=0;
  if(right0)begin
   case(row0)
    3:if(value_col0==1)begin override_now=1;override_glyph_now=digit_glyph({2'b0,shown_image}+4'd1);end
    4:if(shown_failed&&(value_col0==3||value_col0==4))begin
       override_now=1;override_glyph_now=hex_glyph(value_col0==3?shown_error[7:4]:shown_error[3:0]);end
    6:case(value_col0)
       0:begin override_now=1;override_glyph_now=shown_brightness[7]?G_002D:G_002B;end
       1:begin override_now=1;override_glyph_now=bright_tens(shown_brightness);end
       2:begin override_now=1;override_glyph_now=bright_ones(shown_brightness);end
       default:begin end
      endcase
    7:if(shown_contrast>=2&&shown_contrast<=6)case(value_col0)
       0:begin override_now=1;override_glyph_now=shown_contrast>=4?G_0031:G_0030;end
       1:begin override_now=1;case(shown_contrast)
          2,6:override_glyph_now=G_0035;3:override_glyph_now=G_0037;
          5:override_glyph_now=G_0032;default:override_glyph_now=G_0030;endcase end
       2:begin override_now=1;override_glyph_now=(shown_contrast==3||shown_contrast==5)?G_0035:G_0030;end
       default:begin end
      endcase
    default:begin end
   endcase
  end
 end
 reg [23:0] base[0:2],ink[0:2],shade[0:2];
 reg [11:0] xx[0:2],yy[0:2];reg [3:0] ctl[0:2];
 reg [2:0] panel,border,glyph,shadow;
 reg [5:0] message0;reg [3:0] text_col0,font_y0,font_y1,font_x0,font_x1,font_x2;
 reg override1;reg [6:0] override_glyph1,text_glyph1;
 reg [15:0] bits2;
 always @(posedge clk)begin
  text_glyph1<=text_memory[{message0,text_col0}];
  bits2<=font_memory[{(override1?override_glyph1:text_glyph1),font_y1}];
 end
 integer i;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin
  for(i=0;i<3;i=i+1)begin base[i]<=0;ink[i]<=0;shade[i]<=0;xx[i]<=0;yy[i]<=0;ctl[i]<=4'b0110;end
  panel<=0;border<=0;glyph<=0;shadow<=0;message0<=0;text_col0<=0;
  font_y0<=0;font_y1<=0;font_x0<=0;font_x1<=0;font_x2<=0;
  row0<=0;value_col0<=0;right0<=0;override1<=0;override_glyph1<=0;
  x_out<=0;y_out<=0;rgb_out<=0;de_out<=0;hs_out<=1;vs_out<=1;picture_visible_out<=0;
 end else begin
  base[0]<=rgb;xx[0]<=x;yy[0]<=y;ctl[0]<={de,hs,vs,picture_visible};
  for(i=1;i<3;i=i+1)begin
   base[i]<=base[i-1];ink[i]<=ink[i-1];shade[i]<=shade[i-1];
   xx[i]<=xx[i-1];yy[i]<=yy[i-1];ctl[i]<=ctl[i-1];
  end
  panel[0]<=ui_visible&&de&&in_panel;
  shadow[0]<=ui_visible&&de&&in_shadow;
  border[0]<=ui_visible&&de&&in_panel&&(!in_inner||
     (x>=576&&x<578&&y>=120&&y<640)||(y>=158&&y<160));
  panel[2:1]<=panel[1:0];border[2:1]<=border[1:0];glyph[2:1]<=glyph[1:0];shadow[2:1]<=shadow[1:0];
  glyph[0]<=ui_visible&&layout_ready&&de&&glyph_y_now&&(label_hit||state_hit);
  message0<=is_right?state_now:label_now;
  text_col0<=local_x[8:5];
  font_y0<=font_y_now;font_y1<=font_y0;font_x0<=local_x[4:1];font_x1<=font_x0;font_x2<=font_x1;
  row0<=row_now;value_col0<=value_col_now;right0<=is_right;
  override1<=override_now;override_glyph1<=override_glyph_now;
  shade[0]<=((shown_field==1&&row_now==6)||(shown_field==2&&row_now==7))?24'hd5f4e8:
             ((row_now==10&&shown_keys!=0)?24'hfcebd5:(y<112?24'hf5fbff:(row_now==1?24'hedf6fc:24'heaf4fc)));
  ink[0]<=row_now<=1?24'h163046:((row_now==4&&shown_failed)?24'hba332c:
          ((row_now==9&&shown_audio)?24'h00796b:((row_now==10&&shown_keys!=0)?24'h885718:
          (label_hit?24'h42566c:24'h173b54))));
  rgb_out<=border[2]?24'hf9fdff:((glyph[2]&&bits2[15-font_x2])?ink[2]:
           (panel[2]?tint(base[2],shade[2]):(shadow[2]?drop_shadow(base[2]):base[2])));
  x_out<=xx[2];y_out<=yy[2];{de_out,hs_out,vs_out,picture_visible_out}<=ctl[2];
 end
endmodule
