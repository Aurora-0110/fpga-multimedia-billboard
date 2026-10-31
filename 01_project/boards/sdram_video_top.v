`timescale 1ns/1ps
// v040 STATIC diagnostic, not hardware accepted. 640x480 output retained.
// No concurrent sweep while reading; KEY0 drains/flushes/repaints the epoch.
module sdram_video_top (
    input  wire        clk24m,        // P13  24MHz 晶振
    input  wire [1:0]  key_n,         // P51/P52 低有效
    output wire        led_sclk,      // P59
    output wire        led_dout,      // P45
    output wire        led_latch,     // P57
    output wire        hdmi_clk_p,    // P47
    output wire [2:0]  hdmi_d_p       // P49/P55/P61
);

    //------------------------------------------------------------------ 时钟
    wire clk_sd, clk_24, locked_sd;
    wire clk_pix, clk_5x, locked_vid;

    pll_sdram u_pll_sd (
        .clk_in (clk24m),
        .rst_n  (1'b1),
        .clk_sd (clk_sd),      // 49.5MHz
        .clk_24 (clk_24),      // 24MHz（未用）
        .locked (locked_sd)
    );

    pll_wrap #(.FIN_MHZ(24)) u_pll_vid (
        .clk_in  (clk24m),
        .rst_n   (1'b1),
        .clk_pix (clk_pix),    // 25.2MHz
        .clk_5x  (clk_5x),     // 126MHz
        .clk_aux (),
        .locked  (locked_vid)
    );

    //------------------------------------------------------------------ 复位
    wire rst_sd_n, rst_pix_n;
    // Losing either PLL lock resets the whole session, not just one FIFO side.
    wire clocks_ok=locked_sd && locked_vid;
    reset_release u_reset_sd(.clk(clk_sd),.async_n(clocks_ok),.rst_n(rst_sd_n));
    reset_release u_reset_pix(.clk(clk_pix),.async_n(clocks_ok),.rst_n(rst_pix_n));

    //------------------------------------------------------------------ SDRAM 控制器
    wire         req_valid, req_we, req_ready, ctrl_idle;
    wire [1:0]   req_bank;
    wire [10:0]  req_row;
    wire [5:0]   req_col;
    wire [127:0] req_wdata;
    wire         rsp_valid;
    wire [127:0] rsp_rdata;

    wire         mem_cke, mem_cs_n, mem_ras_n, mem_cas_n, mem_we_n;
    wire [10:0]  mem_addr;
    wire [1:0]   mem_ba;
    wire [3:0]   mem_dm;
    wire [31:0]  dq_out, dq_in, dq_bus;
    wire         dq_oe;
    wire         init_done;
    wire [31:0]  refresh_count;

    assign dq_bus = dq_oe ? dq_out : 32'bz;
    assign dq_in  = dq_bus;

    sdram_ctrl #(
        .T_RCD        (2),
        .T_RP         (2),
        .T_WR         (2),
        .T_RFC        (3),
        .REFRESH_CLKS (772),
        .RD_WAIT      (2)          // CL=3：命令在 S_ISSUE 寄存、次拍到引脚，
                                   // +3 拍数据回来 = S_RD_W 的第 3 拍开始采样（RD_WAIT=2）
    ) u_ctrl (
        .clk           (clk_sd),
        .rst_n         (rst_sd_n),
        .req_valid     (req_valid),
        .req_we        (req_we),
        .req_bank      (req_bank),
        .req_row       (req_row),
        .req_col       (req_col),
        .req_wdata     (req_wdata),
        .req_ready     (req_ready),
        .idle          (ctrl_idle),
        .rsp_valid     (rsp_valid),
        .rsp_rdata     (rsp_rdata),
        .init_done     (init_done),
        .refresh_count (refresh_count),
        .mem_cke       (mem_cke),
        .mem_cs_n      (mem_cs_n),
        .mem_ras_n     (mem_ras_n),
        .mem_cas_n     (mem_cas_n),
        .mem_we_n      (mem_we_n),
        .mem_addr      (mem_addr),
        .mem_ba        (mem_ba),
        .mem_dm        (mem_dm),
        .dq_out        (dq_out),
        .dq_oe         (dq_oe),
        .dq_in         (dq_in)
    );

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

    //------------------------------------------------------------------ 按键 / 重画
    wire key0_press, key1_press;

    key_debounce #(.CNT(49500)) u_key0 (
        .clk (clk_sd), .rst_n (rst_sd_n), .key_n (key_n[0]), .press (key0_press)
    );
    key_debounce #(.CNT(49500)) u_key1 (
        .clk (clk_sd), .rst_n (rst_sd_n), .key_n (key_n[1]), .press (key1_press)
    );

    wire pipe_run, pipe_sd_n, pipe_pix_n;
    wire owner_write, owner_read, allow_req, read_enable;
    wire [1:0] session_phase;
    wire frame_ready;
    fb_session_ctrl u_session(
        .clk(clk_sd),.rst_n(rst_sd_n),.restart(key0_press),
        .frame_ready(frame_ready),.ctrl_idle(ctrl_idle),
        .pipe_run(pipe_run),.owner_write(owner_write),.owner_read(owner_read),
        .allow_req(allow_req),.read_enable(read_enable),.phase(session_phase));
    // Same assertion epoch for both sides; synchronous release in each domain.
    wire pipe_async_n=pipe_run && rst_sd_n && rst_pix_n;
    reset_release u_pipe_sd(.clk(clk_sd),.async_n(pipe_async_n),.rst_n(pipe_sd_n));
    reset_release u_pipe_pix(.clk(clk_pix),.async_n(pipe_async_n),.rst_n(pipe_pix_n));

    wire w_valid, w_ready, r_valid, r_ready;
    wire [1:0] w_bank, r_bank;
    wire [10:0] w_row, r_row;
    wire [5:0] w_col, r_col;
    wire [127:0] w_data;
    wire [11:0] sweep_y;
    fb_writer #(.ENABLE_SWEEP(0)) u_wr(
        .clk(clk_sd),.rst_n(pipe_sd_n),.init_done(init_done && owner_write),
        .restart(1'b0),.req_valid(w_valid),.req_bank(w_bank),.req_row(w_row),
        .req_col(w_col),.req_wdata(w_data),.req_ready(w_ready),
        .frame_ready(frame_ready),.sweep_y(sweep_y));

    wire fifo_we, fifo_full, fifo_empty, fifo_pop;
    wire [10:0] fifo_wused, fifo_rused;
    wire [31:0] fifo_wdata, fifo_rdata;
    fb_reader u_rd(
        .clk(clk_sd),.rst_n(pipe_sd_n),.enable(read_enable && init_done),
        .fifo_used({1'b0,fifo_wused}),.req_valid(r_valid),.req_bank(r_bank),
        .req_row(r_row),.req_col(r_col),.req_ready(r_ready),
        .rsp_valid(rsp_valid),.rsp_rdata(rsp_rdata),
        .fifo_we(fifo_we),.fifo_wdata(fifo_wdata));
    async_fifo #(.WIDTH(32),.AW(10)) u_fifo(
        .wclk(clk_sd),.wrst_n(pipe_sd_n),.wr_en(fifo_we),.wdata(fifo_wdata),
        .wfull(fifo_full),.wused(fifo_wused),
        .rclk(clk_pix),.rrst_n(pipe_pix_n),.rd_en(fifo_pop),.rdata(fifo_rdata),
        .rempty(fifo_empty),.rused(fifo_rused));

    // Owner is retained throughout DRAIN, including the registered acceptance ACK.
    assign req_valid=allow_req && ((owner_write && w_valid)||(owner_read && r_valid));
    assign req_we=owner_write;
    assign req_bank=owner_write?w_bank:r_bank;
    assign req_row=owner_write?w_row:r_row;
    assign req_col=owner_write?w_col:r_col;
    assign req_wdata=w_data;
    assign w_ready=req_ready && owner_write;
    assign r_ready=req_ready && owner_read;

    wire [11:0] x,y;
    wire de,hs,vs,frame_start;
    video_timing u_vt(.clk(clk_pix),.rst_n(rst_pix_n),.x(x),.y(y),
        .hs(hs),.vs(vs),.de(de),.frame_start(frame_start));
    reg [1:0] read_sync;
    always @(posedge clk_pix or negedge pipe_pix_n)
        if(!pipe_pix_n) read_sync<=0;
        else read_sync<={read_sync[0],read_enable};
    wire [23:0] px;
    wire de_d,hs_d,vs_d,display_running,display_fault;
    wire [15:0] underrun;
    fb_display_guard u_display(
        .clk(clk_pix),.rst_n(pipe_pix_n),.enable(read_sync[1]),
        .frame_start(frame_start),.de(de),.hs(hs),.vs(vs),
        .fifo_empty(fifo_empty),.fifo_used(fifo_rused),.fifo_data(fifo_rdata),
        .fifo_pop(fifo_pop),.rgb(px),.de_d(de_d),.hs_d(hs_d),.vs_d(vs_d),
        .running(display_running),.fault(display_fault),.underrun_count(underrun));
    hdmi_tx_wrap u_hdmi(
        .clk_pix(clk_pix),.clk_5x(clk_5x),.rst_n(rst_pix_n),
        .r(px[23:16]),.g(px[15:8]),.b(px[7:0]),.de(de_d),.hs(hs_d),.vs(vs_d),
        .tmds_clk_p(hdmi_clk_p),.tmds_clk_n(),.tmds_d_p(hdmi_d_p),.tmds_d_n());

    reg [24:0] hcnt;
    reg [1:0] fault_sync, running_sync;
    reg overflow_fault;
    always @(posedge clk_sd or negedge rst_sd_n)
        if(!rst_sd_n) hcnt<=0; else hcnt<=hcnt+1'b1;
    always @(posedge clk_sd or negedge pipe_sd_n)
        if(!pipe_sd_n) begin fault_sync<=0; running_sync<=0; overflow_fault<=0; end
        else begin
            fault_sync<={fault_sync[0],display_fault};
            running_sync<={running_sync[0],display_running};
            if(fifo_we && fifo_full) overflow_fault<=1;
        end
    // Logical bit order, not a claim about physical LED numbering/polarity.
    wire [15:0] led_data={init_done,frame_ready,hcnt[24],fault_sync[1],
        running_sync[1],overflow_fault,session_phase,8'h00};
    led_595 #(.CNT(200)) u_led(.clk(clk_sd),.rst_n(rst_sd_n),.data(led_data),
        .sclk(led_sclk),.dout(led_dout),.latch(led_latch));
    wire unused=(|clk_24)|(|refresh_count)|key1_press|(|underrun)|(|x)|(|y)|(|sweep_y);
endmodule
