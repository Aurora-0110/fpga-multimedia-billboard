`timescale 1ns/1ps
// v050 continuous SDRAM-only diagnostic: no TF/HDMI; this build NOT hardware tested.
// All external I/O LVCMOS33 per AG88_VIP_Board_V1.0 schematic page 1.
module sdram_bist_top(input wire clk24m,key0_n,output wire led_sclk,led_dout,led_latch);
    wire clk_sd,clk_24,locked,base_rst_n,run_rst_n;
    pll_sdram u_pll(.clk_in(clk24m),.rst_n(1'b1),.clk_sd(clk_sd),.clk_24(clk_24),.locked(locked));
    bist_reset_ctrl u_reset(.clk_sd(clk_sd),.locked(locked),.key_n(key0_n),
        .base_rst_n(base_rst_n),.run_rst_n(run_rst_n));
    wire req_valid,req_we,req_ready,ctrl_idle,rsp_valid,init_done;
    wire [1:0] req_bank,mem_ba;
    wire [10:0] req_row,mem_addr;
    wire [5:0] req_col;
    wire [127:0] req_wdata,rsp_rdata;
    wire [31:0] refresh_count,dq_out;
    tri [31:0] dq_bus;
    wire dq_oe,mem_cke,mem_cs_n,mem_ras_n,mem_cas_n,mem_we_n;
    wire [3:0] mem_dm;
    assign dq_bus=dq_oe?dq_out:32'bz;
    sdram_ctrl #(.RD_WAIT(2)) u_ctrl(
        .clk(clk_sd),.rst_n(run_rst_n),.req_valid(req_valid),.req_we(req_we),
        .req_bank(req_bank),.req_row(req_row),.req_col(req_col),.req_wdata(req_wdata),
        .req_ready(req_ready),.idle(ctrl_idle),.rsp_valid(rsp_valid),.rsp_rdata(rsp_rdata),
        .init_done(init_done),.refresh_count(refresh_count),.mem_cke(mem_cke),.mem_cs_n(mem_cs_n),
        .mem_ras_n(mem_ras_n),.mem_cas_n(mem_cas_n),.mem_we_n(mem_we_n),.mem_addr(mem_addr),
        .mem_ba(mem_ba),.mem_dm(mem_dm),.dq_out(dq_out),.dq_oe(dq_oe),.dq_in(dq_bus));
    EG_PHY_SDRAM_2M_32 u_ram (
        .clk   (clk_sd),
        .ras_n (mem_ras_n),
        .cas_n (mem_cas_n),
        .we_n  (mem_we_n),
        .addr  (mem_addr),
        .ba    (mem_ba),
        .dq    (dq_bus),
        .cs_n  (mem_cs_n),
        .dm0   (mem_dm[0]),
        .dm1   (mem_dm[1]),
        .dm2   (mem_dm[2]),
        .dm3   (mem_dm[3]),
        .cke   (mem_cke)
    );


    wire done,passed,test_round,fail_round;
    wire [3:0] error_code,phase;
    wire [18:0] fail_burst;
    wire [19:0] burst_cnt;
    wire [20:0] writes_done,reads_done;
    wire [127:0] fail_expected,fail_actual;
    wire seq_enable,seq_rst_n,loop_running,loop_failed;
    wire [31:0] completed;
    wire [3:0] first_error;
    bist_loop_ctrl u_loop(.clk(clk_sd),.rst_n(run_rst_n),.seq_done(done),.seq_passed(passed),
        .seq_error(error_code),.seq_enable(seq_enable),.running(loop_running),
        .completed(completed),.failed(loop_failed),.first_error(first_error));
    // Preserve falling-edge reset release for positive-edge BIST consumers.
    reset_release #(.RELEASE_FALLING_EDGE(1)) u_seq_reset(.clk(clk_sd),
        .async_n(run_rst_n && seq_enable),.rst_n(seq_rst_n));
    sdram_bist_seq u_bist(.clk(clk_sd),.rst_n(seq_rst_n),.init_done(init_done),.ctrl_idle(ctrl_idle),
        .refresh_count(refresh_count),.req_valid(req_valid),.req_we(req_we),.req_bank(req_bank),
        .req_row(req_row),.req_col(req_col),.req_wdata(req_wdata),.req_ready(req_ready),
        .rsp_valid(rsp_valid),.rsp_rdata(rsp_rdata),.done(done),.passed(passed),.error_code(error_code),
        .fail_burst(fail_burst),.fail_round(fail_round),.fail_expected(fail_expected),.fail_actual(fail_actual),
        .burst_cnt(burst_cnt),.writes_done(writes_done),.reads_done(reads_done),.phase(phase),.test_round(test_round));
    reg [24:0] heartbeat;
    always @(posedge clk_sd or negedge base_rst_n)
        if(!base_rst_n) heartbeat<=0;else heartbeat<=heartbeat+1'b1;
    wire [7:0] status_leds;
    bist_loop_led u_encode(.heartbeat(heartbeat[24]),.running(loop_running),.failed(loop_failed),
        .completed(completed),.first_error(first_error),.leds(status_leds));
    bist_status_595 #(.WIDTH(8)) u_status(.clk(clk_sd),.rst_n(base_rst_n),.data(status_leds),
        .sclk(led_sclk),.dout(led_dout),.latch(led_latch));
endmodule
