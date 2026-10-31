`timescale 1ns/1ps
// One real 74HC595, eight active-high LEDs. No invisible status bits.
// L0 heartbeat; L1 RUN; L2 >=1 successful loop in current session; L3 sticky FAIL.
// L7..L4: count modulo16 normally, FIRST error code when FAIL.
module bist_loop_led(
    input wire heartbeat,running,failed,
    input wire [31:0] completed,
    input wire [3:0] first_error,
    output wire [7:0] leds
);
    assign leds={failed?first_error:completed[3:0],failed,
                 (!failed && completed!=0),(!failed && running),heartbeat};
endmodule
