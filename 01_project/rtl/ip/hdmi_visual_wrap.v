`timescale 1ns / 1ps
//--------------------------------------------------------------------------------
// hdmi_tx_wrap.v —— 把 RGB + 行场同步 变成 4 对 TMDS（3 数据 + 1 时钟）
//
// 通道映射（HDMI 规范固定）：
//   D0 = 蓝(B) + HS/VS 控制位      D1 = 绿(G)      D2 = 红(R)
// 顶层仅连接 P 逻辑端口；实际差分对由 NG88 的 LVDS25 PAD 配对实现。
// *_n 为此 RTL 包装层的未使用占位输出，不是外部 N 引脚驱动。
//--------------------------------------------------------------------------------
module hdmi_visual_wrap #(parameter INDEPENDENT_SERIAL_RESET=0, parameter HDMI_AUDIO_ENABLE=0, parameter HDMI_AUDIO_GATE_ENABLE=0) (
    input  wire       clk_pix,
    input  wire       clk_5x,
    input  wire       rst_n,
    input  wire [7:0] r,
    input  wire [7:0] g,
    input  wire [7:0] b,
    input  wire       de,
    input  wire       hs,
    input  wire       vs,
    output wire       tmds_clk_p,
    output wire       tmds_clk_n,
    output wire [2:0] tmds_d_p,
    output wire [2:0] tmds_d_n,
    input wire serial_async_n, // PLL lock, not the pixel-domain released reset
    input wire [11:0] cx,cy, // aligned with incoming RGB/DE
    input wire picture_visible, // pixel domain; held across horizontal/vertical blanking
    input wire signed [23:0] pcm_l,pcm_r,
    input wire pcm_valid,
    output wire audio_fault
);
    // v055: two local reset domains. The production top supplies PLL lock
    // directly; never deassert a 371.25MHz reset from a 74.25MHz falling edge.
    wire serial_rst_n;
    generate if(INDEPENDENT_SERIAL_RESET) begin: g_local_serial_reset
        // Consumers are posedge clk_5x flops: release on the SAME edge
        // for a full 2.693 ns recovery budget, not a half-cycle 1.347 ns.
        reset_release #(.RELEASE_FALLING_EDGE(0)) release5(
            .clk(clk_5x),.async_n(serial_async_n),.rst_n(serial_rst_n));
    end else begin: g_legacy_serial_reset
        // Compatibility for historical tops; NOT the active idx_video_top.
        reg [1:0] rst5_sync;
        always @(posedge clk_5x or negedge rst_n)
            if(!rst_n) rst5_sync<=0;
            else rst5_sync<={rst5_sync[0],1'b1};
        assign serial_rst_n=rst5_sync[1];
    end endgenerate
    wire rst=~serial_rst_n;

    // Register ALL pixel payload/control together: break FIFO RAM/mux ->
    // encoder combinational chain without changing RGB/DE/HS/VS alignment.
    wire [8:0] pb,pg,pr;wire [3:0] nb,ng,nr;
    tmds_prepare prep_b(.din(b),.q_m(pb),.n1q_m(nb));
    tmds_prepare prep_g(.din(g),.q_m(pg),.n1q_m(ng));
    tmds_prepare prep_r(.din(r),.q_m(pr),.n1q_m(nr));
    reg [8:0] mb_q,mg_q,mr_q;reg [3:0] nb_q,ng_q,nr_q;
    reg de_q,hs_q,vs_q,picture_q;
    reg [11:0] cx_q,cy_q;
    always @(posedge clk_pix or negedge rst_n)
        if(!rst_n) begin mb_q<=0;mg_q<=0;mr_q<=0;nb_q<=0;ng_q<=0;nr_q<=0;picture_q<=0;de_q<=0;hs_q<=0;vs_q<=0;cx_q<=0;cy_q<=0;end
        else begin mb_q<=pb;mg_q<=pg;mr_q<=pr;nb_q<=nb;ng_q<=ng;nr_q<=nr;picture_q<=picture_visible;de_q<=de;hs_q<=hs;vs_q<=vs;cx_q<=cx;cy_q<=cy;end

    wire vp,ip,aux;wire [9:0] ab,ag,ar;
    generate if(HDMI_AUDIO_ENABLE)begin: audio
        // Same post-gain PCM is shared with the spectrum analyzer.
        hdmi_audio_packets #(.GATE_ENABLE(HDMI_AUDIO_GATE_ENABLE)) packets(.clk_pix(clk_pix),.rst_n(rst_n),.cx(cx_q),.cy(cy_q),
          .pcm_l(pcm_l),.pcm_r(pcm_r),.pcm_valid(pcm_valid),.audio_enable(picture_q),.video_preamble(vp),.island_preamble(ip),
          .aux_period(aux),.aux_b(ab),.aux_g(ag),.aux_r(ar),.hs(hs_q),.vs(vs_q),.overflow(audio_fault));
    end else begin: no_audio
        assign vp=0;assign ip=0;assign aux=0;assign ab=0;assign ag=0;assign ar=0;assign audio_fault=0;
    end endgenerate
    // Same register boundary as video encoders: no active-pixel latency change.
    reg aux_q;reg [9:0] ab_q,ag_q,ar_q;
    always @(posedge clk_pix or negedge rst_n)
      if(!rst_n)begin aux_q<=0;ab_q<=0;ag_q<=0;ar_q<=0;end
      else begin aux_q<=aux&&!de_q;ab_q<=ab;ag_q<=ag;ar_q<=ar;end

    // ---- 编码 ----
    wire [9:0] q_b, q_g, q_r;

    tmds_encoder #(.PREPARED_INPUT(1)) u_enc_b (
        .clk   (clk_pix),
        .rst_n (rst_n),
        .din   (8'd0),.q_m_in(mb_q),.ones_in(nb_q),
        .de    (de_q),
        .c     ({vs_q, hs_q}),
        .q     (q_b)
    );

    tmds_encoder #(.PREPARED_INPUT(1)) u_enc_g (
        .clk   (clk_pix),
        .rst_n (rst_n),
        .din   (8'd0),.q_m_in(mg_q),.ones_in(ng_q),
        .de    (de_q),
        .c     ({1'b0,vp|ip}),
        .q     (q_g)
    );

    tmds_encoder #(.PREPARED_INPUT(1)) u_enc_r (
        .clk   (clk_pix),
        .rst_n (rst_n),
        .din   (8'd0),.q_m_in(mr_q),.ones_in(nr_q),
        .de    (de_q),
        .c     ({1'b0,ip}),
        .q     (q_r)
    );

    // v072: register the COMPLETE selected symbol in the pixel domain.
    // The 371MHz load path must not include the auxiliary/video selection.
    // All data lanes, controls, guards and islands gain exactly one pixel.
    // Legacy video-only builds retain their original latency.
    wire [9:0] symbol_b,symbol_g,symbol_r;
    generate if(HDMI_AUDIO_ENABLE) begin: g_symbol_pipe
        reg [9:0] b,g,r;
        always @(posedge clk_pix or negedge rst_n)
          if(!rst_n) begin b<=10'b1101010100;g<=10'b1101010100;r<=10'b1101010100;end
          else begin b<=aux_q ? ab_q:q_b;g<=aux_q ? ag_q:q_g;r<=aux_q ? ar_q:q_r;end
        assign symbol_b=b;assign symbol_g=g;assign symbol_r=r;
    end else begin: g_no_symbol_pipe
        assign symbol_b=q_b;assign symbol_g=q_g;assign symbol_r=q_r;
    end endgenerate

    // ---- 串行化 ----
    tmds_serializer #(.SEPARATE_PIXEL_RESET(1)) u_ser_b (
        .clk_pix (clk_pix),
        .clk_5x (clk_5x),
        .rst    (rst),
        .rst_pix_n(rst_n),
        .din    (symbol_b),
        .q      (tmds_d_p[0])
    );

    tmds_serializer #(.SEPARATE_PIXEL_RESET(1)) u_ser_g (
        .clk_pix (clk_pix),
        .clk_5x (clk_5x),
        .rst    (rst),
        .rst_pix_n(rst_n),
        .din    (symbol_g),
        .q      (tmds_d_p[1])
    );

    tmds_serializer #(.SEPARATE_PIXEL_RESET(1)) u_ser_r (
        .clk_pix (clk_pix),
        .clk_5x (clk_5x),
        .rst    (rst),
        .rst_pix_n(rst_n),
        .din    (symbol_r),
        .q      (tmds_d_p[2])
    );

    tmds_clock_lane #(.SEPARATE_PIXEL_RESET(1)) u_ser_clk (
        .clk_pix (clk_pix),
        .clk_5x (clk_5x),
        .rst    (rst),
        .rst_pix_n(rst_n),
        .q      (tmds_clk_p)
    );

    assign tmds_clk_n = 1'b0;
    assign tmds_d_n   = 3'b000;

endmodule
