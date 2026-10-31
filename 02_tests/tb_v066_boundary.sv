`timescale 1ns/1ps
module tb_v066_boundary;
reg pix=0,sd=0;always #7 pix=~pix;always #5 sd=~sd;
reg rp=1;wire [11:0]x,y;wire hs,vs,de,fs;
video_timing #(.H_ACTIVE(1280),.H_FP(110),.H_SYNC(40),.H_BP(220),.V_ACTIVE(720),.V_FP(5),.V_SYNC(5),.V_BP(20)) timing(.clk(pix),.rst_n(rp),.x(x),.y(y),.hs(hs),.vs(vs),.de(de),.frame_start(fs));
wire window=de&&x>=320&&x<960&&y>=120&&y<600;
reg[7:0] image[0:307199];string filename;
integer wi=0,ri=0,checked=0,edge_checked=0,frames=0;
wire full,empty,pop;wire[12:0]wu,ru;wire[7:0]data;
async_fifo #(.WIDTH(8),.AW(12)) fifo(.wclk(sd),.wrst_n(rp),.wr_en(rp&&!full),.wdata(image[wi]),.wfull(full),.wused(wu),.rclk(pix),.rrst_n(rp),.rd_en(pop),.rdata(data),.rempty(empty),.rused(ru));
always @(posedge sd or negedge rp)if(!rp)wi<=0;else if(!full)wi<=wi==307199?0:wi+1;
wire [23:0] rgb;wire dd,hd,vd,running,fault;
idx_display display(.clk(pix),.rst_n(rp),.timing_rst_n(rp),.enable(1'b1),.frame_start(fs),.de(de),.hs(~hs),.vs(~vs),.window(window),.empty(empty),.used(ru),.data(data),.pop(pop),.rgb(rgb),.de_d(dd),.hs_d(hd),.vs_d(vd),.running(running),.fault(fault));
// Actual top-level mux block is extracted unchanged by run_v066_boundary.py.
`include "v066_actual_screen_mux.vh"
function [23:0] expand(input[7:0]v);expand={v[7:5],v[7:5],v[7:6],v[4:2],v[4:2],v[4:3],v[1:0],v[1:0],v[1:0],v[1:0]};endfunction
reg ex_de,ex_hs,ex_vs,ex_pop,ex_win,ex_edge;reg[23:0]ex_rgb,ex_screen;integer exx,exy;
always @(posedge pix)if(rp)begin
 ex_de=de;ex_hs=~hs;ex_vs=~vs;ex_pop=pop;ex_win=window;ex_edge=de&&(x<4||x>=1276||y<4||y>=716);exx=x;exy=y;
 ex_rgb=0;
 if(pop)begin
  if(ri!==((y-120)*640+(x-320)))$fatal(1,"FIFO coordinate mismatch x=%0d y=%0d ri=%0d",x,y,ri);
  ex_rgb=expand(image[ri]);ri=(ri==307199)?0:ri+1;checked=checked+1;
  if(x==959)edge_checked=edge_checked+1;
 end
 ex_screen=ex_edge?24'hffffff:(ex_win?ex_rgb:24'h081830);
 #1;
 if(fault)$fatal(1,"underflow");
 if({dd,hd,vd}!=={ex_de,ex_hs,ex_vs})$fatal(1,"control alignment");
 if(rgb!==ex_rgb)$fatal(1,"RGB mismatch x=%0d y=%0d got=%h expected=%h",exx,exy,rgb,ex_rgb);
 if(screen_rgb!==ex_screen)$fatal(1,"screen mux mismatch x=%0d y=%0d",exx,exy);
 if(checked==614400)begin
  if(edge_checked!=960)$fatal(1,"edge count");
  $display("PASS boundary actual_FIFO_2frames pixels=%0d right_edge=%0d RGB_controls_and_actual_top_mux",checked,edge_checked);$finish;
 end
end
initial begin
 if(!$value$plusargs("IMAGE=%s",filename))$fatal(1,"image required");
 $readmemh(filename,image);
 if(^image[0]===1'bx||^image[307199]===1'bx)$fatal(1,"fixture missing");
 #1;rp=0;#100;rp=1;
 #100000000;$fatal(1,"timeout");
end
endmodule
