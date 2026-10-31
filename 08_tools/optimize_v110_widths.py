from pathlib import Path
import shutil
r=Path(__file__).resolve().parents[1]
backup=r/'04_evidence/v110_pre_width_optimization_sources';backup.mkdir(exist_ok=False)
for name in ['scale/bilinear_stream_scaler.v','tf/bmp_pixel_stream.v']:
 p=r/'01_project/rtl'/name;shutil.copy2(p,backup/p.name)
p=r/'01_project/rtl/scale/bilinear_stream_scaler.v';s=p.read_text('utf-8')
s=s.replace(' reg [15:0] w,h,loaded,wx,dx,dy,sx,sy;', ''' // Range-proven widths: dimensions validated BEFORE capture; source row
 // count includes h as a sentinel, but indices never exceed max-1.
 localparam WW=MAX_WIDTH<2?1:$clog2(MAX_WIDTH+1),HH=MAX_HEIGHT<2?1:$clog2(MAX_HEIGHT+1);
 localparam SXW=MAX_WIDTH<2?1:$clog2(MAX_WIDTH),SYW=MAX_HEIGHT<2?1:$clog2(MAX_HEIGHT);
 localparam DXW=OUT_WIDTH<2?1:$clog2(OUT_WIDTH),DYW=OUT_HEIGHT<2?1:$clog2(OUT_HEIGHT);
 localparam RXW=OUT_WIDTH+MAX_WIDTH<4?1:$clog2(OUT_WIDTH+MAX_WIDTH-2);
 localparam RYW=OUT_HEIGHT+MAX_HEIGHT<4?1:$clog2(OUT_HEIGHT+MAX_HEIGHT-2);
 localparam FXW=OUT_WIDTH<3?1:$clog2(OUT_WIDTH-1),FYW=OUT_HEIGHT<3?1:$clog2(OUT_HEIGHT-1);
 reg [WW-1:0] w;reg [HH-1:0] h,loaded;
 reg [SXW-1:0] wx,sx;reg [SYW-1:0] sy;
 reg [DXW-1:0] dx;reg [DYW-1:0] dy;''')
s=s.replace('reg [31:0] rx,ry,fxrem,fyrem;', 'reg [RXW-1:0] rx;reg [RYW-1:0] ry;\n reg [FXW-1:0] fxrem;reg [FYW-1:0] fyrem;')
s=s.replace("wire [15:0] xnext=(sx+16'd1<w)?sx+16'd1:sx;", "wire [SXW:0] sx_plus={1'b0,sx}+1'b1;\n wire [SXW-1:0] xnext=sx_plus<w?sx_plus[SXW-1:0]:sx;")
s=s.replace("wire [15:0] ynext=(sy+16'd1<h)?sy+16'd1:sy;", "wire [SYW:0] sy_plus={1'b0,sy}+1'b1;\n wire [SYW-1:0] ynext=sy_plus<h?sy_plus[SYW-1:0]:sy;")
s=s.replace('wire [31:0] next_fxrem=fxrem<<1,next_fyrem=fyrem<<1;', "wire [FXW:0] next_fxrem={fxrem,1'b0};\n wire [FYW:0] next_fyrem={fyrem,1'b0};")
s=s.replace('wire [15:0] logical_y=td?dy:OUT_HEIGHT-1-dy;', 'wire [15:0] logical_y=td?dy:OUT_HEIGHT-1-dy;\n wire [15:0] logical_x=dx;').replace('.in_tag({logical_y,dx})','.in_tag({logical_y,logical_x})')
p.write_text(s,encoding='utf-8')
p=r/'01_project/rtl/tf/bmp_pixel_stream.v';s=p.read_text('utf-8')
s=s.replace(' reg [15:0] x,y;', ''' localparam BOUND_W=DYNAMIC_SIZE?MAX_WIDTH:WIDTH,BOUND_H=DYNAMIC_SIZE?MAX_HEIGHT:HEIGHT;
 localparam WW=BOUND_W<2?1:$clog2(BOUND_W+1),HH=BOUND_H<2?1:$clog2(BOUND_H+1);
 localparam STRIDE_MAX=((BOUND_W*3+3)/4)*4;
 localparam STRIDE_W=STRIDE_MAX<2?1:$clog2(STRIDE_MAX+1);
 // Force 64-bit constant math so generic large parameter values cannot wrap.
 localparam RASTER_MAX=64'd1*STRIDE_MAX*BOUND_H;
 localparam RASTER_W=RASTER_MAX<2?1:$clog2(RASTER_MAX+1);
 localparam COUNT_MAX=64'd1*BOUND_W*BOUND_H;
 localparam COUNT_W=COUNT_MAX<2?1:$clog2(COUNT_MAX+1);
 reg [WW-1:0] x;reg [HH-1:0] y;''')
s=s.replace('reg [15:0] locked_width,locked_height;', 'reg [WW-1:0] locked_width;reg [HH-1:0] locked_height;')
s=s.replace('reg [31:0] locked_stride,expected_pixels;', 'reg [STRIDE_W-1:0] locked_stride;reg [COUNT_W-1:0] expected_pixels;').replace('reg [63:0] raster_bytes;', 'reg [RASTER_W-1:0] raster_bytes;')
s=s.replace("wire [39:0] lba_calc={8'b0,data_base}+(({8'b0,current_cluster}-40'd2)<<mounted_shift)+sector_in_cluster;",''' reg [35:0] addr_work;reg [2:0] addr_shifts;
 wire [35:0] addr_operand=state==ADDR_BASE?{4'd0,data_base}:{28'd0,sector_in_cluster};
 wire [35:0] addr_sum=addr_work+addr_operand;''')
s=s.replace('FAT_READ2=16,FAT_READ3=17;', 'FAT_READ2=16,FAT_READ3=17,ADDR_SHIFT=18,ADDR_BASE=19,ADDR_SECTOR=20,ADDR_CHECK=21;')
s=s.replace("wire [64:0] required={33'd0,pixel_offset}+{1'b0,raster_bytes};", "wire [64:0] required={33'd0,pixel_offset}+raster_bytes;")
s=s.replace('state<=IDLE;read_req<=0;', 'state<=IDLE;addr_work<=0;addr_shifts<=0;read_req<=0;')
s=s.replace("raster_bytes<={32'd0,locked_stride}*{48'd0,locked_height};", 'raster_bytes<=locked_stride*locked_height;').replace("expected_pixels<={16'd0,locked_width}*{16'd0,locked_height};", 'expected_pixels<=locked_width*locked_height;')
s=s.replace('''       if(lba_calc[39:32]!=0) fail(4);
       else begin read_lba<=lba_calc[31:0];kind_fat<=0;timer<=0;state<=ISSUE;end''', '''       addr_work<={4'd0,current_cluster}-36'd2;addr_shifts<=mounted_shift[2:0];state<=ADDR_SHIFT;''')
s=s.replace('      ISSUE:begin', '''      ADDR_SHIFT:if(addr_shifts==0)state<=ADDR_BASE;
       else begin addr_work<=addr_work<<1;addr_shifts<=addr_shifts-1'b1;end
      ADDR_BASE:begin addr_work<=addr_sum;state<=ADDR_SECTOR;end
      ADDR_SECTOR:begin addr_work<=addr_sum;state<=ADDR_CHECK;end
      ADDR_CHECK:if(addr_work[35:32]!=0)fail(4);
       else begin read_lba<=addr_work[31:0];kind_fat<=0;timer<=0;state<=ISSUE;end
      ISSUE:begin''')
s=s.replace("pixel_count<=pixel_count+1'b1;", "pixel_count<={{(32-COUNT_W){1'b0}},(pixel_count[COUNT_W-1:0]+1'b1)};")
p.write_text(s,encoding='utf-8')
print('Range-proven scaler and BMP arithmetic narrowed; 40-bit barrel removed')
