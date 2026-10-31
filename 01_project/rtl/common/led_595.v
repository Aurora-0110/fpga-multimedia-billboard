`timescale 1ns / 1ps
//--------------------------------------------------------------------------------
// led_595.v —— 板载 74HC595 移位寄存器驱动（3 线：SCLK / DOUT / LATCH）
//   16bit 数据 MSB 先出，送完后给一个 LATCH 脉冲把数据搬到输出端。
//   这台 AN88_VIP 板上 595 串了多片（数码管段/位），这里只验证"能把数据打出去"。
//--------------------------------------------------------------------------------
module led_595 #(
    parameter integer CNT = 20          // SCLK 半周期 = CNT 个 clk
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [15:0] data,
    output reg         sclk,
    output reg         dout,
    output reg         latch
);
    localparam S_IDLE  = 2'd0,
               S_SHIFT = 2'd1,
               S_LATCH = 2'd2;

    reg [1:0]  st;
    reg [4:0]  bit_idx;
    reg [7:0]  div;
    reg        sclk_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st      <= S_IDLE;
            bit_idx <= 5'd0;
            div     <= 8'd0;
            sclk    <= 1'b0;
            dout    <= 1'b0;
            latch   <= 1'b0;
            sclk_r  <= 1'b0;
        end else begin
            latch <= 1'b0;
            case (st)
                S_IDLE: begin
                    bit_idx <= 5'd0;
                    div     <= 8'd0;
                    sclk    <= 1'b0;
                    st      <= S_SHIFT;
                end

                S_SHIFT: begin
                    if (div == CNT - 1) begin
                        div <= 8'd0;
                        if (!sclk_r) begin
                            // 上升沿之前先摆好数据
                            dout   <= data[15 - bit_idx];
                            sclk   <= 1'b1;
                            sclk_r <= 1'b1;
                        end else begin
                            sclk   <= 1'b0;
                            sclk_r <= 1'b0;
                            if (bit_idx == 5'd15) begin
                                bit_idx <= 5'd0;
                                st      <= S_LATCH;
                            end else begin
                                bit_idx <= bit_idx + 5'd1;
                            end
                        end
                    end else begin
                        div <= div + 8'd1;
                    end
                end

                S_LATCH: begin
                    latch <= 1'b1;
                    st    <= S_IDLE;
                end

                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
