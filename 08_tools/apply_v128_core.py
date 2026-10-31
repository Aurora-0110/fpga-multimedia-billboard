from pathlib import Path
import re
r=Path(__file__).resolve().parents[1];p=r/'01_project/rtl/audio/tf_wav_playback.v';s=p.read_text(encoding='utf-8')
s=s.replace('output reg signed [23:0] left,right,output reg valid,epoch,output reg playing,','output reg signed [23:0] left,right,output reg valid,epoch,output reg playing,\n output reg sample_consumed,output wire session_ready,')
s=s.replace('wire sr,pr;','wire sr,pr;\n assign session_ready=pr;')
s=s.replace('acc<=0;left<=0;right<=0;valid<=0;epoch<=0;','acc<=0;left<=0;right<=0;valid<=0;epoch<=0;sample_consumed<=0;')
s=s.replace('valid<=0;epoch<=0;\n  if(sample_tick)','valid<=0;epoch<=0;sample_consumed<=0;\n  if(sample_tick)')
s=s.replace('left<=held[47:24];right<=held[23:0];epoch<=first_sample;','left<=held[47:24];right<=held[23:0];epoch<=first_sample;sample_consumed<=1;')
p.write_text(s,encoding='utf-8')
# Precompute transition geometry once per producer frame, no change to requests or FIFO cycles.
p=r/'01_project/rtl/video/idx_pair_reader.v';s=p.read_text(encoding='utf-8')
s=s.replace('wire [15:0] shift_bursts=step*SHIFT_BURSTS;\n wire [15:0] split=LINE_BURSTS-shift_bursts;','reg [15:0] shift_bursts,split; // V128 frame-rate geometry, not per-request arithmetic')
s=s.replace('row_base<=0;sh<=0;', 'shift_bursts<=0;split<=LINE_BURSTS;\n  row_base<=0;sh<=0;')
s=s.replace('front_bank<=~front_bank;current_index<=next_index;step<=0;sliding<=0;', 'front_bank<=~front_bank;current_index<=next_index;step<=0;sliding<=0;\n     shift_bursts<=0;split<=LINE_BURSTS;')
s=s.replace('end else step<=step+1\'b1;',"end else begin step<=step+1'b1;shift_bursts<=shift_bursts+SHIFT_BURSTS;split<=split-SHIFT_BURSTS;end")
s=s.replace('next_index<=target_index;step<=1;sliding<=1;request_seen<=1;', 'next_index<=target_index;step<=1;sliding<=1;request_seen<=1;\n    shift_bursts<=SHIFT_BURSTS;split<=LINE_BURSTS-SHIFT_BURSTS;')
p.write_text(s,encoding='utf-8')
# Capture selected SDRAM address at arbitration, on the SAME cycle grant is registered.
# Request valid/ack/command scheduling is unchanged; no added transaction bubble.
p=r/'01_project/rtl/video/idx_pair_pipeline.v';s=p.read_text(encoding='utf-8')
s=s.replace('reg [1:0] grant;reg issued;', 'reg [1:0] grant;reg issued;reg [18:0] transaction_addr;')
s=s.replace('wire legal_load=load_addr<WIDTH*HEIGHT/16;',"wire legal_load=load_addr<WIDTH*HEIGHT/16;\n wire [18:0] wa=load_addr+(dest_bank?19'd131072:19'd0);")
s=s.replace('if(!wrst)begin grant<=0;issued<=0;end', 'if(!wrst)begin grant<=0;issued<=0;transaction_addr<=0;end')
s=s.replace('if(rv&&(!load_valid||!legal_load||wu<2048))grant<=1;', 'if(rv&&(!load_valid||!legal_load||wu<2048))begin grant<=1;transaction_addr<=ra;end')
s=s.replace('else if(load_valid&&legal_load)grant<=2;', 'else if(load_valid&&legal_load)begin grant<=2;transaction_addr<=wa;end')
s=s.replace(" wire [18:0] wa=load_addr+(dest_bank?19'd131072:19'd0);\n wire [18:0] a=grant==2?wa:ra;", ' wire [18:0] a=transaction_addr;')
p.write_text(s,encoding='utf-8')
print('Modified PCM real-consumption telemetry; frame-rate transition geometry; registered transaction address.')
