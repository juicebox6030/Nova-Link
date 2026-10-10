#include "nl_sim.h"

#include "nova_link/nl_config_file.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Measured payload layout (NL_SIM_PAYLOAD_HDR bytes, rest zero-filled):
 *   [0]    sending device index
 *   [1..4] per-device send counter (LE)
 *   [5..8] global send time in us (LE, low 32 bits)
 */

#define SEEN_WINDOW 4096u /* reorder / duplicate detection window per flow */

typedef struct {
    bool active;
    uint8_t sender;
    uint32_t freq;
    uint64_t start, end;
    uint8_t data[NL_MAX_FRAGMENT];
    uint8_t len;
    uint8_t listen_ok; /* receivers that have been listening throughout */
    uint8_t heard_any; /* receivers that listened at some point */
    uint8_t collided;  /* receivers where another packet overlapped */
} air_t;

typedef struct {
    uint64_t hi;              /* highest counter + 1 seen (0 = none) */
    uint8_t bits[SEEN_WINDOW / 8];
} seen_t;

typedef struct sim_node {
    struct nl_sim *sim;
    uint8_t idx;
    bool booted;
    uint32_t clock_offset;
    uint8_t claims; /* zone bits */

    nl_radio_t radio;
    nl_spi_link_t link;
    nl_host_t host;
    nl_plugin_def_t plugin;

    nl_radio_action_t act;
    uint64_t wake;
    uint64_t busy_until;
    bool listening;
    uint32_t rx_freq;
    uint8_t last_pending;

    /* Deferred SPI (spi_deferred) */
    uint64_t spi_now;       /* SPI-side clock, at or ahead of the sim clock */
    uint64_t radio_loop_at; /* next radio main-loop iteration */
    const uint8_t *armed;   /* reply loaded into the SPI peripheral */
    size_t armed_len;

    uint64_t next_poll;
    uint64_t next_send[2];
    uint32_t counter;
} sim_node_t;

struct nl_sim {
    nl_sim_scenario_t sc;
    uint64_t now;
    uint32_t rng;
    uint64_t measure_end;
    uint64_t last_boot;
    sim_node_t node[NL_SIM_MAX_NODES];
    air_t air[NL_SIM_MAX_AIR];

    uint32_t freq_list[NL_SIM_MAX_FREQS];
    uint64_t freq_busy[NL_SIM_MAX_FREQS];
    uint8_t nfreq;

    seen_t seen[NL_SIM_MAX_NODES][NL_SIM_MAX_NODES];
    uint64_t flow_delivered[NL_SIM_MAX_NODES][NL_SIM_MAX_NODES];
    uint32_t lat_hist[NL_SIM_LAT_BUCKETS];
    uint64_t lat_sum;
    uint32_t lat_max;
    nl_sim_result_t res;
};

/* ---- Helpers ------------------------------------------------------------ */

static double rand01(uint32_t *rng)
{
    return (double)(nl_rand_next(rng) >> 8) / 16777216.0;
}

static uint32_t local_time(const sim_node_t *n, uint64_t t)
{
    return (uint32_t)(t + n->clock_offset);
}

/** Global time of a node-local deadline, never earlier than @p t. */
static uint64_t global_deadline(const sim_node_t *n, uint64_t t, nl_time_us_t until)
{
    int32_t d = nl_time_diff(until, local_time(n, t));
    return d > 0 ? t + (uint64_t)d : t;
}

static bool hears(const struct nl_sim *sim, uint8_t tx, uint8_t rx)
{
    return sim->sc.link_loss[tx][rx] < 1.0;
}

void nl_sim_phy_default(nl_sim_phy_t *phy, uint8_t band)
{
    memset(phy, 0, sizeof(*phy));
    phy->preamble_bytes = 4;
    phy->sync_bytes = 4;
    phy->length_bytes = 1;
    phy->crc_bytes = 2;
    if (band == NL_BAND_2G4) {
        phy->bitrate_bps = 250000;
        phy->turnaround_us = 150;
    } else {
        phy->bitrate_bps = 200000;
        phy->turnaround_us = 200;
    }
}

uint32_t nl_sim_airtime_us(const nl_sim_phy_t *phy, size_t len)
{
    uint64_t bytes = (uint64_t)phy->preamble_bytes + phy->sync_bytes +
                     phy->length_bytes + phy->crc_bytes + len;
    uint32_t bps = phy->bitrate_bps ? phy->bitrate_bps : 1;
    return (uint32_t)((bytes * 8u * 1000000u + bps - 1u) / bps);
}

void nl_sim_scenario_default(nl_sim_scenario_t *sc, uint8_t nodes)
{
    memset(sc, 0, sizeof(*sc));
    if (nodes > NL_SIM_MAX_NODES) {
        nodes = NL_SIM_MAX_NODES;
    }
    sc->nodes = nodes;
    sc->duration_us = 5000000;
    sc->warmup_us = 1000000;
    sc->tick_us = 10;
    sc->host_poll_us = 1000;
    sc->seed = 1;
    nl_sim_phy_default(&sc->phy[NL_BAND_SUBGHZ], NL_BAND_SUBGHZ);
    nl_sim_phy_default(&sc->phy[NL_BAND_2G4], NL_BAND_2G4);
    nl_radio_params_default(&sc->params);
    nl_host_config_default(&sc->host);
    nl_config_zone_plan_default(&sc->plan);
    sc->wake_on_push = true;
    sc->finish_rx = true;
    sc->radio_loop_us = 200;
    sc->spi_hz = 8000000;
    for (uint8_t i = 0; i < nodes; i++) {
        nl_sim_node_cfg_t *n = &sc->node[i];
        n->enabled = true;
        n->listen_mask = 1u << 1;
        n->boot_us = (uint64_t)i * 5000u / (nodes > 1 ? (uint64_t)(nodes - 1) : 1u);
        n->traffic[0].zone = 1;
        n->traffic[0].period_us = 50000;
        n->traffic[0].jitter_us = 5000;
        n->traffic[0].payload_len = 32;
        n->traffic[0].burst = 1;
    }
}

size_t nl_sim_size(void)
{
    return sizeof(struct nl_sim);
}

/* ---- SPI loopback ------------------------------------------------------- */

/**
 * Deferred mode: run the radio main loop's iterations due by SPI time
 * @p until. Each drains the queued requests and, if @p bus_idle, loads
 * the reply; during a transaction it is left for the ISR's
 * nl_radio_spi_arm(). Radio time is the sim clock.
 */
static void radio_loop_until(struct nl_sim *sim, sim_node_t *n, uint64_t until,
                             bool bus_idle)
{
    while (n->radio_loop_at <= until) {
        while (nl_radio_poll(&n->radio, local_time(n, sim->now))) {
            size_t len;
            const uint8_t *p = bus_idle ? nl_radio_spi_arm(&n->radio, &len) : NULL;
            if (p != NULL) {
                n->armed = p;
                n->armed_len = len;
            }
        }
        n->radio_loop_at += 1u + nl_rand_upto(&sim->rng, sim->sc.radio_loop_us);
    }
}

static int hal_transfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t len)
{
    sim_node_t *n = ctx;
    struct nl_sim *sim = n->sim;
    size_t olen;
    const uint8_t *out;
    if (sim->sc.spi_deferred) {
        radio_loop_until(sim, n, n->spi_now, true);
        out = n->armed;
        olen = n->armed_len;
    } else {
        out = nl_radio_outbox(&n->radio, &olen);
    }
    memset(rx, 0, len);
    if (out != NULL) {
        memcpy(rx, out, olen < len ? olen : len);
    }
    if (sim->sc.spi_fault_rate > 0.0 && len > 0 &&
        rand01(&sim->rng) < sim->sc.spi_fault_rate) {
        rx[nl_rand_next(&sim->rng) % len] ^= 0x04;
    }
    if (!sim->sc.spi_deferred) {
        nl_radio_spi_complete(&n->radio, tx, len, local_time(n, sim->now));
        return 0;
    }
    /* The transaction ends (chip select high) len * 8 SPI clocks later. */
    uint32_t hz = sim->sc.spi_hz ? sim->sc.spi_hz : 1u;
    n->spi_now += ((uint64_t)len * 8000000u + hz - 1u) / hz;
    radio_loop_until(sim, n, n->spi_now, false);
    nl_radio_spi_isr(&n->radio, tx, len);
    n->armed = nl_radio_spi_arm(&n->radio, &n->armed_len);
    return 0;
}

static bool hal_int_ready(void *ctx)
{
    return nl_radio_int_ready(&((sim_node_t *)ctx)->radio);
}

static void hal_delay(void *ctx, uint32_t us)
{
    sim_node_t *n = ctx;
    if (n->sim->sc.spi_deferred) {
        n->spi_now += us;
        radio_loop_until(n->sim, n, n->spi_now, true);
    } /* direct mode: SPI timing is not modelled */
}

/* ---- Measurement plugin -------------------------------------------------- */

static int plugin_init(nl_host_t *h, uint8_t slot, void *user)
{
    sim_node_t *n = user;
    for (uint8_t z = 1; z < NL_NUM_ZONES; z++) {
        if (n->claims & (1u << z)) {
            int rc = nl_host_claim(h, slot, z, NL_CLAIM_SHARED);
            if (rc < 0) {
                return rc;
            }
        }
    }
    return NL_OK;
}

static void record_latency(struct nl_sim *sim, uint32_t lat)
{
    uint32_t b = lat / NL_SIM_LAT_BUCKET_US;
    if (b >= NL_SIM_LAT_BUCKETS) {
        sim->res.late++;
        b = NL_SIM_LAT_BUCKETS - 1u;
    }
    sim->lat_hist[b]++;
    sim->lat_sum += lat;
    if (lat > sim->lat_max) {
        sim->lat_max = lat;
    }
}

static bool measured(const struct nl_sim *sim, uint64_t t)
{
    return t >= sim->sc.warmup_us && t < sim->measure_end;
}

static void plugin_fragment(nl_host_t *h, uint8_t slot, const nl_fragment_t *f,
                            void *user)
{
    (void)h;
    (void)slot;
    sim_node_t *n = user;
    struct nl_sim *sim = n->sim;
    if (f->payload_len < NL_SIM_PAYLOAD_HDR || f->payload[0] >= sim->sc.nodes) {
        return;
    }
    uint8_t tx = f->payload[0];
    uint32_t counter = nl_get_u32le(&f->payload[1]);
    uint32_t sent = nl_get_u32le(&f->payload[5]);
    if (!measured(sim, sent)) {
        return;
    }
    seen_t *s = &sim->seen[tx][n->idx];
    uint64_t c = counter;
    if (c + SEEN_WINDOW <= s->hi) {
        sim->res.reordered++; /* too old to tell; assume reordered */
        return;
    }
    uint8_t *byte = &s->bits[(c % SEEN_WINDOW) / 8];
    uint8_t bit = (uint8_t)(1u << (c % 8));
    if (c < s->hi) {
        if (*byte & bit) {
            sim->res.duplicates++;
            return;
        }
        sim->res.reordered++;
    } else {
        /* Clear the window slots we are skipping over. */
        for (uint64_t k = s->hi; k <= c && k < s->hi + SEEN_WINDOW; k++) {
            s->bits[(k % SEEN_WINDOW) / 8] &= (uint8_t)~(1u << (k % 8));
        }
        s->hi = c + 1;
    }
    *byte |= bit;
    sim->res.delivered++;
    sim->flow_delivered[tx][n->idx]++;
    record_latency(sim, (uint32_t)sim->now - sent);
}

/* ---- Medium --------------------------------------------------------------- */

static void account_freq(struct nl_sim *sim, uint32_t freq, uint64_t us)
{
    for (uint8_t i = 0; i < sim->nfreq; i++) {
        if (sim->freq_list[i] == freq) {
            sim->freq_busy[i] += us;
            return;
        }
    }
    if (sim->nfreq < NL_SIM_MAX_FREQS) {
        sim->freq_list[sim->nfreq] = freq;
        sim->freq_busy[sim->nfreq++] = us;
    }
}

static void air_add(struct nl_sim *sim, sim_node_t *n, const nl_radio_action_t *act,
                    uint64_t start, uint64_t end)
{
    air_t *a = NULL;
    for (int i = 0; i < NL_SIM_MAX_AIR; i++) {
        if (!sim->air[i].active) {
            a = &sim->air[i];
            break;
        }
    }
    sim->res.air_tx++;
    if (a == NULL) {
        return; /* more concurrent packets than tracked: drop silently */
    }
    memset(a, 0, sizeof(*a));
    a->active = true;
    a->sender = n->idx;
    a->freq = act->freq_hz;
    a->start = start;
    a->end = end;
    a->len = act->len;
    memcpy(a->data, act->data, act->len);
    for (uint8_t r = 0; r < sim->sc.nodes; r++) {
        if (r != n->idx && hears(sim, n->idx, r)) {
            a->listen_ok |= (uint8_t)(1u << r);
        }
    }
    for (int i = 0; i < NL_SIM_MAX_AIR; i++) {
        air_t *o = &sim->air[i];
        if (o == a || !o->active || o->freq != a->freq || o->end <= a->start ||
            a->end <= o->start) {
            continue;
        }
        for (uint8_t r = 0; r < sim->sc.nodes; r++) {
            if (hears(sim, a->sender, r) && hears(sim, o->sender, r)) {
                a->collided |= (uint8_t)(1u << r);
                o->collided |= (uint8_t)(1u << r);
            }
        }
    }
    account_freq(sim, a->freq, end - start);
}

/** Clear receivers that are not listening on an on-air packet's frequency. */
static void air_track(struct nl_sim *sim, uint64_t t)
{
    for (int i = 0; i < NL_SIM_MAX_AIR; i++) {
        air_t *a = &sim->air[i];
        if (!a->active || t < a->start || t >= a->end) {
            continue;
        }
        for (uint8_t r = 0; r < sim->sc.nodes; r++) {
            const sim_node_t *m = &sim->node[r];
            uint8_t bit = (uint8_t)(1u << r);
            bool on = m->booted && m->listening && m->rx_freq == a->freq;
            if (on) {
                a->heard_any |= bit;
            } else {
                a->listen_ok &= (uint8_t)~bit;
            }
        }
    }
}

static void air_deliver(struct nl_sim *sim, uint64_t t)
{
    for (int i = 0; i < NL_SIM_MAX_AIR; i++) {
        air_t *a = &sim->air[i];
        if (!a->active || t < a->end) {
            continue;
        }
        a->active = false;
        for (uint8_t r = 0; r < sim->sc.nodes; r++) {
            uint8_t bit = (uint8_t)(1u << r);
            if (r == a->sender || !(a->heard_any & bit)) {
                continue;
            }
            if (!(a->listen_ok & bit)) {
                sim->res.air_missed++;
                continue;
            }
            if (a->collided & bit) {
                sim->res.air_collided++;
                continue;
            }
            double loss = sim->sc.per + sim->sc.link_loss[a->sender][r];
            if (loss > 0.0 && rand01(&sim->rng) < loss) {
                sim->res.air_lost++;
                continue;
            }
            sim_node_t *m = &sim->node[r];
            sim->res.air_rx_ok++;
            nl_radio_rx_packet(&m->radio, a->data, a->len, local_time(m, t));
            m->wake = t; /* the platform loops after every packet */
        }
    }
}

/* ---- Devices --------------------------------------------------------------- */

static void node_boot(struct nl_sim *sim, sim_node_t *n, uint64_t t)
{
    const nl_sim_node_cfg_t *c = &sim->sc.node[n->idx];
    n->booted = true;
    nl_radio_init(&n->radio);
    nl_radio_seed(&n->radio, nl_rand_next(&sim->rng));
    nl_spi_hal_t hal = {hal_transfer, hal_int_ready, hal_delay, n};
    nl_spi_link_init(&n->link, &hal);
    if (sim->sc.spi_read_retries != 0) {
        n->link.read_retries = sim->sc.spi_read_retries;
    }
    nl_link_ops_t ops;
    nl_spi_link_ops(&n->link, &ops);

    nl_host_config_t cfg = sim->sc.host;
    cfg.origin_id = n->idx;
    cfg.rand_seed = nl_rand_next(&sim->rng);
    snprintf(cfg.name, sizeof(cfg.name), "node%u", (unsigned)n->idx);
    nl_host_init(&n->host, &cfg, &ops);

    nl_zone_plan_t plan = sim->sc.plan;
    for (uint8_t z = 0; z < NL_NUM_ZONES; z++) {
        if (c->priority[z] != 0) {
            plan.zone[z].priority = c->priority[z];
        }
    }
    nl_host_set_rf(&n->host, &sim->sc.params, &plan);

    n->claims = c->listen_mask;
    for (int k = 0; k < 2; k++) {
        if (c->traffic[k].zone != 0) {
            n->claims |= (uint8_t)(1u << c->traffic[k].zone);
        }
    }
    n->claims &= (uint8_t)~1u;
    n->plugin.name = "sim";
    n->plugin.type_id = 0x5157;
    n->plugin.init = plugin_init;
    n->plugin.on_fragment = plugin_fragment;
    n->plugin.user = n;
    nl_host_register(&n->host, &n->plugin);

    n->wake = t;
    n->busy_until = t;
    n->spi_now = t;
    n->radio_loop_at = t;
    n->armed = NULL;
    n->armed_len = 0;
    n->next_poll = t;
    for (int k = 0; k < 2; k++) {
        const nl_sim_traffic_t *tr = &c->traffic[k];
        uint32_t p = tr->period_us ? tr->period_us : 1u;
        n->next_send[k] = t + nl_rand_upto(&sim->rng, p);
    }
}

static void node_send(struct nl_sim *sim, sim_node_t *n, const nl_sim_traffic_t *tr,
                      uint64_t t)
{
    uint8_t payload[NL_MAX_PAYLOAD];
    uint8_t len = tr->payload_len;
    if (len < NL_SIM_PAYLOAD_HDR) {
        len = NL_SIM_PAYLOAD_HDR;
    }
    if (len > NL_MAX_PAYLOAD) {
        len = NL_MAX_PAYLOAD;
    }
    uint16_t burst = tr->burst ? tr->burst : 1u;
    for (uint16_t b = 0; b < burst; b++) {
        memset(payload, 0, sizeof(payload));
        payload[0] = n->idx;
        nl_put_u32le(&payload[1], n->counter++);
        nl_put_u32le(&payload[5], (uint32_t)t);
        int rc = nl_host_send(&n->host, 0, tr->zone, payload, len,
                              b + 1u < burst ? (uint8_t)(tr->flags | NL_FLAG_BURST)
                                             : tr->flags);
        if (!measured(sim, t)) {
            continue;
        }
        if (rc != NL_OK) {
            sim->res.send_failed++;
            continue;
        }
        sim->res.sent++;
        for (uint8_t r = 0; r < sim->sc.nodes; r++) {
            const sim_node_t *m = &sim->node[r];
            if (r != n->idx && m->booted && (m->claims & (1u << tr->zone))) {
                sim->res.expected++;
            }
        }
    }
}

static void node_host_step(struct nl_sim *sim, sim_node_t *n, uint64_t t)
{
    const nl_sim_node_cfg_t *c = &sim->sc.node[n->idx];
    if (sim->sc.spi_deferred) {
        if (n->spi_now < t) {
            n->spi_now = t;
        }
        radio_loop_until(sim, n, n->spi_now, true);
    }
    for (int k = 0; k < 2; k++) {
        const nl_sim_traffic_t *tr = &c->traffic[k];
        if (tr->zone == 0 || tr->period_us == 0) {
            continue;
        }
        while (t >= n->next_send[k]) {
            node_send(sim, n, tr, t);
            n->next_send[k] += tr->period_us + nl_rand_upto(&sim->rng, tr->jitter_us);
        }
    }
    if (t >= n->next_poll) {
        nl_host_poll(&n->host, local_time(n, t));
        n->next_poll += sim->sc.host_poll_us ? sim->sc.host_poll_us : 1000u;
    }
    uint8_t pending = nl_radio_tx_pending(&n->radio);
    if (pending > n->last_pending && sim->sc.wake_on_push) {
        n->wake = t;
    }
    n->last_pending = pending;
}

/**
 * Clear-channel check: is a packet that @p n can hear on the air on @p freq
 * at @p t? A packet whose sender is still in its turnaround is not on the
 * air yet, which is the window where two checks can both pass.
 */
static bool channel_busy(const struct nl_sim *sim, const sim_node_t *n,
                         uint32_t freq, uint64_t t)
{
    for (int i = 0; i < NL_SIM_MAX_AIR; i++) {
        const air_t *a = &sim->air[i];
        if (a->active && a->freq == freq && t >= a->start && t < a->end &&
            a->sender != n->idx && hears(sim, a->sender, n->idx)) {
            return true;
        }
    }
    return false;
}

/** End of a packet @p n has been receiving since its start, or 0. */
static uint64_t rx_in_progress(const struct nl_sim *sim, const sim_node_t *n, uint64_t t)
{
    if (!n->listening) {
        return 0;
    }
    uint8_t bit = (uint8_t)(1u << n->idx);
    for (int i = 0; i < NL_SIM_MAX_AIR; i++) {
        const air_t *a = &sim->air[i];
        if (a->active && a->freq == n->rx_freq && t >= a->start && t < a->end &&
            (a->listen_ok & bit) && (a->heard_any & bit)) {
            return a->end;
        }
    }
    return 0;
}

static void node_radio_step(struct nl_sim *sim, sim_node_t *n, uint64_t t)
{
    if (t < n->busy_until || t < n->wake) {
        return;
    }
    if (sim->sc.finish_rx) {
        uint64_t end = rx_in_progress(sim, n, t);
        if (end != 0) {
            n->wake = end; /* sync detected: finish this packet first */
            return;
        }
    }
    nl_radio_next_action(&n->radio, local_time(n, t), &n->act);
    /* Terminates: every deferral moves one queued fragment into the future. */
    while (n->act.type == NL_ACT_TX && n->act.cca &&
           channel_busy(sim, n, n->act.freq_hz, t)) {
        nl_radio_tx_busy(&n->radio, local_time(n, t));
        sim->res.air_deferred++;
        nl_radio_next_action(&n->radio, local_time(n, t), &n->act);
    }
    n->last_pending = nl_radio_tx_pending(&n->radio);
    switch (n->act.type) {
    case NL_ACT_TX: {
        const nl_sim_phy_t *phy = &sim->sc.phy[n->act.band == NL_BAND_2G4];
        uint64_t start = t + phy->turnaround_us;
        uint64_t end = start + nl_sim_airtime_us(phy, n->act.len);
        n->listening = false;
        air_add(sim, n, &n->act, start, end);
        n->busy_until = end;
        n->wake = end;
        break;
    }
    case NL_ACT_RX:
        n->listening = true;
        n->rx_freq = n->act.freq_hz;
        n->wake = global_deadline(n, t, n->act.until);
        break;
    default:
        n->listening = false;
        n->wake = global_deadline(n, t, n->act.until);
        break;
    }
    if (n->wake == t) {
        n->wake = t + 1; /* decide again on the next tick */
    }
}

static bool all_discovered(const struct nl_sim *sim)
{
    for (uint8_t i = 0; i < sim->sc.nodes; i++) {
        const sim_node_t *a = &sim->node[i];
        if (!sim->sc.node[i].enabled) {
            continue;
        }
        if (!a->booted) {
            return false;
        }
        for (uint8_t j = 0; j < sim->sc.nodes; j++) {
            if (j != i && sim->sc.node[j].enabled && nl_host_peer(&a->host, j) == NULL) {
                return false;
            }
        }
    }
    return true;
}

/* ---- Public API ------------------------------------------------------------ */

int nl_sim_init(nl_sim_t *sim, const nl_sim_scenario_t *sc)
{
    if (sc->nodes == 0 || sc->nodes > NL_SIM_MAX_NODES || sc->tick_us == 0) {
        return NL_ERR_ARG;
    }
    memset(sim, 0, sizeof(*sim));
    sim->sc = *sc;
    sim->rng = nl_rand_seed(sc->seed);
    uint64_t drain = 500000u;
    if (drain > sc->duration_us / 4u) {
        drain = sc->duration_us / 4u;
    }
    sim->measure_end = sc->duration_us - drain;
    sim->res.discovery_us = -1;
    for (uint8_t i = 0; i < sc->nodes; i++) {
        sim_node_t *n = &sim->node[i];
        n->sim = sim;
        n->idx = i;
        n->clock_offset = nl_rand_next(&sim->rng);
        if (sc->node[i].enabled && sc->node[i].boot_us > sim->last_boot) {
            sim->last_boot = sc->node[i].boot_us;
        }
    }
    return NL_OK;
}

void nl_sim_advance(nl_sim_t *sim, uint64_t until_us)
{
    for (uint64_t t = sim->now; t < until_us; t += sim->sc.tick_us) {
        sim->now = t;
        air_deliver(sim, t);
        for (uint8_t i = 0; i < sim->sc.nodes; i++) {
            sim_node_t *n = &sim->node[i];
            if (!sim->sc.node[i].enabled) {
                continue;
            }
            if (!n->booted) {
                if (t < sim->sc.node[i].boot_us) {
                    continue;
                }
                node_boot(sim, n, t);
            }
            node_host_step(sim, n, t);
        }
        for (uint8_t i = 0; i < sim->sc.nodes; i++) {
            if (sim->node[i].booted) {
                node_radio_step(sim, &sim->node[i], t);
            }
        }
        air_track(sim, t);
        if (sim->res.discovery_us < 0 && t >= sim->last_boot &&
            (t - sim->last_boot) % 1000u < sim->sc.tick_us && all_discovered(sim)) {
            sim->res.discovery_us = (int64_t)(t - sim->last_boot);
        }
    }
    sim->now = until_us;
}

static uint32_t percentile(const nl_sim_t *sim, uint64_t total, double q)
{
    if (total == 0) {
        return 0;
    }
    uint64_t target = (uint64_t)((double)total * q);
    uint64_t acc = 0;
    for (uint32_t b = 0; b < NL_SIM_LAT_BUCKETS; b++) {
        acc += sim->lat_hist[b];
        if (acc > target) {
            return (b + 1u) * NL_SIM_LAT_BUCKET_US;
        }
    }
    return NL_SIM_LAT_BUCKETS * NL_SIM_LAT_BUCKET_US;
}

void nl_sim_result(const nl_sim_t *sim, nl_sim_result_t *res)
{
    *res = sim->res;
    uint64_t total = 0;
    for (uint32_t b = 0; b < NL_SIM_LAT_BUCKETS; b++) {
        total += sim->lat_hist[b];
    }
    res->lat_p50_us = percentile(sim, total, 0.50);
    res->lat_p90_us = percentile(sim, total, 0.90);
    res->lat_p99_us = percentile(sim, total, 0.99);
    res->lat_max_us = sim->lat_max;
    res->lat_mean_us = total ? (double)sim->lat_sum / (double)total : 0.0;
    uint64_t busiest = 0;
    for (uint8_t i = 0; i < sim->nfreq; i++) {
        if (sim->freq_busy[i] > busiest) {
            busiest = sim->freq_busy[i];
        }
    }
    res->busiest_channel_util =
        sim->now ? (double)busiest / (double)sim->now : 0.0;
    for (uint8_t i = 0; i < sim->sc.nodes; i++) {
        const sim_node_t *n = &sim->node[i];
        if (!n->booted) {
            continue;
        }
        res->radio_tx_dropped += n->radio.stats.tx_dropped;
        res->radio_rx_dropped += n->radio.stats.rx_dropped;
        res->spi_errors += n->link.stats.crc_errors + n->link.stats.proto_errors +
                           n->link.stats.io_errors;
        res->radio_resets += n->host.stats.radio_resets;
        res->spi_transactions += n->link.stats.transactions;
        res->spi_read_retries += n->link.stats.read_retries;
        res->spi_overruns += n->radio.spi_overruns;
        res->spi_reply_busy += n->radio.spi_reply_busy;
    }
}

nl_host_t *nl_sim_host(nl_sim_t *sim, uint8_t node)
{
    return &sim->node[node].host;
}

nl_radio_t *nl_sim_radio(nl_sim_t *sim, uint8_t node)
{
    return &sim->node[node].radio;
}

uint64_t nl_sim_flow_delivered(const nl_sim_t *sim, uint8_t tx, uint8_t rx)
{
    return sim->flow_delivered[tx][rx];
}

int nl_sim_run(const nl_sim_scenario_t *sc, nl_sim_result_t *res)
{
    nl_sim_t *sim = malloc(sizeof(*sim));
    if (sim == NULL) {
        return NL_ERR_FULL;
    }
    int rc = nl_sim_init(sim, sc);
    if (rc == NL_OK) {
        nl_sim_advance(sim, sc->duration_us);
        nl_sim_result(sim, res);
    }
    free(sim);
    return rc;
}
