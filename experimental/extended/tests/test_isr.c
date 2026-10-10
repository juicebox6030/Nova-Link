/*
 * Deferred SPI handoff, critical sections and plugin hooks. Built against
 * a copy of the core compiled with tests/isr_config/nl_config_user.h
 * (counting hooks) and NL_ISR_BUILD=1 (logging compiled out).
 */
#include "nl_test.h"

#include "nova_link/nl_host.h"
#include "nova_link/nl_radio.h"
#include "nova_link/nl_log.h"

/* The ISR build must drop every log call, NL_LOGE included. */
#if NL_LOG_MIN_LEVEL != 4
#error "NL_ISR_BUILD must default NL_LOG_MIN_LEVEL to 4 (NL_LOG_NONE)"
#endif

/* ---- Counting hooks (declared in isr_config/nl_config_user.h) ----------- */

static unsigned crit_depth, crit_max, crit_enters, crit_exits;
static unsigned plug_stack[8], plug_depth, plug_enters, plug_exits, plug_bad;

unsigned nl_test_crit_enter(void)
{
    crit_enters++;
    unsigned saved = crit_depth++;
    if (crit_depth > crit_max) {
        crit_max = crit_depth;
    }
    return saved;
}

void nl_test_crit_exit(unsigned saved)
{
    crit_exits++;
    /* Nest-safe: exit restores exactly the state its enter saved. */
    if (crit_depth != saved + 1u) {
        plug_bad |= 0x100u;
    }
    crit_depth = saved;
}

void nl_test_plugin_enter(unsigned id)
{
    plug_enters++;
    if (plug_depth < 8) {
        plug_stack[plug_depth] = id;
    }
    plug_depth++;
}

void nl_test_plugin_exit(unsigned id)
{
    plug_exits++;
    if (plug_depth == 0 || (plug_depth <= 8 && plug_stack[plug_depth - 1] != id)) {
        plug_bad++;
    }
    if (plug_depth > 0) {
        plug_depth--;
    }
}

static void reset_counters(void)
{
    crit_depth = crit_max = crit_enters = crit_exits = 0;
    plug_depth = plug_enters = plug_exits = plug_bad = 0;
}

/* ---- Helpers ------------------------------------------------------------- */

static void setup(nl_radio_t *r)
{
    nl_radio_init(r);
    nl_radio_params_t p;
    nl_radio_params_default(&p);
    p.origin_id = 1;
    nl_zone_plan_t plan;
    memset(&plan, 0, sizeof(plan));
    for (int z = 0; z < NL_NUM_ZONES; z++) {
        plan.zone[z].subghz_hz = 903000000u + 3000000u * (uint32_t)z;
    }
    plan.zone[1].priority = 1;
    nl_radio_configure(r, &p, &plan);
    reset_counters();
}

/** Encode a request; returns its length. */
static size_t req(uint8_t *buf, uint8_t cmd, const uint8_t *data, size_t len)
{
    int n = nl_link_encode(cmd, data, len, buf, NL_LINK_FRAME_MAX);
    CHECK(n > 0);
    return (size_t)n;
}

static size_t frag(uint8_t *buf, uint8_t origin, uint8_t zone, uint8_t seq)
{
    const uint8_t payload[] = {0xC0, 0xFF, 0xEE};
    nl_fragment_t f = {.origin_id = origin, .zone_id = zone, .seq = seq,
                       .payload = payload, .payload_len = sizeof(payload)};
    return (size_t)nl_fragment_encode(&f, buf, NL_MAX_FRAGMENT);
}

/** Arm the reply and decode it; returns its command (0 = nothing armed). */
static uint8_t armed_cmd(nl_radio_t *r, nl_link_view_t *v)
{
    size_t n = 0;
    const uint8_t *p = nl_radio_spi_arm(r, &n);
    if (p == NULL) {
        CHECK_EQ(n, 0);
        return 0;
    }
    CHECK_EQ(nl_link_find(p, n, v, NULL), NL_OK);
    return v->cmd;
}

/* ---- Deferred path ------------------------------------------------------- */

static void test_isr_then_poll(void)
{
    nl_radio_t r;
    setup(&r);
    uint8_t b[NL_LINK_FRAME_MAX];
    size_t n = req(b, NL_CMD_PING, NULL, 0);
    nl_link_view_t v;

    nl_radio_spi_isr(&r, b, n);
    CHECK_EQ(r.spi_wr, 1);
    CHECK_EQ(armed_cmd(&r, &v), 0); /* not handled yet */
    CHECK_EQ(nl_radio_poll(&r, 10), 1);
    CHECK_EQ(r.spi_rd, 1);
    CHECK_EQ(r.outbox_state, NL_OUTBOX_READY);
    CHECK_EQ(armed_cmd(&r, &v), NL_RSP_PONG);
    CHECK_EQ(r.outbox_state, NL_OUTBOX_ARMED);
    CHECK_EQ(armed_cmd(&r, &v), 0); /* already armed */

    /* The host's response read: filler only, frees the outbox, not queued. */
    uint8_t fill[NL_LINK_FRAME_MAX];
    memset(fill, 0, sizeof(fill));
    nl_radio_spi_isr(&r, fill, sizeof(fill));
    CHECK_EQ(r.outbox_state, NL_OUTBOX_EMPTY);
    CHECK_EQ(r.spi_wr, 1);
    CHECK_EQ(nl_radio_poll(&r, 20), 0);
    CHECK_EQ(r.spi_overruns, 0);
}

static void test_isr_push(void)
{
    nl_radio_t r;
    setup(&r);
    uint8_t f[NL_MAX_FRAGMENT], b[NL_LINK_FRAME_MAX + 4];
    size_t fl = frag(f, 0, 1, 7);
    /* Leading filler before the sync byte is skipped. */
    b[0] = 0;
    b[1] = 0;
    size_t n = 2 + req(b + 2, NL_CMD_PUSH, f, fl);
    nl_radio_spi_isr(&r, b, n);
    nl_radio_status_t st;
    nl_radio_get_status(&r, &st);
    CHECK_EQ(st.tx_queue_len, 0);
    CHECK_EQ(nl_radio_poll(&r, 0), 1);
    nl_radio_get_status(&r, &st);
    CHECK_EQ(st.tx_queue_len, 1);
    /* PUSH has no reply. */
    CHECK_EQ(r.outbox_state, NL_OUTBOX_EMPTY);
}

static void test_overrun(void)
{
    nl_radio_t r;
    setup(&r);
    uint8_t b[NL_LINK_FRAME_MAX];
    size_t n = req(b, NL_CMD_PING, NULL, 0);
    for (int i = 0; i < NL_RADIO_SPI_SLOTS + 1; i++) {
        nl_radio_spi_isr(&r, b, n);
    }
    CHECK_EQ(r.spi_overruns, 1);
    for (int i = 0; i < NL_RADIO_SPI_SLOTS; i++) {
        CHECK_EQ(nl_radio_poll(&r, 0), 1);
    }
    CHECK_EQ(nl_radio_poll(&r, 0), 0);
    /* Space again after the main loop caught up. */
    nl_radio_spi_isr(&r, b, n);
    CHECK_EQ(r.spi_overruns, 1);
    CHECK_EQ(nl_radio_poll(&r, 0), 1);
}

static void test_index_wrap(void)
{
    nl_radio_t r;
    setup(&r);
    uint8_t b[NL_LINK_FRAME_MAX];
    size_t n = req(b, NL_CMD_PING, NULL, 0);
    nl_link_view_t v;
    for (int i = 0; i < 300; i++) { /* the uint8_t indices wrap */
        nl_radio_spi_isr(&r, b, n);
        CHECK_EQ(nl_radio_poll(&r, 0), 1);
        CHECK_EQ(armed_cmd(&r, &v), NL_RSP_PONG);
        nl_radio_spi_isr(&r, NULL, 0);
    }
    CHECK_EQ(r.spi_overruns, 0);
}

static void test_empty_poll(void)
{
    nl_radio_t r;
    setup(&r);
    nl_radio_t before = r;
    CHECK_EQ(nl_radio_poll(&r, 1000), 0);
    CHECK(memcmp(&before, &r, sizeof(r)) == 0);
    CHECK_EQ(crit_enters, 0);
}

static void test_pull_reply_busy(void)
{
    nl_radio_t r;
    setup(&r);
    uint8_t f[NL_MAX_FRAGMENT], b[NL_LINK_FRAME_MAX];
    for (uint8_t s = 0; s < 2; s++) {
        size_t fl = frag(f, 3, 1, s);
        nl_radio_rx_packet(&r, f, fl, 0);
    }
    size_t n = req(b, NL_CMD_PULL, NULL, 0);
    nl_link_view_t v;

    /* Two PULLs queued before the main loop runs. It handles the first and
     * arms the reply (SPI idle), then handles the second while that reply
     * is still owned by SPI: no reply, and the fragment is not dequeued. */
    nl_radio_spi_isr(&r, b, n);
    nl_radio_spi_isr(&r, b, n);
    CHECK_EQ(nl_radio_poll(&r, 0), 1);
    CHECK_EQ(armed_cmd(&r, &v), NL_RSP_FRAGMENT);
    CHECK_EQ(r.rxq_count, 1);
    CHECK_EQ(nl_radio_poll(&r, 0), 1);
    CHECK_EQ(r.spi_reply_busy, 1);
    CHECK_EQ(r.rxq_count, 1);
    CHECK_EQ(r.outbox_state, NL_OUTBOX_ARMED);

    /* The host's read clocks the armed reply out; its retried PULL then
     * gets the second fragment. */
    nl_radio_spi_isr(&r, NULL, 0);
    CHECK_EQ(r.outbox_state, NL_OUTBOX_EMPTY);
    nl_radio_spi_isr(&r, b, n);
    nl_radio_poll(&r, 0);
    CHECK_EQ(armed_cmd(&r, &v), NL_RSP_FRAGMENT);
    CHECK(v.len > 0);
    CHECK_EQ(v.data[1], 1); /* seq 1 */
    CHECK_EQ(r.rxq_count, 0);
}

static void test_ready_reply_replaced(void)
{
    nl_radio_t r;
    setup(&r);
    uint8_t b[NL_LINK_FRAME_MAX];
    nl_link_view_t v;
    nl_radio_spi_isr(&r, b, req(b, NL_CMD_PING, NULL, 0));
    nl_radio_spi_isr(&r, b, req(b, NL_CMD_STATUS, NULL, 0));
    nl_radio_poll(&r, 0);
    nl_radio_poll(&r, 0);
    /* The never-armed PONG was replaced by the newer STATUS reply. */
    CHECK_EQ(armed_cmd(&r, &v), NL_RSP_STATUS);
    CHECK_EQ(r.spi_reply_busy, 0);
}

static void test_direct_path_unchanged(void)
{
    nl_radio_t r;
    setup(&r);
    uint8_t b[NL_LINK_FRAME_MAX];
    size_t n = req(b, NL_CMD_PING, NULL, 0);
    nl_radio_spi_complete(&r, b, n, 0);
    size_t olen;
    const uint8_t *o = nl_radio_outbox(&r, &olen);
    nl_link_view_t v;
    CHECK_EQ(nl_link_find(o, olen, &v, NULL), NL_OK);
    CHECK_EQ(v.cmd, NL_RSP_PONG);
    CHECK_EQ(r.outbox_state, NL_OUTBOX_EMPTY);
}

/* ---- Critical sections ---------------------------------------------------- */

static void test_critical_balanced(void)
{
    nl_radio_t r;
    setup(&r);
    uint8_t f[NL_MAX_FRAGMENT], b[NL_LINK_FRAME_MAX];
    nl_link_view_t v;
    for (uint8_t s = 0; s < NL_RADIO_RXQ_DEPTH + 2; s++) { /* incl. drop-oldest */
        size_t fl = frag(f, 3, 1, s);
        nl_radio_rx_packet(&r, f, fl, 0);
    }
    nl_radio_spi_isr(&r, b, req(b, NL_CMD_PULL, NULL, 0));
    nl_radio_poll(&r, 0);
    armed_cmd(&r, &v);
    nl_radio_spi_isr(&r, NULL, 0);
    nl_radio_params_t p;
    nl_radio_params_default(&p);
    p.origin_id = 2;
    nl_zone_plan_t plan;
    memset(&plan, 0, sizeof(plan));
    nl_radio_configure(&r, &p, &plan);
    CHECK(crit_enters > 0);
    CHECK_EQ(crit_enters, crit_exits);
    CHECK_EQ(crit_depth, 0);
    CHECK_EQ(crit_max, 1); /* no section nests another */
    CHECK_EQ(plug_bad, 0);
}

/* ---- Logging compiled out ------------------------------------------------- */

static void test_rejects_counted_not_logged(void)
{
    nl_radio_t r;
    setup(&r);
    nl_log_set_level(NL_LOG_DEBUG);
    uint8_t b[NL_LINK_FRAME_MAX];
    const uint8_t junk[3] = {1, 2, 3};
    nl_radio_spi_complete(&r, b, req(b, 0x7E, NULL, 0), 0);          /* unknown */
    nl_radio_spi_complete(&r, b, req(b, NL_CMD_ZONE_CONFIG, junk, 3), 0);
    nl_radio_spi_complete(&r, b, req(b, NL_CMD_RADIO_CONFIG, junk, 3), 0);
    nl_radio_spi_complete(&r, b, req(b, NL_CMD_PUSH, junk, 1), 0); /* < header */
    CHECK_EQ(r.spi_rejected, 4);
    size_t n = req(b, NL_CMD_PING, NULL, 0);
    b[n - 1] ^= 0xFF;
    nl_radio_spi_complete(&r, b, n, 0);
    CHECK_EQ(r.spi_crc_errors, 1);
    CHECK_EQ(nl_test_log_count(NL_LOG_DEBUG), 0);
    nl_log_set_level(NL_LOG_INFO);
}

static void test_loge_compiled_out(void)
{
    /* At level 4 NL_LOGE is ((void)0): its arguments are never evaluated. */
    int evaluated = 0;
    NL_LOGE("isr", "%d", ++evaluated);
    CHECK_EQ(evaluated, 0);
    CHECK_EQ(nl_test_log_count(NL_LOG_ERROR), 0);
}

/* ---- Plugin hooks ----------------------------------------------------------- */

static int fake_push(void *ctx, const uint8_t *frag_, size_t len)
{
    (void)ctx;
    (void)frag_;
    (void)len;
    return NL_OK;
}

static uint8_t pull_buf[2][NL_MAX_FRAGMENT];
static size_t pull_len[2];
static int pull_n;

static int fake_pull(void *ctx, uint8_t *buf, size_t cap)
{
    (void)ctx;
    if (pull_n == 0 || pull_len[pull_n - 1] > cap) {
        return 0;
    }
    pull_n--;
    memcpy(buf, pull_buf[pull_n], pull_len[pull_n]);
    return (int)pull_len[pull_n];
}

typedef struct {
    int calls;
    unsigned depth_seen;
} probe_t;

static int probe_init(nl_host_t *h, uint8_t slot, void *user)
{
    ((probe_t *)user)->calls++;
    ((probe_t *)user)->depth_seen = plug_depth;
    return nl_host_claim(h, slot, 1, NL_CLAIM_SHARED);
}

static void probe_frag(nl_host_t *h, uint8_t slot, const nl_fragment_t *f, void *user)
{
    (void)h;
    (void)f;
    ((probe_t *)user)->calls++;
    if (plug_depth != 1 || plug_stack[0] != slot) {
        plug_bad++;
    }
}

static void probe_meta(nl_host_t *h, uint8_t slot, uint8_t origin, const uint8_t *d,
                       size_t len, void *user)
{
    (void)h;
    (void)origin;
    (void)d;
    (void)len;
    ((probe_t *)user)->calls++;
    if (plug_depth != 1 || plug_stack[0] != slot) {
        plug_bad++;
    }
}

static void probe_tick(nl_host_t *h, uint8_t slot, nl_time_us_t now, void *user)
{
    (void)h;
    (void)now;
    ((probe_t *)user)->calls++;
    if (plug_depth != 1 || plug_stack[0] != slot) {
        plug_bad++;
    }
}

static void probe_deinit(nl_host_t *h, uint8_t slot, void *user)
{
    (void)h;
    (void)slot;
    ((probe_t *)user)->calls++;
}

static void test_plugin_hooks(void)
{
    static nl_host_t host;
    nl_host_config_t cfg;
    nl_host_config_default(&cfg);
    cfg.origin_id = 2;
    cfg.announce_interval_us = 0;
    cfg.announce_boot_spread_us = 0;
    cfg.status_interval_us = 0;
    nl_link_ops_t ops = {fake_push, fake_pull, NULL, NULL, NULL, NULL};
    CHECK_EQ(nl_host_init(&host, &cfg, &ops), NL_OK);
    reset_counters();

    probe_t pr = {0, 0};
    nl_plugin_def_t def = {.name = "p", .type_id = 0x77, .init = probe_init,
                           .on_fragment = probe_frag, .on_meta = probe_meta,
                           .on_tick = probe_tick, .deinit = probe_deinit,
                           .user = &pr};
    int slot = nl_host_register(&host, &def);
    CHECK_EQ(slot, 0);
    CHECK_EQ(pr.depth_seen, 1);

    /* One fragment on the claimed zone, one PLUGIN_DATA record for it. */
    pull_len[1] = frag(pull_buf[1], 3, 1, 0);
    const uint8_t rec[] = {NL_META_PLUGIN_DATA, 4, 0x77, 0x00, 'h', 'i'};
    nl_fragment_t mf = {.origin_id = 3, .zone_id = 0, .seq = 0,
                        .payload = rec, .payload_len = sizeof(rec)};
    pull_len[0] = (size_t)nl_fragment_encode(&mf, pull_buf[0], NL_MAX_FRAGMENT);
    pull_n = 2;
    nl_host_poll(&host, 1000);
    CHECK_EQ(nl_host_unregister(&host, (uint8_t)slot), NL_OK);

    CHECK_EQ(pr.calls, 5); /* init, fragment, meta, tick, deinit */
    CHECK_EQ(plug_enters, 5);
    CHECK_EQ(plug_exits, 5);
    CHECK_EQ(plug_depth, 0);
    CHECK_EQ(plug_bad, 0);
}

int main(void)
{
    RUN(test_isr_then_poll);
    RUN(test_isr_push);
    RUN(test_overrun);
    RUN(test_index_wrap);
    RUN(test_empty_poll);
    RUN(test_pull_reply_busy);
    RUN(test_ready_reply_replaced);
    RUN(test_direct_path_unchanged);
    RUN(test_critical_balanced);
    RUN(test_rejects_counted_not_logged);
    RUN(test_loge_compiled_out);
    RUN(test_plugin_hooks);
    return nl_test_finish();
}
