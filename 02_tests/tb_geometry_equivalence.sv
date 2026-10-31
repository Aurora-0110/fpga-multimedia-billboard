`timescale 1ns/1ps
module tb_geometry_equivalence;
reg clk=0,rst_n=0;always #10 clk=~clk;
wire old_mount,new_mount,old_done,new_done;wire[3:0] oe,ne;
fat32_bmp_probe_v056 old(.clk(clk),.rst_n(rst_n),.sd_ready(1'b0),.sd_read_done(1'b0),.sd_error(4'b0),.data_valid(1'b0),.data_index(9'b0),.data_byte(8'b0),.mounted(old_mount),.done(old_done),.error_code(oe));
fat32_bmp_probe dut(.clk(clk),.rst_n(rst_n),.sd_ready(1'b0),.sd_read_done(1'b0),.sd_error(4'b0),.data_valid(1'b0),.data_index(9'b0),.data_byte(8'b0),.mounted(new_mount),.done(new_done),.error_code(ne));
`define SET(F,V) old.F=V;dut.F=old.F;
integer i,seed=32'h57beef,pass=0,invalid=0;reg[31:0] v;
initial begin
 v=$urandom(seed);
 for(i=0;i<2048;i=i+1)begin
 rst_n=0;repeat(2)@(negedge clk);rst_n=1;
 `SET(jump,8'heb) `SET(bps,512) `SET(spc,1<<($urandom%8))
 `SET(reserved,32+($urandom%1024)) `SET(nfats,1+($urandom%2))
 `SET(fatsz,8192) `SET(root_entries,0) `SET(total16,0) `SET(fat16,0)
 `SET(fs_version,0) `SET(ext_flags,0) `SET(root0,2+($urandom%1024))
 `SET(partitioned,$urandom%2) `SET(partition_start,2048)
 v=(65525+($urandom%100000))*old.spc+old.reserved+old.nfats*old.fatsz;
 `SET(total32,v) `SET(partition_size,v)
 case(i%16)
 0:begin `SET(spc,3) end
 1:begin `SET(nfats,3) end
 2:begin `SET(total32,old.reserved+old.nfats*old.fatsz) end
 3:begin `SET(fatsz,1) end
 4:begin `SET(root0,32'hf0000002) end
 5:begin `SET(root0,1) end
 6:begin `SET(total32,32'hffffffff) end
 7:begin `SET(partition_start,32'hffff0000) end
 8:begin `SET(ext_flags,16'h0081) `SET(nfats,2) end
 9:begin `SET(ext_flags,16'h0082) end
 10:begin `SET(root0,old.total32) end
 11:begin `SET(partitioned,1) `SET(partition_size,old.total32-1) end
 12:begin `SET(fatsz,32'hffffffff) end
 13:begin `SET(total32,old.reserved+old.nfats*old.fatsz+65524*old.spc) end
 14:begin `SET(root0,32'h0fffffef) end
 default:begin end
 endcase
 old.state=5;dut.state=5;
 repeat(8)@(negedge clk);
 if({old_mount,old_done,oe}!=={new_mount,new_done,ne})$fatal(1,"geometry result i=%0d old=%b/%b/%h new=%b/%b/%h",i,old_mount,old_done,oe,new_mount,new_done,ne);
 if(old_mount)begin
 pass=pass+1;
 if({old.data_base,old.fat_base,old.cluster_max,old.read_lba,old.mounted_spc,old.mounted_shift}!=={dut.data_base,dut.fat_base,dut.cluster_max,dut.read_lba,dut.mounted_spc,dut.mounted_shift})$fatal(1,"geometry metadata i=%0d",i);
 end else invalid=invalid+1;
 end
 if(pass<100||invalid<100)$fatal(1,"unbalanced coverage");
 $display("PASS geometry differential cases=2048 accepted=%0d rejected=%0d seed=57beef",pass,invalid);$finish;
end
endmodule
