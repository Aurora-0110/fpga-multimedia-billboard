// Test-only sparse sector fixture loader and expected result checker.
reg [7:0] fixture_data[0:8191];reg [31:0] fixture_lbas[0:15],expected_lbas[0:63];
string fixture_path;integer blocks,expected_reads,expected_error,expected_mount,expected_found,expected_ok;
integer expected_top_down,expected_cluster,expected_offset,expected_size,sdsc_mode,crc_read,stall_mode,sd_init_error;
integer arg_unused,request_count=0;
initial begin
 if(!$value$plusargs("FIXTURE=%s",fixture_path)) $fatal(1,"No FIXTURE directory");
 arg_unused=$value$plusargs("BLOCKS=%d",blocks);arg_unused=$value$plusargs("READS=%d",expected_reads);
 arg_unused=$value$plusargs("ERROR=%d",expected_error);arg_unused=$value$plusargs("MOUNT=%d",expected_mount);
 arg_unused=$value$plusargs("FOUND=%d",expected_found);arg_unused=$value$plusargs("OK=%d",expected_ok);
 arg_unused=$value$plusargs("TOPDOWN=%d",expected_top_down);arg_unused=$value$plusargs("CLUSTER=%d",expected_cluster);
 arg_unused=$value$plusargs("OFFSET=%d",expected_offset);arg_unused=$value$plusargs("SIZE=%d",expected_size);
 arg_unused=$value$plusargs("SDSC=%d",sdsc_mode);arg_unused=$value$plusargs("CRC_READ=%d",crc_read);
 arg_unused=$value$plusargs("STALL=%d",stall_mode);arg_unused=$value$plusargs("SD_INIT_ERROR=%d",sd_init_error);
 $readmemh({fixture_path,"/lbas.hex"},fixture_lbas,0,blocks-1);
 $readmemh({fixture_path,"/data.hex"},fixture_data,0,blocks*512-1);
 $readmemh({fixture_path,"/requests.hex"},expected_lbas,0,(expected_reads==0)?0:expected_reads-1);
end
function integer find_block;input [31:0] lba;integer j;
 begin find_block=-1;for(j=0;j<blocks;j=j+1) if(fixture_lbas[j]==lba) find_block=j;end
endfunction
task note_request;input [31:0] lba;
 begin
  if(request_count>=expected_reads || lba!==expected_lbas[request_count])
   $fatal(1,"Unexpected read #%0d LBA=%0d expected=%0d",request_count,lba,expected_lbas[request_count]);
  request_count=request_count+1;
 end
endtask
task check_result;
 begin
  if(error_code!==expected_error || mounted!==expected_mount || file_found!==expected_found || bmp_ok!==expected_ok)
   $fatal(1,"Flags err=%0d mount=%0d found=%0d bmp=%0d expected %0d/%0d/%0d/%0d",error_code,mounted,file_found,bmp_ok,expected_error,expected_mount,expected_found,expected_ok);
  if(request_count!=expected_reads) $fatal(1,"Read count %0d expected %0d",request_count,expected_reads);
  if(expected_ok && (top_down!==expected_top_down || file_cluster!==expected_cluster || pixel_offset!==expected_offset || file_size!==expected_size))
   $fatal(1,"Parsed file metadata mismatch: cluster=%0d offset=%0d size=%0d topdown=%0d",file_cluster,pixel_offset,file_size,top_down);
 end
endtask
