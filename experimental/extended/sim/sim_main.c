/**
 * nl_sim: run NOVA-LINK network scenarios and parameter sweeps.
 *
 *   nl_sim [--key value]... [--sweep key=v1,v2,...] [--runs N] [--csv]
 *
 * Run "nl_sim --help" for the option list.
 */
#include "nl_sim.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_OPTS 64
#define MAX_SWEEP 32

typedef struct {
    const char *key;
    const char *val;
} opt_t;

static void usage(void)
{
    puts("usage: nl_sim [options]\n"
         "\n"
         "scenario:\n"
         "  --preset NAME       broadcast (default): every node sends and listens on zone 1\n"
         "                      zones: node i sends on zone 1+(i%zones), listens on all\n"
         "                      star: node 0 sends on zone 1, the others only listen\n"
         "                      silent: no traffic (discovery only)\n"
         "  --nodes N           devices (1..8, default 4)\n"
         "  --zones K           zones used by the zones preset (1..7, default 3)\n"
         "  --rate HZ           sends per second per sending node (default 20)\n"
         "  --payload B         payload bytes (9..100, default 32)\n"
         "  --burst N           fragments per send, BURST flag on all but the last\n"
         "  --duration S        simulated seconds (default 5)\n"
         "  --warmup S          seconds before measurement starts (default 1)\n"
         "  --boot-spread S     power-up spread across nodes (default 0.005)\n"
         "  --seed N            random seed (default 1)\n"
         "\n"
         "radio core (nl_radio_params_t):\n"
         "  --band subghz|2g4|dual  --policy immediate|in_slot  --repeats N\n"
         "  --dwell US  --repeat-interval US  --repeat-jitter US  --discovery US\n"
         "  --mgmt-hold US  --mgmt-repeats N  --burst-extend US  --cca-backoff US\n"
         "host: --announce US  --announce-jitter US  --announce-spread US\n"
         "      --announce-ramp N  --poll US\n"
         "\n"
         "RF model:\n"
         "  --per P             packet error rate on every link (0..1)\n"
         "  --hidden            split nodes into two groups that cannot hear each\n"
         "                      other; node 0 hears everyone (hidden terminals)\n"
         "  --bitrate BPS       sub-GHz bitrate (default 200000)\n"
         "  --bitrate24 BPS     2.4 GHz bitrate (default 250000)\n"
         "  --turnaround US     RX->TX switch time, both bands\n"
         "  --spi-fault P       probability a SPI response is corrupted\n"
         "  --no-wake-on-push   radio only re-plans at slot ends (pessimistic platform)\n"
         "  --no-finish-rx      slot changes abort a packet being received\n"
        "  --spi-deferred      radio handles SPI via the ISR handoff + main-loop poll\n"
        "  --radio-loop-us US  deferred: max radio main-loop iteration (default 200)\n"
        "  --spi-hz HZ         deferred: SPI clock (default 8000000)\n"
        "  --spi-read-retries N  host response re-reads, 50 us apart (default 4)\n"
         "  --tick US           simulation step (default 10)\n"
         "\n"
         "output:\n"
         "  --sweep KEY=V1,V2,..  repeat the run for each value of one option\n"
         "  --runs N            seeds per configuration (results are pooled)\n"
         "  --csv               machine-readable output\n"
         "  --expect-delivery F exit 1 if pooled delivery ratio < F\n"
         "  --expect-p99-ms F   exit 1 if any run's p99 latency > F ms\n"
         "  --expect-discovery-ms F  exit 1 if any run's discovery time > F ms\n"
         "\n"
         "columns: delivery = unique fragments delivered / expected; collide and\n"
         "missed = receptions lost to overlaps / to the receiver not listening for\n"
         "the whole packet (tuned in late, left early, or transmitting itself);\n"
         "defer = transmissions put off by a busy clear-channel check;\n"
         "load% = airtime on the busiest frequency / time, every transmission\n"
         "counted, so overlapping ones add up and over 100% means saturated;\n"
         "disc ms = worst time until every device knew every other.");
}

static double num(const char *key, const char *val)
{
    char *end;
    double d = strtod(val, &end);
    if (end == val || *end != '\0') {
        fprintf(stderr, "nl_sim: bad value for --%s: '%s'\n", key, val);
        exit(2);
    }
    return d;
}

static uint32_t u32(const char *key, const char *val)
{
    double d = num(key, val);
    if (d < 0 || d > 4294967295.0) {
        fprintf(stderr, "nl_sim: --%s out of range\n", key);
        exit(2);
    }
    return (uint32_t)d;
}

static uint8_t u8(const char *key, const char *val)
{
    uint32_t v = u32(key, val);
    if (v > 255) {
        fprintf(stderr, "nl_sim: --%s out of range\n", key);
        exit(2);
    }
    return (uint8_t)v;
}

static uint64_t seconds(const char *key, const char *val)
{
    double d = num(key, val);
    if (d < 0 || d > 3600) {
        fprintf(stderr, "nl_sim: --%s out of range\n", key);
        exit(2);
    }
    return (uint64_t)(d * 1e6);
}

/** Options that shape the scenario before the others apply. */
typedef struct {
    uint8_t nodes;
    uint8_t zones;
    const char *preset;
} base_t;

static void build_base(nl_sim_scenario_t *sc, const base_t *b)
{
    nl_sim_scenario_default(sc, b->nodes);
    for (uint8_t i = 0; i < sc->nodes; i++) {
        nl_sim_node_cfg_t *n = &sc->node[i];
        if (strcmp(b->preset, "zones") == 0) {
            n->listen_mask = 0;
            for (uint8_t z = 1; z <= b->zones; z++) {
                n->listen_mask |= (uint8_t)(1u << z);
            }
            n->traffic[0].zone = (uint8_t)(1u + i % b->zones);
        } else if (strcmp(b->preset, "star") == 0) {
            if (i != 0) {
                n->traffic[0].zone = 0;
            }
        } else if (strcmp(b->preset, "silent") == 0) {
            n->traffic[0].zone = 0;
        } else if (strcmp(b->preset, "broadcast") != 0) {
            fprintf(stderr, "nl_sim: unknown preset '%s'\n", b->preset);
            exit(2);
        }
    }
}

static void each_traffic(nl_sim_scenario_t *sc, void (*fn)(nl_sim_traffic_t *, double),
                         double v)
{
    for (uint8_t i = 0; i < sc->nodes; i++) {
        fn(&sc->node[i].traffic[0], v);
    }
}

static void set_rate(nl_sim_traffic_t *t, double hz)
{
    t->period_us = hz > 0 ? (uint32_t)(1e6 / hz) : 0;
    t->jitter_us = t->period_us / 10u;
}

static void set_payload(nl_sim_traffic_t *t, double v)
{
    t->payload_len = (uint8_t)v;
}

static void set_burst(nl_sim_traffic_t *t, double v)
{
    t->burst = (uint16_t)v;
}

/** Apply one option. @return 1 if handled, 0 if it is an output option. */
static int apply(nl_sim_scenario_t *sc, const char *k, const char *v)
{
    nl_radio_params_t *p = &sc->params;
    if (!strcmp(k, "nodes") || !strcmp(k, "zones") || !strcmp(k, "preset")) {
        return 1; /* handled by build_base */
    } else if (!strcmp(k, "rate")) {
        each_traffic(sc, set_rate, num(k, v));
    } else if (!strcmp(k, "payload")) {
        uint32_t b = u32(k, v);
        if (b < NL_SIM_PAYLOAD_HDR || b > NL_MAX_PAYLOAD) {
            fprintf(stderr, "nl_sim: --payload must be %d..%d\n", NL_SIM_PAYLOAD_HDR,
                    NL_MAX_PAYLOAD);
            exit(2);
        }
        each_traffic(sc, set_payload, b);
    } else if (!strcmp(k, "burst")) {
        each_traffic(sc, set_burst, u32(k, v));
    } else if (!strcmp(k, "duration")) {
        sc->duration_us = seconds(k, v);
    } else if (!strcmp(k, "warmup")) {
        sc->warmup_us = seconds(k, v);
    } else if (!strcmp(k, "boot-spread")) {
        uint64_t s = seconds(k, v);
        for (uint8_t i = 0; i < sc->nodes; i++) {
            sc->node[i].boot_us = sc->nodes > 1 ? s * i / (uint64_t)(sc->nodes - 1u) : 0;
        }
    } else if (!strcmp(k, "seed")) {
        sc->seed = u32(k, v);
    } else if (!strcmp(k, "band")) {
        if (!strcmp(v, "subghz")) {
            p->band = NL_BAND_SUBGHZ;
        } else if (!strcmp(v, "2g4")) {
            p->band = NL_BAND_2G4;
        } else if (!strcmp(v, "dual")) {
            p->band = NL_BAND_DUAL;
        } else {
            fprintf(stderr, "nl_sim: --band subghz|2g4|dual\n");
            exit(2);
        }
    } else if (!strcmp(k, "policy")) {
        if (!strcmp(v, "immediate")) {
            p->tx_policy = NL_TX_IMMEDIATE;
        } else if (!strcmp(v, "in_slot")) {
            p->tx_policy = NL_TX_IN_SLOT;
        } else {
            fprintf(stderr, "nl_sim: --policy immediate|in_slot\n");
            exit(2);
        }
    } else if (!strcmp(k, "repeats")) {
        p->tx_repeats = u8(k, v);
    } else if (!strcmp(k, "dwell")) {
        p->dwell_us = u32(k, v);
    } else if (!strcmp(k, "repeat-interval")) {
        p->repeat_interval_us = u32(k, v);
    } else if (!strcmp(k, "repeat-jitter")) {
        p->repeat_jitter_us = u32(k, v);
    } else if (!strcmp(k, "discovery")) {
        p->discovery_interval_us = u32(k, v);
    } else if (!strcmp(k, "mgmt-hold")) {
        p->mgmt_hold_us = u32(k, v);
    } else if (!strcmp(k, "mgmt-repeats")) {
        p->mgmt_repeats = u8(k, v);
    } else if (!strcmp(k, "cca-backoff")) {
        p->cca_backoff_us = u32(k, v);
    } else if (!strcmp(k, "burst-extend")) {
        p->burst_extend_us = u32(k, v);
    } else if (!strcmp(k, "announce")) {
        sc->host.announce_interval_us = u32(k, v);
    } else if (!strcmp(k, "announce-jitter")) {
        sc->host.announce_jitter_us = u32(k, v);
    } else if (!strcmp(k, "announce-spread")) {
        sc->host.announce_boot_spread_us = u32(k, v);
    } else if (!strcmp(k, "announce-ramp")) {
        sc->host.announce_ramp_steps = u8(k, v);
    } else if (!strcmp(k, "poll")) {
        sc->host_poll_us = u32(k, v);
    } else if (!strcmp(k, "per")) {
        sc->per = num(k, v);
    } else if (!strcmp(k, "hidden")) {
        for (uint8_t i = 1; i < sc->nodes; i++) {
            for (uint8_t j = 1; j < sc->nodes; j++) {
                if ((i % 2) != (j % 2)) {
                    sc->link_loss[i][j] = 1.0;
                }
            }
        }
    } else if (!strcmp(k, "bitrate")) {
        sc->phy[NL_BAND_SUBGHZ].bitrate_bps = u32(k, v);
    } else if (!strcmp(k, "bitrate24")) {
        sc->phy[NL_BAND_2G4].bitrate_bps = u32(k, v);
    } else if (!strcmp(k, "turnaround")) {
        sc->phy[0].turnaround_us = sc->phy[1].turnaround_us = u32(k, v);
    } else if (!strcmp(k, "spi-fault")) {
        sc->spi_fault_rate = num(k, v);
    } else if (!strcmp(k, "no-wake-on-push")) {
        sc->wake_on_push = false;
    } else if (!strcmp(k, "no-finish-rx")) {
        sc->finish_rx = false;
    } else if (!strcmp(k, "spi-deferred")) {
        sc->spi_deferred = true;
    } else if (!strcmp(k, "radio-loop-us")) {
        sc->radio_loop_us = u32(k, v);
    } else if (!strcmp(k, "spi-hz")) {
        sc->spi_hz = u32(k, v);
    } else if (!strcmp(k, "spi-read-retries")) {
        sc->spi_read_retries = u8(k, v);
    } else if (!strcmp(k, "tick")) {
        sc->tick_us = u32(k, v);
    } else {
        return 0;
    }
    return 1;
}

static bool is_flag(const char *k)
{
    return !strcmp(k, "hidden") || !strcmp(k, "no-wake-on-push") ||
           !strcmp(k, "no-finish-rx") || !strcmp(k, "spi-deferred") ||
           !strcmp(k, "csv") ||
           !strcmp(k, "help");
}

static void build(nl_sim_scenario_t *sc, const opt_t *opts, int nopts, const char *skey,
                  const char *sval)
{
    base_t b = {4, 3, "broadcast"};
    for (int i = 0; i <= nopts; i++) {
        const char *k = i < nopts ? opts[i].key : skey;
        const char *v = i < nopts ? opts[i].val : sval;
        if (k == NULL) {
            continue;
        }
        if (!strcmp(k, "nodes")) {
            b.nodes = u8(k, v);
        } else if (!strcmp(k, "zones")) {
            b.zones = u8(k, v);
        } else if (!strcmp(k, "preset")) {
            b.preset = v;
        }
    }
    if (b.nodes < 1 || b.nodes > NL_SIM_MAX_NODES || b.zones < 1 ||
        b.zones >= NL_NUM_ZONES) {
        fprintf(stderr, "nl_sim: --nodes 1..8, --zones 1..7\n");
        exit(2);
    }
    build_base(sc, &b);
    for (int i = 0; i < nopts; i++) {
        apply(sc, opts[i].key, opts[i].val);
    }
    if (skey != NULL) {
        apply(sc, skey, sval);
    }
}

typedef struct {
    nl_sim_result_t sum;
    double p50, p90, p99;
    uint32_t worst_p99, max;
    int64_t worst_discovery;
    bool never_discovered;
    double util;
    int runs;
} pooled_t;

static void pool(pooled_t *pl, const nl_sim_result_t *r)
{
    nl_sim_result_t *s = &pl->sum;
    s->sent += r->sent;
    s->send_failed += r->send_failed;
    s->expected += r->expected;
    s->delivered += r->delivered;
    s->duplicates += r->duplicates;
    s->reordered += r->reordered;
    s->air_tx += r->air_tx;
    s->air_rx_ok += r->air_rx_ok;
    s->air_collided += r->air_collided;
    s->air_missed += r->air_missed;
    s->air_lost += r->air_lost;
    s->air_deferred += r->air_deferred;
    s->radio_tx_dropped += r->radio_tx_dropped;
    s->radio_rx_dropped += r->radio_rx_dropped;
    s->spi_errors += r->spi_errors;
    s->spi_transactions += r->spi_transactions;
    s->spi_read_retries += r->spi_read_retries;
    s->spi_overruns += r->spi_overruns;
    s->spi_reply_busy += r->spi_reply_busy;
    pl->p50 += r->lat_p50_us;
    pl->p90 += r->lat_p90_us;
    pl->p99 += r->lat_p99_us;
    if (r->lat_p99_us > pl->worst_p99) {
        pl->worst_p99 = r->lat_p99_us;
    }
    if (r->lat_max_us > pl->max) {
        pl->max = r->lat_max_us;
    }
    if (r->discovery_us < 0) {
        pl->never_discovered = true;
    } else if (r->discovery_us > pl->worst_discovery) {
        pl->worst_discovery = r->discovery_us;
    }
    if (r->busiest_channel_util > pl->util) {
        pl->util = r->busiest_channel_util;
    }
    pl->runs++;
}

int main(int argc, char **argv)
{
    opt_t opts[MAX_OPTS];
    int nopts = 0, runs = 1;
    bool csv = false;
    const char *sweep = NULL;
    double expect_delivery = -1, expect_p99_ms = -1, expect_disc_ms = -1;

    for (int i = 1; i < argc; i++) {
        if (strncmp(argv[i], "--", 2) != 0) {
            fprintf(stderr, "nl_sim: unexpected argument '%s'\n", argv[i]);
            return 2;
        }
        const char *k = argv[i] + 2;
        const char *v = "";
        if (!is_flag(k)) {
            if (i + 1 >= argc) {
                fprintf(stderr, "nl_sim: --%s needs a value\n", k);
                return 2;
            }
            v = argv[++i];
        }
        if (!strcmp(k, "help")) {
            usage();
            return 0;
        } else if (!strcmp(k, "csv")) {
            csv = true;
        } else if (!strcmp(k, "sweep")) {
            sweep = v;
        } else if (!strcmp(k, "runs")) {
            runs = (int)u32(k, v);
        } else if (!strcmp(k, "expect-delivery")) {
            expect_delivery = num(k, v);
        } else if (!strcmp(k, "expect-p99-ms")) {
            expect_p99_ms = num(k, v);
        } else if (!strcmp(k, "expect-discovery-ms")) {
            expect_disc_ms = num(k, v);
        } else if (nopts < MAX_OPTS) {
            nl_sim_scenario_t probe;
            nl_sim_scenario_default(&probe, 1);
            if (!apply(&probe, k, v)) {
                fprintf(stderr, "nl_sim: unknown option --%s (see --help)\n", k);
                return 2;
            }
            opts[nopts].key = k;
            opts[nopts].val = v;
            nopts++;
        }
    }
    if (runs < 1) {
        runs = 1;
    }

    /* Split "key=v1,v2,..." into values. */
    char sweep_buf[512];
    const char *skey = "";
    const char *svals[MAX_SWEEP];
    int nvals = 0;
    if (sweep != NULL) {
        snprintf(sweep_buf, sizeof(sweep_buf), "%s", sweep);
        char *eq = strchr(sweep_buf, '=');
        if (eq == NULL || eq == sweep_buf) {
            fprintf(stderr, "nl_sim: --sweep KEY=V1,V2,...\n");
            return 2;
        }
        *eq = '\0';
        skey = sweep_buf;
        for (char *tok = strtok(eq + 1, ","); tok && nvals < MAX_SWEEP;
             tok = strtok(NULL, ",")) {
            svals[nvals++] = tok;
        }
    }
    if (nvals == 0) {
        svals[nvals++] = NULL;
    }

    if (csv) {
        printf("%s%sruns,sent,expected,delivered,delivery,duplicates,reordered,"
               "p50_us,p90_us,p99_us,max_us,air_tx,collided,missed,lost,"
               "busiest_util,txq_drops,rxq_drops,spi_errors,discovery_us,deferred,"
               "spi_transactions,spi_read_retries,spi_overruns,spi_reply_busy\n",
               sweep ? skey : "", sweep ? "," : "");
    } else {
        printf("%-12s %9s %8s %8s %8s %8s %8s %7s %7s %7s %6s %9s\n",
               sweep ? skey : "config", "delivery", "p50 ms", "p90 ms", "p99 ms", "max ms",
               "collide", "missed", "defer", "load%", "txdrop", "disc ms");
    }

    int status = 0;
    for (int s = 0; s < nvals; s++) {
        pooled_t pl;
        memset(&pl, 0, sizeof(pl));
        for (int run = 0; run < runs; run++) {
            nl_sim_scenario_t sc;
            build(&sc, opts, nopts, svals[s] ? skey : NULL, svals[s]);
            sc.seed += (uint32_t)run * 7919u;
            nl_sim_result_t r;
            if (nl_sim_run(&sc, &r) != NL_OK) {
                fprintf(stderr, "nl_sim: invalid scenario\n");
                return 2;
            }
            pool(&pl, &r);
        }
        const nl_sim_result_t *t = &pl.sum;
        double delivery = t->expected ? (double)t->delivered / (double)t->expected : 1.0;
        double n = (double)pl.runs;
        long long disc = pl.never_discovered ? -1 : (long long)pl.worst_discovery;
        const char *label = svals[s] ? svals[s] : "-";
        if (csv) {
            printf("%s%s%d,%llu,%llu,%llu,%.6f,%llu,%llu,%.0f,%.0f,%.0f,%u,%llu,%llu,%llu,"
                   "%llu,%.4f,%u,%u,%u,%lld,%llu,%u,%u,%u,%u\n",
                   sweep ? label : "", sweep ? "," : "", pl.runs,
                   (unsigned long long)t->sent, (unsigned long long)t->expected,
                   (unsigned long long)t->delivered, delivery,
                   (unsigned long long)t->duplicates, (unsigned long long)t->reordered,
                   pl.p50 / n, pl.p90 / n, pl.p99 / n, pl.max,
                   (unsigned long long)t->air_tx, (unsigned long long)t->air_collided,
                   (unsigned long long)t->air_missed, (unsigned long long)t->air_lost,
                   pl.util, t->radio_tx_dropped, t->radio_rx_dropped, t->spi_errors, disc,
                   (unsigned long long)t->air_deferred, t->spi_transactions,
                   t->spi_read_retries, t->spi_overruns, t->spi_reply_busy);
        } else {
            char dbuf[16];
            if (disc < 0) {
                snprintf(dbuf, sizeof(dbuf), "never");
            } else {
                snprintf(dbuf, sizeof(dbuf), "%.1f", (double)disc / 1000.0);
            }
            printf("%-12s %8.2f%% %8.2f %8.2f %8.2f %8.2f %8llu %7llu %7llu %7.1f %6u %9s\n",
                   label, 100.0 * delivery, pl.p50 / n / 1000.0, pl.p90 / n / 1000.0,
                   pl.p99 / n / 1000.0, pl.max / 1000.0,
                   (unsigned long long)t->air_collided, (unsigned long long)t->air_missed,
                   (unsigned long long)t->air_deferred, 100.0 * pl.util,
                   t->radio_tx_dropped, dbuf);
            if (t->spi_overruns != 0 || t->spi_read_retries != 0 ||
                t->spi_reply_busy != 0) {
                double tr = t->spi_transactions ? (double)t->spi_transactions : 1.0;
                printf("%-12s spi: %u transactions, re-reads %u (%.2f%%), overruns %u "
                       "(%.3f%%), reply busy %u, errors %u\n",
                       "", t->spi_transactions, t->spi_read_retries,
                       100.0 * t->spi_read_retries / tr, t->spi_overruns,
                       100.0 * t->spi_overruns / tr, t->spi_reply_busy, t->spi_errors);
            }
        }
        if (expect_delivery >= 0 && delivery < expect_delivery) {
            fprintf(stderr, "nl_sim: %s: delivery %.4f < %.4f\n", label, delivery,
                    expect_delivery);
            status = 1;
        }
        if (expect_p99_ms >= 0 && pl.worst_p99 > expect_p99_ms * 1000.0) {
            fprintf(stderr, "nl_sim: %s: p99 %.2f ms > %.2f ms\n", label,
                    pl.worst_p99 / 1000.0, expect_p99_ms);
            status = 1;
        }
        if (expect_disc_ms >= 0 &&
            (disc < 0 || (double)disc > expect_disc_ms * 1000.0)) {
            fprintf(stderr, "nl_sim: %s: discovery %s\n", label,
                    disc < 0 ? "never completed" : "too slow");
            status = 1;
        }
    }
    return status;
}
