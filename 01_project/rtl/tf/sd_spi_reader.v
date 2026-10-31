// Read-only SD-v2 SPI block reader, request handshake after init. CMD17 arbitrary LBA.
// No write/erase. Capture data only provisionally; consumer commits after read_done AND ready (CRC passed).
`timescale 1ns/1ps
module sd_spi_reader #(
 parameter integer HALF_DIV=60,DATA_HALF_DIV=HALF_DIV,POWER_WAIT_CYCLES=2400000,
 INIT_GAP_CYCLES=24000,MAX_INIT_TRIES=1000,
 R1_MAX_BYTES=64,TOKEN_MAX_BYTES=16384
)(input wire clk,rst_n,input wire miso,
 input wire read_req,input wire [31:0] read_lba,output wire ready,
 output wire sck,mosi,output reg cs_n,
 output reg init_done,read_done,signature_ok,
 output reg [3:0] error_code,output reg high_capacity,
 output reg [15:0] data_crc,received_crc,output reg [31:0] data_sum,
 output reg [7:0] last_r1,output reg [5:0] last_cmd,
 output reg data_valid,output reg [8:0] data_index,output reg [7:0] data_byte);
 localparam POWER=0,DUMMY=1,DUMMY_NEXT=2,GAP=3,SELECT_CARD=4,
 SEND=5,SEND_NEXT=6,POLL=7,CHECK_R1=8,EXTRA=9,EXTRA_NEXT=10,
 HANDLE=11,WAIT_INIT=12,TOKEN=13,CHECK_TOKEN=14,DATA=15,
 DATA_NEXT=16,CRC_HI=17,CRC_HI_NEXT=18,CRC_LO=19,CRC_LO_NEXT=20,
 FINISH=21,FINISH_NEXT=22,END_OK=23,ERROR_IDLE=24,WAIT_BYTE=25;
 reg [5:0] state,resume_state;
 assign ready=init_done && state==END_OK && error_code==0;
 // Switch only after the slow post-init trailing byte has finished with CS high.
 reg data_mode;
 reg byte_start;reg [7:0] byte_tx,byte_rx_saved;
 wire byte_done,byte_busy;wire [7:0] byte_rx;
 reg [31:0] wait_count,cmd_arg,extra_data;
 reg [7:0] cmd_crc;
 reg [2:0] cmd_pos,extra_pos;
 reg [6:0] dummy_count;
 reg [15:0] r1_count,token_count,init_tries;
 reg [3:0] cmd0_tries;
 reg [8:0] payload_index;
 reg [7:0] signature_low;
 spi_byte #(.HALF_DIV(HALF_DIV),.DATA_HALF_DIV(DATA_HALF_DIV)) spi(.clk(clk),.rst_n(rst_n),.start(byte_start),.fast_mode(data_mode),
 .tx(byte_tx),.miso(miso),.sck(sck),.mosi(mosi),.busy(byte_busy),.done(byte_done),.rx(byte_rx));
 function [15:0] crc16_byte;
  input [15:0] old_crc;input [7:0] value;
  reg [15:0] c;integer k;
  begin c=old_crc;for(k=7;k>=0;k=k-1)
   if(c[15]^value[k]) c={c[14:0],1'b0}^16'h1021;else c={c[14:0],1'b0};
   crc16_byte=c;end
 endfunction
 task transfer;
  input [7:0] value;input [5:0] next_state;
  begin byte_tx<=value;byte_start<=1;resume_state<=next_state;state<=WAIT_BYTE;end
 endtask
 task command;
  input [5:0] number;input [31:0] argument;input [7:0] crc;
  begin last_cmd<=number;cmd_arg<=argument;cmd_crc<=crc;
   cmd_pos<=0;r1_count<=0;extra_data<=0;extra_pos<=0;state<=GAP;end
 endtask
 task fail;
  input [3:0] code;
  begin error_code<=code;state<=FINISH;end
 endtask
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   data_mode<=0;state<=POWER;resume_state<=POWER;byte_start<=0;byte_tx<=8'hff;byte_rx_saved<=8'hff;
   cs_n<=1;init_done<=0;read_done<=0;signature_ok<=0;error_code<=0;
   high_capacity<=0;data_crc<=0;received_crc<=0;data_sum<=0;
   last_r1<=8'hff;last_cmd<=0;data_valid<=0;data_index<=0;data_byte<=0;
   wait_count<=0;cmd_arg<=0;extra_data<=0;cmd_crc<=8'hff;
   cmd_pos<=0;extra_pos<=0;dummy_count<=0;r1_count<=0;token_count<=0;
   init_tries<=0;cmd0_tries<=0;payload_index<=0;signature_low<=0;
  end else begin
   byte_start<=0;data_valid<=0;
   case(state)
    POWER: if(wait_count==POWER_WAIT_CYCLES-1) begin wait_count<=0;state<=DUMMY;end
           else wait_count<=wait_count+1'b1;
    DUMMY: transfer(8'hff,DUMMY_NEXT);
    DUMMY_NEXT: if(dummy_count==9) command(0,0,8'h95);
                else begin dummy_count<=dummy_count+1'b1;state<=DUMMY;end
    GAP: begin cs_n<=1;transfer(8'hff,SELECT_CARD);end
    SELECT_CARD: begin cs_n<=0;transfer(8'hff,SEND);end
    SEND: case(cmd_pos)
     0:transfer({2'b01,last_cmd},SEND_NEXT);
     1:transfer(cmd_arg[31:24],SEND_NEXT);
     2:transfer(cmd_arg[23:16],SEND_NEXT);
     3:transfer(cmd_arg[15:8],SEND_NEXT);
     4:transfer(cmd_arg[7:0],SEND_NEXT);
     5:transfer(cmd_crc,SEND_NEXT);
     default:fail(4'hf);
    endcase
    SEND_NEXT: if(cmd_pos==5) state<=POLL;else begin cmd_pos<=cmd_pos+1'b1;state<=SEND;end
    POLL: transfer(8'hff,CHECK_R1);
    CHECK_R1: begin
     if(!byte_rx_saved[7]) begin
      last_r1<=byte_rx_saved;
      if((last_cmd==8 && byte_rx_saved==1)||(last_cmd==58 && byte_rx_saved==0)) state<=EXTRA;
      else state<=HANDLE;
     end else if(r1_count==R1_MAX_BYTES-1) begin
      if(last_cmd==0 && cmd0_tries<9) begin cmd0_tries<=cmd0_tries+1'b1;command(0,0,8'h95);end
      else fail(1);
     end else begin r1_count<=r1_count+1'b1;state<=POLL;end
    end
    EXTRA: transfer(8'hff,EXTRA_NEXT);
    EXTRA_NEXT: begin
     extra_data<={extra_data[23:0],byte_rx_saved};
     if(extra_pos==3) state<=HANDLE;else begin extra_pos<=extra_pos+1'b1;state<=EXTRA;end
    end
    HANDLE: case(last_cmd)
     0:if(last_r1==1) command(8,32'h000001aa,8'h87);
       else if(cmd0_tries<9) begin cmd0_tries<=cmd0_tries+1'b1;command(0,0,8'h95);end
       else fail(2);
     8:if(last_r1==1 && extra_data==32'h000001aa) command(55,0,8'hff);else fail(3);
     55:if(last_r1==1 || last_r1==0) command(41,32'h40000000,8'hff);else fail(4);
     41:if(last_r1==0) command(58,0,8'hff);
        else if(last_r1!=1 || init_tries==MAX_INIT_TRIES-1) fail(5);
        else begin init_tries<=init_tries+1'b1;wait_count<=0;cs_n<=1;state<=WAIT_INIT;end
     58:if(last_r1!=0 || !extra_data[31] || !(|extra_data[23:15])) fail(6);
        else begin high_capacity<=extra_data[30];
         if(extra_data[30]) begin init_done<=1;state<=FINISH;end
         else command(16,512,8'hff);
        end
     16:if(last_r1==0) begin init_done<=1;state<=FINISH;end else fail(7);
     17:if(last_r1==0) begin token_count<=0;state<=TOKEN;end else fail(7);
     default:fail(4'hf);
    endcase
    WAIT_INIT: if(wait_count==INIT_GAP_CYCLES-1) begin wait_count<=0;command(55,0,8'hff);end
               else wait_count<=wait_count+1'b1;
    TOKEN: transfer(8'hff,CHECK_TOKEN);
    CHECK_TOKEN: if(byte_rx_saved==8'hfe) begin payload_index<=0;data_crc<=0;data_sum<=0;state<=DATA;end
                 else if(byte_rx_saved!=8'hff) fail(9);
                 else if(token_count==TOKEN_MAX_BYTES-1) fail(8);
                 else begin token_count<=token_count+1'b1;state<=TOKEN;end
    DATA: transfer(8'hff,DATA_NEXT);
    DATA_NEXT: begin
     data_valid<=1;data_byte<=byte_rx_saved;data_index<=payload_index;
     data_crc<=crc16_byte(data_crc,byte_rx_saved);data_sum<=data_sum+byte_rx_saved;
     if(payload_index==510) signature_low<=byte_rx_saved;
     if(payload_index==511) begin signature_ok<=signature_low==8'h55 && byte_rx_saved==8'haa;state<=CRC_HI;end
     else begin payload_index<=payload_index+1'b1;state<=DATA;end
    end
    CRC_HI:transfer(8'hff,CRC_HI_NEXT);
    CRC_HI_NEXT:begin received_crc[15:8]<=byte_rx_saved;state<=CRC_LO;end
    CRC_LO:transfer(8'hff,CRC_LO_NEXT);
    CRC_LO_NEXT:begin
     received_crc[7:0]<=byte_rx_saved;
     if({received_crc[15:8],byte_rx_saved}!=data_crc) fail(10);
     else begin read_done<=1;state<=FINISH;end
    end
    FINISH:begin cs_n<=1;transfer(8'hff,FINISH_NEXT);end
    FINISH_NEXT:if(error_code==0) state<=END_OK;else state<=ERROR_IDLE;
    END_OK:begin
     cs_n<=1;
     if(init_done) data_mode<=1;
     if(read_req) begin
      read_done<=0;signature_ok<=0;
      if(!high_capacity && |read_lba[31:23]) fail(7);
      else command(17,high_capacity ? read_lba : (read_lba<<9),8'hff);
     end
    end
    ERROR_IDLE:cs_n<=1;
    WAIT_BYTE:if(byte_done) begin byte_rx_saved<=byte_rx;state<=resume_state;end
    default:fail(4'hf);
   endcase
  end
 end
endmodule
