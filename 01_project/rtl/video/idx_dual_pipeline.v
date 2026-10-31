`timescale 1ns/1ps
// Concurrent background write + single visible read stream. Bank ownership and
// registered ACK routing remain fixed for the COMPLETE physical transaction.
// No content reset/PLL reset/FIFO flush is performed during image transitions.
module idx_dual_pipeline(
 input wire clk_sd,clk_pix,rst_sd_n,rst_pix_n,front_valid,dest_bank,
 input wire transition_request,input wire [1:0] target_index,
 output wire transition_done,
 input wire frame_start,de,hs,vs,window,
 input wire load_valid,input wire [18:0] load_addr,input wire [127:0] load_data,
 output wire load_ack,
 output wire [23:0] rgb,output wire de_d,hs_d,vs_d,
 output wire init_done,display_running,display_fault,picture_visible,
 output reg overflow_fault,output wire [1:0] displayed_index,output wire [5:0] displayed_step,
 output wire mem_cke,mem_cs_n,mem_ras_n,mem_cas_n,mem_we_n,
 output wire [10:0] mem_addr,output wire [1:0] mem_ba,output wire [3:0] mem_dm,
 output wire [31:0] dq_out,output wire dq_oe,input wire [31:0] dq_in);
 wire wrst,prst;
 wire epoch_n=rst_sd_n&&rst_pix_n;
 reset_release #(.RELEASE_FALLING_EDGE(1)) rs(.clk(clk_sd),.async_n(epoch_n),.rst_n(wrst));
 reset_release #(.RELEASE_FALLING_EDGE(1)) rp(.clk(clk_pix),.async_n(epoch_n),.rst_n(prst));
 reg [1:0] grant;reg issued;
 wire idle,ack,resp;wire [127:0] rd;wire [31:0] refresh;
 wire rv,fw,ff,fe,pop;wire [18:0] ra;
 wire [15:0] fwd,frd;wire [12:0] wu,ru;
 wire sliding;wire [5:0] step;
 idx_slide_reader reader(.clk(clk_sd),.rst_n(wrst),.enable(front_valid&&init_done),.fifo_used(wu),
 .transition_request(transition_request),.target_index(target_index),.transition_done(transition_done),.sliding(sliding),.step(step),
 .req_valid(rv),.req_addr(ra),.req_ready(ack&&grant==1),.rsp_valid(resp),.rsp_rdata(rd),.fifo_we(fw),.fifo_wdata(fwd));
 async_fifo #(.WIDTH(16),.AW(12)) fifo(.wclk(clk_sd),.wrst_n(wrst),.wr_en(fw),.wdata(fwd),
 .wfull(ff),.wused(wu),.rclk(clk_pix),.rrst_n(prst),.rd_en(pop),.rdata(frd),.rempty(fe),.rused(ru));
 // Reader priority below half-full. Above half-full, service a waiting TF write.
 // The 4K-pixel FIFO reserves latency for refresh/row switches/write turnaround.
 always @(posedge clk_sd or negedge wrst)
 if(!wrst)begin grant<=0;issued<=0;end
 else if(grant==0)begin
  if(init_done&&idle)begin
   if(rv&&(!load_valid||wu<2048))grant<=1;
   else if(load_valid)grant<=2;
  end
 end else begin
  if(ack)issued<=1;
  if(issued&&idle)begin grant<=0;issued<=0;end
 end
 assign load_ack=ack&&grant==2;
 wire [18:0] wa=load_addr+(dest_bank?19'd131072:19'd0);
 wire [18:0] a=grant==2?wa:ra;
 sdram_ctrl #(.RD_WAIT(2)) ctrl(.clk(clk_sd),.rst_n(rst_sd_n),
 .req_valid(grant!=0&&!issued),.req_we(grant==2),.req_bank(a[18:17]),
 .req_row(a[16:6]),.req_col(a[5:0]),.req_wdata(load_data),.req_ready(ack),.idle(idle),
 .rsp_valid(resp),.rsp_rdata(rd),.init_done(init_done),.refresh_count(refresh),
 .mem_cke(mem_cke),.mem_cs_n(mem_cs_n),.mem_ras_n(mem_ras_n),.mem_cas_n(mem_cas_n),
 .mem_we_n(mem_we_n),.mem_addr(mem_addr),.mem_ba(mem_ba),.mem_dm(mem_dm),
 .dq_out(dq_out),.dq_oe(dq_oe),.dq_in(dq_in));
 (* ASYNC_REG="TRUE" *) reg [1:0] en;
 always @(posedge clk_pix or negedge prst)if(!prst)en<=0;else en<={en[0],front_valid};
 idx_display display(.clk(clk_pix),.rst_n(prst),.timing_rst_n(rst_pix_n),.enable(en[1]),.frame_start(frame_start),
 .de(de),.hs(hs),.vs(vs),.window(window),.empty(fe),.used(ru),.data(frd[7:0]),.pop(pop),
 .rgb(rgb),.de_d(de_d),.hs_d(hs_d),.vs_d(vs_d),.running(display_running),.fault(display_fault),.picture_visible(picture_visible));
 // FIFO rdata and display RGB both update after the SAME pop edge. Do not
 // register metadata again: that would label the first pixel with the previous
 // frame's step/index (one-pixel lag at every transition boundary).
 assign displayed_index=frd[15:14];
 assign displayed_step=frd[13:8];
 always @(posedge clk_sd or negedge wrst)
 if(!wrst)overflow_fault<=0;else if(fw&&ff)overflow_fault<=1;
endmodule

