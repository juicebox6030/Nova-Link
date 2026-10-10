#include "nl_test.h"

#include "nl_sim.h"

#include <stdlib.h>

static nl_sim_t *sim_new(const nl_sim_scenario_t *sc)
{
    nl_sim_t *sim = malloc(nl_sim_size());
    CHECK(sim != NULL);
    CHECK_EQ(nl_sim_init(sim, sc), NL_OK);
    return sim;
}

static void test_airtime(void)
{
    nl_sim_phy_t phy;
    nl_sim_phy_default(&phy, NL_BAND_SUBGHZ);
    /* 4 preamble + 4 sync + 1 length + 2 CRC + 2 header + 32 payload = 45 B
     * at 200 kbps. */
    CHECK_EQ(nl_sim_airtime_us(&phy, 34), 1800);
    CHECK_EQ(nl_sim_airtime_us(&phy, NL_MAX_FRAGMENT), 4520);
    nl_sim_phy_default(&phy, NL_BAND_2G4);
    CHECK_EQ(nl_sim_airtime_us(&phy, 34), 1440);
}

static void test_two_nodes_clean(void)
{
    nl_sim_scenario_t sc;
    nl_sim_scenario_default(&sc, 2);
    nl_sim_result_t r;
    CHECK_EQ(nl_sim_run(&sc, &r), NL_OK);
    CHECK(r.sent > 100);
    CHECK_EQ(r.expected, r.sent);
    /* Not 100%: a device cannot hear while it sends its own zone 0 train. */
    CHECK((double)r.delivered >= 0.97 * (double)r.expected);
    CHECK_EQ(r.duplicates, 0);
    CHECK_EQ(r.spi_errors, 0);
    CHECK_EQ(r.radio_tx_dropped, 0);
    CHECK(r.discovery_us >= 0 && r.discovery_us < 1000000);
    /* At least one packet's airtime (1.8 ms) plus host polling. */
    CHECK(r.lat_p50_us >= 1800);
    CHECK(r.lat_p99_us < 40000);
}

static void test_deterministic(void)
{
    nl_sim_scenario_t sc;
    nl_sim_scenario_default(&sc, 3);
    sc.duration_us = 2000000;
    sc.per = 0.2;
    nl_sim_result_t a, b, c;
    nl_sim_run(&sc, &a);
    nl_sim_run(&sc, &b);
    CHECK_EQ(a.delivered, b.delivered);
    CHECK_EQ(a.air_tx, b.air_tx);
    CHECK_EQ(a.lat_max_us, b.lat_max_us);
    sc.seed = 99;
    nl_sim_run(&sc, &c);
    CHECK(c.air_tx != a.air_tx || c.lat_max_us != a.lat_max_us);
}

static void test_total_loss(void)
{
    nl_sim_scenario_t sc;
    nl_sim_scenario_default(&sc, 2);
    sc.duration_us = 2000000;
    sc.per = 1.0;
    nl_sim_result_t r;
    nl_sim_run(&sc, &r);
    CHECK(r.sent > 0);
    CHECK_EQ(r.delivered, 0);
    CHECK_EQ(r.air_rx_ok, 0);
    CHECK(r.air_lost > 0);
    CHECK_EQ(r.discovery_us, -1);
}

static void test_repeats_beat_loss(void)
{
    /* Independent 30% loss: 1 send would deliver 70% and 3 repeats 97%, less
     * the receptions missed while the receiver transmits (~60% and ~90%). */
    nl_sim_scenario_t sc;
    nl_sim_scenario_default(&sc, 2);
    sc.per = 0.3;
    nl_sim_result_t one, three;
    sc.params.tx_repeats = 1;
    nl_sim_run(&sc, &one);
    sc.params.tx_repeats = 3;
    nl_sim_run(&sc, &three);
    double d1 = (double)one.delivered / (double)one.expected;
    double d3 = (double)three.delivered / (double)three.expected;
    CHECK(d1 > 0.45 && d1 < 0.75);
    CHECK(d3 > 0.82);
    CHECK(d3 > d1 + 0.2);
}

static void test_hidden_terminal(void)
{
    nl_sim_scenario_t sc;
    nl_sim_scenario_default(&sc, 3);
    sc.duration_us = 3000000;
    sc.link_loss[1][2] = sc.link_loss[2][1] = 1.0;
    nl_sim_t *sim = sim_new(&sc);
    nl_sim_advance(sim, sc.duration_us);
    CHECK_EQ(nl_sim_flow_delivered(sim, 1, 2), 0);
    CHECK_EQ(nl_sim_flow_delivered(sim, 2, 1), 0);
    CHECK(nl_sim_flow_delivered(sim, 0, 1) > 0);
    CHECK(nl_sim_flow_delivered(sim, 2, 0) > 0);
    /* Devices 1 and 2 never learn of each other: there is no relaying. */
    CHECK(nl_host_peer(nl_sim_host(sim, 1), 2) == NULL);
    CHECK(nl_host_peer(nl_sim_host(sim, 0), 2) != NULL);
    nl_sim_result_t r;
    nl_sim_result(sim, &r);
    CHECK_EQ(r.discovery_us, -1);
    free(sim);
}

static void test_collisions_counted(void)
{
    /* Eight talkers on one channel at 50 Hz with 100-byte payloads offer
     * 8 x 50 x 4.5 ms = 1.8 Erlang of first transmissions alone: listen
     * before talk cannot prevent collisions at that load. */
    nl_sim_scenario_t sc;
    nl_sim_scenario_default(&sc, 8);
    sc.duration_us = 2000000;
    for (int i = 0; i < 8; i++) {
        sc.node[i].traffic[0].period_us = 20000;
        sc.node[i].traffic[0].payload_len = 100;
    }
    nl_sim_result_t r;
    nl_sim_run(&sc, &r);
    CHECK(r.air_collided > 0);
    CHECK(r.busiest_channel_util > 0.5);
    CHECK(r.delivered < r.expected);
}

static void test_spi_faults_survived(void)
{
    nl_sim_scenario_t sc;
    nl_sim_scenario_default(&sc, 2);
    sc.duration_us = 4000000;
    sc.spi_fault_rate = 0.05; /* the link is mostly idle: few transfers to hit */
    nl_sim_result_t r;
    nl_sim_run(&sc, &r);
    CHECK(r.spi_errors > 0);
    /* Push and config retries absorb corruption; a corrupted pull response
     * loses that fragment (pulls are not retried), so allow a little loss. */
    CHECK((double)r.delivered >= 0.9 * (double)r.expected);
    CHECK_EQ(r.duplicates, 0);
}

static void test_late_boot_counts(void)
{
    /* A device that boots after the warm-up only counts from its boot on. */
    nl_sim_scenario_t sc;
    nl_sim_scenario_default(&sc, 3);
    sc.duration_us = 3000000;
    sc.node[2].boot_us = 2000000;
    sc.node[2].traffic[0].zone = 0;
    nl_sim_result_t r;
    nl_sim_run(&sc, &r);
    CHECK(r.expected > r.sent);       /* node 2 adds receptions once up */
    CHECK(r.expected < 2u * r.sent);  /* ...but not for the first 2 s */
    CHECK((double)r.delivered >= 0.97 * (double)r.expected);
}

static void test_spi_deferred(void)
{
    /* ISR handoff + main-loop poll: replies come late and the host re-reads,
     * but within its read window (5 x 50 us) nothing is lost. */
    nl_sim_scenario_t sc;
    nl_sim_scenario_default(&sc, 2);
    sc.duration_us = 4000000;
    sc.spi_deferred = true;
    nl_sim_result_t r;
    nl_sim_run(&sc, &r);
    CHECK(r.spi_transactions > 0);
    CHECK(r.spi_read_retries > 0);
    CHECK_EQ(r.spi_errors, 0);
    CHECK_EQ(r.spi_overruns, 0);
    CHECK_EQ(r.spi_reply_busy, 0);
    CHECK((double)r.delivered >= 0.97 * (double)r.expected);

    /* A main loop slower than the read window loses replies... */
    sc.radio_loop_us = 2000;
    nl_sim_run(&sc, &r);
    CHECK(r.spi_errors > 0);
    CHECK((double)r.delivered < 0.9 * (double)r.expected);

    /* ...until the window covers it again. */
    sc.spi_read_retries = 40;
    nl_sim_run(&sc, &r);
    CHECK_EQ(r.spi_errors, 0);
    CHECK((double)r.delivered >= 0.97 * (double)r.expected);
}

int main(void)
{
    RUN(test_airtime);
    RUN(test_two_nodes_clean);
    RUN(test_deterministic);
    RUN(test_total_loss);
    RUN(test_repeats_beat_loss);
    RUN(test_hidden_terminal);
    RUN(test_collisions_counted);
    RUN(test_spi_faults_survived);
    RUN(test_late_boot_counts);
    RUN(test_spi_deferred);
    return nl_test_finish();
}
