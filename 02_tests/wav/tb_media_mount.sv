`timescale 1ns/1ps
module tb_media_mount;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg sd_ready=0,sd_read_done=0,data_valid=0;reg[3:0]sd_error=0;
 reg[8:0]data_index=0;reg[7:0]data_byte=0;
 wire read_req,mounted,file_found,bmp_ok,done,top_down;
 wire[31:0]read_lba,file_size,pixel_offset,file_cluster,data_base,fat_base,cluster_max,mounted_root,row_stride;
 wire[15:0]sectors_scanned,source_width,source_height;wire[7:0]mounted_spc;wire[3:0]mounted_shift,error_code;
 wire[7:0]file_letter=8'h41;
 media_bmp_probe #(.DYNAMIC_SIZE(1),.MAX_DIR_SECTORS(4),.INIT_TIMEOUT_CYCLES(10000),.READ_TIMEOUT_CYCLES(10000)) dut(.*);
 reg[31:0]lbas[0:15];reg[7:0]bytes[0:8191];string fixture;
 integer blocks,expected_error,expected_base,expected_fat,fault=0,fault_lba=-1,server=0,pos=0,sel=0,i,reads=0;
 initial begin
  if(!$value$plusargs("FIXTURE=%s",fixture)||!$value$plusargs("BLOCKS=%d",blocks)||!$value$plusargs("ERROR=%d",expected_error)||!$value$plusargs("BASE=%d",expected_base)||!$value$plusargs("FAT=%d",expected_fat))$fatal(1,"args");
  if(!$value$plusargs("FAULT=%d",fault))fault=0;
  if(!$value$plusargs("FAULT_LBA=%d",fault_lba))fault_lba=-1;
  $readmemh({fixture,"/lbas.hex"},lbas,0,blocks-1);$readmemh({fixture,"/data.hex"},bytes,0,blocks*512-1);
  repeat(6)@(negedge clk);rst_n=1;wait(done);repeat(4)@(negedge clk);
  if(error_code!==expected_error[3:0])$fatal(1,"error expected=%0d got=%0d",expected_error,error_code);
  if(expected_error==0&&(!mounted||!bmp_ok||!file_found||data_base!=expected_base||fat_base!=expected_fat||source_width!=640||source_height!=480||row_stride!=1920||file_size!=921654||pixel_offset!=54||file_cluster!=3||cluster_max!=65526||mounted_root!=2||mounted_spc!=1||mounted_shift!=0))$fatal(1,"metadata got base=%0d fat=%0d max=%0d",data_base,fat_base,cluster_max);
  if(expected_error!=0&&bmp_ok)$fatal(1,"erroneous BMP accepted");
  i=reads;repeat(25)@(negedge clk);if(reads!=i||read_req)$fatal(1,"extra read after terminal");
  $display("PASS mount/error MBR/BPB/full-sector fault=%0d err=%0d reads=%0d",fault,error_code,reads);$finish;
 end
 always @(posedge clk)begin
  data_valid<=0;
  if(!rst_n)begin sd_ready<=0;sd_read_done<=0;server<=0;end
  else case(server)
   0:begin sd_ready<=1;server<=1;end
   1:if(read_req)begin
    sel=-1;for(i=0;i<blocks;i=i+1)if(lbas[i]==read_lba)sel=i;
    if(sel<0)$fatal(1,"unexpected LBA %0d",read_lba);
    reads<=reads+1;sd_ready<=0;sd_read_done<=0;pos<=0;server<=2;
   end
   2:begin
    data_valid<=!(read_lba==fault_lba&&fault==1&&pos==200);
    data_index<=read_lba==fault_lba&&fault==2&&pos==200?199:pos;
    data_byte<=bytes[sel*512+pos];
    if(pos==511)server<=3;else pos<=pos+1;
   end
   3:begin sd_ready<=1;sd_read_done<=1;server<=1;end
  endcase
 end
 initial begin #1000000;$fatal(1,"mount TB timeout");end
endmodule
