`timescale 1ns/1ps
// Elaboration-only check. Missing vendor primitives are ignored by -i;
// this test intentionally makes NO claims about their runtime behavior.
module tb_v065_production_defaults;
 idx_video_top dut(.clk24m(1'b0),.key0_n(1'b1),.key1_n(1'b1),.tf_miso(1'b1));
 initial begin
  #1;
  if(dut.TF_HALF_DIV!=124 || dut.TF_DATA_HALF_DIV!=12 || dut.TF_POWER_WAIT!=4950000) $fatal(1,"production SPI defaults");
  if(dut.USE_TF!=1 || dut.PLAYLIST_ENABLE!=1 || dut.AUTO_PLAY!=1 || dut.AUTO_DWELL_CYCLES!=247500000) $fatal(1,"production playlist defaults");
  if(dut.playlist.select_image.DWELL_CYCLES!=247500000) $fatal(1,"dwell parameter propagation");
  if(dut.tf_source.loader.source.reader.spi.HALF_DIV!=124 || dut.tf_source.loader.source.reader.spi.DATA_HALF_DIV!=12) $fatal(1,"SPI parameter propagation");
  $display("PASS production parameter elaboration init124 data12 dwell247500000");
  $finish;
 end
endmodule
