#include "nl_test.h"

#include "nova_link/nl_host.h"
#include "nova_link/nl_segment.h"

/* ---- Fake link ---------------------------------------------------------- */

#define FAKE_MAX 64

typedef struct {
    uint8_t data[NL_MAX_FRAGMENT];
    size_t len;
} pkt_t;

typedef struct {
    pkt_t pushed[FAKE_MAX];
    int npushed;
    pkt_t rx[FAKE_MAX];
    int rx_head, rx_tail;
    int pulls;
    int configures;
    nl_radio_params_t params;
    nl_zone_plan_t plan;
    nl_radio_status_t status;
    bool fail_push, fail_pull, fail_configure;
} fake_t;

static int fake_push(void *ctx, const uint8_t *frag, size_t len)
{
    fake_t *f = ctx;
    if (f->fail_push || f->npushed == FAKE_MAX) {
        return NL_ERR_IO;
    }
    memcpy(f->pushed[f->npushed].data, frag, len);
    f->pushed[f->npushed++].len = len;
    return NL_OK;
}

static int fake_pull(void *ctx, uint8_t *buf, size_t cap)
{
    fake_t *f = ctx;
    f->pulls++;
    if (f->fail_pull) {
        return NL_ERR_IO;
    }
    if (f->rx_head == f->rx_tail) {
        return 0;
    }
    pkt_t *p = &f->rx[f->rx_head++];
    if (p->len > cap) {
        return NL_ERR_SIZE;
    }
    memcpy(buf, p->data, p->len);
    return (int)p->len;
}

static int fake_configure(void *ctx, const nl_radio_params_t *params,
                          const nl_zone_plan_t *plan)
{
    fake_t *f = ctx;
    if (f->fail_configure) {
        return NL_ERR_IO;
    }
    f->configures++;
    f->params = *params;
    f->plan = *plan;
    f->status.flags |= NL_STATUS_F_CONFIGURED;
    return NL_OK;
}

static int fake_status(void *ctx, nl_radio_status_t *st)
{
    *st = ((fake_t *)ctx)->status;
    return NL_OK;
}

static void fake_rx(fake_t *f, uint8_t origin, uint8_t zone, uint8_t seq,
                    const void *payload, size_t len)
{
    nl_fragment_t fr = {.origin_id = origin, .zone_id = zone, .seq = seq,
                        .payload = payload, .payload_len = (uint8_t)len};
    pkt_t *p = &f->rx[f->rx_tail++];
    p->len = (size_t)nl_fragment_encode(&fr, p->data, sizeof(p->data));
}

static void decode_pushed(const fake_t *f, int i, nl_fragment_t *out)
{
    CHECK(i < f->npushed);
    CHECK_EQ(nl_fragment_decode(f->pushed[i].data, f->pushed[i].len, out), NL_OK);
}

/* ---- Test plugins ------------------------------------------------------- */

typedef struct {
    uint8_t claim_zone[4];
    nl_claim_mode_t claim_mode[4];
    int nclaims;
    int init_rc;
    int fragments;
    nl_fragment_t last;
    uint8_t last_payload[NL_MAX_PAYLOAD];
    int metas;
    uint8_t meta_origin;
    uint8_t meta_data[NL_META_MAX_VALUE];
    size_t meta_len;
    int ticks, deinits;
} probe_t;

static int probe_init(nl_host_t *h, uint8_t slot, void *user)
{
    probe_t *p = user;
    for (int i = 0; i < p->nclaims; i++) {
        int rc = nl_host_claim(h, slot, p->claim_zone[i], p->claim_mode[i]);
        if (rc < 0) {
            return rc;
        }
    }
    return p->init_rc;
}

static void probe_frag(nl_host_t *h, uint8_t slot, const nl_fragment_t *f, void *user)
{
    (void)h;
    (void)slot;
    probe_t *p = user;
    p->fragments++;
    p->last = *f;
    memcpy(p->last_payload, f->payload, f->payload_len);
    p->last.payload = p->last_payload;
}

static void probe_meta(nl_host_t *h, uint8_t slot, uint8_t origin, const uint8_t *data,
                       size_t len, void *user)
{
    (void)h;
    (void)slot;
    probe_t *p = user;
    p->metas++;
    p->meta_origin = origin;
    memcpy(p->meta_data, data, len);
    p->meta_len = len;
}

static void probe_tick(nl_host_t *h, uint8_t slot, nl_time_us_t now, void *user)
{
    (void)h;
    (void)slot;
    (void)now;
    ((probe_t *)user)->ticks++;
}

static void probe_deinit(nl_host_t *h, uint8_t slot, void *user)
{
    (void)h;
    (void)slot;
    ((probe_t *)user)->deinits++;
}

static nl_plugin_def_t probe_def(const char *name, uint16_t type, probe_t *p)
{
    nl_plugin_def_t d = {.name = name, .type_id = type, .init = probe_init,
                         .on_fragment = probe_frag, .on_meta = probe_meta,
                         .on_tick = probe_tick, .deinit = probe_deinit, .user = p};
    return d;
}

static void probe_claims(probe_t *p, uint8_t zone, nl_claim_mode_t mode)
{
    p->claim_zone[p->nclaims] = zone;
    p->claim_mode[p->nclaims++] = mode;
}

/* ---- Fixture ------------------------------------------------------------ */

static fake_t fake;
static nl_host_t host;

static void setup_cfg(nl_host_config_t *cfg)
{
    memset(&fake, 0, sizeof(fake));
    nl_link_ops_t ops = {fake_push, fake_pull, NULL, fake_configure, fake_status, &fake};
    CHECK_EQ(nl_host_init(&host, cfg, &ops), NL_OK);
    nl_radio_params_t params;
    nl_radio_params_default(&params);
    nl_zone_plan_t plan;
    memset(&plan, 0, sizeof(plan));
    for (int z = 0; z < NL_NUM_ZONES; z++) {
        plan.zone[z].subghz_hz = 903000000u + 3000000u * (uint32_t)z;
    }
    plan.zone[3].priority = 4;
    nl_host_set_rf(&host, &params, &plan);
}

/** Host with origin 2, no periodic announcements, no status polling. */
static void setup(void)
{
    nl_host_config_t cfg;
    nl_host_config_default(&cfg);
    cfg.announce_boot_spread_us = 0;
    cfg.origin_id = 2;
    cfg.announce_interval_us = 0;
    cfg.status_interval_us = 0;
    setup_cfg(&cfg);
}

/** Run the first poll and flush the startup announcements. */
static nl_time_us_t start(void)
{
    nl_host_poll(&host, 0);
    nl_time_us_t t = host.cfg.meta_lead_us;
    while (nl_meta_queue_pending(&host.meta)) {
        nl_host_poll(&host, t);
        t += host.cfg.meta_interval_us;
    }
    t += host.cfg.mgmt_flag_hold_us;
    nl_host_poll(&host, t);
    fake.npushed = 0;
    fake.pulls = 0;
    memset(&host.stats, 0, sizeof(host.stats));
    return t;
}

/* ---- Tests -------------------------------------------------------------- */

static void test_init_args(void)
{
    nl_host_config_t cfg;
    nl_host_config_default(&cfg);
    cfg.announce_boot_spread_us = 0;
    nl_link_ops_t ops = {fake_push, fake_pull, NULL, NULL, NULL, &fake};
    CHECK_EQ(nl_host_init(&host, NULL, &ops), NL_ERR_ARG);
    CHECK_EQ(nl_host_init(&host, &cfg, NULL), NL_ERR_ARG);
    cfg.origin_id = NL_NUM_ORIGINS;
    CHECK_EQ(nl_host_init(&host, &cfg, &ops), NL_ERR_ARG);
    cfg.origin_id = 0;
    cfg.max_pull_per_poll = 0; /* would never pull */
    CHECK_EQ(nl_host_init(&host, &cfg, &ops), NL_ERR_ARG);
    cfg.max_pull_per_poll = 1;
    CHECK_EQ(nl_host_init(&host, &cfg, &ops), NL_OK);
    ops.pull = NULL;
    CHECK_EQ(nl_host_init(&host, &cfg, &ops), NL_ERR_ARG);
}

static void test_register(void)
{
    setup();
    probe_t a = {0}, b = {0}, bad = {0};
    probe_claims(&a, 1, NL_CLAIM_EXCLUSIVE);
    probe_claims(&b, 1, NL_CLAIM_SHARED); /* conflicts with a */
    probe_claims(&bad, 5, NL_CLAIM_SHARED);
    bad.init_rc = NL_ERR_IO;
    nl_plugin_def_t da = probe_def("a", 1, &a), db = probe_def("b", 1, &b);
    nl_plugin_def_t dbad = probe_def("bad", 1, &bad);

    CHECK_EQ(nl_host_register(&host, &da), 0);
    CHECK_EQ(nl_host_register(&host, &db), NL_ERR_CONFLICT);
    CHECK_EQ(nl_host_register(&host, &dbad), NL_ERR_IO);
    CHECK(nl_test_log_contains(NL_LOG_ERROR, "plugin 'bad' init failed"));
    /* Failed init released its claims and its slot. */
    CHECK_EQ(nl_claims_zone_mask(&host.claims), 1 << 1);
    CHECK_EQ(nl_host_find_plugin(&host, "bad"), NL_ERR_NOT_FOUND);
    CHECK_EQ(nl_host_find_plugin(&host, "a"), 0);

    CHECK_EQ(nl_host_unregister(&host, 0), NL_OK);
    CHECK_EQ(a.deinits, 1);
    CHECK_EQ(nl_claims_zone_mask(&host.claims), 0);
    CHECK_EQ(nl_host_unregister(&host, 0), NL_ERR_NOT_FOUND);
    CHECK_EQ(nl_host_register(&host, &db), 0);

    static probe_t many[NL_MAX_PLUGINS];
    nl_plugin_def_t dm[NL_MAX_PLUGINS];
    for (int i = 1; i < NL_MAX_PLUGINS; i++) {
        dm[i] = probe_def("m", 1, &many[i]);
        CHECK_EQ(nl_host_register(&host, &dm[i]), i);
    }
    CHECK_EQ(nl_host_register(&host, &da), NL_ERR_FULL);
}

static void test_effective_plan_and_configure(void)
{
    setup();
    probe_t a = {0};
    probe_claims(&a, 1, NL_CLAIM_SHARED);
    probe_claims(&a, 3, NL_CLAIM_READ_ONLY);
    nl_plugin_def_t da = probe_def("a", 1, &a);
    nl_host_register(&host, &da);

    nl_host_poll(&host, 0);
    CHECK_EQ(fake.configures, 1);
    CHECK_EQ(fake.params.origin_id, 2);
    CHECK_EQ(fake.plan.zone[0].priority, 0);
    CHECK_EQ(fake.plan.zone[1].priority, 1); /* claimed, unconfigured: minimum 1 */
    CHECK_EQ(fake.plan.zone[3].priority, 4); /* claimed: configured priority */
    CHECK_EQ(fake.plan.zone[2].priority, 0);
    CHECK_EQ(fake.plan.zone[5].subghz_hz, 918000000u);

    nl_host_poll(&host, 1000);
    CHECK_EQ(fake.configures, 1); /* nothing changed */

    nl_host_release(&host, 0, 3);
    nl_host_poll(&host, 2000);
    CHECK_EQ(fake.configures, 2);
    CHECK_EQ(fake.plan.zone[3].priority, 0);

    /* A failing configure is retried on the next poll. */
    nl_host_claim(&host, 0, 6, NL_CLAIM_SHARED);
    fake.fail_configure = true;
    nl_host_poll(&host, 3000);
    CHECK_EQ(host.stats.link_errors, 1);
    fake.fail_configure = false;
    nl_host_poll(&host, 4000);
    CHECK_EQ(fake.configures, 3);
    CHECK_EQ(fake.plan.zone[6].priority, 1);
}

static void test_send_rules(void)
{
    setup();
    probe_t a = {0};
    probe_claims(&a, 1, NL_CLAIM_SHARED);
    probe_claims(&a, 2, NL_CLAIM_READ_ONLY);
    nl_plugin_def_t da = probe_def("a", 1, &a);
    nl_host_register(&host, &da);
    start();

    const uint8_t pl[NL_MAX_PAYLOAD + 1] = {1, 2, 3};
    CHECK_EQ(nl_host_send(&host, 0, 1, pl, 3, 0), NL_OK);
    /* Plugins cannot set MGMT_LISTEN themselves. */
    CHECK_EQ(nl_host_send(&host, 0, 1, pl, 3, NL_FLAG_BURST | NL_FLAG_MGMT_LISTEN), NL_OK);
    CHECK_EQ(nl_host_send(&host, 0, 1, pl, NL_MAX_PAYLOAD, 0), NL_OK);
    CHECK_EQ(nl_host_send(&host, 0, 1, pl, NL_MAX_PAYLOAD + 1, 0), NL_ERR_SIZE);
    CHECK_EQ(nl_host_send(&host, 0, 2, pl, 3, 0), NL_ERR_PERM);
    CHECK(nl_test_log_contains(NL_LOG_WARN, "may not send on zone 2 (claim: read-only)"));
    CHECK_EQ(nl_host_send(&host, 0, 4, pl, 3, 0), NL_ERR_PERM);
    CHECK_EQ(nl_host_send(&host, 0, 0, pl, 3, 0), NL_ERR_PERM);
    CHECK_EQ(nl_host_send(&host, 5, 1, pl, 3, 0), NL_ERR_ARG);
    CHECK_EQ(host.stats.tx_denied, 3);

    nl_fragment_t f;
    for (int i = 0; i < 3; i++) {
        decode_pushed(&fake, i, &f);
        CHECK_EQ(f.origin_id, 2);
        CHECK_EQ(f.zone_id, 1);
        CHECK_EQ(f.seq, i);
        CHECK_EQ(f.flags, i == 1 ? NL_FLAG_BURST : 0);
    }

    /* A failed push does not consume a sequence number. */
    fake.fail_push = true;
    CHECK_EQ(nl_host_send(&host, 0, 1, pl, 3, 0), NL_ERR_IO);
    CHECK_EQ(host.stats.tx_errors, 1);
    fake.fail_push = false;
    nl_host_send(&host, 0, 1, pl, 3, 0);
    decode_pushed(&fake, 3, &f);
    CHECK_EQ(f.seq, 3);
}

static void test_mgmt_flag_and_lead(void)
{
    setup();
    probe_t a = {0};
    probe_claims(&a, 1, NL_CLAIM_SHARED);
    nl_plugin_def_t da = probe_def("a", 0x77, &a);
    nl_host_register(&host, &da);
    nl_time_us_t t = start();
    const uint8_t pl[1] = {0};
    nl_fragment_t f;

    nl_host_send(&host, 0, 1, pl, 1, 0);
    decode_pushed(&fake, 0, &f);
    CHECK_EQ(f.flags, 0);

    nl_host_poll(&host, t);
    CHECK_EQ(nl_host_meta_send_plugin(&host, 0, (const uint8_t *)"hi", 2), NL_OK);
    nl_host_send(&host, 0, 1, pl, 1, 0);
    decode_pushed(&fake, 1, &f);
    CHECK_EQ(f.flags, NL_FLAG_MGMT_LISTEN);

    /* Zone 0 data waits for the lead time. */
    nl_host_poll(&host, t + host.cfg.meta_lead_us - 1);
    CHECK_EQ(fake.npushed, 2);
    nl_host_poll(&host, t + host.cfg.meta_lead_us);
    CHECK_EQ(fake.npushed, 3);
    decode_pushed(&fake, 2, &f);
    CHECK_EQ(f.zone_id, 0);
    const uint8_t rec[] = {NL_META_PLUGIN_DATA, 4, 0x77, 0x00, 'h', 'i'};
    CHECK_EQ(f.payload_len, sizeof(rec));
    CHECK_MEM(f.payload, rec, sizeof(rec));
    CHECK_EQ(host.stats.meta_fragments, 1);

    /* Flag stays on for the hold time after the last zone 0 fragment. */
    nl_time_us_t sent = t + host.cfg.meta_lead_us;
    nl_host_poll(&host, sent + host.cfg.mgmt_flag_hold_us - 1);
    nl_host_send(&host, 0, 1, pl, 1, 0);
    decode_pushed(&fake, 3, &f);
    CHECK_EQ(f.flags, NL_FLAG_MGMT_LISTEN);
    nl_host_poll(&host, sent + host.cfg.mgmt_flag_hold_us);
    nl_host_send(&host, 0, 1, pl, 1, 0);
    decode_pushed(&fake, 4, &f);
    CHECK_EQ(f.flags, 0);
}

static void test_meta_rate_limit(void)
{
    setup();
    nl_time_us_t t = start();
    nl_host_poll(&host, t);
    uint8_t v[NL_META_MAX_VALUE] = {0};
    for (int i = 0; i < 3; i++) {
        CHECK_EQ(nl_host_meta_push(&host, 0x80, v, sizeof(v)), NL_OK);
    }
    nl_time_us_t first = t + host.cfg.meta_lead_us;
    for (nl_time_us_t now = t; now < first + 3 * host.cfg.meta_interval_us; now += 1000) {
        nl_host_poll(&host, now);
    }
    CHECK_EQ(fake.npushed, 3);
    CHECK_EQ(host.stats.meta_fragments, 3);
    CHECK(!nl_meta_queue_pending(&host.meta));
}

/** Copy everything @p from pushed into @p to's receive path. */
static void deliver(fake_t *from, nl_host_t *to, nl_time_us_t now)
{
    for (int i = 0; i < from->npushed; i++) {
        nl_host_handle_rx(to, from->pushed[i].data, from->pushed[i].len, now);
    }
    from->npushed = 0;
}

static void test_announcements_build_peer_view(void)
{
    nl_host_config_t cfg;
    nl_host_config_default(&cfg);
    cfg.announce_boot_spread_us = 0;
    cfg.origin_id = 2;
    memcpy(cfg.name, "stage-left", 11);
    cfg.announce_interval_us = 1000000;
    cfg.status_interval_us = 0;
    setup_cfg(&cfg);
    probe_t a = {0};
    probe_claims(&a, 4, NL_CLAIM_EXCLUSIVE);
    nl_plugin_def_t da = probe_def("dmx", 0xD001, &a);
    nl_host_register(&host, &da);

    fake_t fake_b = {0};
    nl_host_t b;
    nl_link_ops_t ops = {fake_push, fake_pull, NULL, NULL, NULL, &fake_b};
    nl_host_config_t cb;
    nl_host_config_default(&cb);
    cb.announce_boot_spread_us = 0;
    cb.origin_id = 5;
    cb.peer_expiry_us = 3000000;
    nl_host_init(&b, &cb, &ops);

    for (nl_time_us_t t = 0; t <= 50000; t += 5000) {
        nl_host_poll(&host, t);
    }
    deliver(&fake, &b, 50000);
    b.now = 50000;
    const nl_host_peer_t *p = nl_host_peer(&b, 2);
    CHECK(p != NULL);
    if (p != NULL) {
        CHECK_STR(p->info.name, "stage-left");
        CHECK_EQ(p->info.proto_version, NL_LINK_PROTOCOL_VERSION);
    }
    const nl_remote_claim_t *rc = nl_remote_claims_get(&b.remote, 2, 4, 50000);
    CHECK(rc != NULL);
    if (rc != NULL) {
        CHECK_EQ(rc->mode, NL_CLAIM_EXCLUSIVE);
        CHECK_EQ(rc->plugin_type, 0xD001);
    }
    CHECK(nl_host_peer(&b, 3) == NULL);

    /* Periodic announcements keep the peer alive; silence expires it. */
    for (nl_time_us_t t = 50000; t <= 5000000; t += 5000) {
        nl_host_poll(&host, t);
        deliver(&fake, &b, t);
    }
    b.now = 5000000;
    CHECK(nl_host_peer(&b, 2) != NULL);
    b.now = 5000000 + 3000001;
    CHECK(nl_host_peer(&b, 2) == NULL);

    /* A claim change triggers an immediate re-announcement. */
    nl_host_release(&host, 0, 4);
    nl_host_poll(&host, 5005000);
    nl_host_poll(&host, 5005000 + host.cfg.meta_lead_us);
    deliver(&fake, &b, 5020000);
    CHECK(nl_remote_claims_get(&b.remote, 2, 4, 5020000) == NULL);
}

static void test_claim_announcement_truncated(void)
{
    setup();
    static probe_t p[NL_MAX_PLUGINS];
    nl_plugin_def_t d[NL_MAX_PLUGINS];
    for (int i = 0; i < NL_MAX_PLUGINS; i++) {
        for (uint8_t z = 1; z < 4; z++) {
            probe_claims(&p[i], z, NL_CLAIM_SHARED);
        }
        p[i].claim_zone[3] = 4;
        p[i].claim_mode[3] = NL_CLAIM_SHARED;
        p[i].nclaims = 4;
        d[i] = probe_def("p", 1, &p[i]);
        nl_host_register(&host, &d[i]);
    }
    nl_host_poll(&host, 0); /* 32 claims, 24 fit */
    CHECK(nl_test_log_contains(NL_LOG_WARN, "claim announcement truncated to 24 entries"));
}

static void test_dispatch(void)
{
    setup();
    probe_t a = {0}, b = {0};
    probe_claims(&a, 1, NL_CLAIM_SHARED);
    probe_claims(&b, 1, NL_CLAIM_READ_ONLY);
    nl_plugin_def_t da = probe_def("a", 1, &a), db = probe_def("b", 1, &b);
    nl_host_register(&host, &da);
    nl_host_register(&host, &db);
    start();
    a.ticks = 0;

    fake_rx(&fake, 3, 1, 10, "abc", 3);
    fake_rx(&fake, 3, 1, 10, "abc", 3); /* duplicate */
    fake_rx(&fake, 2, 1, 11, "own", 3); /* own origin */
    fake_rx(&fake, 3, 6, 12, "nobody", 6);
    fake.rx[fake.rx_tail++].len = 1; /* malformed */
    nl_host_poll(&host, 1000000);
    CHECK_EQ(a.fragments, 1);
    CHECK_EQ(b.fragments, 1);
    CHECK_EQ(a.last.origin_id, 3);
    CHECK_EQ(a.last.seq, 10);
    CHECK_MEM(a.last.payload, "abc", 3);
    CHECK_EQ(host.stats.rx_duplicates, 1);
    CHECK_EQ(host.stats.rx_undelivered, 1);
    CHECK_EQ(host.stats.rx_invalid, 1);
    CHECK_EQ(host.stats.rx_fragments, 2);
    CHECK_EQ(a.ticks, 1);
    /* Without rx_pending the host pulls until the radio returns 0. */
    CHECK_EQ(fake.pulls, 6); /* 5 fragments + the empty answer */
}

static void test_pull_bounds(void)
{
    nl_host_config_t cfg;
    nl_host_config_default(&cfg);
    cfg.announce_boot_spread_us = 0;
    cfg.max_pull_per_poll = 3;
    cfg.announce_interval_us = 0;
    setup_cfg(&cfg);
    for (int i = 0; i < 5; i++) {
        fake_rx(&fake, 3, 1, (uint8_t)i, "x", 1);
    }
    nl_host_poll(&host, 0);
    CHECK_EQ(fake.pulls, 3);
    nl_host_poll(&host, 1);
    CHECK_EQ(host.stats.rx_fragments, 5);

    fake.fail_pull = true;
    fake.pulls = 0;
    nl_host_poll(&host, 2);
    CHECK_EQ(fake.pulls, 1);
    CHECK_EQ(host.stats.link_errors, 1);
}

static int monitor_calls;
static void monitor(nl_host_t *h, const nl_fragment_t *f, nl_time_us_t now, void *user)
{
    (void)h;
    (void)f;
    (void)now;
    (void)user;
    monitor_calls++;
}

static int hook_calls;
static uint8_t hook_last_type;
static void hook(nl_host_t *h, uint8_t origin, uint8_t type, const uint8_t *v, uint8_t len,
                 void *user)
{
    (void)h;
    (void)origin;
    (void)v;
    (void)len;
    (void)user;
    hook_calls++;
    hook_last_type = type;
}

static void test_meta_dispatch(void)
{
    setup();
    probe_t a = {0}, other = {0};
    nl_plugin_def_t da = probe_def("a", 0x1234, &a), dother = probe_def("o", 0x9999, &other);
    nl_host_register(&host, &da);
    nl_host_register(&host, &dother);
    monitor_calls = hook_calls = 0;
    nl_host_set_monitor(&host, monitor, NULL);
    nl_host_set_meta_hook(&host, hook, NULL);

    const uint8_t recs[] = {NL_META_PLUGIN_DATA, 5, 0x34, 0x12, 'x', 'y', 'z',
                            0xC0, 1, 0xEE,             /* vendor type */
                            NL_META_PLUGIN_DATA, 1, 0}; /* too short */
    fake_rx(&fake, 6, 0, 0, recs, sizeof(recs));
    const uint8_t bad[] = {NL_META_DEBUG_TEXT, 50, 'a'};
    fake_rx(&fake, 6, 0, 1, bad, sizeof(bad));
    nl_host_poll(&host, 0);

    CHECK_EQ(a.metas, 1);
    CHECK_EQ(other.metas, 0);
    CHECK_EQ(a.meta_origin, 6);
    CHECK_EQ(a.meta_len, 3);
    CHECK_MEM(a.meta_data, "xyz", 3);
    CHECK_EQ(hook_calls, 3);
    CHECK_EQ(monitor_calls, 2);
    CHECK_EQ(host.stats.rx_invalid, 2); /* short PLUGIN_DATA + overrun TLV */
}

static void test_remote_type_check(void)
{
    setup();
    probe_t a = {0};
    probe_claims(&a, 2, NL_CLAIM_SHARED);
    nl_plugin_def_t da = probe_def("a", 0x10, &a);
    nl_host_register(&host, &da);

    uint8_t v[NL_META_MAX_VALUE + 2];
    nl_meta_claim_t c[] = {{2, NL_CLAIM_SHARED, 0x20}, {3, NL_CLAIM_READ_ONLY, 0x20}};
    v[0] = NL_META_CLAIM_ANNOUNCE;
    v[1] = (uint8_t)nl_meta_encode_claims(c, 1, &v[2], NL_META_MAX_VALUE);
    nl_host_handle_rx(&host, NULL, 0, 0); /* NULL data is invalid, not a crash */
    fake_rx(&fake, 4, 0, 0, v, (size_t)v[1] + 2);
    fake_rx(&fake, 4, 2, 0, "x", 1);
    nl_host_poll(&host, 0);
    CHECK_EQ(a.fragments, 0);
    CHECK_EQ(host.stats.rx_type_mismatch, 1);

    /* Origins that never announced are given the benefit of the doubt. */
    fake_rx(&fake, 5, 2, 0, "x", 1);
    nl_host_poll(&host, 1);
    CHECK_EQ(a.fragments, 1);

    /* A read-only remote claim says nothing about what it sends. */
    v[1] = (uint8_t)nl_meta_encode_claims(&c[1], 1, &v[2], NL_META_MAX_VALUE);
    c[1].zone = 2;
    v[1] = (uint8_t)nl_meta_encode_claims(&c[1], 1, &v[2], NL_META_MAX_VALUE);
    fake_rx(&fake, 4, 0, 1, v, (size_t)v[1] + 2);
    fake_rx(&fake, 4, 2, 1, "x", 1);
    nl_host_poll(&host, 2);
    CHECK_EQ(a.fragments, 2);

    host.cfg.check_remote_types = false;
    c[0].zone = 2;
    v[1] = (uint8_t)nl_meta_encode_claims(c, 1, &v[2], NL_META_MAX_VALUE);
    fake_rx(&fake, 4, 0, 2, v, (size_t)v[1] + 2);
    fake_rx(&fake, 4, 2, 2, "x", 1);
    nl_host_poll(&host, 3);
    CHECK_EQ(a.fragments, 3);
}

static void test_segmented(void)
{
    setup();
    probe_t a = {0};
    probe_claims(&a, 1, NL_CLAIM_SHARED);
    nl_plugin_def_t da = probe_def("a", 1, &a);
    nl_host_register(&host, &da);
    start();

    static uint8_t msg[NL_SEG_MAX_MESSAGE];
    for (size_t i = 0; i < sizeof(msg); i++) {
        msg[i] = (uint8_t)(i ^ (i >> 8));
    }
    size_t max_ok = (size_t)NL_RADIO_TXQ_DEPTH * NL_SEG_DATA_MAX;
    CHECK_EQ(nl_host_send_segmented(&host, 0, 1, msg, max_ok + 1), NL_ERR_SIZE);
    CHECK(nl_test_log_contains(NL_LOG_WARN, "exceeds radio queue"));
    CHECK_EQ(fake.npushed, 0);

    CHECK_EQ(nl_host_send_segmented(&host, 0, 1, msg, 512), NL_OK);
    CHECK_EQ(fake.npushed, 6);
    uint8_t buf[600];
    nl_reasm_t r;
    nl_reasm_init(&r, buf, sizeof(buf));
    const uint8_t *out = NULL;
    size_t out_len = 0;
    int done = 0;
    for (int i = 0; i < 6; i++) {
        nl_fragment_t f;
        decode_pushed(&fake, i, &f);
        CHECK_EQ(f.seq, i);
        CHECK_EQ(f.flags, i < 5 ? NL_FLAG_BURST : 0);
        done += nl_reasm_feed(&r, f.seq, f.payload, f.payload_len, &out, &out_len);
    }
    CHECK_EQ(done, 1);
    CHECK_EQ(out_len, 512);
    CHECK_MEM(out, msg, 512);
    CHECK_EQ(nl_host_send_segmented(&host, 0, 0, msg, 10), NL_ERR_PERM);
}

static void test_status_reset_and_congestion(void)
{
    nl_host_config_t cfg;
    nl_host_config_default(&cfg);
    cfg.announce_boot_spread_us = 0;
    cfg.origin_id = 1;
    cfg.announce_interval_us = 0;
    cfg.status_interval_us = 1000;
    setup_cfg(&cfg);
    probe_t a = {0};
    probe_claims(&a, 3, NL_CLAIM_SHARED);
    probe_claims(&a, 5, NL_CLAIM_READ_ONLY);
    nl_plugin_def_t da = probe_def("a", 1, &a);
    nl_host_register(&host, &da);
    nl_time_us_t t = start();
    CHECK_EQ(fake.configures, 1);

    /* Radio drops 7 TX fragments. */
    t += host.cfg.status_interval_us;
    fake.status.tx_dropped = 7;
    nl_host_poll(&host, t);
    CHECK(nl_test_log_contains(NL_LOG_WARN, "radio dropped 7 TX fragments"));
    nl_host_poll(&host, t + host.cfg.meta_lead_us);
    nl_fragment_t f;
    decode_pushed(&fake, 0, &f);
    const uint8_t rec[] = {NL_META_CONGESTION, 3, 1 << 3, 7, 0};
    CHECK_EQ(f.zone_id, 0);
    CHECK_MEM(f.payload, rec, sizeof(rec));
    t += 100000;

    /* Radio resets: unconfigured, counters back to zero. */
    nl_test_log_clear();
    fake.status.flags = 0;
    fake.status.tx_dropped = 0;
    fake.status.rx_dropped = 0;
    nl_host_poll(&host, t);
    CHECK_EQ(host.stats.radio_resets, 1);
    CHECK(!nl_test_log_contains(NL_LOG_WARN, "radio dropped"));
    nl_host_poll(&host, t + 1000);
    CHECK_EQ(fake.configures, 2);
    CHECK_EQ(host.stats.radio_resets, 1);
    CHECK(!nl_test_log_contains(NL_LOG_WARN, "radio dropped"));

    /* New drops after the reset are reported relative to the new baseline. */
    fake.status.tx_dropped = 2;
    fake.status.rx_dropped = 4;
    nl_host_poll(&host, t + 2000);
    CHECK(nl_test_log_contains(NL_LOG_WARN, "radio dropped 2 TX fragments"));
    CHECK(nl_test_log_contains(NL_LOG_WARN, "RX queue overflowed (4 lost)"));

    /* A reset we missed (already reconfigured) shows as counters going back. */
    nl_test_log_clear();
    fake.status.tx_dropped = 1;
    fake.status.rx_dropped = 0;
    nl_host_poll(&host, t + 3000);
    CHECK(!nl_test_log_contains(NL_LOG_WARN, "radio dropped"));
    CHECK(!nl_test_log_contains(NL_LOG_WARN, "overflowed"));
}

static void test_meta_debug_truncates(void)
{
    setup();
    char text[200];
    memset(text, 'q', sizeof(text) - 1);
    text[sizeof(text) - 1] = '\0';
    CHECK_EQ(nl_host_meta_debug(&host, text), NL_OK);
    CHECK_EQ(nl_host_meta_debug(&host, NULL), NL_ERR_ARG);
    uint8_t out[NL_MAX_PAYLOAD];
    CHECK_EQ(nl_meta_queue_pack(&host.meta, out, sizeof(out)), NL_MAX_PAYLOAD);
    CHECK_EQ(out[1], NL_META_MAX_VALUE);
}

/** Poll every 1 ms over [from, to) and record when announcements get queued. */
static int announce_times(nl_time_us_t from, nl_time_us_t to, nl_time_us_t *out, int max)
{
    int n = 0;
    for (nl_time_us_t t = from; t < to; t += 1000) {
        bool before = nl_meta_queue_pending(&host.meta);
        nl_host_poll(&host, t);
        if (!before && nl_meta_queue_pending(&host.meta) && n < max) {
            out[n++] = t;
        }
    }
    return n;
}

static void announce_cfg(nl_host_config_t *cfg, uint32_t seed)
{
    nl_host_config_default(cfg);
    cfg->origin_id = 2;
    cfg->rand_seed = seed;
    cfg->announce_interval_us = 800000;
    cfg->announce_jitter_us = 0;
    cfg->announce_boot_spread_us = 0;
    cfg->announce_ramp_steps = 0;
    cfg->status_interval_us = 0;
}

static void test_announce_boot_spread(void)
{
    /* Devices powered on together must not all announce at once. */
    nl_host_config_t cfg;
    nl_time_us_t first = UINT32_MAX, last = 0;
    for (uint32_t seed = 1; seed <= 8; seed++) {
        announce_cfg(&cfg, seed);
        cfg.announce_boot_spread_us = 100000;
        setup_cfg(&cfg);
        nl_time_us_t t[2] = {0, 0};
        CHECK_EQ(announce_times(0, 901000, t, 2), 2);
        CHECK(t[0] <= 100000);
        CHECK_EQ(t[1] - t[0], 800000); /* then the normal period */
        first = t[0] < first ? t[0] : first;
        last = t[0] > last ? t[0] : last;
    }
    CHECK(last - first >= 20000);

    announce_cfg(&cfg, 1);
    setup_cfg(&cfg);
    nl_time_us_t t = 1;
    CHECK_EQ(announce_times(0, 1000, &t, 1), 1);
    CHECK_EQ(t, 0); /* no spread: on the first poll */
}

static void test_announce_ramp(void)
{
    /* The first periods are halved, quartered, ... so a device that
     * started alone is found quickly once others appear. */
    nl_host_config_t cfg;
    announce_cfg(&cfg, 1);
    cfg.announce_ramp_steps = 3;
    setup_cfg(&cfg);
    nl_time_us_t t[6] = {0};
    CHECK_EQ(announce_times(0, 2400000, t, 6), 6);
    const nl_time_us_t want[6] = {0, 100000, 300000, 700000, 1500000, 2300000};
    for (int i = 0; i < 6; i++) {
        CHECK_EQ(t[i], want[i]);
    }

    cfg.announce_ramp_steps = 200; /* clamped to 16 */
    setup_cfg(&cfg);
    CHECK_EQ(host.ramp_left, 16);
}

static void test_announce_reply_to_newcomer(void)
{
    /* A device that does not know us is answered within
     * min(jitter, mgmt_hold / 2), at a random point so the answers of
     * several devices do not collide. */
    nl_time_us_t lo = UINT32_MAX, hi = 0;
    for (uint32_t seed = 1; seed <= 8; seed++) {
        nl_host_config_t cfg;
        announce_cfg(&cfg, seed);
        cfg.announce_interval_us = 10000000;
        cfg.announce_jitter_us = 250000;
        setup_cfg(&cfg);
        nl_time_us_t t0 = start();
        uint32_t window = host.params.mgmt_hold_us / 2u;
        CHECK(window < cfg.announce_jitter_us);

        fake_t fb = {0};
        nl_host_t b;
        nl_link_ops_t ops = {fake_push, fake_pull, NULL, NULL, NULL, &fb};
        nl_host_config_t cb;
        announce_cfg(&cb, seed);
        cb.origin_id = 6;
        nl_host_init(&b, &cb, &ops);
        for (nl_time_us_t t = 0; t <= 50000; t += 5000) {
            nl_host_poll(&b, t);
        }
        deliver(&fb, &host, t0);
        CHECK(nl_host_peer(&host, 6) != NULL);
        CHECK(host.reply_pending);

        nl_time_us_t t[2] = {0, 0};
        CHECK_EQ(announce_times(t0, t0 + 500000, t, 2), 1);
        CHECK(t[0] - t0 <= window + 1000);
        lo = t[0] < lo ? t[0] : lo;
        hi = t[0] > hi ? t[0] : hi;

        /* b missed the answer: its next announcement still lacks our bit
         * in NL_META_PEERS, so it is answered again. */
        for (nl_time_us_t tb = 60000; tb <= 850000; tb += 5000) {
            nl_host_poll(&b, tb);
        }
        deliver(&fb, &host, t0 + 500000);
        CHECK(host.reply_pending);
        CHECK_EQ(announce_times(t0 + 500000, t0 + 1000000, t, 2), 1);

        /* Our answers say we know b. */
        int peers_records = 0;
        for (int i = 0; i < fake.npushed; i++) {
            nl_fragment_t f;
            decode_pushed(&fake, i, &f);
            nl_meta_iter_t it;
            uint8_t type;
            const uint8_t *v;
            uint8_t vlen;
            nl_meta_iter_init(&it, f.payload, f.payload_len);
            while (nl_meta_iter_next(&it, &type, &v, &vlen) == 1) {
                if (type == NL_META_PEERS) {
                    CHECK_EQ(vlen, 1);
                    CHECK_EQ(v[0], 1u << 6);
                    peers_records++;
                }
            }
        }
        CHECK_EQ(peers_records, 2);

        /* Once b has heard us, its announcements stop asking. */
        deliver(&fake, &b, 850000);
        CHECK(nl_host_peer(&b, 2) != NULL);
        for (nl_time_us_t tb = 855000; tb <= 1650000; tb += 5000) {
            nl_host_poll(&b, tb);
        }
        deliver(&fb, &host, t0 + 1000000);
        CHECK(!host.reply_pending);
    }
    CHECK(hi - lo >= 10000);
}

int main(void)
{
    RUN(test_init_args);
    RUN(test_register);
    RUN(test_effective_plan_and_configure);
    RUN(test_send_rules);
    RUN(test_mgmt_flag_and_lead);
    RUN(test_meta_rate_limit);
    RUN(test_announcements_build_peer_view);
    RUN(test_claim_announcement_truncated);
    RUN(test_dispatch);
    RUN(test_pull_bounds);
    RUN(test_meta_dispatch);
    RUN(test_remote_type_check);
    RUN(test_segmented);
    RUN(test_status_reset_and_congestion);
    RUN(test_meta_debug_truncates);
    RUN(test_announce_boot_spread);
    RUN(test_announce_ramp);
    RUN(test_announce_reply_to_newcomer);
    return nl_test_finish();
}
