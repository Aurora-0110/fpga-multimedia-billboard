`timescale 1ns / 1ps
//--------------------------------------------------------------------------------
// tmds_encoder.v —— DVI/HDMI 的 8b/10b 编码器（TMDS）
//
// 参考：Digital Visual Interface Rev 1.0, Section 3.3.3（TMDS Encoding Algorithm）
// 每像素 8bit 数据 -> 10bit 编码，保证直流平衡与跳变次数。
//
//   de=0（消隐期）：输出 4 个固定控制字（同步信息就藏在这里）
//         c1 c0 = 00 -> 10'b1101010100
//                 01 -> 10'b0010101011
//                 10 -> 10'b0101010100
//                 11 -> 10'b1010101011
//   de=1（有效像素）：先做“最少跳变”映射得到 q_m，再做 DC 平衡得到 q
//
// 三个通道各用一个编码器：R(蓝)通道的 c1/vs、c0/hs 承载行场同步。
//--------------------------------------------------------------------------------
module tmds_encoder (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  din,     // 8bit 像素/控制
    input  wire        de,      // 数据有效
    input  wire [1:0]  c,       // 消隐期控制位 {c1,c0}
    output reg  [9:0]  q        // 10bit TMDS 码
);

    // ---- 第一级：8bit -> 9bit，尽量减少跳变 ----
    reg [3:0] n1d;              // din 中 1 的个数
    integer   i;
    always @(*) begin
        n1d = 4'd0;
        for (i = 0; i < 8; i = i + 1)
            n1d = n1d + din[i];
    end

    wire use_xnor = (n1d > 4'd4) || ((n1d == 4'd4) && (din[0] == 1'b0));

    reg [8:0] q_m;
    always @(*) begin
        q_m[0] = din[0];
        for (i = 1; i < 8; i = i + 1)
            q_m[i] = use_xnor ? ~(q_m[i-1] ^ din[i]) : (q_m[i-1] ^ din[i]);
        q_m[8] = ~use_xnor;
    end

    // q_m 中 1 / 0 的个数
    reg [3:0] n1q_m, n0q_m;
    always @(*) begin
        n1q_m = 4'd0;
        n0q_m = 4'd0;
        for (i = 0; i < 8; i = i + 1) begin
            n1q_m = n1q_m +  q_m[i];
            n0q_m = n0q_m + ~q_m[i];
        end
    end

    // ---- 第二级：DC 平衡，用 cnt 记录累计不平衡 ----
    reg signed [4:0] cnt;       // -8..+8

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            q   <= 10'b1101010100;
            cnt <= 5'sd0;
        end else if (!de) begin
            case (c)
                2'b00: q <= 10'b1101010100;
                2'b01: q <= 10'b0010101011;
                2'b10: q <= 10'b0101010100;
                default: q <= 10'b1010101011;
            endcase
            cnt <= 5'sd0;
        end else if (cnt == 5'sd0 || n1q_m == n0q_m) begin
            q[9]   <= ~q_m[8];
            q[8]   <=  q_m[8];
            q[7:0] <=  q_m[8] ? q_m[7:0] : ~q_m[7:0];
            cnt    <=  q_m[8] ? (cnt + $signed({1'b0, n0q_m}) - $signed({1'b0, n1q_m}))
                              : (cnt + $signed({1'b0, n1q_m}) - $signed({1'b0, n0q_m}));
        end else begin
            if ((cnt > 5'sd0 && n1q_m > n0q_m) || (cnt < 5'sd0 && n0q_m > n1q_m)) begin
                q[9]   <= 1'b1;
                q[8]   <= q_m[8];
                q[7:0] <= ~q_m[7:0];
                cnt    <= cnt + $signed({1'b0, n0q_m}) - $signed({1'b0, n1q_m})
                              + $signed({4'b0000, q_m[8]});
            end else begin
                q[9]   <= 1'b0;
                q[8]   <= q_m[8];
                q[7:0] <= q_m[7:0];
                cnt    <= cnt + $signed({1'b0, n1q_m}) - $signed({1'b0, n0q_m})
                              - $signed({4'b0000, ~q_m[8]});
            end
        end
    end

endmodule
