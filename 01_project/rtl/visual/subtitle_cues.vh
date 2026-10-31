// Generated SRT metadata. Endpoint is exclusive; overlaps rejected.
localparam integer CUE_COUNT=6;
function [31:0] cue_start;input [2:0] id;begin case(id)
3'd0:cue_start=32'd0;
3'd1:cue_start=32'd2200;
3'd2:cue_start=32'd5500;
3'd3:cue_start=32'd8500;
3'd4:cue_start=32'd11500;
3'd5:cue_start=32'd15000;
default:cue_start=32'd4294967295;endcase end endfunction
function [31:0] cue_end;input [2:0] id;begin case(id)
3'd0:cue_end=32'd2000;
3'd1:cue_end=32'd5000;
3'd2:cue_end=32'd8000;
3'd3:cue_end=32'd11000;
3'd4:cue_end=32'd14500;
3'd5:cue_end=32'd16000;
default:cue_end=32'd4294967295;endcase end endfunction
function [4:0] cue_length;input [2:0] id;begin case(id)
3'd0:cue_length=5'd10;
3'd1:cue_length=5'd12;
3'd2:cue_length=5'd14;
3'd3:cue_length=5'd13;
3'd4:cue_length=5'd14;
3'd5:cue_length=5'd12;
default:cue_length=5'd0;endcase end endfunction
localparam [6:0] SUB_DIGIT_ZERO=7'd1,SUB_COLON=7'd11;
