`timescale 1ns/1ps
// Logical bit i is schematic LEDi (U9 Qi). No inversion: 1 means lit.
// LED0 heartbeat; LED1 RUN; LED2 PASS; LED3 FAIL; LED7..4 error nibble.
// Fail closed on inconsistent terminal inputs; code F means done=1/pass=0/code=0.
module bist_led_encode(
    input wire heartbeat,done,passed,input wire [3:0] error_code,
    output wire [7:0] leds
);
    wire good=done && passed && (error_code==0);
    wire bad=done && !good;
    wire [3:0] code=bad?((error_code==0)?4'hf:error_code):4'h0;
    assign leds={code,bad,good,!done,heartbeat};
endmodule
