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
// 三个通道各用一个编码器：B(蓝)通道的 c1/vs、c0/hs 承载行场同步。
//--------------------------------------------------------------------------------
module tmds_encoder #(parameter PREPARED_INPUT=0) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  din,     // 8bit 像素/控制
    input  wire        de,      // 数据有效
    input  wire [1:0]  c,       // 消隐期控制位 {c1,c0}
    output reg  [9:0]  q,       // 10bit TMDS 码
    input wire [8:0] q_m_in, input wire [3:0] ones_in
);

    // v100: balanced population counts and parallel prefix XORs.  This is
    // still ONE pixel clock of latency (including control symbols), not an
    // extra pipeline stage.  Audio packet/guard-band alignment is unchanged.
    wire [8:0] raw_qm;
    wire [3:0] raw_ones;
    tmds_prepare prepare(.din(din),.q_m(raw_qm),.n1q_m(raw_ones));
    wire [8:0] q_m=PREPARED_INPUT?q_m_in:raw_qm;
    wire [3:0] n1q_m=PREPARED_INPUT?ones_in:raw_ones;
    wire use_xnor=!q_m[8];
    reg signed [4:0] cnt;
    wire neutral = (cnt == 5'sd0) || (n1q_m == 4'd4);
    wire same_sign = (!cnt[4] && cnt != 5'sd0 && n1q_m > 4'd4)
                  || ( cnt[4] && n1q_m < 4'd4);
    wire invert_bits = neutral ? use_xnor : same_sign;

    // The TEN-bit emitted disparity is always even.  Half of its delta
    // is (n1-4-use_xnor) when not inverted, (5-n1-use_xnor) otherwise.
    // Add only those four upper bits and preserve cnt[0].  This is
    // modulo-32 identical for ALL 32 cnt encodings, not only even states.
    // It replaces the original serial cnt+n1-n0+header carry chains.
    wire [3:0] delta_plain = n1q_m - 4'd4 - {3'b000,use_xnor};
    wire [3:0] delta_invert = 4'd5 - n1q_m - {3'b000,use_xnor};
    wire [3:0] delta_half = invert_bits ? delta_invert : delta_plain;
    wire [3:0] count_upper_next = cnt[4:1] + delta_half;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            q <= 10'b1101010100;
            cnt <= 5'sd0;
        end else if (!de) begin
            case (c)
                2'b00: q <= 10'b1101010100;
                2'b01: q <= 10'b0010101011;
                2'b10: q <= 10'b0101010100;
                default: q <= 10'b1010101011;
            endcase
            cnt <= 5'sd0;
        end else begin
            q <= {invert_bits,q_m[8],q_m[7:0] ^ {8{invert_bits}}};
            cnt <= {count_upper_next,cnt[0]};
        end
    end
endmodule

// v110 stage-1 preparation. The active HDMI wrapper moves this logic into
// the EXISTING input register boundary, so video, controls and audio islands
// keep precisely the former total latency. No new clock or timing exception.
module tmds_prepare(input [7:0] din,output [8:0] q_m,output [3:0] n1q_m);
    function [3:0] ones8;
        input [7:0] bits;
        reg [1:0] p0, p1, p2, p3;
        reg [2:0] lo, hi;
        begin
            p0 = {1'b0,bits[0]} + {1'b0,bits[1]};
            p1 = {1'b0,bits[2]} + {1'b0,bits[3]};
            p2 = {1'b0,bits[4]} + {1'b0,bits[5]};
            p3 = {1'b0,bits[6]} + {1'b0,bits[7]};
            lo = {1'b0,p0} + {1'b0,p1};
            hi = {1'b0,p2} + {1'b0,p3};
            ones8 = {1'b0,lo} + {1'b0,hi};
        end
    endfunction

    wire [3:0] n1d = ones8(din);
    wire use_xnor = (n1d > 4'd4) || ((n1d == 4'd4) && !din[0]);

    assign q_m[8] = !use_xnor;
    // Expanding qm[i]=qm[i-1] XOR din[i] XOR use_xnor removes
    // the seven serial conditional XOR/XNOR operations.  An odd number
    // of XNOR steps contributes exactly one inversion; even cancels.
    genvar k;
    generate for (k=0; k<8; k=k+1) begin : prefix
        if ((k % 2) != 0)
            assign q_m[k] = (^din[k:0]) ^ use_xnor;
        else
            assign q_m[k] = ^din[k:0];
    end endgenerate

    assign n1q_m = ones8(q_m[7:0]);
endmodule
