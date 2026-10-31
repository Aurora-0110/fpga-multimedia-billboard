`timescale 1ns/1ps
// Parallel-symbol simulation. Native ODDR has a separate unchanged regression.
module tmds_serializer #(parameter SEPARATE_PIXEL_RESET=0)(input clk_pix,clk_5x,rst,rst_pix_n,input [9:0]din,output q);assign q=0;endmodule
module tmds_clock_lane #(parameter SEPARATE_PIXEL_RESET=0)(input clk_pix,clk_5x,rst,rst_pix_n,output q);assign q=0;endmodule
module tb_v071_audio;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 wire [11:0] x,y;wire hs,vs,de,fs;
 video_timing #(.H_ACTIVE(1280),.H_FP(110),.H_SYNC(40),.H_BP(220),.V_ACTIVE(720),.V_FP(5),.V_SYNC(5),.V_BP(20))
 timing(.clk(clk),.rst_n(rst_n),.x(x),.y(y),.hs(hs),.vs(vs),.de(de),.frame_start(fs));
 wire [23:0] rgb={x[7:0],y[7:0],x[7:0]^y[7:0]};wire fault;
 hdmi_tx_wrap #(.HDMI_AUDIO_ENABLE(1)) dut(.clk_pix(clk),.clk_5x(clk),.rst_n(rst_n),.serial_async_n(rst_n),
 .r(rgb[23:16]),.g(rgb[15:8]),.b(rgb[7:0]),.de(de),.hs(~hs),.vs(~vs),.cx(x),.cy(y),.audio_fault(fault));
 hdmi_tx_wrap ref_video(.clk_pix(clk),.clk_5x(clk),.rst_n(rst_n),.serial_async_n(rst_n),
 .r(rgb[23:16]),.g(rgb[15:8]),.b(rgb[7:0]),.de(de),.hs(~hs),.vs(~vs),.cx(x),.cy(y));
 integer fp,fa,fr,cycle=0,active=0,serialsamples=0,frames=0;
 integer px,py,was_de,vp,ip,ax,hh,vv;
 integer dx=0,dy=0,dd=0,dvp=0,dip=0,dax=0,dh=0,dv=0;
 reg [9:0] eb,eg,er,rb,rg,rr;
 string dir;
 initial begin
 if(!$value$plusargs("OUT=%s",dir))$fatal(1,"OUT required");
 fp=$fopen({dir,"/symbols.txt"},"w");fa=$fopen({dir,"/pcm.txt"},"w");fr=$fopen({dir,"/rx.txt"},"w");
 repeat(5)@(negedge clk);rst_n=1;
 repeat(1242510)@(negedge clk);
 if(fault)$fatal(1,"audio FIFO overflow");
 if(active<921600 || serialsamples<750)$fatal(1,"incomplete run");
 // Assert reset at non-boundary, verify all pending packets/FIFO/I2S clear.
 rst_n=0;#1;
 if(dut.audio.packets.count!==0 || dut.audio.packets.overflow!==0 || dut.audio.gain.valid!==0)$fatal(1,"reset flush failed");
 repeat(5)@(negedge clk);rst_n=1;repeat(5000)@(negedge clk);
 if(fault)$fatal(1,"overflow after reset");
 $fclose(fp);$fclose(fa);$fclose(fr);
 $display("PASS v072_parallel_audio_video active=%0d pcm_frames=%0d reset_flush=1",active,serialsamples);$finish;
 end
 always @(negedge rst_n)begin dx=0;dy=0;dd=0;dvp=0;dip=0;dax=0;dh=0;dv=0;end
 always @(posedge clk)if(rst_n)begin
  cycle=cycle+1;
  if(dut.audio.pv)begin
   $fwrite(fr,"%0d %06h %06h\n",cycle,dut.audio.il,dut.audio.ir);
   serialsamples=serialsamples+1;
  end
  if(dut.audio.gv)$fwrite(fa,"%0d %06h %06h\n",cycle,dut.audio.gl,dut.audio.gr);
  // Metadata belongs to the extra output stage, not the encoder stage.
  px=dx;py=dy;was_de=dd;vp=dvp;ip=dip;ax=dax;hh=dh;vv=dv;
  dx=dut.cx_q;dy=dut.cy_q;dd=dut.de_q;dvp=dut.vp;dip=dut.ip;dax=dut.aux;dh=dut.hs_q;dv=dut.vs_q;
  eb=dut.ab_q;eg=dut.ag_q;er=dut.ar_q;
  rb=ref_video.u_ser_b.din;rg=ref_video.u_ser_g.din;rr=ref_video.u_ser_r.din;
  #0.1;
  if(was_de)begin
   active=active+1;
   if(dut.u_ser_b.din!==rb || dut.u_ser_g.din!==rg || dut.u_ser_r.din!==rr)
    $fatal(1,"audio modified active pixel x=%0d y=%0d",px,py);
  end
  if(ax)begin
   if(dut.u_ser_b.din!==eb || dut.u_ser_g.din!==eg || dut.u_ser_r.din!==er)$fatal(1,"aux pipeline misalignment");
  end
  if(px>=1280 && px<1330 || px>=1638)
   $fwrite(fp,"%0d %0d %0d %03h %03h %03h %0d %0d %0d %0d %0d\n",cycle,px,py,dut.u_ser_b.din,dut.u_ser_g.din,dut.u_ser_r.din,ax,vp,ip,hh,vv);
  if(fault)$fatal(1,"audio FIFO overflow");
 end
 initial begin #30000000;$fatal(1,"timeout");end
endmodule
