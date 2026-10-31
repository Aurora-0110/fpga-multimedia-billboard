`timescale 1ns/1ps
//--------------------------------------------------------------------------------
// sdram_ctrl.v -- EG4S20NG88 片内 2M x 32 SDR SDRAM 控制器（视频带宽版）
//
//   与诊断版 (6MHz, BL=1) 的区别:
//     - 工作时钟 49.5MHz, BL=4, open-page (行命中不再 ACT)
//     - 一次请求搬 4 个字 (128bit), 行/列/刷新/预充在同一个 FSM 里仲裁
//     - v041: accept-time row lookup + last-word response bypass.
//       Keep CL/BL, RD_WAIT and all physical recovery timings unchanged.
//       Throughput and correctness are simulation results, NOT PHY acceptance.
//
//   片内 SDRAM: 4 bank x 2048 row x 256 col x 32bit = 2M 字 = 8MB
//   字地址 21bit : {bank[1:0], row[10:0], col[7:0]}
//   突发地址 19bit: {bank[1:0], row[10:0], col[7:2]}
//
//   时序 (49.5MHz, 20.2ns/拍, 取整到拍, 各留 1 拍余量):
//     tRCD=2  tRP=2  tWR=2  tRFC=3  CL=3
//--------------------------------------------------------------------------------
module sdram_ctrl #(
    parameter integer T_RCD        = 2,
    parameter integer T_RP         = 2,
    parameter integer T_WR         = 2,
    parameter integer T_RFC        = 3,
    parameter integer REFRESH_CLKS = 772,   // 15.6us @ 49.5MHz (4096 次/64ms, 2048 行两轮)
    parameter integer RD_WAIT      = 2      // v039/v040 SAME-EDGE bus-model anchor regression; hardware still unverified
) (
    input  wire         clk,
    input  wire         rst_n,

    // 请求接口: 一次 4 字 (128bit)
    input  wire         req_valid,
    input  wire         req_we,
    input  wire [1:0]   req_bank,
    input  wire [10:0]  req_row,
    input  wire [5:0]   req_col,      // col[7:2]
    input  wire [127:0] req_wdata,
    output wire         idle, // No accepted transaction/ACK/response pending.
    output reg          req_ready,    // 接受请求时给 1 拍

    output reg          rsp_valid,
    output reg  [127:0] rsp_rdata,

    output reg          init_done,
    output reg  [31:0]  refresh_count,

    // SDRAM 引脚
    output reg          mem_cke,
    output reg          mem_cs_n,
    output reg          mem_ras_n,
    output reg          mem_cas_n,
    output reg          mem_we_n,
    output reg  [10:0]  mem_addr,
    output reg  [1:0]   mem_ba,
    output wire [3:0]   mem_dm,
    output reg  [31:0]  dq_out,
    output reg          dq_oe,
    input  wire [31:0]  dq_in
);

    localparam S_BOOT    = 5'd0,
               S_CKE_W   = 5'd1,
               S_PRE_A   = 5'd2,
               S_PRE_A_W = 5'd3,
               S_REF_I   = 5'd4,
               S_REF_I_W = 5'd5,
               S_MRS     = 5'd6,
               S_MRS_W   = 5'd7,
               S_IDLE    = 5'd8,
               S_CHK     = 5'd9,
               S_PRE_B   = 5'd10,
               S_ACT     = 5'd11,
               S_ISSUE   = 5'd12,
               S_RD_W    = 5'd13,
               S_RD_D    = 5'd14,
               S_WR_D    = 5'd15,
               S_WR_END  = 5'd16,
               S_RF_PRE  = 5'd17,
               S_RF_GO   = 5'd18,
               S_DONE    = 5'd19;

    // 模式寄存器: BL=4 (A2..A0=010), 顺序 (A3=0), CL=3 (A6..A4=011)
    localparam [10:0] MRS_VAL = 11'b000_0_011_0_010;
    localparam [15:0] RFC     = REFRESH_CLKS;

    reg [4:0]  state;
    reg [15:0] wait_cnt;

    // 请求锁存
    reg         we_q;
    reg [1:0]   bank_q;
    reg [10:0]  row_q;
    reg [5:0]   col_q;
    reg [127:0] wd_q;

    // 行打开状态 (4 个 bank 用标量寄存器, 避免被综合成 RAM)
    reg [3:0]  open_v;
    reg [10:0] open_row0, open_row1, open_row2, open_row3;

    wire [10:0] cur_open_row = (bank_q == 2'd0) ? open_row0 :
                               (bank_q == 2'd1) ? open_row1 :
                               (bank_q == 2'd2) ? open_row2 : open_row3;
    wire        cur_open     = open_v[bank_q];

    // Lookup the incoming address on acceptance (the latched address is still
    // used by all command states). This removes only an internal FSM bubble.
    wire [10:0] incoming_open_row = (req_bank == 0) ? open_row0 :
                                   (req_bank == 1) ? open_row1 :
                                   (req_bank == 2) ? open_row2 : open_row3;

    // 读/写数据移位
    reg [127:0] sh;
    reg [2:0]   dcnt;

    // 刷新
    reg [15:0] ref_age;
    reg        ref_pending;

    assign mem_dm = 4'b0000;

    // 常量引脚
    assign idle = init_done && (state == S_IDLE) && !req_ready && !rsp_valid;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mem_cke  <= 1'b0;
            mem_cs_n <= 1'b0;
        end else begin
            mem_cke  <= 1'b1;
            mem_cs_n <= 1'b0;
        end
    end

    // 刷新年龄: 只产生 tick, ref_pending 由主状态机维护 (避免多驱动)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)                        ref_age <= 16'd0;
        else if (ref_age >= RFC)           ref_age <= 16'd0;
        else                               ref_age <= ref_age + 16'd1;
    end
    wire ref_tick = (ref_age == RFC);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state         <= S_BOOT;
            wait_cnt      <= 16'd0;
            req_ready     <= 1'b0;
            rsp_valid     <= 1'b0;
            rsp_rdata     <= 128'd0;
            init_done     <= 1'b0;
            refresh_count <= 32'd0;
            mem_ras_n     <= 1'b1;
            mem_cas_n     <= 1'b1;
            mem_we_n      <= 1'b1;
            mem_addr      <= 11'd0;
            mem_ba        <= 2'd0;
            dq_out        <= 32'd0;
            dq_oe         <= 1'b0;
            we_q          <= 1'b0;
            bank_q        <= 2'd0;
            row_q         <= 11'd0;
            col_q         <= 6'd0;
            wd_q          <= 128'd0;
            sh            <= 128'd0;
            dcnt          <= 3'd0;
            open_v        <= 4'd0;
            open_row0     <= 11'd0;
            open_row1     <= 11'd0;
            open_row2     <= 11'd0;
            open_row3     <= 11'd0;
            ref_pending   <= 1'b0;
        end else begin
            req_ready <= 1'b0;
            rsp_valid <= 1'b0;
            if (ref_tick) ref_pending <= 1'b1;

            case (state)
            //--------------------------------------------- 上电初始化
            S_BOOT: begin
                wait_cnt <= wait_cnt + 16'd1;
                if (wait_cnt == 16'h7FFF) begin      // ~0.66ms @49.5MHz
                    wait_cnt <= 16'd0;
                    state    <= S_CKE_W;
                end
            end

            S_CKE_W: begin
                wait_cnt <= wait_cnt + 16'd1;
                if (wait_cnt == 16'h00FF) begin
                    wait_cnt <= 16'd0;
                    state    <= S_PRE_A;
                end
            end

            S_PRE_A: begin
                mem_ras_n <= 1'b0; mem_cas_n <= 1'b1; mem_we_n <= 1'b0;  // PRE ALL
                mem_addr  <= 11'b100_0000_0000;
                mem_ba    <= 2'd0;
                wait_cnt  <= 16'd0;
                state     <= S_PRE_A_W;
            end

            S_PRE_A_W: begin
                mem_ras_n <= 1'b1; mem_cas_n <= 1'b1; mem_we_n <= 1'b1;
                wait_cnt  <= wait_cnt + 16'd1;
                if (wait_cnt >= T_RP) begin
                    wait_cnt <= 16'd0;
                    state    <= S_REF_I;
                end
            end

            S_REF_I: begin
                mem_ras_n <= 1'b0; mem_cas_n <= 1'b0; mem_we_n <= 1'b1;  // AREF
                mem_ba    <= 2'd0;
                mem_addr  <= 11'd0;
                wait_cnt  <= 16'd0;
                state     <= S_REF_I_W;
            end

            S_REF_I_W: begin
                mem_ras_n <= 1'b1; mem_cas_n <= 1'b1; mem_we_n <= 1'b1;
                wait_cnt  <= wait_cnt + 16'd1;
                if (wait_cnt >= T_RFC) begin
                    wait_cnt <= 16'd0;
                    if (refresh_count == 32'd1) begin
                        state <= S_MRS;                     // 两次 AREF 后写模式寄存器
                    end else begin
                        refresh_count <= refresh_count + 32'd1;
                        state         <= S_REF_I;
                    end
                end
            end

            S_MRS: begin
                mem_ras_n <= 1'b0; mem_cas_n <= 1'b0; mem_we_n <= 1'b0;  // MRS
                mem_ba    <= 2'd0;
                mem_addr  <= MRS_VAL;
                wait_cnt  <= 16'd0;
                state     <= S_MRS_W;
            end

            S_MRS_W: begin
                mem_ras_n <= 1'b1; mem_cas_n <= 1'b1; mem_we_n <= 1'b1;
                wait_cnt  <= wait_cnt + 16'd1;
                if (wait_cnt >= T_RCD) begin
                    wait_cnt      <= 16'd0;
                    refresh_count <= 32'd0;
                    ref_pending   <= 1'b0;
                    init_done     <= 1'b1;
                    state         <= S_IDLE;
                end
            end

            //--------------------------------------------- 主循环
            S_IDLE: begin
                if (ref_pending || ref_tick) begin
                    ref_pending <= 1'b0;
                    state       <= S_RF_PRE;
                end else if (req_valid) begin
                    we_q      <= req_we;
                    bank_q    <= req_bank;
                    row_q     <= req_row;
                    col_q     <= req_col;
                    wd_q      <= req_wdata;
                    req_ready <= 1'b1;
                    wait_cnt  <= 16'd0;
                    if (open_v[req_bank] && incoming_open_row == req_row)
                        state <= S_ISSUE;
                    else if (open_v[req_bank]) state <= S_PRE_B;
                    else state <= S_ACT;
                end
            end

            S_CHK: begin
                wait_cnt <= 16'd0;
                if (cur_open && (cur_open_row == row_q)) begin
                    state <= S_ISSUE;          // 行命中
                end else if (cur_open) begin
                    state <= S_PRE_B;          // 换行: 先预充
                end else begin
                    state <= S_ACT;            // 未打开: 先激活
                end
            end

            S_PRE_B: begin
                mem_ras_n <= (wait_cnt == 16'd0) ? 1'b0 : 1'b1;
                mem_cas_n <= 1'b1;
                mem_we_n  <= (wait_cnt == 16'd0) ? 1'b0 : 1'b1;
                mem_addr  <= 11'd0;                        // A10=0: 单 bank 预充（BA 选 bank）
                                                           // 注意：写 {1'b0,row_q} 会把 A10 变成
                                                           // row_q[10]，等于 PRE ALL 却只清了
                                                           // 一个 bank 的 open_v，后面会误判行打开
                mem_ba    <= bank_q;
                if (wait_cnt == 16'd0) open_v[bank_q] <= 1'b0;
                wait_cnt  <= wait_cnt + 16'd1;
                if (wait_cnt >= T_RP) begin
                    wait_cnt <= 16'd0;
                    state    <= S_ACT;
                end
            end

            S_ACT: begin
                mem_ras_n <= (wait_cnt == 16'd0) ? 1'b0 : 1'b1;
                mem_cas_n <= 1'b1;
                mem_we_n  <= 1'b1;
                mem_addr  <= row_q;
                mem_ba    <= bank_q;
                if (wait_cnt == 16'd0) begin
                    open_v[bank_q] <= 1'b1;
                    case (bank_q)
                    2'd0:    open_row0 <= row_q;
                    2'd1:    open_row1 <= row_q;
                    2'd2:    open_row2 <= row_q;
                    default: open_row3 <= row_q;
                    endcase
                end
                wait_cnt <= wait_cnt + 16'd1;
                if (wait_cnt >= T_RCD) begin
                    wait_cnt <= 16'd0;
                    state    <= S_ISSUE;
                end
            end

            S_ISSUE: begin
                mem_ba <= bank_q;
                if (we_q) begin
                    mem_ras_n <= 1'b1; mem_cas_n <= 1'b0; mem_we_n <= 1'b0;  // WRITE
                    mem_addr  <= {3'b000, col_q, 2'b00};                     // A7..A2
                    dq_out    <= wd_q[31:0];
                    dq_oe     <= 1'b1;
                    sh        <= wd_q;
                    dcnt      <= 3'd1;
                    state     <= S_WR_D;
                end else begin
                    mem_ras_n <= 1'b1; mem_cas_n <= 1'b0; mem_we_n <= 1'b1;  // READ
                    mem_addr  <= {3'b000, col_q, 2'b00};
                    wait_cnt  <= 16'd0;
                    state     <= S_RD_W;
                end
            end

            S_RD_W: begin
                mem_ras_n <= 1'b1; mem_cas_n <= 1'b1; mem_we_n <= 1'b1;
                wait_cnt  <= wait_cnt + 16'd1;
                if (wait_cnt >= RD_WAIT) begin
                    wait_cnt <= 16'd0;
                    dcnt     <= 3'd0;
                    state    <= S_RD_D;
                end
            end

            S_RD_D: begin
                mem_ras_n <= 1'b1; mem_cas_n <= 1'b1; mem_we_n <= 1'b1;
                sh[32*dcnt +: 32] <= dq_in;
                dcnt <= dcnt + 3'd1;
                if (dcnt == 3'd3) begin
                    // sh[127:96] is being written by NBA on this edge, so
                    // explicitly bypass dq_in rather than return stale sh.
                    rsp_rdata <= {dq_in, sh[95:0]};
                    rsp_valid <= 1'b1;
                    state <= S_IDLE;
                end
            end

            S_WR_D: begin
                mem_ras_n <= 1'b1; mem_cas_n <= 1'b1; mem_we_n <= 1'b1;
                dq_out <= sh[32*dcnt +: 32];
                dcnt   <= dcnt + 3'd1;
                if (dcnt == 3'd3) state <= S_WR_END;
            end

            S_WR_END: begin
                dq_oe    <= 1'b0;
                dq_out   <= 32'd0;
                wait_cnt <= wait_cnt + 16'd1;
                if (wait_cnt >= T_WR) begin
                    wait_cnt <= 16'd0;
                    state    <= S_IDLE;
                end
            end

            S_DONE: begin
                mem_ras_n <= 1'b1; mem_cas_n <= 1'b1; mem_we_n <= 1'b1;
                rsp_rdata <= sh;
                rsp_valid <= 1'b1;
                state     <= S_IDLE;
            end

            //--------------------------------------------- 刷新
            S_RF_PRE: begin
                mem_ras_n <= 1'b0; mem_cas_n <= 1'b1; mem_we_n <= 1'b0;  // PRE ALL
                mem_addr  <= 11'b100_0000_0000;
                mem_ba    <= 2'd0;
                open_v    <= 4'b0000;
                wait_cnt  <= 16'd0;
                state     <= S_RF_GO;
            end

            S_RF_GO: begin
                if (wait_cnt < T_RP) begin
                    mem_ras_n <= 1'b1; mem_cas_n <= 1'b1; mem_we_n <= 1'b1;
                    wait_cnt  <= wait_cnt + 16'd1;
                end else if (wait_cnt < T_RP + 16'd1) begin
                    mem_ras_n <= 1'b0; mem_cas_n <= 1'b0; mem_we_n <= 1'b1;  // AREF
                    mem_addr  <= 11'd0;
                    mem_ba    <= 2'd0;
                    wait_cnt  <= wait_cnt + 16'd1;
                end else begin
                    mem_ras_n <= 1'b1; mem_cas_n <= 1'b1; mem_we_n <= 1'b1;
                    wait_cnt  <= wait_cnt + 16'd1;
                    if (wait_cnt >= T_RP + 16'd1 + T_RFC) begin
                        wait_cnt      <= 16'd0;
                        refresh_count <= refresh_count + 32'd1;
                        state         <= S_IDLE;
                    end
                end
            end

            default: state <= S_IDLE;
            endcase
        end
    end
endmodule
