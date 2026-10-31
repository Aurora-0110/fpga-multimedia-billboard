"""Independent receiver for actual parallel TMDS words at the native serializer inputs.
No electrical/HDMI receiver conformance or audible-output claim. Uses a polynomial
long-division BCH checker, not the RTL streaming implementation.
"""
from pathlib import Path
import sys,json,math,collections,hashlib
TERC=[0x29c,0x263,0x2e4,0x2e2,0x171,0x11e,0x18e,0x13c,0x2cc,0x139,0x19c,0x2c6,0x28e,0x271,0x163,0x2c3]
INV={x:i for i,x in enumerate(TERC)};CTL=[0x354,0x0ab,0x154,0x2ab]
RESET_CYCLE=1242510

def reverse(x,n):return int(f'{x:0{n}b}'[::-1],2)
def bch(data,n):
    # Normal polynomial x^8+x^7+x^6+1, reflected transmission order.
    dividend=reverse(data,n)<<8
    for i in range(n+7,7,-1):
        if dividend>>i&1:dividend^=0x1c1<<(i-8)
    return reverse(dividend,8)
def verify_packet(h,subs):
    assert h>>24==bch(h&0xffffff,24),'header BCH'
    for s in subs:assert s>>56==bch(s&((1<<56)-1),56),'subpacket BCH'
def signed(x):return x-(1<<24) if x&(1<<23) else x
def read_pcm(p):
    segs=[[],[]]
    for ln in p.read_text().splitlines():
        a,b,c=ln.split();a=int(a);segs[int(a>RESET_CYCLE)].append((a,int(b,16),int(c,16)))
    return segs

def check_gated_pcm(actual, incoming, enabled):
    expected=incoming if enabled else (0,0)
    assert actual==expected, ("gate/PCM",enabled,actual,expected)

def main(out):
    pcm=read_pcm(out/'pcm.txt');rx=read_pcm(out/'rx.txt')
    gates={int(c):int(g) for c,g in (ln.split() for ln in (out/'gate.txt').read_text().splitlines())}
    muted=audible=0;transitions=[]
    for seg in range(2):
        assert len(pcm[seg])==len(rx[seg]),'RX/gain sample count'
        for i,((c,l,r),(rc,il,ir)) in enumerate(zip(pcm[seg],rx[seg])):
            expected=round(math.sin(2*math.pi*(i%48)/48)*1048576)
            assert signed(il)==signed(ir)==expected,('I2S bit alignment/tone',seg,i,signed(il),expected)
            assert c==rc+1 and signed(l)==signed(r)==expected//4,('signed gain',seg,i)
        if len(pcm[seg])>2:
            ds=[b[0]-a[0] for a,b in zip(pcm[seg],pcm[seg][1:])]
            assert set(ds)<={1546,1547},('48k cadence',set(ds))
            rate=74250000*(len(ds))/(pcm[seg][-1][0]-pcm[seg][0][0])
            assert abs(rate-48000)<30
    assert len(pcm[0])>=790 and len(pcm[1])>=3,'incomplete test'
    lines={};symbols=0
    for ln in (out/'symbols.txt').read_text().splitlines():
        c,x,y,bs,gs,rs,aux,vp,ip,hs,vs=ln.split();c,x,y=map(int,(c,x,y));b,g,r=[int(q,16) for q in (bs,gs,rs)];aux,vp,ip,hs,vs=map(int,(aux,vp,ip,hs,vs))
        seg=int(c>RESET_CYCLE);next_active=(y<719 or y==749)
        want_aux=1292<=x<1328 or (next_active and 1648<=x<1650)
        assert aux==want_aux and vp==(next_active and 1640<=x<1648) and ip==(1284<=x<1292),'period geometry'
        if 1292<=x<1294 or 1326<=x<1328:
            assert (b,g,r)==(TERC[12+2*vs+hs],0x133,0x133),'island guard'
        elif next_active and 1648<=x<1650:
            assert (b,g,r)==(0x2cc,0x133,0x2cc),'video guard'
        elif not aux:
            assert (b,g,r)==(CTL[2*vs+hs],CTL[bool(vp or ip)],CTL[ip]),'control/preamble symbols'
        lines.setdefault((seg,c-x,y),{})[x]=(b,g,r,hs,vs,c)
        symbols+=1
    types=collections.Counter();decoded=[[],[]];frame=[0,0];headers=[];acr=[]
    for (seg,base,y),row in sorted(lines.items()):
        if not all(x in row for x in range(1294,1326)):continue
        h=0;subs=[0]*4
        for k in range(32):
            b,g,r,hs,vs,c=row[1294+k]
            bn,gn,rn=INV[b],INV[g],INV[r]
            assert bn&3==2*vs+hs and bn>>3==1,'HS/VS in TERC4'
            h|=((bn>>2)&1)<<k
            for j in range(4):subs[j]|=((gn>>j)&1)<<(2*k)|((rn>>j)&1)<<(2*k+1)
        verify_packet(h,subs);headers.append((h,subs));h&=0xffffff;subs=[s&((1<<56)-1) for s in subs]
        typ=h&255;types[typ]+=1
        if typ==1:
            assert h==1 and len(set(subs))==1
            raw=subs[0].to_bytes(7,'little');cts=((raw[1]&15)<<16)|(raw[2]<<8)|raw[3];n=((raw[4]&15)<<16)|(raw[5]<<8)|raw[6]
            assert (n,cts)==(6144,74250) and 74250000*n//(128*cts)==48000,'ACR 48kHz'
            acr.append((seg,base+1294))
        elif typ==2:
            fi=frame[seg];assert h==(0x100f02 if fi==0 else 0x000f02),'audio header present/B flags'
            for j,s in enumerate(subs):
                l=s&0xffffff;r=(s>>24)&0xffffff;flags=s>>48;idx=fi+j
                cl=((0x0b02100004>>idx)&1) if idx<40 else 0;cr=((0x0b02200004>>idx)&1) if idx<40 else 0
                pl=(l.bit_count()+cl)&1;pr=(r.bit_count()+cr)&1
                assert flags==((pr<<7)|(cr<<6)|(pl<<3)|(cl<<2)),('IEC status/parity',idx,flags)
                decoded[seg].append((l,r,base+1294))
            frame[seg]=(fi+4)%192
        elif typ in [0x82,0x84]:
            raw=b''.join(s.to_bytes(7,'little') for s in subs);length=(h>>16)&255
            assert ((h&255)+((h>>8)&255)+length+sum(raw[:length+1]))%256==0,'InfoFrame checksum'
            assert h==(0x0d0282 if typ==0x82 else 0x0a0184)
            assert subs[0]==(0x0000040828102b if typ==0x82 else 0x00000000000170)
            assert all(s==0 for s in subs[1:])
        else:assert typ==0 and h==0 and all(s==0 for s in subs),'unknown packet'
    for t in [0,1,2,0x82,0x84]:assert types[t]>0,('missing packet type',t)
    assert types[2]>=195 and types[1]>=16 and types[0x82]>=2 and types[0x84]>=2,'insufficient duration'
    for seg in range(2):
        assert len(decoded[seg])<=len(pcm[seg])
        for i,(l,r,c) in enumerate(decoded[seg]):
            pc,pl,pr=pcm[seg][i]
            # Packet x=1294 vs select x=1280 plus one output register: 15 clocks.
            # Raw trace: select cycle1283, first received symbol cycle1298.
            on=gates[c-15]
            check_gated_pcm((l,r),(pl,pr),on)
            assert pc<c,("PCM FIFO order",seg,i)
            if on:audible+=1
            else:muted+=1
        if seg==0:
            assert muted>200 and audible>300,('missing mute/tone phases',muted,audible)
        assert len(pcm[seg])-len(decoded[seg])<8,'unexplained sample loss'
    # A changed received bit MUST fail, protecting against an always-PASS checker.
    negative=False
    try:verify_packet(headers[0][0]^1,headers[0][1])
    except AssertionError:negative=True
    assert negative,'negative control was not detected'
    mute_negative=False
    try:check_gated_pcm((1,0),(1,0),False)
    except AssertionError:mute_negative=True
    assert mute_negative,'muted PCM leakage negative control was not detected'
    result={'passed':True,'trace_sha256':{f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in ['symbols.txt','pcm.txt','rx.txt','gate.txt']},'symbols_checked':symbols,'packets':dict(types),'received_i2s_frames':[len(x) for x in rx],'hdmi_pcm_frames':[len(x) for x in decoded],'pcm_tail_pending':[len(pcm[i])-len(decoded[i]) for i in range(2)],'checks':['active TMDS equals legacy in TB','32-symbol TERC4 islands and HS/VS','8-preamble/2-guard geometry','polynomial BCH all headers/subpackets','AVI/AudioInfo checksum and fields','ACR N6144 CTS74250 48kHz','I2S serial receive sine/stereo and 48k cadence','signed 24bit divide4','IEC60958 192-frame C/B/parity','visible: HDMI PCM equals I2S/gain FIFO order; hidden: zero PCM after FIFO','reset flush and restart','deliberate BCH corruption rejected','deliberate muted-PCM leakage rejected'],'muted_pcm_negative_control':mute_negative,'muted_frames':muted,'audible_frames':audible,'scope':'digital parallel TMDS receiver only; no native serializer/electrical/audio sink verification'}
    (out/'independent_decode.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))

if __name__=='__main__':main(Path(sys.argv[1]))
