// Behavioral SD-v2 SPI card, byte-queue implementation independent of host FSM.
// Test-only, NOT a vendor electrical model. Supports fault injection with +CASE=N.
`timescale 1ns/1ps
module sd_fat_card_model(input wire rst_n,cs_n,sck,mosi,output wire miso);
 reg miso_drive=1;assign miso=cs_n ? 1'b1 : miso_drive;
 integer mode=0,head=0,tail=0,packet_pos=0,cmd0_count=0,acmd_count=0;
 integer command_count=0,read_count=0,setlen_count=0,high_cs_clocks=0;
 integer blocks=0,sdsc_mode=0,crc_read=0,block_index=0;
 reg [31:0] fixture_lbas[0:15];reg [7:0] fixture_data[0:8191];string fixture_path;
 reg app_pending=0,initialized=0;reg [7:0] packet[0:5],queue[0:2047],payload[0:511];
 reg [7:0] outgoing,incoming;reg [31:0] argument;reg [15:0] crc;
 integer i,k,delay_bytes,j;reg [5:0] command_number;
 function [15:0] crc16;
  input [15:0] c_in;input [7:0] b;
  reg [15:0] c;integer n;
  begin c=c_in ^ {b,8'h00};for(n=0;n<8;n=n+1)
   c=c[15] ? (c<<1)^16'h1021 : (c<<1);
   crc16=c;end
 endfunction
 task put;input [7:0] b;begin
  if(tail>=2048) $fatal(1,"model queue overflow");queue[tail]=b;tail=tail+1;end endtask
 task process_command;
  begin
   command_number=packet[0][5:0];argument={packet[1],packet[2],packet[3],packet[4]};
   command_count=command_count+1;
   if(mode==2) begin end
   else begin
    delay_bytes=(mode==12)?8:2;for(j=0;j<delay_bytes;j=j+1) put(8'hff);
    case(command_number)
     0:begin
      if(high_cs_clocks<80) $fatal(1,"Less than 74 startup clocks");
      if(argument!=0 || packet[5]!=8'h95) $fatal(1,"Bad CMD0 packet");
      cmd0_count=cmd0_count+1;app_pending=0;initialized=0;
      put((mode==13 && cmd0_count==1)?8'h05:8'h01);
     end
     8:begin
      if(argument!=32'h1aa || packet[5]!=8'h87) $fatal(1,"Bad CMD8 packet");
      if(mode==3) put(8'h05);
      else begin put(1);put(0);put(0);put(1);put(mode==7?8'hab:8'haa);end
     end
     55:begin app_pending=1;put(mode==14?8'h05:(initialized?0:1));end
     41:begin
      if(!app_pending || argument!=32'h40000000) $fatal(1,"ACMD41 missing CMD55/HCS");
      app_pending=0;acmd_count=acmd_count+1;
      if(mode==4 || acmd_count<3) put(1);else begin put(0);initialized=1;end
     end
     58:begin
      if(!initialized) $fatal(1,"CMD58 before initialization");
      put(0);put(sdsc_mode?8'h80:8'hc0);
      put(8'hff);put(8'h80);put(0);
     end
     16:begin
      if(argument!=512) $fatal(1,"Bad block length");
      setlen_count=setlen_count+1;put(mode==15?8'h04:8'h00);
     end
     17:begin
      if(!initialized) $fatal(1,"CMD17 before initialization");
      if(sdsc_mode && (argument[8:0]!=0 || setlen_count==0)) $fatal(1,"SDSC address/CMD16 incorrect");
      block_index=-1;
      for(integer m=0;m<blocks;m=m+1) if(fixture_lbas[m]==(sdsc_mode?(argument>>9):argument)) block_index=m;
      if(block_index<0) $fatal(1,"Unmapped fixture CMD17 argument=%h",argument);
      for(integer m=0;m<512;m=m+1) payload[m]=fixture_data[block_index*512+m];
      if(mode==1 && setlen_count==0) $fatal(1,"SDSC missing CMD16");
      read_count=read_count+1;
      if(mode==10) put(8'h04);
      else begin
       put(0);
       if(mode!=5) begin
        put(8'hff);put(8'hff);put(8'hff);
        if(mode==8) put(8'h0b);
        else begin
         put(8'hfe);crc=0;
         for(j=0;j<512;j=j+1) begin put(payload[j]);crc=crc16(crc,payload[j]);end
         put(crc[15:8]);put(read_count==crc_read?(crc[7:0]^8'h01):crc[7:0]);
        end
       end
      end
     end
     default:$fatal(1,"Unexpected / possibly destructive CMD%0d",command_number);
    endcase
   end
  end
 endtask
 initial begin
  i=$value$plusargs("SDSC=%d",sdsc_mode);i=$value$plusargs("CRC_READ=%d",crc_read);
  i=$value$plusargs("BLOCKS=%d",blocks);if(!$value$plusargs("FIXTURE=%s",fixture_path)) $fatal(1,"Missing fixture");
  $readmemh({fixture_path,"/lbas.hex"},fixture_lbas,0,blocks-1);
  $readmemh({fixture_path,"/data.hex"},fixture_data,0,blocks*512-1);
  for(i=0;i<512;i=i+1) payload[i]=i[7:0]^8'ha5;
  payload[510]=(mode==11)?8'h00:8'h55;payload[511]=8'haa;
 end
 always @(negedge rst_n) begin
  initialized=0;app_pending=0;cmd0_count=0;acmd_count=0;
  command_count=0;read_count=0;setlen_count=0;high_cs_clocks=0;
 end
 always @(posedge sck) if(cs_n && rst_n) high_cs_clocks=high_cs_clocks+1;
 always begin
  @(negedge cs_n);
  begin: card_session
   head=0;tail=0;packet_pos=0;
   while(!cs_n) begin
    outgoing=(head<tail)?queue[head]:8'hff;
    if(head<tail) head=head+1;
    incoming=0;
    for(k=7;k>=0;k=k-1) begin
     miso_drive=outgoing[k];@(posedge sck);incoming[k]=mosi;
     if(k==0) begin
      if(packet_pos!=0 || incoming[7:6]==2'b01) begin
       packet[packet_pos]=incoming;
       if(packet_pos==5) begin packet_pos=0;process_command;end
       else packet_pos=packet_pos+1;
      end
     end
     @(negedge sck);
    end
   end
  end
 end
 always @(posedge cs_n) begin disable card_session;miso_drive=1;end
endmodule
