`timescale 1ns/1ps
// v043: key retry and PLL loss reset BOTH client and SDRAM controller.
// Debouncer is outside retry reset, so a held key cannot cause a reset loop.
module bist_reset_ctrl #(
    parameter integer POR_CLKS=256, KEY_CLKS=49500, RETRY_CLKS=16
)(input wire clk_sd,locked,key_n,output wire base_rst_n,run_rst_n);
    // POR stays in the memory clock domain: no 24MHz -> 49.5MHz recovery path.
    reg [15:0] por=16'd0;
    always @(posedge clk_sd or negedge locked)
        if(!locked) por<=0;
        else if(por<POR_CLKS) por<=por+1'b1;
    wire power_ok=(por>=POR_CLKS);
    reset_release #(.RELEASE_FALLING_EDGE(1)) u_base(.clk(clk_sd),.async_n(power_ok && locked),.rst_n(base_rst_n));
    wire press;
    key_debounce #(.CNT(KEY_CLKS)) u_key(.clk(clk_sd),.rst_n(base_rst_n),.key_n(key_n),.press(press));
    reg [15:0] retry;
    always @(posedge clk_sd or negedge base_rst_n)
        if(!base_rst_n) retry<=0;
        else if(press) retry<=RETRY_CLKS;
        else if(retry!=0) retry<=retry-1'b1;
    reset_release #(.RELEASE_FALLING_EDGE(1)) u_run(.clk(clk_sd),.async_n(base_rst_n && retry==0),.rst_n(run_rst_n));
endmodule
