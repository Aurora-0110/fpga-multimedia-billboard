`timescale 1ns/1ps
module tb_spi_loader_speed;
parameter INIT_DIV=6,DATA_DIV=1,MISO_DELAY_NS=0;
 reg [7:0] file_letter=8'h41;integer selected=0;
reg clk=0;always #10.101 clk=~clk;
reg rst_n=0,enable=0,req_ack=0;wire miso,cs_n,sck,mosi,req_valid,done,sd_init,mounted,bmp_ok;
wire[18:0]req_addr;wire[127:0]req_data;wire[7:0]error_code;
tf_bmp_loader #(.RUNTIME_NAME(1),.HALF_DIV(INIT_DIV),.DATA_HALF_DIV(DATA_DIV),.POWER_WAIT_CYCLES(16),.INIT_GAP_CYCLES(4)) dut(.*);
wire card_miso; assign #(MISO_DELAY_NS) miso=card_miso;
sd_playlist_card_model card(.rst_n(rst_n),.cs_n(cs_n),.sck(sck),.mosi(mosi),.miso(card_miso));
reg[7:0]image[0:921653];string path;integer expected_error=0,top=0,flip=0,seen=0,cycle=0,k,pos,row,tries=0;
integer target_bursts=80,retry_load=0,begin_cycle=0,init_cycle=0,header_cycle=0,first_cycle=0;
integer epoch=0,saved_seen,mode_switches=0,slow_edges=0,fast_edges=0;
integer last_edge_cycle=0,expected_div=0,byte_start_cycle=0;
reg previous_sck=0,previous_busy=0,previous_mode=0,previous_sd_init=0,previous_header=0;
reg[31:0] rolling_hash=0,expected_crc=0;
always @(posedge clk) begin
 #1;
 if(!rst_n)begin
  previous_sck=0;previous_busy=0;previous_mode=0;previous_sd_init=0;previous_header=0;
  mode_switches=0;slow_edges=0;fast_edges=0;
 end else begin
  if(sd_init&&!previous_sd_init)init_cycle=cycle;
  if(bmp_ok&&!previous_header)header_cycle=cycle;
  previous_sd_init=sd_init;previous_header=bmp_ok;
  if(dut.source.reader.data_mode&&!previous_mode)begin
   if(!cs_n||sck||dut.source.reader.byte_busy||!sd_init)$fatal(1,"unsafe init/data mode boundary");
   if(!card.initialized || (card.sdsc_mode && card.setlen_count!=1))$fatal(1,"fast before CMD58/CMD16 completion");
   mode_switches=mode_switches+1;
  end
  previous_mode=dut.source.reader.data_mode;
  if(dut.source.reader.byte_busy&&!previous_busy)begin
   expected_div=dut.source.reader.spi.data_mode?DATA_DIV:INIT_DIV;
   last_edge_cycle=cycle;
  end
  if(sck!=previous_sck)begin
   if(cycle-last_edge_cycle!=expected_div)$fatal(1,"SPI runt/long half-pulse got=%0d expected=%0d",cycle-last_edge_cycle,expected_div);
   last_edge_cycle=cycle;
   if(dut.source.reader.spi.data_mode)fast_edges=fast_edges+1;else slow_edges=slow_edges+1;
  end
  previous_sck=sck;previous_busy=dut.source.reader.byte_busy;
 end
end
reg[23:0]p;reg[7:0]q;
always @(negedge clk)begin
 req_ack=0;
 if(rst_n)begin
 cycle=cycle+1;enable=cycle%41>7;
 if(req_valid&&cycle%13==0)begin
  row=top?seen/40:479-seen/40;
  if(req_addr!==row*40+seen%40)$fatal(1,"loader address order %0d",req_addr);
  for(k=0;k<16;k=k+1)begin
   pos=54+((seen/40)*640+(seen%40)*16+k)*3;
   p={image[pos+2],image[pos+1],image[pos]};
   if(flip&&pos<=100&&pos+2>=100)begin
    if(pos==100)p[0]=~p[0];else if(pos+1==100)p[8]=~p[8];else p[16]=~p[16];
   end
   if(selected==1)p=p^24'he0e0e0;
   if(selected==2)p=p^24'hc0c0c0;
   q={p[23:21],p[15:13],p[7:6]};
   if(req_data[k*8+:8]!==q)$fatal(1,"loader pixel %0d lane %0d got=%h expected=%h",seen,k,req_data[k*8+:8],q);
  end
  if(seen==0)first_cycle=cycle;
  rolling_hash=(rolling_hash<<1)^(rolling_hash>>31)^req_addr;
  for(k=0;k<16;k=k+1)rolling_hash=(rolling_hash<<1)^(rolling_hash>>31)^req_data[k*8+:8];
  seen=seen+1;req_ack=1;
 end
 end
end
initial begin
 if(!$value$plusargs("IMAGE=%s",path))$fatal(1,"IMAGE required");$readmemh(path,image);
 if($value$plusargs("ERROR=%d",expected_error))begin end
 if($value$plusargs("TOP=%d",top))begin end
 if($value$plusargs("FLIP=%d",flip))begin end
 if($value$plusargs("SELECT=%d",selected))begin end
 if($value$plusargs("BURSTS=%d",target_bursts))begin end
 if($value$plusargs("RETRY=%d",retry_load))begin end
 if($value$plusargs("CRC=%h",expected_crc))begin end
 file_letter="A"+selected;
 repeat(10)@(posedge clk);#1;rst_n=1;begin_cycle=cycle;
 if(retry_load)begin
  wait(seen>=40);@(negedge clk);rst_n=0;#1;
  if(sck||!cs_n||dut.source.reader.data_mode)$fatal(1,"retry reset unsafe");
  repeat(6)@(negedge clk);seen=0;cycle=0;rolling_hash=0;rst_n=1;begin_cycle=cycle;epoch=1;
 end
 if(expected_error)begin
  wait(error_code!=0);saved_seen=seen;
  if(error_code!==expected_error)$fatal(1,"wrong error %h expected %h",error_code,expected_error);
  repeat(500)@(negedge clk);
  if(seen!=saved_seen||done!==0||dut.source.done!==1||dut.source.ok!==0||error_code!==expected_error||req_valid||sck||!cs_n)$fatal(1,"failed load did not stop safely: seen=%0d saved=%0d done=%b source_done=%b ok=%b err=%h req=%b sck=%b cs=%b",seen,saved_seen,done,dut.source.done,dut.source.ok,error_code,req_valid,sck,cs_n);
  if(card.read_count==1&&seen!=0)$fatal(1,"bad first sector emitted pixels");
  if(card.read_count==7&&seen!=30)$fatal(1,"corrupt payload sector leaked pixels, bursts=%0d expected30",seen);
 end else begin
  if(target_bursts==19200)wait(done||error_code!=0);else wait(seen>=target_bursts||error_code!=0);
  if(error_code||!sd_init||!mounted||!bmp_ok)$fatal(1,"SPI header/payload failure %h",error_code);
  if(dut.source.probe.file_cluster!==3+selected)$fatal(1,"wrong selected cluster");
  if(seen!=target_bursts)$fatal(1,"burst count mismatch");
  if(target_bursts==19200)begin
   if(dut.source.pixel_count!=307200||!dut.source.ok)$fatal(1,"incomplete full image");
   if(dut.source.payload_crc32!==expected_crc)$fatal(1,"CRC32 mismatch got=%h expected=%h",dut.source.payload_crc32,expected_crc);
   repeat(200)@(negedge clk);if(!done||req_valid)$fatal(1,"success not sticky");
  end
 end
 if(mode_switches!=1||slow_edges==0||fast_edges==0)$fatal(1,"mode coverage missing");
 $display("METRICS init_div=%0d data_div=%0d selected=%0d init_cycles=%0d header_cycles=%0d first_burst_cycles=%0d total_cycles=%0d reads=%0d bursts=%0d hash=%08h crc=%08h retry=%0d error=%h",INIT_DIV,DATA_DIV,selected,init_cycle-begin_cycle,header_cycle-begin_cycle,first_cycle-begin_cycle,cycle-begin_cycle,card.read_count,seen,rolling_hash,dut.source.payload_crc32,epoch,error_code);
 $display("PASS dual-speed SPI loader; every accepted RGB332 pixel/address checked; slow_edges=%0d fast_edges=%0d",slow_edges,fast_edges);$finish;
end
initial begin #20000000000;$fatal(1,"loader timeout");end
endmodule
