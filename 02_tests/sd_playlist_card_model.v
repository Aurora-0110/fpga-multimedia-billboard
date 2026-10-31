// Behavioral SD-v2 SPI card, byte-queue implementation independent of host FSM.
// Test-only, NOT a vendor electrical model. Supports fault injection with +CASE=N.
`timescale 1ns/1ps
module sd_playlist_card_model(input wire rst_n,cs_n,sck,mosi,output wire miso);
 reg miso_drive=1;assign miso=cs_n ? 1'b1 : miso_drive;
 integer mode=0,head=0,tail=0,packet_pos=0,cmd0_count=0,acmd_count=0;
 integer command_count=0,read_count=0,setlen_count=0,high_cs_clocks=0;
 integer blocks=0,sdsc_mode=0,crc_read=0,block_index=0;
 reg [7:0] image[0:921653],boot[0:511],root[0:511];string fixture_path;
 integer lba=0,cluster=0,cluster_n=0,file_pos=0,link=0,flip=0,top_image=0;
 function [7:0] disk_byte;input integer address,offset;integer c,n,p,v;
 begin
  disk_byte=0;
  if(address==0) disk_byte=boot[offset];
  else if(address>=32 && address<1056) begin
   c=(address-32)*128+offset/4;
   if(c==2) v=32'h0fffffff;
   else if(c>=3 && (c-3)%137<=2) begin
    n=(c-3)/137;v=((n+1)*4096>=921654)?32'h0fffffff:c+137;
   end else v=0;
   disk_byte=(v>>((offset%4)*8))&255;
  end else if(address>=1056 && address<1064) disk_byte=(address==1056)?root[offset]:0;
  else if(address>=1064) begin
   c=(address-1056)/8+2;
   if((c-3)%137>2) $fatal(1,"Unexpected data cluster %0d",c);
   n=(c-3)/137;p=n*4096+((address-1056)%8)*512+offset;
   if(p<921654) begin
    disk_byte=image[p];
    // Headers stay unchanged; payloads differ per file, including high RGB bits.
    if(p>=54 && (c-3)%137==1) disk_byte=disk_byte^8'he0;
    if(p>=54 && (c-3)%137==2) disk_byte=disk_byte^8'hc0;
   end
   if(flip && p==100) disk_byte=disk_byte^1;
   if(top_image && p>=22 && p<=25) disk_byte=(32'hfffffe20>>((p-22)*8))&255;
  end else $fatal(1,"Unmapped LBA %0d",address);
 end
 endfunction
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
      lba=sdsc_mode?(argument>>9):argument;
      for(integer m=0;m<512;m=m+1) payload[m]=disk_byte(lba,m);
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
  i=$value$plusargs("FLIP=%d",flip);i=$value$plusargs("TOP=%d",top_image);
  if(!$value$plusargs("IMAGE=%s",fixture_path)) $fatal(1,"Missing IMAGE");
  $readmemh(fixture_path,image);
  for(i=0;i<512;i=i+1) begin boot[i]=0;root[i]=0;end
  boot[0]=8'heb;boot[11]=0;boot[12]=2;boot[13]=8;boot[14]=32;boot[16]=1;
  // total sectors=700000, one FAT=1024 sectors, root cluster=2.
  boot[32]=8'h60;boot[33]=8'hae;boot[34]=8'h0a;
  boot[36]=0;boot[37]=4;boot[44]=2;boot[510]=8'h55;boot[511]=8'haa;
  root[0]="A";for(i=1;i<8;i=i+1) root[i]=" ";root[8]="B";root[9]="M";root[10]="P";
  root[11]=8'h20;root[26]=3;root[28]=8'h36;root[29]=8'h10;root[30]=8'h0e;
  for(integer f=1;f<3;f=f+1)begin
   for(integer h=0;h<32;h=h+1)root[f*32+h]=root[h];
   root[f*32]="A"+f;root[f*32+26]=3+f;
  end

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
