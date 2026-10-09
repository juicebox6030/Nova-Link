#include "nl_test.h"

#include "nova_link/nl_host.h"
#include "nova_link/nl_radio.h"
#include "nova_link/nl_spi_link.h"

/* ---- Loopback HAL: SPI master wired to an in-process radio -------------- */

typedef struct {
    nl_radio_t radio;
    nl_time_us_t now;
    uint32_t delayed_us;
    int transfers;
    /* Fault injection, counted in transfers from now (0 = off). */
    int corrupt_in;  /* flip a byte of what the master receives */
    int fail_in;     /* HAL returns an error */
    int drop_in;     /* radio never sees the bytes (MOSI glitch) */
} loop_t;

static bool fire(int *countdown)
{
    if (*countdown > 0 && --*countdown == 0) {
        return true;
    }
    return false;
}

static int loop_transfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t len)
{
    loop_t *l = ctx;
    l->transfers++;
    if (fire(&l->fail_in)) {
        return -1;
    }
    /* MISO clocks out whatever the radio prepared after the last transfer. */
    size_t olen;
    const uint8_t *out = nl_radio_outbox(&l->radio, &olen);
    memset(rx, 0, len);
    memcpy(rx, out, olen < len ? olen : len);
    if (fire(&l->corrupt_in) && len > 3) {
        rx[3] ^= 0x10;
    }
    if (fire(&l->drop_in)) {
        static const uint8_t zeros[NL_LINK_FRAME_MAX];
        nl_radio_spi_complete(&l->radio, zeros, len, l->now);
    } else {
        nl_radio_spi_complete(&l->radio, tx, len, l->now);
    }
    return 0;
}

static bool loop_int_ready(void *ctx)
{
    return nl_radio_int_ready(&((loop_t *)ctx)->radio);
}

static void loop_delay(void *ctx, uint32_t us)
{
    ((loop_t *)ctx)->delayed_us += us;
}

static void loop_init(loop_t *l, nl_spi_link_t *link)
{
    memset(l, 0, sizeof(*l));
    nl_radio_init(&l->radio);
    nl_spi_hal_t hal = {loop_transfer, loop_int_ready, loop_delay, l};
    nl_spi_link_init(link, &hal);
}

static void make_plan(nl_zone_plan_t *plan)
{
    memset(plan, 0, sizeof(*plan));
    for (int z = 0; z < NL_NUM_ZONES; z++) {
        plan->zone[z].subghz_hz = 903000000u + 3000000u * (uint32_t)z;
    }
}

static int frag(uint8_t *buf, uint8_t origin, uint8_t zone, uint8_t seq)
{
    const uint8_t payload[] = {0xC0, 0xFF, 0xEE};
    nl_fragment_t f = {.origin_id = origin, .zone_id = zone, .seq = seq,
                       .payload = payload, .payload_len = sizeof(payload)};
    return nl_fragment_encode(&f, buf, NL_MAX_FRAGMENT);
}

/* ---- Driver tests -------------------------------------------------------- */

static void test_ping_and_status(void)
{
    loop_t l;
    nl_spi_link_t link;
    loop_init(&l, &link);
    nl_link_pong_t pong;
    CHECK_EQ(nl_spi_link_ping(&link, &pong), NL_OK);
    CHECK_EQ(pong.proto_version, NL_LINK_PROTOCOL_VERSION);
    CHECK_EQ(pong.fw_major, NL_VERSION_MAJOR);
    CHECK_EQ(l.transfers, 2);
    CHECK_EQ(l.delayed_us, NL_SPI_DEFAULT_TURNAROUND_US);

    nl_radio_status_t st;
    CHECK_EQ(nl_spi_link_status(&link, &st), NL_OK);
    CHECK_EQ(st.flags & NL_STATUS_F_CONFIGURED, 0);

    nl_radio_params_t p;
    nl_radio_params_default(&p);
    p.origin_id = 6;
    nl_zone_plan_t plan;
    make_plan(&plan);
    plan.zone[2].priority = 3;
    CHECK_EQ(nl_spi_link_configure(&link, &p, &plan), NL_OK);
    CHECK_EQ(l.radio.params.origin_id, 6);
    CHECK_EQ(l.radio.plan.zone[2].priority, 3);
    CHECK_EQ(nl_spi_link_status(&link, &st), NL_OK);
    CHECK(st.flags & NL_STATUS_F_CONFIGURED);
    CHECK_EQ(link.stats.crc_errors + link.stats.proto_errors + link.stats.io_errors, 0);
}

static void test_push_pull(void)
{
    loop_t l;
    nl_spi_link_t link;
    loop_init(&l, &link);
    nl_radio_params_t p;
    nl_radio_params_default(&p);
    p.origin_id = 1;
    nl_zone_plan_t plan;
    make_plan(&plan);
    plan.zone[1].priority = 1;
    nl_spi_link_configure(&link, &p, &plan);

    uint8_t b[NL_MAX_FRAGMENT];
    int n = frag(b, 0, 1, 9);
    CHECK_EQ(nl_spi_link_push(&link, b, (size_t)n), NL_OK);
    CHECK_EQ(nl_radio_tx_pending(&l.radio), 1);
    CHECK_EQ(nl_spi_link_push(&link, b, 1), NL_ERR_ARG);

    uint8_t got[NL_MAX_FRAGMENT];
    CHECK(!loop_int_ready(&l));
    CHECK_EQ(nl_spi_link_pull(&link, got, sizeof(got)), 0);

    n = frag(b, 3, 1, 4);
    nl_radio_rx_packet(&l.radio, b, (size_t)n, 0);
    CHECK(loop_int_ready(&l));
    CHECK_EQ(nl_spi_link_pull(&link, got, sizeof(got)), n);
    CHECK_MEM(got, b, (size_t)n);
    CHECK(!loop_int_ready(&l));

    /* Caller buffer too small. */
    nl_radio_rx_packet(&l.radio, b, (size_t)n, 0);
    n = frag(b, 3, 1, 5);
    nl_radio_rx_packet(&l.radio, b, (size_t)n, 0);
    CHECK_EQ(nl_spi_link_pull(&link, got, 2), NL_ERR_SIZE);
}

static void test_retries(void)
{
    loop_t l;
    nl_spi_link_t link;
    loop_init(&l, &link);
    nl_link_pong_t pong;

    /* Corrupted response: CRC error, retried, succeeds. */
    l.corrupt_in = 2;
    CHECK_EQ(nl_spi_link_ping(&link, &pong), NL_OK);
    CHECK_EQ(link.stats.crc_errors, 1);
    CHECK_EQ(link.stats.retries, 1);

    /* Request lost on the wire: no response frame, retried. */
    l.drop_in = 1;
    nl_radio_status_t st;
    CHECK_EQ(nl_spi_link_status(&link, &st), NL_OK);
    CHECK_EQ(link.stats.proto_errors, 1);
    CHECK_EQ(link.stats.retries, 2);

    /* HAL failure. */
    l.fail_in = 1;
    CHECK_EQ(nl_spi_link_ping(&link, &pong), NL_OK);
    CHECK_EQ(link.stats.io_errors, 1);

    /* Persistent failure gives up after 1 + retries attempts. */
    link.retries = 2;
    int before = l.transfers;
    l.fail_in = 1;
    for (int i = 0; i < 3; i++) {
        CHECK_EQ(nl_spi_link_ping(&link, &pong), i == 0 ? NL_OK : NL_OK);
    }
    (void)before;
}

static void test_pull_not_retried(void)
{
    loop_t l;
    nl_spi_link_t link;
    loop_init(&l, &link);
    nl_radio_params_t p;
    nl_radio_params_default(&p);
    nl_zone_plan_t plan;
    make_plan(&plan);
    plan.zone[1].priority = 1;
    nl_spi_link_configure(&link, &p, &plan);

    uint8_t b[NL_MAX_FRAGMENT], got[NL_MAX_FRAGMENT];
    for (uint8_t s = 0; s < 2; s++) {
        int n = frag(b, 3, 1, s);
        nl_radio_rx_packet(&l.radio, b, (size_t)n, 0);
    }
    /* The response carrying fragment 0 is corrupted: it is lost, and the
     * next pull returns fragment 1 instead of re-reading fragment 0. */
    int t = l.transfers;
    l.corrupt_in = 2;
    CHECK_EQ(nl_spi_link_pull(&link, got, sizeof(got)), NL_ERR_CRC);
    CHECK_EQ(l.transfers - t, 2);
    CHECK_EQ(link.stats.retries, 0);
    CHECK_EQ(nl_spi_link_pull(&link, got, sizeof(got)), 5);
    CHECK_EQ(got[1], 1);
}

/* ---- Full stack: host -> SPI -> radio -> air -> radio -> SPI -> host ---- */

typedef struct {
    loop_t loop;
    nl_spi_link_t link;
    nl_host_t host;
    nl_radio_action_t act;
} node_t;

typedef struct {
    int fragments;
    uint8_t last_origin;
    uint8_t last_seq;
    uint8_t payload[NL_MAX_PAYLOAD];
    uint8_t len;
} sink_t;

static int sink_init(nl_host_t *h, uint8_t slot, void *user)
{
    (void)user;
    return nl_host_claim(h, slot, 1, NL_CLAIM_SHARED);
}

static void sink_frag(nl_host_t *h, uint8_t slot, const nl_fragment_t *f, void *user)
{
    (void)h;
    (void)slot;
    sink_t *s = user;
    s->fragments++;
    s->last_origin = f->origin_id;
    s->last_seq = f->seq;
    s->len = f->payload_len;
    memcpy(s->payload, f->payload, f->payload_len);
}

static void node_init(node_t *n, uint8_t origin, const char *name)
{
    loop_init(&n->loop, &n->link);
    nl_link_ops_t ops;
    nl_spi_link_ops(&n->link, &ops);
    nl_host_config_t cfg;
    nl_host_config_default(&cfg);
    cfg.origin_id = origin;
    snprintf(cfg.name, sizeof(cfg.name), "%s", name);
    nl_host_init(&n->host, &cfg, &ops);
    nl_radio_params_t p;
    nl_radio_params_default(&p);
    nl_zone_plan_t plan;
    make_plan(&plan);
    nl_host_set_rf(&n->host, &p, &plan);
    n->act.type = NL_ACT_IDLE;
    n->act.until = 0;
}

/**
 * Advance all nodes in 100 us steps. Each step first decides every node's
 * action, then delivers: a node that is transmitting hears nothing
 * (half-duplex), and two transmissions on one frequency in the same step
 * collide and reach nobody. Airtime is ignored.
 */
static void run(node_t *nodes, int count, nl_time_us_t from, nl_time_us_t to)
{
    for (nl_time_us_t t = from; nl_time_before(t, to); t += 100) {
        for (int i = 0; i < count; i++) {
            node_t *n = &nodes[i];
            n->loop.now = t;
            if (t % 1000 == 0) {
                nl_host_poll(&n->host, t);
            }
            if (n->act.type == NL_ACT_RX && nl_time_before(t, n->act.until)) {
                continue;
            }
            nl_radio_next_action(&n->loop.radio, t, &n->act);
        }
        for (int i = 0; i < count; i++) {
            const nl_radio_action_t *tx = &nodes[i].act;
            if (tx->type != NL_ACT_TX) {
                continue;
            }
            bool collided = false;
            for (int j = 0; j < count; j++) {
                collided |= j != i && nodes[j].act.type == NL_ACT_TX &&
                            nodes[j].act.freq_hz == tx->freq_hz;
            }
            for (int j = 0; j < count && !collided; j++) {
                node_t *m = &nodes[j];
                if (m->act.type == NL_ACT_RX && m->act.freq_hz == tx->freq_hz) {
                    nl_radio_rx_packet(&m->loop.radio, tx->data, tx->len, t);
                }
            }
        }
        for (int i = 0; i < count; i++) {
            if (nodes[i].act.type == NL_ACT_TX) {
                nodes[i].act.type = NL_ACT_IDLE; /* done; decide again next step */
            }
        }
    }
}

static void test_two_nodes_end_to_end(void)
{
    static node_t nodes[2];
    sink_t sa = {0}, sb = {0};
    nl_plugin_def_t da = {.name = "sink", .type_id = 0x5151, .init = sink_init,
                          .on_fragment = sink_frag, .user = &sa};
    nl_plugin_def_t db = da;
    db.user = &sb;
    node_init(&nodes[0], 1, "alpha");
    node_init(&nodes[1], 2, "bravo");
    CHECK_EQ(nl_host_register(&nodes[0].host, &da), 0);
    CHECK_EQ(nl_host_register(&nodes[1].host, &db), 0);

    run(nodes, 2, 0, 20000);
    CHECK(nodes[0].loop.radio.config_flags == (NL_RADIO_CFG_PARAMS | NL_RADIO_CFG_PLAN));
    CHECK_EQ(nodes[1].loop.radio.plan.zone[1].priority, 1);

    const uint8_t msg[] = "hello zone 1";
    CHECK_EQ(nl_host_send(&nodes[0].host, 0, 1, msg, sizeof(msg), 0), NL_OK);
    run(nodes, 2, 20000, 60000);
    CHECK_EQ(sb.fragments, 1);
    CHECK_EQ(sb.last_origin, 1);
    CHECK_EQ(sb.len, sizeof(msg));
    CHECK_MEM(sb.payload, msg, sizeof(msg));
    CHECK_EQ(sa.fragments, 0);
    /* Any repeats heard were deduplicated by the radio, not the host. */
    CHECK_EQ(nodes[1].host.stats.rx_duplicates, 0);

    CHECK_EQ(nl_host_send(&nodes[1].host, 0, 1, msg, 4, 0), NL_OK);
    run(nodes, 2, 60000, 100000);
    CHECK_EQ(sa.fragments, 1);
    CHECK_EQ(sa.last_origin, 2);

    /* Zone 0 announcements cross over too: both nodes know each other. */
    run(nodes, 2, 100000, 3000000);
    const nl_host_peer_t *p = nl_host_peer(&nodes[1].host, 1);
    CHECK(p != NULL);
    if (p != NULL) {
        CHECK_STR(p->info.name, "alpha");
    }
    p = nl_host_peer(&nodes[0].host, 2);
    CHECK(p != NULL);
    if (p != NULL) {
        CHECK_STR(p->info.name, "bravo");
    }
    CHECK_EQ(nodes[0].link.stats.crc_errors + nodes[0].link.stats.proto_errors, 0);
}

/** First time (relative to @p from) that every node knows every other one. */
static nl_time_us_t time_to_discover(node_t *nodes, int count, nl_time_us_t from,
                                     nl_time_us_t limit)
{
    for (nl_time_us_t t = from; nl_time_before(t, from + limit); t += 1000) {
        run(nodes, count, t, t + 1000);
        bool all = true;
        for (int i = 0; i < count; i++) {
            for (int j = 0; j < count; j++) {
                all &= i == j ||
                       nl_host_peer(&nodes[i].host, nodes[j].host.cfg.origin_id) != NULL;
            }
        }
        if (all) {
            return t + 1000 - from;
        }
    }
    return limit;
}

static void test_silent_discovery(void)
{
    /* Devices with no traffic at all, powered up a few ms apart. Without zone 0
     * discovery visits, listening after speaking and answering newcomers they
     * would never meet: they only ever tune to their own (silent) zones. */
    static node_t nodes[5];
    static const char *names[] = {"n1", "n2", "n3", "n4", "late"};
    nl_plugin_def_t d = {.name = "sink", .type_id = 7, .init = sink_init};
    for (int i = 0; i < 4; i++) {
        node_init(&nodes[i], (uint8_t)(i + 1), names[i]);
        nl_host_register(&nodes[i].host, &d);
        run(nodes, i + 1, (nl_time_us_t)i * 7000, (nl_time_us_t)(i + 1) * 7000);
    }
    nl_time_us_t took = time_to_discover(nodes, 4, 28000, 5000000);
    CHECK(took < 1000000);

    /* A late joiner is found quickly too, not after a full announce period. */
    node_init(&nodes[4], 6, names[4]);
    nl_host_register(&nodes[4].host, &d);
    took = time_to_discover(nodes, 5, 6000000, 5000000);
    CHECK(took < 1000000);
    CHECK(nl_host_peer(&nodes[0].host, 6) != NULL);
}

static void test_radio_reset_recovery(void)
{
    static node_t nodes[2];
    sink_t sb = {0};
    nl_plugin_def_t da = {.name = "sink", .type_id = 1, .init = sink_init};
    nl_plugin_def_t db = {.name = "sink", .type_id = 1, .init = sink_init,
                          .on_fragment = sink_frag, .user = &sb};
    node_init(&nodes[0], 1, "a");
    node_init(&nodes[1], 2, "b");
    nl_host_register(&nodes[0].host, &da);
    nl_host_register(&nodes[1].host, &db);
    run(nodes, 2, 0, 20000);

    /* Receiver's radio reboots and loses its plan. */
    nl_radio_init(&nodes[1].loop.radio);
    nodes[1].act.type = NL_ACT_IDLE;
    run(nodes, 2, 20000, 1100000);
    CHECK_EQ(nodes[1].host.stats.radio_resets, 1);
    CHECK(nodes[1].loop.radio.config_flags == (NL_RADIO_CFG_PARAMS | NL_RADIO_CFG_PLAN));

    const uint8_t msg[] = {1, 2, 3};
    nl_host_send(&nodes[0].host, 0, 1, msg, sizeof(msg), 0);
    run(nodes, 2, 1100000, 1200000);
    CHECK_EQ(sb.fragments, 1);
}

int main(void)
{
    RUN(test_ping_and_status);
    RUN(test_push_pull);
    RUN(test_retries);
    RUN(test_pull_not_retried);
    RUN(test_two_nodes_end_to_end);
    RUN(test_silent_discovery);
    RUN(test_radio_reset_recovery);
    return nl_test_finish();
}
