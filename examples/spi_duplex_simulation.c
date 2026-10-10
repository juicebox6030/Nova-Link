/* SPDX-License-Identifier: GPL-3.0-only */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/spi_virtual.h"
#include "nova_link/multiverse_plugin.h"

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(EXIT_FAILURE); } } while (0)
#define OK(x) CHECK((x) == NL_OK)
#define MV(x, result) CHECK((x) == (result))
#define HISTORY_CAPACITY 128u
#define STEP_US UINT64_C(100)
#define LOSS_US UINT64_C(200000)

typedef struct {
    nl_host host;
    nl_radio radio;
    nl_spi_slave slave;
    nl_spi_virtual wire;
    nl_spi_backend spi;
    nl_radio_link link;
    nl_multiverse_context tx, rx;
    nl_module modules[4];
    const nl_module *manifest[4];
    nl_module_instance instances[4];
    nova_dmx_frame_t history[HISTORY_CAPACITY];
    size_t history_count, max_tx, max_rx;
    uint64_t checked_frames;
    size_t last_snapshot;
    unsigned distinct_snapshots;
} node;

static void initialize(node *n, uint8_t origin, uint8_t tx_zone, uint8_t rx_zone)
{
    nl_spi_driver driver;
    nl_radio_link_config link_config;
    nl_multiverse_config config = {.role = NL_MULTIVERSE_TX,
        .zone = tx_zone, .universe = tx_zone, .session = tx_zone,
        .interval_us = 10000, .full_interval_us = 40000,
        .chunks_per_tick = 8};
    memset(n, 0, sizeof(*n));
    OK(nl_host_init_plugins(&n->host, origin, 0));
    OK(nl_radio_init(&n->radio, (uint8_t)((1u << tx_zone) | (1u << rx_zone)),
        300, 0, 0));
    OK(nl_spi_slave_init(&n->slave, &n->radio));
    OK(nl_spi_virtual_init(&n->wire, &n->slave, 300));
    driver = nl_spi_virtual_driver(&n->wire);
    OK(nl_spi_backend_init(&n->spi, &driver));
    OK(nl_spi_backend_link_config(&n->spi, 2, &link_config));
    OK(nl_radio_link_init(&n->link, &link_config));
    MV(nl_multiverse_init(&n->tx, &config), NOVA_MV_OK);
    config.role = NL_MULTIVERSE_RX;
    config.zone = rx_zone;
    config.universe = rx_zone;
    config.session = rx_zone;
    config.peer_origin = origin == 1u ? 2u : 1u;
    config.loss_timeout_us = LOSS_US;
    config.assembly_timeout_us = 100000;
    MV(nl_multiverse_init(&n->rx, &config), NOVA_MV_OK);
    n->modules[0] = nl_multiverse_module(&n->tx);
    n->modules[0].name = "dmx-tx";
    n->modules[1] = nl_multiverse_module(&n->rx);
    n->modules[1].name = "dmx-rx";
    n->modules[2] = nl_spi_backend_link_module(&n->link);
    n->modules[3] = nl_spi_backend_module(&n->spi);
    for (size_t i = 0; i < 4u; ++i) n->manifest[i] = &n->modules[i];
    /* Use every production hook unchanged, including periodic TX refresh. */
    OK(nl_modules_start(&n->host, n->manifest, n->instances, 4));
}

static void submit(node *n)
{
    nova_dmx_frame_t *frame;
    CHECK(n->history_count < HISTORY_CAPACITY);
    frame = &n->history[n->history_count];
    frame->slot_count = NOVA_DMX_MAX_SLOTS;
    for (unsigned i = 0; i < NOVA_DMX_MAX_SLOTS; ++i)
        frame->slots[i] = (uint8_t)(n->history_count * (i % 11u + 1u) +
            i * 73u + n->host.origin * 101u);
    ++n->history_count;
    MV(nl_multiverse_submit(&n->tx, frame), NOVA_MV_OK);
}

static bool same_frame(const nova_dmx_frame_t *a, const nova_dmx_frame_t *b)
{
    return a->slot_count == b->slot_count &&
        memcmp(a->slots, b->slots, a->slot_count) == 0;
}

static void check_received(node *receiver, const node *sender, uint64_t now)
{
    nova_dmx_frame_t frame;
    size_t matched;
    if (receiver->rx.rx.stats.frames == receiver->checked_frames) return;
    /* One completed SPI response per poll can commit at most one DMX state. */
    CHECK(receiver->rx.rx.stats.frames == receiver->checked_frames + 1u);
    MV(nl_multiverse_get(&receiver->rx, now, &frame), NOVA_MV_FRAME_READY);
    for (matched = 0; matched < sender->history_count; ++matched)
        if (same_frame(&frame, &sender->history[matched])) break;
    CHECK(matched < sender->history_count);
    if (receiver->checked_frames != 0u) CHECK(matched >= receiver->last_snapshot);
    if (receiver->checked_frames == 0u || matched != receiver->last_snapshot)
        ++receiver->distinct_snapshots;
    receiver->last_snapshot = matched;
    ++receiver->checked_frames;
}

static void air_step(nl_spi_virtual_air *air, node *sender, node *receiver,
                     uint64_t now, bool connected)
{
    nl_status status = nl_spi_virtual_air_step(air, &sender->radio,
        &receiver->radio, now, connected);
    CHECK(status == NL_OK || status == NL_ERR_EMPTY || status == NL_ERR_BUSY ||
        status == NL_ERR_FULL);
    CHECK(air->rejected == 0u);
}

static void poll_pair(node *a, node *b, nl_spi_virtual_air air[2],
                      uint64_t now, bool connected)
{
    OK(nl_host_poll(&a->host, now));
    OK(nl_host_poll(&b->host, now));
    air_step(&air[0], a, b, now, connected);
    air_step(&air[1], b, a, now, connected);
    check_received(a, b, now);
    check_received(b, a, now);
    for (unsigned i = 0; i < 2u; ++i) {
        node *n = i == 0u ? a : b;
        size_t tx_count = n->radio.tx[n->tx.config.zone].count;
        CHECK(tx_count <= NL_RADIO_TX_DEPTH && n->radio.rx.count <= NL_RADIO_RX_DEPTH);
        if (tx_count > n->max_tx) n->max_tx = tx_count;
        if (n->radio.rx.count > n->max_rx) n->max_rx = n->radio.rx.count;
    }
}

static bool drained(const node *n)
{
    return !n->spi.tx_pending && !n->spi.inflight && !n->spi.rx_pending &&
        !n->spi.abort_pending && !n->link.pending && n->radio.rx.count == 0u &&
        n->radio.tx[n->tx.config.zone].count == 0u && nl_spi_virtual_drained(&n->wire);
}

static void exact_latest(node *receiver, const node *sender, uint64_t now)
{
    nova_dmx_frame_t frame;
    MV(nl_multiverse_get(&receiver->rx, now, &frame), NOVA_MV_FRAME_READY);
    CHECK(same_frame(&frame, &sender->history[sender->history_count - 1u]));
}

int main(void)
{
    static node a, b;
    nl_spi_virtual_air air[2];
    uint64_t now, resumed_frames[2], silence_frames[2], silence_start;
    initialize(&a, 1, 2, 3);
    initialize(&b, 2, 3, 2);
    OK(nl_spi_virtual_air_init(&air[0], 200));
    OK(nl_spi_virtual_air_init(&air[1], 200));
    for (now = 0; now < 200000u; now += STEP_US) {
        if (now % 10000u == 0u) { submit(&a); submit(&b); }
        poll_pair(&a, &b, air, now, true);
    }
    CHECK(a.distinct_snapshots > 5u && b.distinct_snapshots > 5u);
    CHECK(a.spi.stats.tx_completed > 0u && a.spi.stats.rx_committed > 0u);
    CHECK(b.spi.stats.tx_completed > 0u && b.spi.stats.rx_committed > 0u);

    /* Keep production refresh running while both logical air paths stall. */
    for (; now < 240000u; now += STEP_US) {
        if (now % 5000u == 0u) { submit(&a); submit(&b); }
        poll_pair(&a, &b, air, now, false);
    }
    CHECK(a.max_tx == NL_RADIO_TX_DEPTH && b.max_tx == NL_RADIO_TX_DEPTH);
    CHECK(a.tx.stats.backpressure > 0u && b.tx.stats.backpressure > 0u);

    /* B continues TX and RX while A's physical-driver model is disconnected.
     * A's RX FIFO fills, then B retains its frozen air head under congestion. */
    nl_spi_virtual_set_connected(&a.wire, false);
    for (; now < 400000u; now += STEP_US) {
        if (now % 10000u == 0u) { submit(&a); submit(&b); }
        poll_pair(&a, &b, air, now, true);
    }
    CHECK(a.max_rx == NL_RADIO_RX_DEPTH);
    CHECK(a.wire.stats.offline > 0u && air[1].blocked > 0u);
    CHECK(a.tx.tx.stats.coalesced > 0u && b.tx.tx.stats.coalesced > 0u);
    resumed_frames[0] = a.checked_frames;
    resumed_frames[1] = b.checked_frames;
    nl_spi_virtual_set_connected(&a.wire, true);
    nl_spi_virtual_fail_commits(&a.wire, 3);
    nl_spi_virtual_fail_commits(&b.wire, 2);
    submit(&a);
    submit(&b);
    /* Stop changing source levels; periodic production FULLs recover both ways. */
    for (; now < 700000u; now += STEP_US) poll_pair(&a, &b, air, now, true);
    CHECK(a.checked_frames > resumed_frames[0] && b.checked_frames > resumed_frames[1]);
    exact_latest(&a, &b, now);
    exact_latest(&b, &a, now);
    CHECK(a.wire.stats.commit_retries == 3u && b.wire.stats.commit_retries == 2u);

    /* Shut down only the producers through their ordinary module lifecycle;
     * leave RX and SPI services polling while already accepted work drains. */
    OK(nl_modules_stop(&a.instances[0], 1));
    OK(nl_modules_stop(&b.instances[0], 1));
    {
        uint64_t deadline = now + 100000u;
        while (!drained(&a) || !drained(&b) || air[0].pending || air[1].pending) {
            CHECK(now < deadline);
            poll_pair(&a, &b, air, now, true);
            now += STEP_US;
        }
    }
    silence_start = now;
    exact_latest(&a, &b, now);
    exact_latest(&b, &a, now);
    silence_frames[0] = a.checked_frames;
    silence_frames[1] = b.checked_frames;
    for (; now <= silence_start + LOSS_US + STEP_US; now += STEP_US)
        poll_pair(&a, &b, air, now, true);
    CHECK(a.checked_frames == silence_frames[0] && b.checked_frames == silence_frames[1]);
    CHECK(a.rx.rx.link == NOVA_MV_LOST && b.rx.rx.link == NOVA_MV_LOST);
    for (unsigned i = 0; i < 2u; ++i) {
        node *n = i == 0u ? &a : &b;
        nova_dmx_frame_t untouched, frame;
        memset(&untouched, 0xA5, sizeof(untouched));
        frame = untouched;
        MV(nl_multiverse_get(&n->rx, now, &frame), NOVA_MV_NEED_FULL);
        CHECK(memcmp(&frame, &untouched, sizeof(frame)) == 0);
        CHECK(n->link.stats.rx_delivered == n->wire.stats.commits);
        CHECK(n->link.stats.rx_discarded == 0u && n->rx.stats.bad_payloads == 0u);
        OK(nl_modules_stop(n->instances, 4));
    }
    printf("Duplex virtual SPI: %" PRIu64 "/%" PRIu64 " exact 512-level frames; "
        "%u/%u distinct snapshots; TX FIFO peaks %zu/%zu; RX FIFO peaks %zu/%zu.\n",
        a.checked_frames, b.checked_frames, a.distinct_snapshots, b.distinct_snapshots,
        a.max_tx, b.max_tx, a.max_rx, b.max_rx);
    puts("Unchanged production ticks, simultaneous TX/RX, periodic FULL recovery, coalescing, FIFO pressure, commit retries and silence loss passed.");
    puts("Two independent logical air directions; no measured RF capacity, physical SPI timing or proprietary Multiverse compatibility claim.");
    return EXIT_SUCCESS;
}
