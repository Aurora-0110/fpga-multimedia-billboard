`timescale 1ns/1ps
// One outstanding burst, plus one 128-bit unpack buffer. req_ready is a
// registered acceptance ACK, NOT a combinational ready. A response may release
// the outstanding slot on the same edge that the next request is accepted.
// Reserve 8 free FIFO words (one response + one new burst). No new request
// while unpacking; the four writes run independently of SDRAM latency.
module fb_reader #(
    parameter integer LAST_BURST = 76799
) (
    input wire clk, rst_n, enable,
    input wire [11:0] fifo_used,
    output wire req_valid,
    output wire [1:0] req_bank,
    output wire [10:0] req_row,
    output wire [5:0] req_col,
    input wire req_ready,
    input wire rsp_valid,
    input wire [127:0] rsp_rdata,
    output wire fifo_we,
    output wire [31:0] fifo_wdata
);
    reg pending, pushing;
    reg [18:0] baddr;
    reg [127:0] sh;
    reg [1:0] pcnt;
    // Saturation prevents unsigned underflow if an invalid occupancy is seen.
    wire room = (fifo_used <= 12'd1016);
    assign req_valid = enable && room && !pushing && (!pending || rsp_valid);
    assign req_bank = baddr[18:17];
    assign req_row = baddr[16:6];
    assign req_col = baddr[5:0];
    assign fifo_we = pushing;
    assign fifo_wdata = sh[31:0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pending<=0; pushing<=0; baddr<=0; sh<=0; pcnt<=0;
        end else begin
            if (pushing) begin
                sh <= {32'd0, sh[127:32]};
                pcnt <= pcnt + 1'b1;
                if (pcnt == 2'd3) pushing <= 0;
            end
            if (rsp_valid && pending) begin
                sh <= rsp_rdata;
                pcnt <= 0;
                pushing <= 1;
                pending <= 0;
            end
            // ACK wins over response if both are observed together. Advance
            // on acceptance even if enable just fell: the burst must drain.
            if (req_ready) begin
                pending <= 1;
                baddr <= (baddr == LAST_BURST) ? 19'd0 : baddr + 1'b1;
            end
        end
    end
endmodule
