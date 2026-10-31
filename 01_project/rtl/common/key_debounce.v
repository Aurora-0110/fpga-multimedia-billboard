`timescale 1ns / 1ps
//--------------------------------------------------------------------------------
// key_debounce.v —— 按键消抖 + 单周期脉冲
//   按键低有效。同步两级打拍后，稳定低电平持续 CNT 个时钟才认一次按下，
//   松开后同样要稳定 CNT 个时钟才能再次触发。
//--------------------------------------------------------------------------------
module key_debounce #(
    parameter integer CNT = 25000       // 24MHz 下约 1ms
) (
    input  wire clk,
    input  wire rst_n,
    input  wire key_n,                  // 低有效
    output reg  press                   // 单周期脉冲
);
    reg [1:0]  sync;
    reg [15:0] cnt;
    reg        key_state;               // 1=松开, 0=按下（已消抖）

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sync      <= 2'b11;
            cnt       <= 16'd0;
            key_state <= 1'b1;
            press     <= 1'b0;
        end else begin
            sync  <= {sync[0], key_n};
            press <= 1'b0;

            if (sync[1] != key_state) begin
                if (cnt == CNT - 1) begin
                    cnt       <= 16'd0;
                    key_state <= sync[1];
                    if (sync[1] == 1'b0)
                        press <= 1'b1;      // 按下沿
                end else begin
                    cnt <= cnt + 16'd1;
                end
            end else begin
                cnt <= 16'd0;
            end
        end
    end
endmodule
