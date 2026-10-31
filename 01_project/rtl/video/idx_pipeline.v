`timescale 1ns/1ps
module idx_pipeline #(parameter USE_EXTERNAL_SOURCE=0)(
 input wire clk_sd,clk_pix,rst_sd_n,rst_pix_n,restart,
 input wire frame_start,de,hs,vs,window,
 input wire load_valid,load_done,input wire [18:0] load_addr,input wire [127:0] load_data,
 output wire load_ack,load_rst_n,load_enable,
 output wire [23:0] rgb,output wire de_d,hs_d,vs_d,
 output wire init_done,frame_ready,read_enable,display_running,display_fault,picture_visible,
 output reg overflow_fault,output wire [1:0] phase,
 output wire mem_cke,mem_cs_n,mem_ras_n,mem_cas_n,mem_we_n,
 output wire [10:0] mem_addr,output wire [1:0] mem_ba,output wire [3:0] mem_dm,
 output wire [31:0] dq_out,output wire dq_oe,input wire [31:0] dq_in);
 wire idle,ack,resp; wire [127:0] rd;wire [31:0] refresh;
 wire pipe,ow,orr,allow,wrst,prst;
 fb_session_ctrl session(.clk(clk_sd),.rst_n(rst_sd_n),.restart(restart),
 .frame_ready(frame_ready),.ctrl_idle(idle),.pipe_run(pipe),.owner_write(ow),
 .owner_read(orr),.allow_req(allow),.read_enable(read_enable),.phase(phase));
 wire epoch_n=pipe&&rst_sd_n&&rst_pix_n;
 reset_release #(.RELEASE_FALLING_EDGE(1)) rs(.clk(clk_sd),.async_n(epoch_n),.rst_n(wrst));
 reset_release #(.RELEASE_FALLING_EDGE(1)) rp(.clk(clk_pix),.async_n(epoch_n),.rst_n(prst));
 wire wv,rv;wire [18:0] wa,ra;wire [127:0] wd;
 assign load_ack=ack&&ow;
 assign load_rst_n=wrst;
 assign load_enable=init_done&&ow;
 generate if(USE_EXTERNAL_SOURCE)begin: external_source
 assign wv=load_valid;assign wa=load_addr;assign wd=load_data;assign frame_ready=load_done;
 end else begin: generated_source
 idx_writer writer(.clk(clk_sd),.rst_n(wrst),.enable(init_done&&ow),
 .req_ready(ack&&ow),.req_valid(wv),.addr(wa),.data(wd),.done(frame_ready));
 end endgenerate
 wire fw,ff,fe,pop;wire [7:0] fwd,frd;wire [12:0] wu,ru;
 idx_reader reader(.clk(clk_sd),.rst_n(wrst),.enable(read_enable&&init_done),
 .fifo_used(wu),.req_valid(rv),.req_bank(ra[18:17]),.req_row(ra[16:6]),.req_col(ra[5:0]),
 .req_ready(ack&&orr),.rsp_valid(resp),.rsp_rdata(rd),.fifo_we(fw),.fifo_wdata(fwd));
 async_fifo #(.WIDTH(8),.AW(12)) fifo(.wclk(clk_sd),.wrst_n(wrst),.wr_en(fw),.wdata(fwd),
 .wfull(ff),.wused(wu),.rclk(clk_pix),.rrst_n(prst),.rd_en(pop),.rdata(frd),.rempty(fe),.rused(ru));
 wire [18:0] a=ow?wa:ra;
 sdram_ctrl #(.RD_WAIT(2)) ctrl(.clk(clk_sd),.rst_n(rst_sd_n),
 .req_valid(allow&&((ow&&wv)||(orr&&rv))),.req_we(ow),.req_bank(a[18:17]),
 .req_row(a[16:6]),.req_col(a[5:0]),.req_wdata(wd),.req_ready(ack),.idle(idle),
 .rsp_valid(resp),.rsp_rdata(rd),.init_done(init_done),.refresh_count(refresh),
 .mem_cke(mem_cke),.mem_cs_n(mem_cs_n),.mem_ras_n(mem_ras_n),.mem_cas_n(mem_cas_n),
 .mem_we_n(mem_we_n),.mem_addr(mem_addr),.mem_ba(mem_ba),.mem_dm(mem_dm),
 .dq_out(dq_out),.dq_oe(dq_oe),.dq_in(dq_in));
 reg [1:0] en;
 always @(posedge clk_pix or negedge prst)if(!prst)en<=0;else en<={en[0],read_enable};
 idx_display display(.clk(clk_pix),.rst_n(prst),.timing_rst_n(rst_pix_n),.enable(en[1]),.frame_start(frame_start),
 .de(de),.hs(hs),.vs(vs),.window(window),.empty(fe),.used(ru),.data(frd),.pop(pop),
 .rgb(rgb),.de_d(de_d),.hs_d(hs_d),.vs_d(vs_d),.running(display_running),.fault(display_fault),.picture_visible(picture_visible));
 always @(posedge clk_sd or negedge wrst)
 if(!wrst)overflow_fault<=0;else if(fw&&ff)overflow_fault<=1;
endmodule
