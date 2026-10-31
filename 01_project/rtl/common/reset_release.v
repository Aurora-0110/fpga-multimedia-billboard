`timescale 1ns/1ps
// Asynchronous assertion with local-clock deassertion. STAGES must be >= 2.
// Falling release gives positive-edge consumers half a clock for recovery/removal.
// Default preserves legacy positive-edge behavior; enabled only for BIST.
module reset_release #(
    parameter integer STAGES=4,
    parameter integer RELEASE_FALLING_EDGE=0
)(input wire clk, async_n, output wire rst_n);
    generate
        if (RELEASE_FALLING_EDGE != 0) begin: g_falling
            reg [STAGES-2:0] sync_q = {(STAGES-1){1'b0}};
            reg release_q = 1'b0;
            always @(posedge clk or negedge async_n)
                if (!async_n) sync_q <= {(STAGES-1){1'b0}};
                else sync_q <= (sync_q << 1) | 1'b1;
            always @(negedge clk or negedge async_n)
                if (!async_n) release_q <= 1'b0;
                else release_q <= sync_q[STAGES-2];
            assign rst_n = release_q;
        end else begin: g_rising
            reg [STAGES-1:0] stages = {STAGES{1'b0}};
            always @(posedge clk or negedge async_n)
                if (!async_n) stages <= {STAGES{1'b0}};
                else stages <= (stages << 1) | 1'b1;
            assign rst_n = stages[STAGES-1];
        end
    endgenerate
endmodule
