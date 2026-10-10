/* SPDX-License-Identifier: GPL-3.0-only */
/* Deterministic adapter ownership exercise; all times are logical test times. */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/multiverse_plugin.h"
#include "nova_link/fault_backend.h"

#define CHECK(expression) do { if (!(expression)) { \
    fprintf(stderr, "line %d: %s\n", __LINE__, #expression); \
    exit(EXIT_FAILURE); } } while (0)
#define OK(expression) CHECK((expression) == NL_OK)
#define MV(expression, expected) CHECK((expression) == (expected))

typedef struct {
    nl_host host;
    nl_fault_backend adapter;
    nl_fault_adapter binding;
    nl_radio_link transport;
    nl_multiverse_context dmx;
    nl_module descriptors[2];
    const nl_module *manifest[2];
    nl_module_instance instances[2];
} node;

static void initialize(node *n, bool transmitter, uint32_t session)
{
    nl_multiverse_config config = {
        .role = transmitter ? NL_MULTIVERSE_TX : NL_MULTIVERSE_RX,
        .zone = 1, .peer_origin = 1, .universe = 1, .session = session,
        .interval_us = 1000, .full_interval_us = 1000000,
        .loss_timeout_us = 100000, .assembly_timeout_us = 100000,
        .chunks_per_tick = 8
    };
    nl_fault_options options;
    nl_radio_link_config transport_config;
    memset(n, 0, sizeof(*n));
    OK(nl_fault_profile_options(NL_FAULT_DELAYED, &options));
    OK(nl_fault_backend_init(&n->adapter, &options));
    OK(nl_fault_adapter_init(&n->binding, &n->adapter, 2));
    transport_config = nl_fault_adapter_link_config(&n->binding);
    OK(nl_host_init_plugins(&n->host, transmitter ? 1u : 2u, 0));
    OK(nl_radio_link_init(&n->transport, &transport_config));
    MV(nl_multiverse_init(&n->dmx, &config), NOVA_MV_OK);
    n->descriptors[0] = nl_multiverse_module(&n->dmx);
    n->descriptors[1] = nl_radio_link_module(&n->transport);
    n->manifest[0] = &n->descriptors[0];
    n->manifest[1] = &n->descriptors[1];
    OK(nl_modules_start(&n->host, n->manifest, n->instances, 2));
}

static void fill(nova_dmx_frame_t *frame, unsigned update)
{
    frame->slot_count = NOVA_DMX_MAX_SLOTS;
    for (unsigned i = 0; i < NOVA_DMX_MAX_SLOTS; ++i)
        frame->slots[i] = (uint8_t)(update + i * 73u);
}

static void step(node *sender, node *receiver, nl_fault_transfer *t, uint64_t now, bool produce)
{
    OK(nl_fault_backend_set_time(&sender->adapter, now));
    OK(nl_fault_backend_set_time(&receiver->adapter, now));
    if (produce) OK(nl_host_poll(&sender->host, now));
    {
        nl_status result = nl_fault_transfer_step(&sender->adapter, &receiver->adapter, t, now);
        CHECK(result == NL_OK || result == NL_ERR_BUSY || result == NL_ERR_EMPTY || result == NL_ERR_FULL);
        CHECK(t->rejected == 0u);
    }
    OK(nl_host_poll(&receiver->host, now));
    CHECK(sender->adapter.radio.tx[1].count <= NL_RADIO_TX_DEPTH);
    CHECK(receiver->adapter.radio.rx.count <= NL_RADIO_RX_DEPTH);
    CHECK(receiver->transport.stats.rx_delivered == receiver->adapter.stats.commits +
        (receiver->transport.pending && receiver->transport.settled ? 1u : 0u));
    CHECK(receiver->transport.stats.rx_discarded == 0u);
}

static bool drained(const node *sender, const node *receiver, const nl_fault_transfer *t)
{
    return !t->pending && sender->adapter.radio.tx[1].count == 0u &&
        receiver->adapter.radio.rx.count == 0u && !receiver->transport.pending;
}

static void drain(node *sender, node *receiver, nl_fault_transfer *t, uint64_t *now)
{
    uint64_t deadline = *now + 200000;
    while (!drained(sender, receiver, t) || (sender->dmx.active && sender->dmx.tx.active)) {
        CHECK(*now < deadline);
        *now += 100;
        step(sender, receiver, t, *now, sender->dmx.active && sender->dmx.tx.active);
    }
}

static void exact_frame(node *receiver, const nova_dmx_frame_t *desired, uint64_t now)
{
    nova_dmx_frame_t received;
    MV(nl_multiverse_get(&receiver->dmx, now, &received), NOVA_MV_FRAME_READY);
    CHECK(received.slot_count == desired->slot_count);
    CHECK(memcmp(received.slots, desired->slots, desired->slot_count) == 0);
}

int main(void)
{
    static node sender, receiver;
    nova_dmx_frame_t desired = {0};
    nl_fault_transfer t = {.delay = 400};
    nl_frame old_receipt;
    nl_pull_token old_token;
    uint64_t now = 0, accepted, completed, delivered, retries;
    size_t max_tx = 0, max_rx = 0;
    initialize(&sender, true, 42);
    initialize(&receiver, false, 42);
    puts("Logical adapter settings: 100-us event steps, 400-us transfer delay, "
         "900-us receipt commit delay, two receipt attempts/poll, FIFO TX/RX limits 8/16.");
    fill(&desired, 0);
    MV(nl_multiverse_submit(&sender.dmx, &desired), NOVA_MV_OK);
    step(&sender, &receiver, &t, now, true);
    CHECK(t.pending && sender.adapter.radio.tx[1].count == 8u);
    CHECK(sender.transport.stats.tx_accepted == 8u && t.completed == 0u);
    for (now = 100; now <= 500; now += 100) step(&sender, &receiver, &t, now, false);
    CHECK(receiver.transport.pending && receiver.transport.settled);
    CHECK(receiver.transport.stats.rx_delivered == 1u && receiver.adapter.stats.commits == 0u);
    old_receipt = receiver.adapter.receipt;
    old_token = receiver.adapter.receipt_token;
    receiver.adapter.connected = false;
    accepted = sender.transport.stats.tx_accepted;
    completed = t.completed;
    delivered = receiver.transport.stats.rx_delivered;
    retries = receiver.adapter.stats.commit_retries;
    for (; now <= 2000; now += 100) step(&sender, &receiver, &t, now, false);
    CHECK(sender.transport.stats.tx_accepted == accepted && t.completed == completed);
    CHECK(receiver.transport.stats.rx_delivered == delivered);
    CHECK(receiver.adapter.stats.commit_retries > retries && receiver.transport.pending);
    CHECK(sender.adapter.radio.tx[1].count == 7u && t.pending);
    receiver.adapter.connected = true;
    drain(&sender, &receiver, &t, &now);
    exact_frame(&receiver, &desired, now);
    CHECK(sender.transport.stats.tx_accepted == t.completed);
    CHECK(receiver.transport.stats.rx_delivered == t.completed);
    CHECK(receiver.dmx.rx.stats.frames == 1u && receiver.adapter.stats.commits == 8u);

    for (unsigned update = 1; update <= 400; ++update) {
        size_t before;
        uint64_t accepted_before;
        now += 100;
        fill(&desired, update);
        MV(nl_multiverse_submit(&sender.dmx, &desired), NOVA_MV_OK);
        sender.adapter.connected = update < 151u || update > 200u;
        before = sender.adapter.radio.tx[1].count;
        accepted_before = sender.transport.stats.tx_accepted;
        step(&sender, &receiver, &t, now, true);
        if (!sender.adapter.connected) {
            CHECK(sender.adapter.radio.tx[1].count == before);
            CHECK(sender.transport.stats.tx_accepted == accepted_before);
        }
        if (sender.adapter.radio.tx[1].count > max_tx) max_tx = sender.adapter.radio.tx[1].count;
        if (receiver.adapter.radio.rx.count > max_rx) max_rx = receiver.adapter.radio.rx.count;
    }
    CHECK(max_tx == NL_RADIO_TX_DEPTH && max_rx == NL_RADIO_RX_DEPTH);
    CHECK(sender.dmx.stats.backpressure != 0u && sender.adapter.stats.offline_pushes != 0u);
    CHECK(t.blocked != 0u && receiver.adapter.radio.stats.rx_full != 0u);
    CHECK(sender.dmx.tx.stats.updates < 401u);
    drain(&sender, &receiver, &t, &now);
    nl_multiverse_force_full(&sender.dmx);
    now += 1000;
    step(&sender, &receiver, &t, now, true);
    CHECK(t.pending && sender.adapter.radio.tx[1].count == 8u);
    CHECK(nl_modules_stop(sender.instances, 2) == NL_ERR_BUSY);
    CHECK(!sender.instances[0].active && sender.instances[1].active);
    CHECK(sender.transport.host == &sender.host && sender.adapter.stats.stops == 0u);
    CHECK(t.pending && sender.adapter.radio.tx[1].count == 8u);
    drain(&sender, &receiver, &t, &now);
    exact_frame(&receiver, &desired, now);
    CHECK(sender.transport.stats.tx_accepted == t.completed);
    CHECK(receiver.transport.stats.rx_delivered == t.completed);
    OK(nl_modules_stop(sender.instances, 2));
    CHECK(sender.adapter.stats.stops == 1u && sender.host.send == NULL);
    printf("Logical faults: TX/RX peaks %zu/%zu; %" PRIu64 " FIFO congestion retries; "
           "%" PRIu64 " delayed receipt retries; %" PRIu64 " complete DMX updates.\n",
           max_tx, max_rx, t.blocked, receiver.adapter.stats.commit_retries, receiver.dmx.rx.stats.frames);
    printf("Before restart: %" PRIu64 " native PUSH acceptances/completions/receipt dispatches; "
           "%" PRIu64 " disconnected PUSH rejections; %" PRIu64
           " model updates from 401 submitted snapshots; exact latest 512 levels.\n",
           t.completed, sender.adapter.stats.offline_pushes, sender.dmx.tx.stats.updates);

    /* The old lifetime is fully drained. Reset native dedup separately from NLM1. */
    CHECK(drained(&sender, &receiver, &t));
    OK(nl_stream_reset_origin(&receiver.host.streams, 1));
    OK(nl_stream_reset_origin(&receiver.adapter.radio.streams, 1));
    MV(nl_multiverse_bind(&receiver.dmx, 1, 43), NOVA_MV_OK);
    initialize(&sender, true, 43);
    completed = t.completed;
    fill(&desired, 999);
    MV(nl_multiverse_submit(&sender.dmx, &desired), NOVA_MV_OK);
    now += 100;
    step(&sender, &receiver, &t, now, true);
    CHECK(t.original.sequence == 0u);
    while (!receiver.transport.pending) {
        now += 100;
        step(&sender, &receiver, &t, now, false);
    }
    {
        size_t count = receiver.adapter.radio.rx.count;
        CHECK(nl_radio_commit_pull(&receiver.adapter.radio, &old_receipt, old_token) == NL_ERR_STALE);
        CHECK(receiver.adapter.radio.rx.count == count && receiver.transport.pending);
    }
    drain(&sender, &receiver, &t, &now);
    exact_frame(&receiver, &desired, now);
    CHECK(t.completed - completed == 8u && sender.transport.stats.tx_accepted == 8u);
    CHECK(receiver.dmx.rx.sequence == 0u && receiver.dmx.config.session == 43u);
    OK(nl_modules_stop(sender.instances, 2));
    OK(nl_modules_stop(receiver.instances, 2));
    puts("Exact final levels, immutable delayed ownership, one dispatch per receipt, "
         "BUSY shutdown/drain, stale completion rejection and explicit restart passed.");
    puts("Native NLM1 over logical adapter delays; no physical RF/SPI timing or Multiverse interoperability claim.");
    return EXIT_SUCCESS;
}
