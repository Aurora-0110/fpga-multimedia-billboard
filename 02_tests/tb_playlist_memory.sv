`timescale 1ns/1ps
module tb_playlist_memory;
parameter real SD_HALF=10.101;
parameter integer NEGATIVE=0;
reg sd=0,pc=0;always #(SD_HALF) sd=~sd;always #6.734007 pc=~pc;
reg lock=0,key_press=0;wire restart;wire rst,prst;
 wire[1:0]image_index;wire[7:0]file_letter;wire busy,failed;
reset_release r0(.clk(sd),.async_n(lock),.rst_n(rst));
reset_release r1(.clk(pc),.async_n(lock),.rst_n(prst));
wire [11:0] x,y;wire hs,vs,de,fs;
video_timing #(.H_ACTIVE(1280),.H_FP(110),.H_SYNC(40),.H_BP(220),
.V_ACTIVE(720),.V_FP(5),.V_SYNC(5),.V_BP(20)) timing(.clk(pc),.rst_n(prst),
.x(x),.y(y),.hs(hs),.vs(vs),.de(de),.frame_start(fs));
wire win=de&&x>=320&&x<960&&y>=120&&y<600;
wire [23:0] rgb;wire dd,hd,vd,init,fr,ren,run,fault,of;wire [1:0] phase;
wire cke,cs,ras,cas,we,oe;wire [10:0] ma;wire [1:0] ba;wire [3:0] dm;
wire [31:0] dout;tri [31:0] dq;assign dq=oe?dout:32'bz;
wire lv,ldone,lack,lrst,len;wire [18:0] la;wire [127:0] ldata;
idx_pipeline #(.USE_EXTERNAL_SOURCE(1)) dut(.clk_sd(sd),.clk_pix(pc),.rst_sd_n(rst),.rst_pix_n(prst),.restart(restart),
.load_valid(lv),.load_done(ldone),.load_addr(la),.load_data(ldata),.load_ack(lack),.load_rst_n(lrst),.load_enable(len),
.frame_start(fs),.de(de),.hs(~hs),.vs(~vs),.window(win),.rgb(rgb),.de_d(dd),.hs_d(hd),.vs_d(vd),
.init_done(init),.frame_ready(fr),.read_enable(ren),.display_running(run),.display_fault(fault),.overflow_fault(of),.phase(phase),
.mem_cke(cke),.mem_cs_n(cs),.mem_ras_n(ras),.mem_cas_n(cas),.mem_we_n(we),.mem_addr(ma),.mem_ba(ba),.mem_dm(dm),
.dq_out(dout),.dq_oe(oe),.dq_in(dq));
IS42s32200 mem(.Clk(sd),.Cke(cke),.Cs_n(cs),.Ras_n(ras),.Cas_n(cas),.We_n(we),.Addr(ma),.Ba(ba),.Dqm(dm),.Dq(dq));
integer pixels=0,writes=0,reads=0,epochs=0,frames=0;
integer min_used=4096,max_used=0,byteidx=0;
reg inject=0,waspop,expde,exphs,expvs;reg[23:0] expected;
reg [7:0] image[0:921653];string image_path;integer top=0;integer active_image=0;
function [23:0] color;
input integer xx,yy;integer off,row;reg [23:0] raw;reg [7:0] c;
begin
 row=top?yy:479-yy;off=54+row*1920+xx*3;
 raw={image[off+2],image[off+1],image[off]};
 if(active_image==1)raw=raw^24'he0e0e0;
 if(active_image==2)raw=raw^24'hc0c0c0;
 c={raw[23:21],raw[15:13],raw[7:6]};
 color={c[7:5],c[7:5],c[7:6],c[4:2],c[4:2],c[4:3],c[1:0],c[1:0],c[1:0],c[1:0]};
end endfunction
wire req,pv,psdone,psok;wire[31:0] lba,pcnt,pcrc;wire[3:0] err;
wire[23:0] pixel_rgb;wire[15:0] pixel_x,pixel_y;wire pixel_ready;
reg ready=0,rdone=1,dv=0;reg[8:0] di=0;reg[7:0] db=0;
reg[3:0] sd_error=0;wire[7:0] pack_error;
 tf_playlist_ctrl #(.AUTO_ENABLE(1),.DWELL_CYCLES(2000000)) playlist(.clk(sd),.rst_n(rst),.key_press(key_press),.load_rst_n(lrst),
 .phase(phase),.load_done(ldone),.load_error(pack_error),.display_running(run),.stream_fault(fault|of),
 .restart(restart),.image_index(image_index),.file_letter(file_letter),.busy(busy),.failed(failed));
 always @(posedge lrst)active_image=image_index;

bmp_pixel_stream #(.READ_TIMEOUT_CYCLES(3000)) stream(
 .clk(sd),.rst_n(lrst),.start(1'b1),.file_size(32'd921654),.pixel_offset(32'd54),
 .file_cluster(32'd3),.data_base(32'd1000000),.fat_base(32'd10),.cluster_max(32'd65526),
 .mounted_spc(8'd8),.mounted_shift(4'd3),.top_down(top!=0),
 .sd_ready(ready),.sd_read_done(rdone),.sd_error(sd_error),.data_valid(dv),.data_index(di),.data_byte(db),
 .read_req(req),.read_lba(lba),.pixel_valid(pv),.pixel_ready(pixel_ready),.pixel_rgb(pixel_rgb),
 .pixel_x(pixel_x),.pixel_y(pixel_y),.busy(),.done(psdone),.ok(psok),.error_code(err),.pixel_count(pcnt),.payload_crc32(pcrc));
bmp_pixel_packer packer(.clk(sd),.rst_n(lrst),.enable(len),
 .pixel_valid(pv),.pixel_ready(pixel_ready),.pixel_rgb(pixel_rgb),.pixel_x(pixel_x),.pixel_y(pixel_y),
 .source_done(psdone),.source_ok(psok),.source_error({4'b0,err}),
 .req_valid(lv),.req_addr(la),.req_data(ldata),.req_ack(lack),.done(ldone),.error_code(pack_error),.pixel_count(),.burst_count());
integer server=0,pos=0,logical_sector=0,ci=0,cl=0,entry=0,link=0,gb=0;
reg fat_req=0;
function [7:0] sector_byte(input integer k);integer e,i,next_c,g;
begin
 if(!fat_req)begin
  g=logical_sector*512+k;sector_byte=g<921654?image[g]:0;
  if(g>=54&&g<921654&&active_image==1)sector_byte=sector_byte^8'he0;
  if(g>=54&&g<921654&&active_image==2)sector_byte=sector_byte^8'hc0;
 end
 else begin
  e=(lba-10)*128+k/4;i=(e-3)/137;next_c=0;
  if(e>=3&&(e-3)%137==0)next_c=((i+1)*4096>=921654)?32'h0fffffff:e+137;
  sector_byte=next_c>>((k%4)*8);
 end
end endfunction
always @(posedge sd)begin
 dv<=0;
 if(!lrst)begin ready<=0;rdone<=1;server<=0;sd_error<=0;end
 else begin
 if(pack_error)$fatal(1,"BMP chain load error %h",pack_error);
 case(server)
 0:begin ready<=1;server<=1;end
 1:if(req)begin
  ready<=0;rdone<=0;pos<=0;
  fat_req=lba<1000000;
  if(!fat_req)begin
   cl=((lba-1000000)/8)+2;ci=(cl-3)/137;
   if(cl<3||(cl-3)%137!=0)$fatal(1,"invalid fragmented data LBA %d",lba);
   logical_sector=ci*8+(lba-1000000)%8;
   if(logical_sector*512>=921654)$fatal(1,"read past BMP");
  end
  server<=2;
 end
 2:begin dv<=1;di<=pos;db<=sector_byte(pos);if(pos==511)server<=3;else pos<=pos+1;end
 3:begin ready<=1;rdone<=1;server<=1;end
 endcase
 end
end

always @(posedge sd)begin
 if(rst)begin
 if(dut.resp&&dut.reader.pending&&dut.reader.queued)$fatal(1,"response queue overwrite");
 if(of)$fatal(1,"FIFO overflow");
 if(dut.ack&&dut.ow)writes=writes+1;
 if(dut.ack&&dut.orr)reads=reads+1;
 if(dut.fw&&dut.ff)$fatal(1,"overflow write attempt");
 if(dut.wu>4096)$fatal(1,"invalid fifo count");
 end
end
always @(negedge dut.pipe)if(rst)begin
 epochs=epochs+1;
 if(!dut.idle)$fatal(1,"epoch reset before controller idle");
end
always @(posedge pc)begin
 waspop=dut.pop;
 expde=de;exphs=~hs;expvs=~vs;
 expected=waspop?color(x-320,y-120):0;
 if(dut.prst)begin
 if(fault&&!inject)$fatal(1,"unexpected video underflow x=%0d y=%0d",x,y);
 // During orderly retry drain, enable drops before running is cleared/reset.
 // This interval intentionally blanks pixels; consumption is required only
 // while display enable is still asserted (same active predicate as DUT).
 if(run&&dut.display.enable&&win&&!inject&&!waspop)$fatal(1,"pixel not consumed x=%0d y=%0d used=%0d empty=%b",x,y,dut.ru,dut.fe);
 if(!dut.display.enable&&waspop)$fatal(1,"consume while display disabled");
 if(waspop)begin
 if(!win)$fatal(1,"consume outside centered image");
 if(byteidx%307200!==((y-120)*640+x-320))$fatal(1,"frame origin/wrap mismatch");
 byteidx=byteidx+1;pixels=pixels+1;
 if(dut.ru<min_used)min_used=dut.ru;
 if(dut.ru>max_used)max_used=dut.ru;
 end
 #0.001;
 if(dut.prst)begin
 if(rgb!==expected)$fatal(1,"SDRAM pixel mismatch x=%0d y=%0d got=%h expected=%h",x,y,rgb,expected);

 end
 end
end
always @(posedge pc) begin
 if(prst) begin
  expde=de;exphs=~hs;expvs=~vs;
  #0.002;
  if(prst && (dd!==expde||hd!==exphs||vd!==expvs))
   $fatal(1,"outgoing HDMI timing broken during retry: content_reset=%b",dut.prst);
 end
end
// Per-frame 720p timing independent of image readiness.
integer act=0,hcount=0,vcount=0,cycles=0;reg frame_seen=0;
always @(negedge pc)if(prst)begin
 if(fs)begin
 if(frame_seen && (cycles!=1237500 || act!=921600 || hcount!=30000 || vcount!=8250))
 $fatal(1,"720p timing cycles=%0d active=%0d hs=%0d vs=%0d",cycles,act,hcount,vcount);
 if(frame_seen)frames=frames+1;frame_seen=1;
 cycles=0;act=0;hcount=0;vcount=0;
 end
 if(frame_seen)begin cycles=cycles+1;if(de)act=act+1;if(!hs)hcount=hcount+1;if(!vs)vcount=vcount+1;end
end
always @(negedge dut.prst)byteidx=0;
task press;begin @(negedge sd);key_press=1;@(negedge sd);key_press=0;end endtask
integer f;
initial begin
 if(!$value$plusargs("IMAGE=%s",image_path))$fatal(1,"missing image");
 $readmemh(image_path,image);repeat(8)@(negedge sd);lock=1;
 wait(writes>=3);press();repeat(10)@(negedge sd);
 if(image_index!=0)$fatal(1,"busy key changed selection");
 for(f=0;f<4;f=f+1)begin
  wait(!busy&&byteidx>=307200);
  if(failed||image_index!==f%3||active_image!==f%3)$fatal(1,"epoch selection wrong");
  $display("STAGE full_frame file=%c pixels=%0d epochs=%0d",file_letter,byteidx,epochs);$fflush();
  if(f<3)begin wait(restart);wait(!lrst);wait(lrst);end
 end
 if(epochs<3||reads<4*19200||writes!=4*19200)$fatal(1,"missing full epoch coverage");
 $display("PASS autoplay_memory A_B_C_A all_pixels_checked writes=%0d reads=%0d epochs=%0d frames=%0d",writes,reads,epochs,frames);$finish;
end

always begin #5000000; $display("PROGRESS ns=%0t phase=%0d ctrl=%0d pixels=%0d frames=%0d writes=%0d reads=%0d",$time,phase,dut.ctrl.state,pixels,frames,writes,reads);$fflush();end
initial begin #500000000;$fatal(1,"timeout phase=%0d pixels=%0d",phase,pixels);end
endmodule
