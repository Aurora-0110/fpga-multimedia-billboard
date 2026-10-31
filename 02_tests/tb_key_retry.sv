`timescale 1ns/1ps
module tb_key_retry;
reg clk=0;always #10.101 clk=~clk;
reg rst=0,key=1;wire press;integer count=0;
key_debounce #(.CNT(49500)) dut(.clk(clk),.rst_n(rst),.key_n(key),.press(press));
always @(posedge clk)if(press)count=count+1;
task settle(input integer n);begin repeat(n)@(negedge clk);end endtask
initial begin
 settle(5);rst=1;settle(10);
 repeat(12)begin key=0;settle(100);key=1;settle(100);end
 if(count!=0)$fatal(1,"bounce accepted");
 key=0;settle(300000);if(count!=1)$fatal(1,"held press should trigger once %d",count);
 key=1;settle(50000);key=0;settle(50000);if(count!=2)$fatal(1,"second press missing");
 key=1;settle(50000);key=0;settle(50000);if(count!=3)$fatal(1,"third press missing");
 $display("PASS key_retry pulses=%0d bounce_rejected=1 long_hold_single_pulse=1 CNT=49500",count);$finish;
end
initial begin #20000000;$fatal(1,"key test timeout");end
endmodule
