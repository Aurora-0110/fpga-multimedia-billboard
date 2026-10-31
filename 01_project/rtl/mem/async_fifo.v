`timescale 1ns/1ps
//--------------------------------------------------------------------------------
// async_fifo.v -- 双时钟 FIFO（格雷码指针 + 两级同步）
//
//   用途：SDRAM 侧 49.5MHz 写、像素侧 25.2MHz 读，两个时钟不同源，必须走异步 FIFO。
//   深度 2^AW 个字（AW=10 -> 1024 字 = 4KB），一个字 = 一个像素 {8'h00,R,G,B}。
//
//   注意：wfull / rempty 必须**寄存**输出。若组合式地用 (wr_en && !wfull) 去算
//   下一拍指针，再拿下一拍指针算 wfull，就构成组合环（TD 会报 TMR-2507/2509）。
//--------------------------------------------------------------------------------
module async_fifo #(
    parameter integer WIDTH = 32,
    parameter integer AW    = 10
) (
    // ---- 写时钟域 ----
    input  wire             wclk,
    input  wire             wrst_n,
    input  wire             wr_en,
    input  wire [WIDTH-1:0] wdata,
    output reg              wfull,
    output reg  [AW:0]      wused,

    // ---- 读时钟域 ----
    input  wire             rclk,
    input  wire             rrst_n,
    input  wire             rd_en,
    output reg  [WIDTH-1:0] rdata,
    output reg              rempty,
    output reg  [AW:0]      rused
);

    localparam integer DEPTH = (1 << AW);

    reg [WIDTH-1:0] mem [0:DEPTH-1];

    reg  [AW:0] wbin, wgray, rbin, rgray;
    reg  [AW:0] wq1_rgray, wq2_rgray;   // 读指针同步到写域
    reg  [AW:0] rq1_wgray, rq2_wgray;   // 写指针同步到读域

    wire winc = wr_en & ~wfull;
    wire rinc = rd_en & ~rempty;

    wire [AW:0] wbin_nxt  = wbin + {{AW{1'b0}}, winc};
    wire [AW:0] wgray_nxt = (wbin_nxt >> 1) ^ wbin_nxt;
    wire [AW:0] rbin_nxt  = rbin + {{AW{1'b0}}, rinc};
    wire [AW:0] rgray_nxt = (rbin_nxt >> 1) ^ rbin_nxt;

    wire wfull_nxt  = (wgray_nxt == {~wq2_rgray[AW:AW-1], wq2_rgray[AW-2:0]});
    wire rempty_nxt = (rgray_nxt == rq2_wgray);

    function [AW:0] gray2bin(input [AW:0] g);
        integer shift;
        reg [AW:0] prefix;
        begin
            // V126: parallel-prefix XOR. No new register or occupancy latency.
            // Every stage doubles the suffix width; AW+1 bits remain exact.
            prefix = g;
            for (shift = 1; shift <= AW; shift = shift * 2)
                prefix = prefix ^ (prefix >> shift);
            gray2bin = prefix;
        end
    endfunction

    // ---------------- 写侧 ----------------
    always @(posedge wclk) begin
        if (winc) mem[wbin[AW-1:0]] <= wdata;
    end

    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            wbin  <= {(AW+1){1'b0}};
            wgray <= {(AW+1){1'b0}};
            wfull <= 1'b0;
        end else begin
            wbin  <= wbin_nxt;
            wgray <= wgray_nxt;
            wfull <= wfull_nxt;
        end
    end

    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            wq1_rgray <= {(AW+1){1'b0}};
            wq2_rgray <= {(AW+1){1'b0}};
        end else begin
            wq1_rgray <= rgray;
            wq2_rgray <= wq1_rgray;
        end
    end

    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) wused <= {(AW+1){1'b0}};
        else         wused <= wbin - gray2bin(wq2_rgray);
    end

    // ---------------- 读侧 ----------------
    always @(posedge rclk) begin
        if (rinc) rdata <= mem[rbin[AW-1:0]];
    end

    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            rbin   <= {(AW+1){1'b0}};
            rgray  <= {(AW+1){1'b0}};
            rempty <= 1'b1;
        end else begin
            rbin   <= rbin_nxt;
            rgray  <= rgray_nxt;
            rempty <= rempty_nxt;
        end
    end

    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            rq1_wgray <= {(AW+1){1'b0}};
            rq2_wgray <= {(AW+1){1'b0}};
        end else begin
            rq1_wgray <= wgray;
            rq2_wgray <= rq1_wgray;
        end
    end

    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) rused <= {(AW+1){1'b0}};
        else         rused <= gray2bin(rq2_wgray) - rbin;
    end

endmodule
