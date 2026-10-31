`timescale 1ns/1ps
// Static diagnostic epoch: RESET -> WRITE -> READ. No read/write arbitration.
// restart stops NEW accepts, drains the accepted transaction (including write
// recovery/read response), THEN asserts both FIFO-domain resets together.
module fb_session_ctrl #(parameter integer RESET_CYCLES=16)(
    input wire clk, rst_n, restart, frame_ready, ctrl_idle,
    output wire pipe_run, owner_write, owner_read, allow_req,
    output wire read_enable,
    output wire [1:0] phase
);
    localparam RESET=0, WRITE=1, READ=2, DRAIN=3;
    reg [1:0] state;
    reg drain_write;
    reg [15:0] hold_count;
    assign phase=state;
    assign pipe_run=(state!=RESET) && rst_n;
    assign owner_write=(state==WRITE)||(state==DRAIN && drain_write);
    assign owner_read=(state==READ)||(state==DRAIN && !drain_write);
    assign allow_req=(state==WRITE || state==READ) && !restart;
    assign read_enable=(state==READ) && !restart;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin state<=RESET; hold_count<=0; drain_write<=1; end
        else case(state)
            RESET: if(hold_count>=RESET_CYCLES-1) begin state<=WRITE; hold_count<=0; end
                   else hold_count<=hold_count+1'b1;
            WRITE: if(restart) begin state<=DRAIN; drain_write<=1; end
                   else if(frame_ready && ctrl_idle) state<=READ;
            READ: if(restart) begin state<=DRAIN; drain_write<=0; end
            DRAIN: if(ctrl_idle) begin state<=RESET; hold_count<=0; end
            default: begin state<=RESET; hold_count<=0; end
        endcase
    end
endmodule
