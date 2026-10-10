/* SPDX-License-Identifier: GPL-3.0-only */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/spi_virtual.h"
#include "nova_link/counter_plugin.h"
#include "nova_link/multiverse_plugin.h"

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(EXIT_FAILURE); } } while (0)
#define OK(x) CHECK((x) == NL_OK)
#define MV(x, result) CHECK((x) == (result))

typedef struct {
    nl_host host;
    nl_radio radio;
    nl_spi_slave slave;
    nl_spi_virtual wire;
    nl_spi_backend spi;
    nl_radio_link link;
    nl_counter_context counter;
    nl_multiverse_context dmx;
    nl_module descriptors[4];
    const nl_module *manifest[4];
    nl_module_instance instances[4];
} node;

static void (*dmx_tick)(nl_host *, nl_plugin_id, uint64_t, void *);
static bool dmx_production;

/* The scenario schedules snapshots explicitly and suppresses idle refreshes
 * while draining queues. RX deadlines still tick on every host poll. */
static void scheduled_dmx_tick(nl_host *host, nl_plugin_id id, uint64_t now, void *context)
{
    nl_multiverse_context *dmx = context;
    if (dmx->config.role == NL_MULTIVERSE_RX || dmx_production)
        dmx_tick(host, id, now, context);
}

static bool needs_dmx(const node *n)
{
    return n->dmx.tx.has_desired && (!n->dmx.tx.has_baseline || n->dmx.tx.active ||
        n->dmx.tx.force_full || n->dmx.tx.desired.slot_count != n->dmx.tx.baseline.slot_count ||
        memcmp(n->dmx.tx.desired.slots, n->dmx.tx.baseline.slots, n->dmx.tx.desired.slot_count) != 0);
}

static void initialize(node *n, bool tx, uint32_t session)
{
    nl_spi_driver driver;
    nl_radio_link_config link;
    nl_multiverse_config config = {.role = tx ? NL_MULTIVERSE_TX : NL_MULTIVERSE_RX,
        .zone = 2, .peer_origin = 1, .universe = 1, .session = session,
        .interval_us = 1000, .full_interval_us = 10000000,
        .loss_timeout_us = 5000000, .assembly_timeout_us = 5000000,
        .chunks_per_tick = 8};
    memset(n, 0, sizeof(*n));
    OK(nl_host_init_plugins(&n->host, tx ? 1u : 2u, 0));
    OK(nl_radio_init(&n->radio, 6, 1000, 0, 0));
    OK(nl_spi_slave_init(&n->slave, &n->radio));
    OK(nl_spi_virtual_init(&n->wire, &n->slave, 400));
    driver = nl_spi_virtual_driver(&n->wire);
    OK(nl_spi_backend_init(&n->spi, &driver));
    OK(nl_spi_backend_link_config(&n->spi, 2, &link));
    OK(nl_radio_link_init(&n->link, &link));
    n->counter.zone = 1;
    n->counter.transmitter = tx;
    MV(nl_multiverse_init(&n->dmx, &config), NOVA_MV_OK);
    n->descriptors[0] = nl_multiverse_module(&n->dmx);
    dmx_tick = n->descriptors[0].hooks.tick;
    n->descriptors[0].hooks.tick = scheduled_dmx_tick;
    n->descriptors[1] = nl_counter_module(&n->counter);
    n->descriptors[2] = nl_spi_backend_link_module(&n->link);
    n->descriptors[3] = nl_spi_backend_module(&n->spi);
    for (size_t i = 0; i < 4; ++i) n->manifest[i] = &n->descriptors[i];
    OK(nl_modules_start(&n->host, n->manifest, n->instances, 4));
    n->counter.transmitter = false;
}

static void fill(nova_dmx_frame_t *f, unsigned update)
{
    f->slot_count = NOVA_DMX_MAX_SLOTS;
    for (unsigned i = 0; i < NOVA_DMX_MAX_SLOTS; ++i) f->slots[i] = (uint8_t)(update + i * 73u);
}

static void step(node *sender, node *receiver, nl_spi_virtual_air *air, uint64_t now, bool produce)
{
    nl_status status;
    dmx_production = produce && needs_dmx(sender);
    OK(nl_host_poll(&sender->host, now));
    status = nl_spi_virtual_air_step(air, &sender->radio, &receiver->radio, now, true);
    CHECK(status == NL_OK || status == NL_ERR_BUSY || status == NL_ERR_EMPTY || status == NL_ERR_FULL);
    CHECK(air->rejected == 0u);
    OK(nl_host_poll(&receiver->host, now));
    for (unsigned z = 1; z <= 2; ++z) CHECK(sender->radio.tx[z].count <= NL_RADIO_TX_DEPTH);
    CHECK(receiver->radio.rx.count <= NL_RADIO_RX_DEPTH);
}

static bool drained(const node *s, const node *r, const nl_spi_virtual_air *air)
{
    return !air->pending && !s->spi.tx_pending && !s->spi.inflight &&
        s->radio.tx[1].count == 0u && s->radio.tx[2].count == 0u &&
        r->radio.rx.count == 0u && !r->link.pending &&
        nl_spi_virtual_drained(&s->wire) && nl_spi_virtual_drained(&r->wire);
}

static void drain(node *s, node *r, nl_spi_virtual_air *air, uint64_t *now)
{
    uint64_t deadline = *now + 3000000;
    while (!drained(s, r, air) || needs_dmx(s)) {
        CHECK(*now < deadline);
        *now += 100;
        step(s, r, air, *now, true);
    }
}

static void exact(node *r, const nova_dmx_frame_t *want, uint64_t now)
{
    nova_dmx_frame_t got;
    MV(nl_multiverse_get(&r->dmx, now, &got), NOVA_MV_FRAME_READY);
    CHECK(got.slot_count == want->slot_count);
    CHECK(memcmp(got.slots, want->slots, want->slot_count) == 0);
}

int main(void)
{
    static node sender, receiver;
    nl_spi_virtual_air air;
    nova_dmx_frame_t desired = {0};
    nl_pull_token old_receipt;
    uint64_t now = 0, completed, begun, frames_before_restart;
    size_t max_tx = 0, max_rx = 0;
    initialize(&sender, true, 42);
    initialize(&receiver, false, 42);
    OK(nl_spi_virtual_air_init(&air, 300));
    fill(&desired, 0);
    MV(nl_multiverse_submit(&sender.dmx, &desired), NOVA_MV_OK);
    OK(nl_spi_virtual_fault_next(&sender.wire, NL_SPI_VIRTUAL_REQUEST_SHORT));
    step(&sender, &receiver, &air, now, true);
    CHECK(sender.spi.tx_pending && sender.radio.tx[2].count == 0u);
    drain(&sender, &receiver, &air, &now);
    exact(&receiver, &desired, now);
    CHECK(sender.wire.stats.malformed_requests == 1u && air.completed == 8u);

    /* Malformed encoded responses abort their receipt then retry the same head. */
    for (unsigned fault = NL_SPI_VIRTUAL_RESPONSE_SHORT; fault <= NL_SPI_VIRTUAL_RESPONSE_LENGTH; ++fault) {
        fill(&desired, fault);
        MV(nl_multiverse_submit(&sender.dmx, &desired), NOVA_MV_OK);
        OK(nl_spi_virtual_fault_next(&receiver.wire, (nl_spi_virtual_fault)fault));
        now += 1000;
        step(&sender, &receiver, &air, now, true);
        drain(&sender, &receiver, &air, &now);
        exact(&receiver, &desired, now);
    }
    CHECK(receiver.spi.stats.malformed == 2u && receiver.spi.stats.rx_aborted == 2u);

    /* A plausible native payload change is detectable only by the NLM1 CRC. */
    fill(&desired, 50);
    MV(nl_multiverse_submit(&sender.dmx, &desired), NOVA_MV_OK);
    OK(nl_spi_virtual_fault_next(&receiver.wire, NL_SPI_VIRTUAL_RESPONSE_PAYLOAD));
    now += 1000;
    step(&sender, &receiver, &air, now, true);
    drain(&sender, &receiver, &air, &now);
    CHECK(receiver.dmx.stats.bad_payloads == 1u);
    nl_multiverse_force_full(&sender.dmx);
    now += 1000;
    step(&sender, &receiver, &air, now, true);
    drain(&sender, &receiver, &air, &now);
    exact(&receiver, &desired, now);

    /* Identical host symptoms before slave acceptance require the same hold.
     * Here the scenario knows no enqueue occurred and explicitly permits retry. */
    fill(&desired, 55);
    MV(nl_multiverse_submit(&sender.dmx, &desired), NOVA_MV_OK);
    OK(nl_spi_virtual_fault_next(&sender.wire, NL_SPI_VIRTUAL_PUSH_UNCERTAIN_BEFORE_ACCEPT));
    completed = receiver.dmx.rx.stats.frames;
    {
        uint64_t deadline = now + 100000;
        do { CHECK(now < deadline); now += 100; step(&sender, &receiver, &air, now, true); } while (!sender.spi.tx_uncertain);
    }
    CHECK(sender.radio.tx[2].count == 0u && !air.pending);
    begun = sender.wire.stats.begins;
    for (unsigned i = 0; i < 50; ++i) { now += 100; step(&sender, &receiver, &air, now, true); }
    CHECK(sender.wire.stats.begins == begun && sender.spi.tx_uncertain);
    CHECK(receiver.dmx.rx.stats.frames == completed);
    OK(nl_spi_backend_resolve_tx(&sender.spi, true));
    drain(&sender, &receiver, &air, &now);
    exact(&receiver, &desired, now);

    /* Driver failure after radio acceptance has ambiguous completion: no retry. */
    fill(&desired, 60);
    MV(nl_multiverse_submit(&sender.dmx, &desired), NOVA_MV_OK);
    OK(nl_spi_virtual_fault_next(&sender.wire, NL_SPI_VIRTUAL_PUSH_UNCERTAIN));
    {
        uint64_t deadline = now + 100000;
        do { CHECK(now < deadline); now += 100; step(&sender, &receiver, &air, now, true); } while (!sender.spi.tx_uncertain);
    }
    begun = sender.wire.stats.begins;
    completed = air.completed;
    for (unsigned i = 0; i < 50; ++i) { now += 100; step(&sender, &receiver, &air, now, true); }
    CHECK(sender.wire.stats.begins == begun && sender.spi.tx_uncertain);
    CHECK(air.completed == completed || air.completed == completed + 1u);
    CHECK(nl_host_unregister(&sender.host, sender.spi.plugin) == NL_ERR_BUSY);
    OK(nl_spi_backend_resolve_tx(&sender.spi, false));
    drain(&sender, &receiver, &air, &now);
    exact(&receiver, &desired, now);

    /* Backpressure accumulates in actual radio queues while INT_READY remains true. */
    nl_spi_virtual_set_connected(&receiver.wire, false);
    for (unsigned i = 0; i < 600; ++i) {
        if (i % 20u == 0u) {
            fill(&desired, i + 100u);
            MV(nl_multiverse_submit(&sender.dmx, &desired), NOVA_MV_OK);
        }
        now += 100;
        step(&sender, &receiver, &air, now, true);
        if (sender.radio.tx[2].count > max_tx) max_tx = sender.radio.tx[2].count;
        if (receiver.radio.rx.count > max_rx) max_rx = receiver.radio.rx.count;
    }
    CHECK(max_tx == NL_RADIO_TX_DEPTH && max_rx == NL_RADIO_RX_DEPTH);
    CHECK(air.blocked != 0u && sender.dmx.stats.backpressure != 0u);
    CHECK(nl_radio_ready(&receiver.radio));
    nl_spi_virtual_set_connected(&receiver.wire, true);
    nl_spi_virtual_fail_commits(&receiver.wire, 3);
    drain(&sender, &receiver, &air, &now);
    nl_multiverse_force_full(&sender.dmx);
    now += 1000;
    step(&sender, &receiver, &air, now, true);
    drain(&sender, &receiver, &air, &now);
    exact(&receiver, &desired, now);
    CHECK(receiver.wire.stats.commit_retries == 3u);
    CHECK(receiver.link.stats.rx_delivered == receiver.wire.stats.commits);
    CHECK(receiver.link.stats.rx_discarded == 0u);

    sender.counter.transmitter = true;
    {
        uint64_t deadline = now + 1000000;
        while (sender.counter.next_value < 50u) { CHECK(now < deadline); now += 100; step(&sender, &receiver, &air, now, true); }
    }
    sender.counter.transmitter = false;
    drain(&sender, &receiver, &air, &now);
    CHECK(receiver.counter.deliveries == 50u && receiver.counter.last_value == 49u);
    old_receipt = receiver.slave.next_receipt - 1u;
    frames_before_restart = receiver.dmx.rx.stats.frames;
    CHECK(drained(&sender, &receiver, &air));
    OK(nl_modules_stop(sender.instances, 4));
    OK(nl_modules_stop(receiver.instances, 4));

    /* Drain, reset native sequence history separately, bind a new model epoch. */
    OK(nl_stream_reset_origin(&receiver.host.streams, 1));
    OK(nl_stream_reset_origin(&receiver.radio.streams, 1));
    {
        nl_multiverse_config config = receiver.dmx.config;
        config.session = 43;
        MV(nl_multiverse_init(&receiver.dmx, &config), NOVA_MV_OK);
        receiver.descriptors[0] = nl_multiverse_module(&receiver.dmx);
        receiver.descriptors[0].hooks.tick = scheduled_dmx_tick;
    }
    OK(nl_modules_start(&receiver.host, receiver.manifest, receiver.instances, 4));
    initialize(&sender, true, 43);
    fill(&desired, 999);
    MV(nl_multiverse_submit(&sender.dmx, &desired), NOVA_MV_OK);
    completed = air.completed;
    nl_spi_virtual_fail_commits(&receiver.wire, 1);
    now += 1000;
    step(&sender, &receiver, &air, now, true);
    {
        uint64_t deadline = now + 100000;
        while (!receiver.wire.retained) { CHECK(now < deadline); now += 100; step(&sender, &receiver, &air, now, true); }
    }
    CHECK(receiver.wire.receipt > old_receipt);
    {
        size_t count = receiver.radio.rx.count;
        nl_spi_driver driver = nl_spi_virtual_driver(&receiver.wire);
        CHECK(driver.settle(driver.context, old_receipt, true) == NL_ERR_STALE);
        CHECK(receiver.radio.rx.count == count && receiver.wire.retained);
    }
    drain(&sender, &receiver, &air, &now);
    exact(&receiver, &desired, now);
    CHECK(air.completed - completed == 8u && receiver.dmx.rx.sequence == 0u);
    OK(nl_modules_stop(sender.instances, 4));
    OK(nl_modules_stop(receiver.instances, 4));
    printf("Paired virtual SPI: 50 exact counters; %" PRIu64 " complete 512-level frames; TX/RX queue peaks %zu/%zu; %" PRIu64 " FIFO backpressure retries.\n",
        frames_before_restart + receiver.dmx.rx.stats.frames, max_tx, max_rx, air.blocked);
    puts("Actual host SPI service -> serialized AA/LEN frames -> actual slave -> native FIFO radios -> serialized PULL -> actual plugins.");
    puts("Delayed ownership, malformed request/response, application CRC corruption, uncertain PUSH before/after acceptance, explicit retry/discard, disconnect/reconnect, commit retries and explicit restart passed.");
    puts("Logical virtual C outcomes and local receipts; no physical SPI ACK/timing or proprietary Multiverse RF interoperability claim.");
    return EXIT_SUCCESS;
}
