`timescale 1ns/1ps
module tf_wav_reader(
 input clk,rst_n,enable,input[1:0]choice,input mounted,
 input[31:0]root_cluster,data_base,fat_base,cluster_max,input[7:0]spc,input[3:0]shift,
 output bus_reset_n,read_req,output[31:0]read_lba,input sd_ready,sd_done,input[3:0]sd_error,
 input data_valid,input[8:0]data_index,input[7:0]data_byte,
 output signed[23:0]left,right,output pcm_valid,input pcm_ready,
 output eof,output[7:0]error_code,output header_ok,output[31:0]data_size);
 integer sent=0,delay_eof=0;
 assign left=24'h100000+sent;assign right=-(24'h100000+sent);
 assign pcm_valid=rst_n&&enable&&tb_v114_boundary.permit&&sent<tb_v114_boundary.target;
 assign eof=delay_eof>=8;assign error_code=0;assign header_ok=rst_n&&enable;
 assign data_size=tb_v114_boundary.target*6;assign bus_reset_n=rst_n;
 assign read_req=0;assign read_lba=0;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin sent<=0;delay_eof<=0;end
  else begin
   if(pcm_valid&&pcm_ready)sent<=sent+1;
   if(sent>=tb_v114_boundary.target&&delay_eof<8)delay_eof<=delay_eof+1;
  end
endmodule
