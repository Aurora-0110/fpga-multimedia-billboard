from pathlib import Path
r=Path(__file__).resolve().parents[1];t=r/'02_tests/wav';rtl=r/'01_project/rtl'
baseline=(rtl/'tf/media_sd_arbiter.v').read_text();(t/'v114_media_sd_arbiter_reference.v').write_text(baseline.replace('module media_sd_arbiter(','module media_sd_arbiter_v114('))
(t/'v116_budget_host.sv').write_text(r'''`timescale 1ns/1ps
// Deterministic sector service-budget model, not an electrical SD model.
// GAP=4 and initial wait are scaled service times, no CRC error injection here.
module v116_budget_host(input clk,rst_n,req,input [31:0] lba,
 output reg ready,done,valid,output reg [8:0] index,output reg [7:0] data,
 output wire [3:0] error);
 `include "wav_fixture.vh"
 assign error=0;
 integer initial_wait,i,waiter;reg active;
 initial if(!$value$plusargs("BLOCK_WAIT=%d",initial_wait))initial_wait=250;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin ready<=1;done<=0;valid<=0;index<=0;data<=0;i<=0;waiter<=0;active<=0;end
 else begin
  valid<=0;
  if(req&&ready)begin active<=1;ready<=0;done<=0;i<=0;waiter<=initial_wait;end
  else if(active)begin
   if(waiter>0)waiter<=waiter-1;
   else if(i<512)begin valid<=1;index<=i;data<=sector_byte(lba,i);i<=i+1;waiter<=3;end
   else begin active<=0;done<=1;ready<=1;end
  end
 end
endmodule
''')
(t/'tb_v116_refill_budget.sv').write_text(r'''`timescale 1ns/1ps
module tb_v116_refill_budget;
 reg sd=0,pix=0,rst=0;always #10.101 sd=~sd;always #6.734 pix=~pix;
 reg [1:0] choice=0;reg paused=0;
 wire ar,areq,ardy,adone,av,urgent;wire [31:0] al;
 wire [3:0] ae,he,be;wire hr,hd,hv,hreq;wire[31:0]hl;
 wire[8:0]hi;wire[7:0]hb;wire signed [23:0] l,r;
 wire pv,ep,playing,und,finished;wire[7:0]err;
 wire [12:0] aq,amin,firstq;wire[7:0]firsts;
 reg b_req=0;wire bready,bdone,bvalid;reg bbusy=0;integer bbytes=0,bsectors=0;
 integer nm,spc_arg,shift_arg,with_bmp,expect_under,mode,n=0,cycles=0,epochs=0;
 integer adata=0,afat=0,bmp=0,urgent_bmp=0,first_under_n=-1,play_at=-1;
 reg [2047:0]mf;reg[47:0]music[0:40000];
 tf_wav_playback #(.PIX_HZ(4640625))dut(
 .clk_sd(sd),.clk_pix(pix),.rst_n(rst),.choice(choice),.mounted(1'b1),.paused(paused),
 .root_cluster(32'd2),.data_base(32'd600),.fat_base(32'd32),.cluster_max(32'd70000),.spc(spc_arg[7:0]),.shift(shift_arg[3:0]),
 .bus_reset_n(ar),.read_req(areq),.read_lba(al),.urgent(urgent),.sd_ready(ardy),.sd_done(adone),.sd_error(ae),
 .data_valid(av),.data_index(hi),.data_byte(hb),.left(l),.right(r),.valid(pv),.epoch(ep),
 .playing(playing),.underrun(und),.error_pix(err),.finished(finished),
 .audio_used(aq),.audio_minimum(amin),.first_underflow_used(firstq),.first_underflow_flags(firsts));
 `ifdef BASELINE
 media_sd_arbiter_v114
 `else
 media_sd_arbiter
 `endif
 arb(.clk(sd),.rst_n(rst),.bmp_reset_n(rst),.aud_reset_n(ar),.audio_urgent(urgent),
 .b_req(b_req),.b_lba(32'd999999),.b_ready(bready),.b_done(bdone),.b_valid(bvalid),.b_error(be),
 .a_req(areq),.a_lba(al),.a_ready(ardy),.a_done(adone),.a_valid(av),.a_error(ae),
 .h_req(hreq),.h_lba(hl),.h_ready(hr),.h_done(hd),.h_valid(hv),.h_error(he),.active(),.owner_audio());
 v116_budget_host host(.clk(sd),.rst_n(rst),.req(hreq),.lba(hl),.ready(hr),.done(hd),.valid(hv),.index(hi),.data(hb),.error(he));
 initial begin
  if(!$value$plusargs("MUSIC=%s",mf)||!$value$plusargs("NM=%d",nm)||!$value$plusargs("SPC=%d",spc_arg)||!$value$plusargs("SHIFT=%d",shift_arg)||!$value$plusargs("BMP=%d",with_bmp)||!$value$plusargs("UNDER=%d",expect_under))$fatal(1,"args");
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  $readmemh(mf,music,0,nm-1);
  repeat(12)@(negedge pix);rst=1;repeat(20)@(negedge pix);choice=1;
  if(mode==1)begin
   wait(n>=4700);@(negedge pix);paused=1;repeat(40000)@(negedge pix);
   if(dut.wu<3584)$fatal(1,"pause refill not sustained");paused=0;
  end
 end
 always @(negedge sd)if(rst)begin
  b_req=0;
  if(with_bmp&&!bbusy&&bready)begin b_req=1;bbusy=1;bbytes=0;end
  if(bvalid)bbytes=bbytes+1;
  if(bdone&&bbusy&&bbytes==512)begin bsectors=bsectors+1;bbusy=0;end
  if(hreq)begin
   if(hl==999999)begin bmp=bmp+1;if(urgent)urgent_bmp=urgent_bmp+1;end
   else if(hl>=32&&hl<600)afat=afat+1;else adata=adata+1;
  end
 end
 always @(posedge pix)if(rst)begin
  cycles=cycles+1;
  if(playing&&play_at==-1)play_at=cycles;
  if(und&&first_under_n==-1)begin
   first_under_n=n;$display("FIRST_A3 n=%0d Q=%0d S=%02h play_cycles=%0d audio_data=%0d fat=%0d bmp=%0d urgent_bmp=%0d",n,firstq,firsts,cycles-play_at,adata,afat,bmp,urgent_bmp);
  end
  if(err!=0)$fatal(1,"reader error %h",err);
  if(pv&&{l,r}!=0)begin
   if(n>=nm||{l,r}!==music[n])$fatal(1,"PCM mismatch n=%0d",n);n=n+1;
  end
  if(pv&&ep)epochs=epochs+1;
  if(finished)begin
   if(n!=nm||und!==expect_under[0]||epochs!=1||with_bmp&&bsectors<3)$fatal(1,"result n=%0d under=%b expected=%0d epochs=%0d bmp=%0d",n,und,expect_under,epochs,bsectors);
   $display("PASS refill-budget SPC=%0d BMP=%0d samples=%0d A3=%0d first_under_n=%0d MIN=%0d audio_data=%0d FAT=%0d BMP=%0d urgent_BMP=%0d",spc_arg,with_bmp,n,und,first_under_n,amin,adata,afat,bmp,urgent_bmp);$finish;
  end
  if(cycles>14000000)$fatal(1,"timeout n=%0d state=%0d",n,dut.reader.state);
 end
endmodule
''')
(t/'run_v116_refill_budget.py').write_text(r'''from pathlib import Path
import os,subprocess,json,struct,datetime,hashlib,argparse
ap=argparse.ArgumentParser();ap.add_argument('--baseline',action='store_true');ap.add_argument('--spc',type=int,default=1);ap.add_argument('--wait',type=int,default=250);ap.add_argument('--bmp',type=int,default=1);ap.add_argument('--under',type=int,default=0);ap.add_argument('--mode',type=int,default=0);a=ap.parse_args()
root=Path(__file__).resolve().parents[2];t=Path(__file__).resolve().parent;rtl=root/'01_project/rtl'
out=root/'04_evidence'/('v116_refill_'+('old_'if a.baseline else 'new_')+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));out.mkdir()
nm=24001;rows=[(((i*197+12345)%0x7ffffe)+1,-(((i*163+31415)%0x7ffffe)+1))for i in range(nm)]
pcm=b''.join((v&0xffffff).to_bytes(3,'little')for row in rows for v in row)
data=b'RIFF'+struct.pack('<I',len(pcm)+36)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,2,48000,288000,6,24)+b'data'+struct.pack('<I',len(pcm))+pcm
(out/'music.hex').write_text(''.join(f'{l&0xffffff:06x}{r&0xffffff:06x}\n'for l,r in rows))
fat={2:0xfffffff};sectors={};rootdir=bytearray(512);rootdir[:11]=b'MUSIC   WAV';rootdir[11]=32;rootdir[26:28]=struct.pack('<H',10);rootdir[28:32]=struct.pack('<I',len(data));sectors[600]=rootdir
num=(len(data)+a.spc*512-1)//(a.spc*512);chain=[10+3*i for i in range(num)]
for j,cl in enumerate(chain):
 fat[cl]=chain[j+1]if j+1<len(chain)else 0xfffffff
 for s in range(a.spc):
  start=(j*a.spc+s)*512
  if start<len(data):sectors[600+(cl-2)*a.spc+s]=data[start:start+512].ljust(512,b'\0')
for cl,val in fat.items():
 lba=32+cl//128;q=bytearray(sectors.get(lba,bytes(512)));q[(cl%128)*4:(cl%128)*4+4]=struct.pack('<I',val);sectors[lba]=q
keys=sorted(sectors);flat=b''.join(sectors[k]for k in keys);(out/'sectors.hex').write_text(''.join(f'{v:02x}\n'for v in flat))
fixture='reg[7:0] disk[0:'+str(len(flat)-1)+'];\ninitial $readmemh("'+(out/'sectors.hex').as_posix()+'",disk);\nfunction[7:0]sector_byte;input[31:0]lba;input integer idx;begin case(lba)\n'
fixture+=''.join(f"32'd{k}:sector_byte=disk[{j*512}+idx];\n"for j,k in enumerate(keys));fixture+="default:sector_byte=0;endcase end endfunction\n";(out/'wav_fixture.vh').write_text(fixture)
b=Path(r'D:\FPGA_Billboard\90_tools\simulation\iverilog\ucrt64\bin');env=dict(os.environ);env.update(PATH=str(b)+os.pathsep+env.get('PATH',''),TEMP=str(root/'00_tmp'),TMP=str(root/'00_tmp'),TMPDIR=str(root/'00_tmp'))
sources=[t/'tb_v116_refill_budget.sv',t/'v116_budget_host.sv',(t/'v114_media_sd_arbiter_reference.v'if a.baseline else rtl/'tf/media_sd_arbiter.v')]+[rtl/x for x in ['tf/fat32_audio_prefetch.v','audio/wav_pcm_decode.v','audio/tf_wav_reader.v','audio/tf_wav_playback.v','audio/audio_choice_cdc.v','mem/async_fifo.v','common/reset_release.v']]
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources+[Path(__file__)]}
exe=out/'test.vvp';c=subprocess.run([str(b/'iverilog.exe'),'-g2012','-I',str(out),*(['-DBASELINE']if a.baseline else []),'-s','tb_v116_refill_budget','-o',str(exe)]+list(map(str,sources)),capture_output=True,text=True,env=env);(out/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
c=subprocess.run([str(b/'vvp.exe'),str(exe),f'+MUSIC={(out/"music.hex").as_posix()}',f'+NM={nm}',f'+SPC={a.spc}',f'+SHIFT={a.spc.bit_length()-1}',f'+BLOCK_WAIT={a.wait}',f'+BMP={a.bmp}',f'+UNDER={a.under}',f'+MODE={a.mode}'],capture_output=True,text=True,env=env,timeout=240)
(out/'run.log').write_text(c.stdout+c.stderr);print(c.stdout,flush=True)
rec={'pass':c.returncode==0 and 'PASS refill-budget'in c.stdout,'args':vars(a),'scope':'Deterministic service-budget transport model with16x accelerated service/consumer, NOT real card timing nor hardware root-cause proof','source_sha256':hashes,'unchanged':all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in hashes.items())};rec['pass'] &=rec['unchanged'];(out/'summary.json').write_text(json.dumps(rec,indent=2));print(out,flush=True);raise SystemExit(0 if rec['pass']else 1)
''')
print('v116 targeted tests created; no production RTL modified yet')
