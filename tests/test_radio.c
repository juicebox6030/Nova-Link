#include "nl_test.h"

#include "nova_link/nl_fragment.h"
#include "nova_link/nl_radio.h"

#define DWELL 2000u
#define SUB(z) (903000000u + 3000000u * (uint32_t)(z))
#define G24(z) (2405000000u + 10000000u * (uint32_t)(z))

static void make_plan(nl_zone_plan_t *plan, const uint8_t prio[NL_NUM_ZONES])
{
    for (int z = 0; z < NL_NUM_ZONES; z++) {
        plan->zone[z].priority = prio[z];
        plan->zone[z].subghz_hz = SUB(z);
        plan->zone[z].ghz24_hz = G24(z);
    }
}

/** Radio with origin 1, default params and the given priorities. */
static void setup(nl_radio_t *r, nl_radio_params_t *p, const uint8_t prio[NL_NUM_ZONES])
{
    nl_radio_init(r);
    nl_radio_params_default(p);
    p->origin_id = 1;
    p->repeat_jitter_us = 0;      /* exact timing; jitter has its own test */
    p->discovery_interval_us = 0; /* likewise discovery visits */
    nl_zone_plan_t plan;
    make_plan(&plan, prio);
    nl_radio_configure(r, p, &plan);
}

static int frag(uint8_t *buf, uint8_t origin, uint8_t zone, uint8_t flags, uint8_t seq)
{
    const uint8_t payload[] = {0x11, 0x22, 0x33};
    nl_fragment_t f = {.origin_id = origin, .zone_id = zone, .flags = flags, .seq = seq,
                       .payload = payload, .payload_len = sizeof(payload)};
    return nl_fragment_encode(&f, buf, NL_MAX_FRAGMENT);
}

static void queue(nl_radio_t *r, uint8_t zone, uint8_t seq, nl_time_us_t now)
{
    uint8_t b[NL_MAX_FRAGMENT];
    int n = frag(b, 0, zone, 0, seq);
    CHECK_EQ(nl_radio_queue_tx(r, b, (size_t)n, now), NL_OK);
}

static void rx(nl_radio_t *r, uint8_t origin, uint8_t zone, uint8_t flags, uint8_t seq,
               nl_time_us_t now)
{
    uint8_t b[NL_MAX_FRAGMENT];
    int n = frag(b, origin, zone, flags, seq);
    nl_radio_rx_packet(r, b, (size_t)n, now);
}

/** Zone of the RX slot at @p now (-1 if the action is not RX). */
static int slot_zone(nl_radio_t *r, nl_time_us_t now)
{
    nl_radio_action_t a;
    nl_radio_next_action(r, now, &a);
    return a.type == NL_ACT_RX ? a.zone : -1;
}

static void test_idle_before_plan(void)
{
    nl_radio_t r;
    nl_radio_init(&r);
    nl_radio_action_t a;
    nl_radio_next_action(&r, 100, &a);
    CHECK_EQ(a.type, NL_ACT_IDLE);
    CHECK_EQ(a.until, 100 + DWELL);
    /* Queued TX is held until a plan arrives. */
    queue(&r, 1, 0, 100);
    nl_radio_next_action(&r, 100, &a);
    CHECK_EQ(a.type, NL_ACT_IDLE);
    nl_radio_status_t st;
    nl_radio_get_status(&r, &st);
    CHECK_EQ(st.flags & NL_STATUS_F_CONFIGURED, 0);
    CHECK_EQ(st.tx_queue_len, 1);
}

static void test_swrr_ratio(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 3, 1, 0, 2, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    int count[NL_NUM_ZONES] = {0};
    /* Start just before the 32-bit time wrap. */
    nl_time_us_t now = 0xFFFFF000u;
    for (int i = 0; i < 600; i++, now += DWELL) {
        int z = slot_zone(&r, now);
        CHECK(z >= 0);
        if (z >= 0) {
            count[z]++;
        }
    }
    CHECK_EQ(count[1], 300);
    CHECK_EQ(count[2], 100);
    CHECK_EQ(count[4], 200);
    CHECK_EQ(count[0] + count[3] + count[5] + count[6] + count[7], 0);
}

static void test_slot_held_until_dwell_ends(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 1, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    nl_radio_action_t a;
    nl_radio_next_action(&r, 0, &a);
    CHECK_EQ(a.type, NL_ACT_RX);
    CHECK_EQ(a.zone, 1);
    CHECK_EQ(a.freq_hz, SUB(1));
    CHECK_EQ(a.band, NL_BAND_SUBGHZ);
    CHECK_EQ(a.until, DWELL);
    CHECK_EQ(slot_zone(&r, DWELL - 1), 1);
    CHECK_EQ(slot_zone(&r, DWELL), 2);
    CHECK_EQ(slot_zone(&r, 2 * DWELL), 1);
}

static void test_priority_cap(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 200, 8, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    int c1 = 0, c2 = 0;
    for (nl_time_us_t now = 0; now < 160 * DWELL; now += DWELL) {
        int z = slot_zone(&r, now);
        c1 += z == 1;
        c2 += z == 2;
    }
    CHECK_EQ(c1, 80);
    CHECK_EQ(c2, 80);
}

static void test_park_on_zone0(void)
{
    const uint8_t none[NL_NUM_ZONES] = {0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, none);
    nl_radio_action_t a;
    nl_radio_next_action(&r, 0, &a);
    CHECK_EQ(a.type, NL_ACT_RX);
    CHECK_EQ(a.zone, 0);
    CHECK_EQ(a.freq_hz, SUB(0));

    /* No frequency for zone 0 either: nothing to do. */
    nl_zone_plan_t plan;
    make_plan(&plan, none);
    plan.zone[0].subghz_hz = 0;
    nl_radio_configure(&r, NULL, &plan);
    nl_radio_next_action(&r, 10, &a);
    CHECK_EQ(a.type, NL_ACT_IDLE);
    CHECK_EQ(a.until, 10 + DWELL);
}

static void test_zone_without_frequency_skipped(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 5, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    nl_radio_init(&r);
    nl_radio_params_default(&p);
    p.origin_id = 1;
    nl_zone_plan_t plan;
    make_plan(&plan, prio);
    plan.zone[3].subghz_hz = 0; /* 2.4 GHz only, but we run sub-GHz */
    p.discovery_interval_us = 0;
    nl_radio_configure(&r, &p, &plan);
    for (nl_time_us_t now = 0; now < 20 * DWELL; now += DWELL) {
        CHECK_EQ(slot_zone(&r, now), 1);
    }
}

static void test_mgmt_listen_adds_zone0(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    nl_time_us_t now = 0;
    for (int i = 0; i < 10; i++, now += DWELL) {
        CHECK_EQ(slot_zone(&r, now), 1);
    }
    /* A peer on zone 1 signals that metadata is coming on zone 0. */
    rx(&r, 2, 1, NL_FLAG_MGMT_LISTEN, 0, now - 1);
    int z0 = 0;
    nl_time_us_t until = now - 1 + p.mgmt_hold_us;
    for (; nl_time_before(now, until); now += DWELL) {
        z0 += slot_zone(&r, now) == 0;
    }
    int slots = (int)(p.mgmt_hold_us / DWELL);
    CHECK(z0 >= slots / 2 - 1 && z0 <= slots / 2 + 1);
    for (int i = 0; i < 10; i++, now += DWELL) {
        CHECK_EQ(slot_zone(&r, now), 1);
    }
}

static void test_zone0_priority_listens_always(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {1, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    int z0 = 0;
    for (nl_time_us_t now = 0; now < 10 * DWELL; now += DWELL) {
        z0 += slot_zone(&r, now) == 0;
    }
    CHECK_EQ(z0, 5);
}

static void test_repeats_and_interval(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    queue(&r, 2, 77, 0);
    nl_radio_action_t a;
    for (int k = 0; k < 3; k++) {
        nl_time_us_t t = (nl_time_us_t)k * p.repeat_interval_us;
        nl_radio_next_action(&r, t, &a);
        CHECK_EQ(a.type, NL_ACT_TX);
        CHECK_EQ(a.zone, 2);
        CHECK_EQ(a.freq_hz, SUB(2));
        CHECK_EQ(a.len, 5);
        CHECK_EQ(a.data[0], nl_fragment_make_header(1, 2, 0)); /* origin re-stamped */
        CHECK_EQ(a.data[1], 77);
        nl_radio_next_action(&r, t, &a);
        if (k < 2) {
            /* Listen until the next repeat is due, not the whole slot. */
            CHECK_EQ(a.type, NL_ACT_RX);
            nl_time_us_t due = t + p.repeat_interval_us;
            CHECK(a.until == due || a.until == ((t / DWELL) + 1) * DWELL);
            CHECK(!nl_time_before(due, a.until));
        }
    }
    CHECK_EQ(a.type, NL_ACT_RX);
    CHECK_EQ(nl_radio_tx_pending(&r), 0);
    CHECK_EQ(r.stats.tx_sent, 3);
}

/** Gaps between the repeats of one fragment, stepping time in 10 us. */
static void repeat_gaps(uint8_t origin, uint32_t jitter, nl_time_us_t gaps[2])
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    p.origin_id = origin;
    p.repeat_jitter_us = jitter;
    nl_radio_configure(&r, &p, NULL);
    queue(&r, 1, 0, 0);
    nl_time_us_t last = 0;
    int sent = 0;
    for (nl_time_us_t t = 0; t < 10000 && sent < 3; t += 10) {
        nl_radio_action_t a;
        nl_radio_next_action(&r, t, &a);
        if (a.type == NL_ACT_TX) {
            if (sent > 0) {
                gaps[sent - 1] = t - last;
            }
            last = t;
            sent++;
        }
    }
    CHECK_EQ(sent, 3);
}

static void test_repeat_jitter(void)
{
    nl_radio_params_t d;
    nl_radio_params_default(&d);
    CHECK(d.repeat_jitter_us > 0);

    /* Gaps stay within [interval, interval + jitter]. */
    int distinct = 0;
    for (uint8_t o = 0; o < NL_NUM_ORIGINS; o++) {
        nl_time_us_t g[2];
        repeat_gaps(o, 1000, g);
        for (int i = 0; i < 2; i++) {
            CHECK(g[i] >= d.repeat_interval_us);
            CHECK(g[i] <= d.repeat_interval_us + 1000 + 10);
        }
        nl_time_us_t ref[2];
        repeat_gaps(0, 1000, ref);
        distinct += g[0] != ref[0] || g[1] != ref[1];
    }
    /* Different originIDs give different sequences (devices desynchronise). */
    CHECK(distinct >= NL_NUM_ORIGINS - 2);

    /* Jitter 0 is exact. */
    nl_time_us_t g[2];
    repeat_gaps(3, 0, g);
    CHECK_EQ(g[0], d.repeat_interval_us);
    CHECK_EQ(g[1], d.repeat_interval_us);

    /* Hardware entropy changes the sequence. */
    nl_radio_t a, b;
    nl_radio_init(&a);
    nl_radio_init(&b);
    nl_radio_seed(&b, 0x12345678u);
    CHECK(a.rng != b.rng);
}

static void test_discovery_visits(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 3, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    p.discovery_interval_us = 10 * DWELL;
    nl_radio_configure(&r, &p, NULL);
    int z0 = 0;
    nl_time_us_t last = 0;
    for (nl_time_us_t now = 0; now < 200 * DWELL; now += DWELL) {
        if (slot_zone(&r, now) == 0) {
            CHECK(z0 == 0 || now - last <= 10 * DWELL);
            last = now;
            z0++;
        }
    }
    CHECK(z0 >= 19 && z0 <= 21);

    /* The visits survive the clock wrapping. */
    setup(&r, &p, prio);
    p.discovery_interval_us = 10 * DWELL;
    nl_radio_configure(&r, &p, NULL);
    z0 = 0;
    for (nl_time_us_t now = 0x7FFFF000u; now != 0x7FFFF000u + 100 * DWELL; now += DWELL) {
        z0 += slot_zone(&r, now) == 0;
    }
    CHECK(z0 >= 9);
}

static void test_listen_after_zone0_tx(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    p.tx_repeats = 1;
    p.mgmt_repeats = 0; /* zone 0 follows tx_repeats */
    nl_radio_configure(&r, &p, NULL);
    queue(&r, 0, 1, 0);
    nl_radio_action_t a;
    nl_time_us_t now = 0;
    do {
        nl_radio_next_action(&r, now, &a);
        now += 100;
    } while (a.type != NL_ACT_TX);
    CHECK_EQ(a.zone, 0);
    /* Zone 0 now shares the rotation (weight 1 vs 1) until mgmt_hold ends. */
    int z0 = 0;
    for (nl_time_us_t t = 10 * DWELL; t < 20 * DWELL; t += DWELL) {
        z0 += slot_zone(&r, t) == 0;
    }
    CHECK_EQ(z0, 5);
    z0 = 0;
    for (nl_time_us_t t = p.mgmt_hold_us + 10 * DWELL; t < p.mgmt_hold_us + 20 * DWELL;
         t += DWELL) {
        z0 += slot_zone(&r, t) == 0;
    }
    CHECK_EQ(z0, 0);
}

static void test_multiple_fragments_interleave(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    p.tx_repeats = 2;
    nl_radio_configure(&r, &p, NULL);
    queue(&r, 1, 10, 0);
    queue(&r, 1, 11, 0);
    nl_radio_action_t a;
    const uint8_t expect[] = {10, 11, 10, 11};
    const nl_time_us_t at[] = {0, 0, 1500, 1500};
    for (int i = 0; i < 4; i++) {
        nl_radio_next_action(&r, at[i], &a);
        CHECK_EQ(a.type, NL_ACT_TX);
        CHECK_EQ(a.data[1], expect[i]);
    }
    nl_radio_next_action(&r, 1500, &a);
    CHECK_EQ(a.type, NL_ACT_RX);
}

static void test_immediate_zone_fairness(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    p.tx_repeats = 1;
    nl_radio_configure(&r, &p, NULL);
    queue(&r, 0, 0, 0);
    queue(&r, 1, 1, 0);
    queue(&r, 1, 2, 0);
    queue(&r, 3, 3, 0);
    queue(&r, 3, 4, 0);
    queue(&r, 7, 5, 0);
    const uint8_t order[] = {1, 3, 7, 1, 3, 0};
    nl_radio_action_t a;
    for (size_t i = 0; i < sizeof(order); i++) {
        nl_radio_next_action(&r, 0, &a);
        CHECK_EQ(a.type, NL_ACT_TX);
        CHECK_EQ(a.zone, order[i]);
    }
}

static void test_tx_eviction(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    for (int i = 0; i < NL_RADIO_TXQ_DEPTH + 2; i++) {
        queue(&r, 2, (uint8_t)i, 0);
    }
    CHECK_EQ(r.stats.tx_dropped, 2);
    CHECK_EQ(nl_radio_tx_pending(&r), NL_RADIO_TXQ_DEPTH);
    nl_radio_action_t a;
    nl_radio_next_action(&r, 0, &a);
    CHECK_EQ(a.data[1], 2); /* oldest two were evicted */
}

static void test_dual_band(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    p.band = NL_BAND_DUAL;
    p.tx_repeats = 1;
    nl_radio_configure(&r, &p, NULL);

    /* RX alternates bands on successive visits to the same zone. */
    nl_radio_action_t a;
    for (int i = 0; i < 4; i++) {
        nl_radio_next_action(&r, (nl_time_us_t)i * DWELL, &a);
        CHECK_EQ(a.type, NL_ACT_RX);
        CHECK_EQ(a.band, (i % 2) ? NL_BAND_2G4 : NL_BAND_SUBGHZ);
        CHECK_EQ(a.freq_hz, (i % 2) ? G24(1) : SUB(1));
    }

    /* One queued fragment goes out on both bands back to back. */
    nl_time_us_t t = 4 * DWELL;
    queue(&r, 1, 9, t);
    nl_radio_next_action(&r, t, &a);
    CHECK_EQ(a.type, NL_ACT_TX);
    CHECK_EQ(a.freq_hz, SUB(1));
    nl_radio_next_action(&r, t, &a);
    CHECK_EQ(a.type, NL_ACT_TX);
    CHECK_EQ(a.freq_hz, G24(1));
    nl_radio_next_action(&r, t, &a);
    CHECK_EQ(a.type, NL_ACT_RX);
    CHECK_EQ(r.stats.tx_sent, 2);

    /* A zone with only one band sends once. */
    nl_zone_plan_t plan;
    make_plan(&plan, prio);
    plan.zone[4].subghz_hz = 0;
    nl_radio_configure(&r, NULL, &plan);
    queue(&r, 4, 10, t);
    nl_radio_next_action(&r, t, &a);
    CHECK_EQ(a.type, NL_ACT_TX);
    CHECK_EQ(a.freq_hz, G24(4));
    nl_radio_next_action(&r, t, &a);
    CHECK_EQ(a.type, NL_ACT_RX);
}

static void test_in_slot_policy(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 1, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    p.tx_policy = NL_TX_IN_SLOT;
    p.tx_repeats = 1;
    nl_radio_configure(&r, &p, NULL);
    queue(&r, 2, 1, 0);
    nl_radio_action_t a;
    nl_radio_next_action(&r, 0, &a);
    CHECK_EQ(a.type, NL_ACT_RX); /* slot belongs to zone 1 */
    CHECK_EQ(a.zone, 1);
    nl_radio_next_action(&r, DWELL, &a);
    CHECK_EQ(a.type, NL_ACT_TX);
    CHECK_EQ(a.zone, 2);

    /* A priority-0 zone with queued TX joins the rotation to send it. */
    queue(&r, 5, 2, 2 * DWELL);
    bool sent = false;
    for (nl_time_us_t t = 2 * DWELL; t < 8 * DWELL && !sent; t += DWELL) {
        nl_radio_next_action(&r, t, &a);
        sent = a.type == NL_ACT_TX && a.zone == 5;
    }
    CHECK(sent);
    for (nl_time_us_t t = 8 * DWELL; t < 20 * DWELL; t += DWELL) {
        CHECK(slot_zone(&r, t) != 5);
    }
}

static void test_rx_filters(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    CHECK(!nl_radio_int_ready(&r));
    rx(&r, 1, 1, 0, 0, 0); /* own origin */
    rx(&r, 2, 3, 0, 0, 0); /* zone we are not subscribed to */
    uint8_t b[NL_MAX_FRAGMENT + 1] = {0};
    nl_radio_rx_packet(&r, b, 1, 0);
    nl_radio_rx_packet(&r, b, NL_MAX_FRAGMENT + 1, 0);
    CHECK_EQ(r.stats.rx_ignored, 4);
    CHECK(!nl_radio_int_ready(&r));

    rx(&r, 2, 1, 0, 5, 0);
    rx(&r, 2, 1, 0, 5, 10); /* repeat of the same fragment */
    rx(&r, 3, 0, 0, 0, 20); /* zone 0 is always accepted */
    CHECK_EQ(r.stats.rx_ok, 2);
    CHECK_EQ(r.stats.rx_dup, 1);
    CHECK(nl_radio_int_ready(&r));
}

static void test_burst_extends_slot(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 1, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    CHECK_EQ(slot_zone(&r, 0), 1);
    rx(&r, 2, 2, NL_FLAG_BURST, 0, 1000); /* other zone: no effect */
    rx(&r, 2, 1, NL_FLAG_BURST, 0, 1500);
    nl_radio_action_t a;
    nl_radio_next_action(&r, DWELL, &a);
    CHECK_EQ(a.zone, 1);
    CHECK_EQ(a.until, 1500 + p.burst_extend_us);
    CHECK_EQ(slot_zone(&r, 1500 + p.burst_extend_us), 2);
}

/* ---- SPI command handling --------------------------------------------- */

/** Run one transaction carrying @p cmd, then a read; return the response. */
static int spi_cmd(nl_radio_t *r, uint8_t cmd, const uint8_t *data, size_t len,
                   nl_link_frame_t *rsp)
{
    uint8_t buf[NL_LINK_FRAME_MAX + 8];
    memset(buf, 0, sizeof(buf));
    int n = nl_link_encode(cmd, data, len, buf, sizeof(buf));
    nl_radio_spi_complete(r, buf, (size_t)n + 4, 0);
    size_t olen;
    const uint8_t *out = nl_radio_outbox(r, &olen);
    if (olen == 0) {
        return NL_ERR_EMPTY;
    }
    return nl_link_decode(out, olen, rsp, NULL);
}

static void test_spi_ping_status(void)
{
    nl_radio_t r;
    nl_radio_init(&r);
    nl_link_frame_t f;
    CHECK_EQ(spi_cmd(&r, NL_CMD_PING, NULL, 0, &f), NL_OK);
    CHECK_EQ(f.cmd, NL_RSP_PONG);
    nl_link_pong_t pong;
    CHECK_EQ(nl_link_pong_decode(f.data, f.len, &pong), NL_OK);
    CHECK_EQ(pong.proto_version, NL_LINK_PROTOCOL_VERSION);
    CHECK_EQ(pong.fw_minor, NL_VERSION_MINOR);

    CHECK_EQ(spi_cmd(&r, NL_CMD_STATUS, NULL, 0, &f), NL_OK);
    CHECK_EQ(f.cmd, NL_RSP_STATUS);
    nl_radio_status_t st;
    CHECK_EQ(nl_radio_status_decode(f.data, f.len, &st), NL_OK);
    CHECK_EQ(st.flags & NL_STATUS_F_CONFIGURED, 0);

    /* Both configs in a single transaction, back to back. */
    nl_radio_params_t p;
    nl_radio_params_default(&p);
    p.origin_id = 4;
    nl_zone_plan_t plan;
    const uint8_t prio[NL_NUM_ZONES] = {0, 2, 0, 0, 0, 0, 0, 0};
    make_plan(&plan, prio);
    uint8_t pb[NL_RADIO_PARAMS_WIRE_SIZE], zb[NL_ZONE_PLAN_WIRE_SIZE];
    nl_radio_params_encode(&p, pb, sizeof(pb));
    nl_zone_plan_encode(&plan, zb, sizeof(zb));
    uint8_t tx[2 * NL_LINK_FRAME_MAX];
    size_t pos = (size_t)nl_link_encode(NL_CMD_RADIO_CONFIG, pb, sizeof(pb), tx, sizeof(tx));
    pos += (size_t)nl_link_encode(NL_CMD_ZONE_CONFIG, zb, sizeof(zb), &tx[pos],
                                  sizeof(tx) - pos);
    nl_radio_spi_complete(&r, tx, pos, 0);
    CHECK_EQ(r.params.origin_id, 4);
    CHECK_EQ(r.plan.zone[1].priority, 2);

    CHECK_EQ(spi_cmd(&r, NL_CMD_STATUS, NULL, 0, &f), NL_OK);
    nl_radio_status_decode(f.data, f.len, &st);
    CHECK(st.flags & NL_STATUS_F_CONFIGURED);
}

static void test_spi_push_pull(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    nl_link_frame_t f;
    CHECK_EQ(spi_cmd(&r, NL_CMD_PULL, NULL, 0, &f), NL_OK);
    CHECK_EQ(f.cmd, NL_RSP_FRAGMENT);
    CHECK_EQ(f.len, 0);

    uint8_t b[NL_MAX_FRAGMENT];
    int n = frag(b, 0, 3, NL_FLAG_BURST, 42);
    CHECK_EQ(spi_cmd(&r, NL_CMD_PUSH, b, (size_t)n, &f), NL_ERR_EMPTY);
    CHECK_EQ(nl_radio_tx_pending(&r), 1);
    CHECK_EQ(r.txq[3][0].data[0], nl_fragment_make_header(1, 3, NL_FLAG_BURST));

    nl_test_log_clear();
    CHECK_EQ(spi_cmd(&r, NL_CMD_PUSH, b, 1, &f), NL_ERR_EMPTY);
    CHECK(nl_test_log_contains(NL_LOG_WARN, "PUSH with bad fragment length"));

    /* RX overflow keeps the newest NL_RADIO_RXQ_DEPTH fragments, in order. */
    for (int i = 0; i < NL_RADIO_RXQ_DEPTH + 4; i++) {
        rx(&r, 2, 1, 0, (uint8_t)i, (nl_time_us_t)i);
    }
    CHECK_EQ(r.stats.rx_dropped, 4);
    for (int i = 4; i < NL_RADIO_RXQ_DEPTH + 4; i++) {
        CHECK_EQ(spi_cmd(&r, NL_CMD_PULL, NULL, 0, &f), NL_OK);
        CHECK_EQ(f.len, 5);
        CHECK_EQ(f.data[1], i);
    }
    CHECK(!nl_radio_int_ready(&r));
}

static void test_spi_rejects(void)
{
    nl_radio_t r;
    nl_radio_init(&r);
    nl_link_frame_t f;
    nl_test_log_clear();
    CHECK_EQ(spi_cmd(&r, 0x42, NULL, 0, &f), NL_ERR_EMPTY);
    CHECK(nl_test_log_contains(NL_LOG_WARN, "unknown link command 0x42"));

    nl_radio_params_t p;
    nl_radio_params_default(&p);
    p.tx_repeats = 0;
    uint8_t pb[NL_RADIO_PARAMS_WIRE_SIZE];
    nl_radio_params_encode(&p, pb, sizeof(pb));
    spi_cmd(&r, NL_CMD_RADIO_CONFIG, pb, sizeof(pb), &f);
    CHECK(nl_test_log_contains(NL_LOG_WARN, "rejected RADIO_CONFIG"));
    spi_cmd(&r, NL_CMD_ZONE_CONFIG, pb, sizeof(pb), &f);
    CHECK(nl_test_log_contains(NL_LOG_WARN, "rejected ZONE_CONFIG"));
    CHECK_EQ(r.config_flags, 0);

    /* Corrupted frame is reported and ignored. */
    uint8_t buf[16] = {0};
    int n = nl_link_encode(NL_CMD_PING, NULL, 0, buf, sizeof(buf));
    buf[n - 1] ^= 0xFF;
    nl_radio_spi_complete(&r, buf, sizeof(buf), 0);
    CHECK(nl_test_log_contains(NL_LOG_WARN, "CRC error"));
    size_t olen;
    nl_radio_outbox(&r, &olen);
    CHECK_EQ(olen, 0);
}

static void test_origin_restamp(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    uint8_t b[NL_MAX_FRAGMENT];
    int n = frag(b, 5, 2, NL_FLAG_MGMT_LISTEN, 0);
    nl_radio_queue_tx(&r, b, (size_t)n, 0);
    CHECK_EQ(r.txq[2][0].data[0], nl_fragment_make_header(1, 2, NL_FLAG_MGMT_LISTEN));
    p.origin_id = 3;
    nl_radio_configure(&r, &p, NULL);
    CHECK_EQ(r.txq[2][0].data[0], nl_fragment_make_header(3, 2, NL_FLAG_MGMT_LISTEN));
}

static void test_zero_repeats_sends_once(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    p.tx_repeats = 0; /* only reachable through nl_radio_configure */
    nl_radio_configure(&r, &p, NULL);
    queue(&r, 1, 0, 0);
    nl_radio_action_t a;
    nl_radio_next_action(&r, 0, &a);
    CHECK_EQ(a.type, NL_ACT_TX);
    CHECK_EQ(nl_radio_tx_pending(&r), 0);
}

/** Step time in 10 us from @p t until the next TX action; returns its time. */
static nl_time_us_t next_tx(nl_radio_t *r, nl_time_us_t t, nl_radio_action_t *a)
{
    for (nl_time_us_t end = t + 100000; t < end; t += 10) {
        nl_radio_next_action(r, t, a);
        if (a->type == NL_ACT_TX) {
            return t;
        }
    }
    CHECK(0); /* no TX within 100 ms */
    return t;
}

static void test_cca_flag(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    CHECK(p.cca_backoff_us != 0); /* on by default */
    queue(&r, 1, 0, 0);
    nl_radio_action_t a;
    nl_radio_next_action(&r, 0, &a);
    CHECK_EQ(a.type, NL_ACT_TX);
    CHECK(a.cca);

    p.cca_backoff_us = 0;
    nl_radio_configure(&r, &p, NULL);
    nl_radio_next_action(&r, p.repeat_interval_us, &a);
    CHECK_EQ(a.type, NL_ACT_TX);
    CHECK(!a.cca);
    CHECK_EQ(nl_radio_tx_busy(&r, p.repeat_interval_us), NL_OK); /* still allowed */
}

static void test_cca_busy_defers(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    CHECK_EQ(nl_radio_tx_busy(&r, 0), NL_ERR_EMPTY); /* nothing emitted */
    queue(&r, 1, 5, 0);
    nl_radio_action_t a;
    nl_radio_next_action(&r, 0, &a);
    CHECK_EQ(a.type, NL_ACT_TX);
    CHECK_EQ(nl_radio_tx_busy(&r, 0), NL_OK);
    CHECK_EQ(nl_radio_tx_busy(&r, 0), NL_ERR_EMPTY); /* only once */
    CHECK_EQ(r.stats.tx_sent, 0);
    CHECK_EQ(r.cca_busy, 1);
    CHECK_EQ(nl_radio_tx_pending(&r), 1);

    /* Retried after 1..cca_backoff_us, and still sent tx_repeats times. */
    nl_time_us_t t = next_tx(&r, 0, &a);
    CHECK(t >= 1 && t <= p.cca_backoff_us + 10);
    CHECK_EQ(a.data[1], 5);
    int sent = 1;
    while (nl_radio_tx_pending(&r) > 0) {
        t = next_tx(&r, t + 10, &a);
        sent++;
    }
    CHECK_EQ(sent, p.tx_repeats);
    CHECK_EQ(r.stats.tx_sent, p.tx_repeats);
}

static void test_cca_busy_last_repeat(void)
{
    /* The last transmission removes the fragment; a busy channel puts it back. */
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    p.tx_repeats = 1;
    nl_radio_configure(&r, &p, NULL);
    queue(&r, 1, 1, 0);
    queue(&r, 1, 2, 0);
    queue(&r, 1, 3, 0);
    nl_radio_action_t a;
    nl_radio_next_action(&r, 0, &a);
    CHECK_EQ(a.data[1], 1);
    CHECK_EQ(nl_radio_tx_pending(&r), 2);
    CHECK_EQ(nl_radio_tx_busy(&r, 0), NL_OK);
    CHECK_EQ(nl_radio_tx_pending(&r), 3);
    CHECK_EQ(r.txq[1][0].data[1], 1); /* back in its place */

    /* The others are not held up by the deferred one. */
    nl_radio_next_action(&r, 0, &a);
    CHECK_EQ(a.type, NL_ACT_TX);
    CHECK_EQ(a.data[1], 2);
    bool seen[4] = {false};
    seen[2] = true;
    nl_time_us_t t = 0;
    while (nl_radio_tx_pending(&r) > 0) {
        t = next_tx(&r, t + 10, &a);
        seen[a.data[1]] = true;
    }
    CHECK(seen[1] && seen[2] && seen[3]);
    CHECK_EQ(r.stats.tx_sent, 3);
}

static void test_cca_push_invalidates_undo(void)
{
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    queue(&r, 1, 1, 0);
    nl_radio_action_t a;
    nl_radio_next_action(&r, 0, &a);
    queue(&r, 1, 2, 0); /* a SPI push in between may shift the queue */
    CHECK_EQ(nl_radio_tx_busy(&r, 0), NL_ERR_EMPTY);
    CHECK_EQ(r.stats.tx_sent, 1); /* counted as sent */
}

static void test_cca_max_defers(void)
{
    /* A permanently busy channel cannot starve a fragment. */
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    setup(&r, &p, prio);
    queue(&r, 1, 0, 0);
    nl_radio_action_t a;
    nl_time_us_t t = 0;
    for (int k = 0; k < NL_RADIO_CCA_MAX_DEFERS; k++) {
        t = next_tx(&r, t, &a);
        CHECK(a.cca);
        CHECK_EQ(nl_radio_tx_busy(&r, t), NL_OK);
    }
    t = next_tx(&r, t, &a);
    CHECK(!a.cca); /* sent without a check */
    t = next_tx(&r, t + 10, &a);
    CHECK(a.cca); /* the count restarts after a transmission */
}

static void test_cca_hold_after_rx(void)
{
    /* After hearing a packet, a device waits its own random 0..cca_backoff_us
     * so devices that waited for the same packet do not all start at once. */
    const uint8_t prio[NL_NUM_ZONES] = {0, 1, 0, 0, 0, 0, 0, 0};
    nl_radio_t r;
    nl_radio_params_t p;
    nl_time_us_t first = UINT32_MAX, last = 0;
    for (uint8_t origin = 0; origin < 8; origin++) {
        setup(&r, &p, prio);
        p.origin_id = origin;
        nl_radio_configure(&r, &p, NULL);
        nl_radio_next_action(&r, 0, &(nl_radio_action_t){0});
        rx(&r, origin == 2 ? 3 : 2, 1, 0, 9, 1000);
        queue(&r, 1, 0, 1000);
        nl_radio_action_t a;
        nl_time_us_t t = next_tx(&r, 1000, &a);
        CHECK(t <= 1000 + p.cca_backoff_us + 10);
        first = t < first ? t : first;
        last = t > last ? t : last;
    }
    CHECK(last - first >= 200); /* spread out */

    setup(&r, &p, prio);
    p.cca_backoff_us = 0;
    nl_radio_configure(&r, &p, NULL);
    rx(&r, 2, 1, 0, 9, 1000);
    queue(&r, 1, 0, 1000);
    nl_radio_action_t a;
    nl_radio_next_action(&r, 1000, &a);
    CHECK_EQ(a.type, NL_ACT_TX); /* no hold without CCA */
}

int main(void)
{
    RUN(test_idle_before_plan);
    RUN(test_swrr_ratio);
    RUN(test_slot_held_until_dwell_ends);
    RUN(test_priority_cap);
    RUN(test_park_on_zone0);
    RUN(test_zone_without_frequency_skipped);
    RUN(test_mgmt_listen_adds_zone0);
    RUN(test_zone0_priority_listens_always);
    RUN(test_repeats_and_interval);
    RUN(test_multiple_fragments_interleave);
    RUN(test_immediate_zone_fairness);
    RUN(test_tx_eviction);
    RUN(test_dual_band);
    RUN(test_in_slot_policy);
    RUN(test_rx_filters);
    RUN(test_burst_extends_slot);
    RUN(test_spi_ping_status);
    RUN(test_spi_push_pull);
    RUN(test_spi_rejects);
    RUN(test_origin_restamp);
    RUN(test_zero_repeats_sends_once);
    RUN(test_repeat_jitter);
    RUN(test_discovery_visits);
    RUN(test_listen_after_zone0_tx);
    RUN(test_cca_flag);
    RUN(test_cca_busy_defers);
    RUN(test_cca_busy_last_repeat);
    RUN(test_cca_push_invalidates_undo);
    RUN(test_cca_max_defers);
    RUN(test_cca_hold_after_rx);
    return nl_test_finish();
}
