/* SPDX-License-Identifier: GPL-3.0-only */
#include "nova/multiverse_synthetic.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #x); exit(1); } } while (0)
#define RESULT(x, r) CHECK((x) == (r))

static nova_mv_tx_config_t tx_config(void)
{
    nova_mv_tx_config_t config = {1, 42, 64, 1000, 5000};
    return config;
}
static nova_mv_rx_config_t rx_config(void)
{
    nova_mv_rx_config_t config = {1, 42, 10000, 500};
    return config;
}
static nova_dmx_frame_t levels(unsigned slots, unsigned seed)
{
    nova_dmx_frame_t frame = {0};
    frame.slot_count = (uint16_t)slots;
    for (unsigned i = 0; i < slots; ++i) frame.slots[i] = (uint8_t)(i * 37u + seed);
    return frame;
}
static void equal_frame(const nova_dmx_frame_t *a, const nova_dmx_frame_t *b)
{
    CHECK(a->slot_count == b->slot_count);
    CHECK(memcmp(a->slots, b->slots, a->slot_count) == 0);
    for (unsigned i = a->slot_count; i < NOVA_DMX_MAX_SLOTS; ++i) CHECK(a->slots[i] == 0);
}
static nova_mv_packet_t full_packet(uint16_t seq, unsigned slots)
{
    nova_mv_packet_t p = {0};
    p.universe = 1;
    p.session = 42;
    p.sequence = seq;
    p.slot_count = p.span_count = p.count = (uint16_t)slots;
    for (unsigned i = 0; i < slots; ++i) p.levels[i] = (uint8_t)i;
    return p;
}
static nova_mv_result_t wire_receive(nova_mv_rx_t *rx, const nova_mv_packet_t *p,
                                     uint64_t now, nova_dmx_frame_t *frame)
{
    uint8_t bytes[NOVA_MV_SYNTHETIC_MAX_BYTES];
    nova_mv_packet_t decoded;
    size_t written;
    RESULT(nova_mv_synthetic_encode(p, bytes, sizeof(bytes), &written), NOVA_MV_OK);
    RESULT(nova_mv_synthetic_decode(bytes, written, &decoded), NOVA_MV_OK);
    return nova_mv_rx_receive(rx, &decoded, NOVA_MV_INTEGRITY_OK, now, frame);
}
static void send_update(nova_mv_tx_t *tx, nova_mv_rx_t *rx, uint64_t now,
                        const nova_dmx_frame_t *expected)
{
    nova_mv_packet_t p;
    nova_dmx_frame_t frame;
    uint64_t token;
    unsigned delivered = 0;
    do {
        RESULT(nova_mv_tx_prepare(tx, now, &p, &token), NOVA_MV_PACKET_READY);
        nova_mv_result_t r = wire_receive(rx, &p, now, &frame);
        if (r == NOVA_MV_FRAME_READY) { equal_frame(&frame, expected); ++delivered; }
        else CHECK(r == NOVA_MV_OK);
        RESULT(nova_mv_tx_complete(tx, token, true, now), NOVA_MV_OK);
    } while (tx->active);
    CHECK(delivered == 1);
}

static void test_roundtrip_all_sizes_and_chunks(void)
{
    const uint16_t chunks[] = {1, 7, 64, 127, 512};
    for (unsigned slots = 0; slots <= 512; ++slots) {
        for (size_t c = 0; c < sizeof(chunks) / sizeof(chunks[0]); ++c) {
            nova_mv_tx_t tx;
            nova_mv_rx_t rx;
            nova_mv_tx_config_t tc = tx_config();
            nova_mv_rx_config_t rc = rx_config();
            nova_dmx_frame_t frame = levels(slots, slots);
            tc.chunk_slots = chunks[c];
            RESULT(nova_mv_tx_init(&tx, &tc), NOVA_MV_OK);
            RESULT(nova_mv_rx_init(&rx, &rc), NOVA_MV_OK);
            RESULT(nova_mv_tx_submit(&tx, &frame), NOVA_MV_OK);
            send_update(&tx, &rx, 0, &frame);
            if (slots > 0) frame.slots[slots / 2u] ^= 0xFF;
            RESULT(nova_mv_tx_submit(&tx, &frame), NOVA_MV_OK);
            send_update(&tx, &rx, 1000, &frame);
            CHECK(tx.pending.kind == NOVA_MV_DELTA);
            send_update(&tx, &rx, 2000, &frame); /* empty-span refresh */
            CHECK(tx.pending.span_count == 0);
            send_update(&tx, &rx, 5000, &frame); /* periodic full resync */
            CHECK(tx.pending.kind == NOVA_MV_FULL);
        }
    }
}

static void test_tx_ownership(void)
{
    nova_mv_tx_t tx;
    nova_mv_tx_config_t tc = tx_config();
    nova_mv_packet_t p, again;
    nova_dmx_frame_t a = levels(100, 1), b = levels(100, 2), c = levels(100, 3);
    uint64_t token, other;
    RESULT(nova_mv_tx_init(&tx, &tc), NOVA_MV_OK);
    RESULT(nova_mv_tx_prepare(&tx, 0, &p, &token), NOVA_MV_IDLE);
    RESULT(nova_mv_tx_submit(&tx, &a), NOVA_MV_OK);
    RESULT(nova_mv_tx_prepare(&tx, 0, &p, &token), NOVA_MV_PACKET_READY);
    RESULT(nova_mv_tx_submit(&tx, &b), NOVA_MV_OK);
    CHECK(tx.stats.coalesced == 0); /* A is frozen and will still be delivered. */
    RESULT(nova_mv_tx_submit(&tx, &c), NOVA_MV_OK);
    RESULT(nova_mv_tx_submit(&tx, &b), NOVA_MV_OK);
    RESULT(nova_mv_tx_submit(&tx, &b), NOVA_MV_OK);
    CHECK(tx.stats.coalesced == 2); /* B then C superseded; identical B is retained. */
    RESULT(nova_mv_tx_prepare(&tx, 1, &again, &other), NOVA_MV_PACKET_READY);
    CHECK(other == token && memcmp(&p, &again, sizeof(p)) == 0);
    RESULT(nova_mv_tx_complete(&tx, token + 1u, true, 2), NOVA_MV_INVALID_TOKEN);
    RESULT(nova_mv_tx_complete(&tx, token, false, 2), NOVA_MV_OK);
    CHECK(!tx.has_baseline && tx.stats.updates == 0);
    RESULT(nova_mv_tx_prepare(&tx, 3, &again, &other), NOVA_MV_PACKET_READY);
    CHECK(other != token && memcmp(&p, &again, sizeof(p)) == 0);
    RESULT(nova_mv_tx_complete(&tx, token, true, 3), NOVA_MV_INVALID_TOKEN);
    RESULT(nova_mv_tx_complete(&tx, other, true, 3), NOVA_MV_OK);
    CHECK(!tx.has_baseline);
    RESULT(nova_mv_tx_prepare(&tx, 4, &again, &other), NOVA_MV_PACKET_READY);
    CHECK(again.offset == 64 && again.count == 36 && again.levels[0] == a.slots[64]);
    nova_mv_tx_force_full(&tx); /* deferred until next update */
    RESULT(nova_mv_tx_complete(&tx, other, true, 4), NOVA_MV_OK);
    equal_frame(&tx.baseline, &a);
    RESULT(nova_mv_tx_prepare(&tx, 5, &p, &token), NOVA_MV_PACKET_READY);
    CHECK(p.kind == NOVA_MV_FULL && p.sequence == 1 && p.levels[0] == b.slots[0]);
    RESULT(nova_mv_tx_complete(&tx, token, true, 5), NOVA_MV_OK);
    RESULT(nova_mv_tx_prepare(&tx, 5, &p, &token), NOVA_MV_PACKET_READY);
    RESULT(nova_mv_tx_complete(&tx, token, true, 5), NOVA_MV_OK);
    equal_frame(&tx.baseline, &b);
    RESULT(nova_mv_tx_prepare(&tx, 1004, &p, &token), NOVA_MV_IDLE);
    RESULT(nova_mv_tx_prepare(&tx, 1005, &p, &token), NOVA_MV_PACKET_READY);
    CHECK(p.kind == NOVA_MV_DELTA && p.count == 0);
    RESULT(nova_mv_tx_complete(&tx, token, true, 1004), NOVA_MV_INVALID_TIME);
    RESULT(nova_mv_tx_complete(&tx, token, true, 1005), NOVA_MV_OK);
    b.slot_count = 2;
    RESULT(nova_mv_tx_submit(&tx, &b), NOVA_MV_OK);
    RESULT(nova_mv_tx_prepare(&tx, 2005, &p, &token), NOVA_MV_PACKET_READY);
    CHECK(p.kind == NOVA_MV_FULL && p.slot_count == 2);
    RESULT(nova_mv_tx_complete(&tx, token, true, 2005), NOVA_MV_OK);
    RESULT(nova_mv_tx_prepare(&tx, 2004, &p, &token), NOVA_MV_INVALID_TIME);
    tx.next_token = UINT64_MAX;
    RESULT(nova_mv_tx_prepare(&tx, 3005, &p, &token), NOVA_MV_EXHAUSTED);
    CHECK(!tx.active);
}

static void test_chunk_reorder_overlap_and_atomicity(void)
{
    nova_mv_rx_t rx;
    nova_mv_rx_config_t rc = rx_config();
    nova_mv_packet_t p = full_packet(0, 8), chunk;
    nova_dmx_frame_t frame = levels(8, 0), output = levels(1, 99);
    /* Tail before head, partially overlapping chunk, then conflicting overlap. */
    RESULT(nova_mv_rx_init(&rx, &rc), NOVA_MV_OK);
    chunk = p; chunk.offset = 4; chunk.count = 4;
    memcpy(chunk.levels, p.levels + 4, 4);
    RESULT(wire_receive(&rx, &chunk, 0, &output), NOVA_MV_OK);
    CHECK(output.slot_count == 1 && output.slots[0] == 99);
    RESULT(wire_receive(&rx, &chunk, 1, &output), NOVA_MV_DUPLICATE);
    chunk = p; chunk.count = 6; chunk.levels[5] = 88;
    RESULT(wire_receive(&rx, &chunk, 2, &output), NOVA_MV_BAD_PACKET);
    CHECK(rx.received == 4 && rx.covered[0] == 0 && rx.assembling.slots[5] == 5);
    chunk = p; chunk.count = 6;
    RESULT(wire_receive(&rx, &chunk, 3, &output), NOVA_MV_FRAME_READY);
    memcpy(frame.slots, p.levels, 8);
    equal_frame(&output, &frame);
    RESULT(wire_receive(&rx, &chunk, 4, &output), NOVA_MV_DUPLICATE);
    chunk.sequence = 1; chunk.kind = NOVA_MV_DELTA;
    chunk.span_start = 2; chunk.span_count = 4; chunk.offset = 0; chunk.count = 2;
    chunk.levels[0] = 10; chunk.levels[1] = 11;
    RESULT(wire_receive(&rx, &chunk, 5, &output), NOVA_MV_OK);
    RESULT(nova_mv_rx_get(&rx, 5, &output), NOVA_MV_FRAME_READY);
    equal_frame(&output, &frame); /* pending delta not visible */
    chunk.offset = 2; chunk.levels[0] = 12; chunk.levels[1] = 13;
    chunk.span_start = 3;
    RESULT(wire_receive(&rx, &chunk, 6, &output), NOVA_MV_BAD_PACKET);
    chunk.span_start = 2;
    RESULT(wire_receive(&rx, &chunk, 7, &output), NOVA_MV_FRAME_READY);
    for (unsigned i = 0; i < 4; ++i) frame.slots[i + 2u] = (uint8_t)(10u + i);
    equal_frame(&output, &frame);
    chunk = full_packet(2, 8); chunk.count = 4;
    RESULT(wire_receive(&rx, &chunk, 8, &output), NOVA_MV_OK);
    chunk.kind = NOVA_MV_DELTA; /* conflicting same-sequence metadata */
    RESULT(wire_receive(&rx, &chunk, 9, &output), NOVA_MV_BAD_PACKET);
    CHECK(rx.active && rx.synchronized && rx.received == 4);
    chunk.kind = NOVA_MV_FULL; chunk.offset = 4;
    memcpy(chunk.levels, "abcd", 4);
    RESULT(wire_receive(&rx, &chunk, 10, &output), NOVA_MV_FRAME_READY);
}

static void test_loss_and_resynchronization(void)
{
    nova_mv_tx_t tx;
    nova_mv_rx_t rx;
    nova_mv_tx_config_t tc = tx_config();
    nova_mv_rx_config_t rc = rx_config();
    nova_dmx_frame_t frame = levels(10, 1), output;
    nova_mv_packet_t p, saved;
    uint64_t token;
    RESULT(nova_mv_tx_init(&tx, &tc), NOVA_MV_OK);
    RESULT(nova_mv_rx_init(&rx, &rc), NOVA_MV_OK);
    RESULT(nova_mv_tx_submit(&tx, &frame), NOVA_MV_OK);
    send_update(&tx, &rx, 0, &frame);
    frame.slots[0] = 20;
    RESULT(nova_mv_tx_submit(&tx, &frame), NOVA_MV_OK);
    RESULT(nova_mv_tx_prepare(&tx, 1000, &p, &token), NOVA_MV_PACKET_READY);
    saved = p;
    RESULT(nova_mv_tx_complete(&tx, token, true, 1000), NOVA_MV_OK); /* RF drop */
    frame.slots[1] = 30;
    RESULT(nova_mv_tx_submit(&tx, &frame), NOVA_MV_OK);
    RESULT(nova_mv_tx_prepare(&tx, 2000, &p, &token), NOVA_MV_PACKET_READY);
    RESULT(wire_receive(&rx, &p, 2000, &output), NOVA_MV_NEED_FULL);
    CHECK(rx.link == NOVA_MV_RECOVERING);
    RESULT(nova_mv_rx_get(&rx, 2000, &output), NOVA_MV_FRAME_READY);
    CHECK(output.slots[0] == 1 && output.slots[1] == 38);
    RESULT(wire_receive(&rx, &saved, 2001, &output), NOVA_MV_NEED_FULL);
    RESULT(nova_mv_tx_complete(&tx, token, true, 2001), NOVA_MV_OK);
    send_update(&tx, &rx, 5000, &frame);
    CHECK(rx.link == NOVA_MV_LIVE);
    RESULT(nova_mv_rx_tick(&rx, 14999), NOVA_MV_OK);
    CHECK(rx.link == NOVA_MV_LIVE);
    RESULT(nova_mv_rx_tick(&rx, 15000), NOVA_MV_OK);
    CHECK(rx.link == NOVA_MV_LOST && rx.stats.losses == 1);
    output.slot_count = 999;
    RESULT(nova_mv_rx_get(&rx, 15000, &output), NOVA_MV_NEED_FULL);
    CHECK(output.slot_count == 999);
    RESULT(nova_mv_rx_tick(&rx, 15001), NOVA_MV_OK);
    CHECK(rx.stats.losses == 1);
    p = tx.pending;
    p.offset = 0;
    p.count = p.span_count;
    RESULT(wire_receive(&rx, &p, 15001, &output), NOVA_MV_DUPLICATE);
    CHECK(rx.link == NOVA_MV_LOST); /* expired replay cannot revive the link */
    RESULT(nova_mv_rx_tick(&rx, 14999), NOVA_MV_INVALID_TIME);
    /* New explicit session rejects old traffic and requires full reacquisition. */
    RESULT(nova_mv_rx_bind(&rx, 43), NOVA_MV_OK);
    p = full_packet(0, 10);
    RESULT(wire_receive(&rx, &p, 15002, &output), NOVA_MV_FILTERED);
    p.session = 43;
    RESULT(wire_receive(&rx, &p, 15003, &output), NOVA_MV_FRAME_READY);
    p.universe = 2;
    RESULT(wire_receive(&rx, &p, 15004, &output), NOVA_MV_FILTERED);
}

static void test_timeouts_and_integrity(void)
{
    nova_mv_rx_t rx;
    nova_mv_rx_config_t rc = rx_config();
    nova_mv_packet_t p = full_packet(0, 8);
    nova_dmx_frame_t output;
    RESULT(nova_mv_rx_init(&rx, &rc), NOVA_MV_OK);
    p.count = 4;
    RESULT(wire_receive(&rx, &p, 0, &output), NOVA_MV_OK);
    RESULT(nova_mv_rx_receive(&rx, &p, NOVA_MV_INTEGRITY_UNKNOWN, 1, &output), NOVA_MV_UNVERIFIED);
    RESULT(nova_mv_rx_receive(&rx, &p, NOVA_MV_INTEGRITY_BAD, 2, &output), NOVA_MV_BAD_PACKET);
    RESULT(wire_receive(&rx, &p, 499, &output), NOVA_MV_DUPLICATE);
    RESULT(nova_mv_rx_tick(&rx, 500), NOVA_MV_OK);
    CHECK(!rx.active && rx.stats.abandoned == 1);
    p.offset = 4; memcpy(p.levels, "abcd", 4);
    RESULT(wire_receive(&rx, &p, 501, &output), NOVA_MV_OK);
    p.sequence = 1; p.offset = 0;
    RESULT(wire_receive(&rx, &p, 502, &output), NOVA_MV_OK);
    CHECK(rx.stats.abandoned == 2 && rx.received == 4);
    p.sequence = 0;
    RESULT(wire_receive(&rx, &p, 503, &output), NOVA_MV_STALE);
    p.sequence = 1; p.offset = 4;
    RESULT(wire_receive(&rx, &p, 504, &output), NOVA_MV_FRAME_READY);
    RESULT(nova_mv_rx_receive(&rx, &p, NOVA_MV_INTEGRITY_UNKNOWN, 10504, &output), NOVA_MV_UNVERIFIED);
    CHECK(rx.link == NOVA_MV_LOST); /* bad/unknown data cannot keep link alive */
    RESULT(nova_mv_rx_bind(&rx, 42), NOVA_MV_OK);
    CHECK(rx.link == NOVA_MV_WAIT_FULL && !rx.has_frame);
    /* uint64 end-of-clock: subtraction-based timeout checks never wrap. */
    p = full_packet(0, 1);
    RESULT(wire_receive(&rx, &p, UINT64_MAX - 5u, &output), NOVA_MV_FRAME_READY);
    RESULT(nova_mv_rx_get(&rx, UINT64_MAX, &output), NOVA_MV_FRAME_READY);
}

static void test_sequence_wrap(void)
{
    nova_mv_rx_t rx;
    nova_mv_tx_t tx;
    nova_mv_tx_config_t tc = tx_config();
    nova_mv_rx_config_t rc = rx_config();
    nova_dmx_frame_t frame = levels(1, 0);
    nova_mv_packet_t p;
    RESULT(nova_mv_tx_init(&tx, &tc), NOVA_MV_OK);
    RESULT(nova_mv_rx_init(&rx, &rc), NOVA_MV_OK);
    RESULT(nova_mv_tx_submit(&tx, &frame), NOVA_MV_OK);
    for (uint64_t i = 0; i < 65540u; ++i) {
        frame.slots[0] = (uint8_t)i;
        RESULT(nova_mv_tx_submit(&tx, &frame), NOVA_MV_OK);
        send_update(&tx, &rx, i * 1000u, &frame);
        CHECK(rx.sequence == (uint16_t)i);
    }
    p = full_packet(2, 1);
    RESULT(wire_receive(&rx, &p, 65540000, &frame), NOVA_MV_STALE);
    p.sequence = 32771;
    RESULT(wire_receive(&rx, &p, 65540001, &frame), NOVA_MV_STALE); /* half-range */
    p.sequence = 4;
    RESULT(wire_receive(&rx, &p, 65540002, &frame), NOVA_MV_FRAME_READY);
}

static void test_codec_and_malformed_inputs(void)
{
    nova_mv_packet_t p = full_packet(0, 2), decoded, untouched;
    uint8_t bytes[NOVA_MV_SYNTHETIC_MAX_BYTES];
    size_t size;
    const uint8_t golden[] = { /* CRC independently checked by Python zlib test. */
        0x4e,0x56,0x53,0x31,0,0,1,0,42,0,0,0,0,0,0,0,2,0,0,0,2,0,0,0,2,0,0,1
    };
    memset(&untouched, 0xAB, sizeof(untouched));
    decoded = untouched;
    RESULT(nova_mv_synthetic_encode(&p, bytes, 31, &size), NOVA_MV_BUFFER_TOO_SMALL);
    CHECK(size == 0);
    RESULT(nova_mv_synthetic_encode(&p, bytes, sizeof(bytes), &size), NOVA_MV_OK);
    CHECK(size == 32 && memcmp(bytes, golden, sizeof(golden)) == 0);
    for (size_t i = 0; i < size; ++i) {
        bytes[i] ^= 1;
        RESULT(nova_mv_synthetic_decode(bytes, size, &decoded), NOVA_MV_BAD_PACKET);
        CHECK(memcmp(&decoded, &untouched, sizeof(decoded)) == 0);
        bytes[i] ^= 1;
    }
    for (size_t i = 0; i < size; ++i)
        RESULT(nova_mv_synthetic_decode(bytes, i, &decoded), NOVA_MV_BAD_PACKET);
    RESULT(nova_mv_synthetic_decode(bytes, size + 1u, &decoded), NOVA_MV_BAD_PACKET);
    RESULT(nova_mv_synthetic_decode(bytes, size, &decoded), NOVA_MV_OK);
    CHECK(decoded.slot_count == 2 && decoded.levels[1] == 1);
    p.count = 3; RESULT(nova_mv_packet_validate(&p), NOVA_MV_BAD_PACKET);
    p = full_packet(0, 2); p.span_start = 1; RESULT(nova_mv_packet_validate(&p), NOVA_MV_BAD_PACKET);
    p = full_packet(0, 2); p.offset = 1; RESULT(nova_mv_packet_validate(&p), NOVA_MV_BAD_PACKET);
    p = full_packet(0, 2); p.count = 0; RESULT(nova_mv_packet_validate(&p), NOVA_MV_BAD_PACKET);
    p = full_packet(0, 2); p.base_sequence = 1; RESULT(nova_mv_packet_validate(&p), NOVA_MV_BAD_PACKET);
    p = full_packet(0, 2); p.kind = NOVA_MV_DELTA; RESULT(nova_mv_packet_validate(&p), NOVA_MV_BAD_PACKET);
    p = full_packet(0, 2); p.universe = 64000; RESULT(nova_mv_packet_validate(&p), NOVA_MV_BAD_PACKET);
}

static void test_invalid_arguments(void)
{
    nova_mv_tx_t tx = {0};
    nova_mv_rx_t rx = {0};
    nova_mv_tx_config_t tc = tx_config();
    nova_mv_rx_config_t rc = rx_config();
    nova_mv_packet_t p;
    nova_dmx_frame_t frame = {0};
    uint64_t token;
    RESULT(nova_mv_tx_submit(&tx, &frame), NOVA_MV_INVALID_ARGUMENT);
    RESULT(nova_mv_rx_tick(&rx, 0), NOVA_MV_INVALID_ARGUMENT);
    tc.chunk_slots = 0; RESULT(nova_mv_tx_init(&tx, &tc), NOVA_MV_INVALID_ARGUMENT);
    tc = tx_config(); tc.interval_us = 0; RESULT(nova_mv_tx_init(&tx, &tc), NOVA_MV_INVALID_ARGUMENT);
    tc = tx_config(); tc.full_interval_us = 1; RESULT(nova_mv_tx_init(&tx, &tc), NOVA_MV_INVALID_ARGUMENT);
    rc.loss_timeout_us = 0; RESULT(nova_mv_rx_init(&rx, &rc), NOVA_MV_INVALID_ARGUMENT);
    rc = rx_config(); rc.assembly_timeout_us = 0; RESULT(nova_mv_rx_init(&rx, &rc), NOVA_MV_INVALID_ARGUMENT);
    tc = tx_config(); rc = rx_config();
    RESULT(nova_mv_tx_init(&tx, &tc), NOVA_MV_OK);
    RESULT(nova_mv_rx_init(&rx, &rc), NOVA_MV_OK);
    RESULT(nova_mv_tx_prepare(&tx, 0, NULL, &token), NOVA_MV_INVALID_ARGUMENT);
    RESULT(nova_mv_tx_prepare(&tx, 0, &p, NULL), NOVA_MV_INVALID_ARGUMENT);
    RESULT(nova_mv_tx_complete(&tx, 0, true, 0), NOVA_MV_INVALID_TOKEN);
    frame.slot_count = 513; RESULT(nova_mv_tx_submit(&tx, &frame), NOVA_MV_INVALID_ARGUMENT);
    RESULT(nova_mv_rx_receive(&rx, NULL, NOVA_MV_INTEGRITY_OK, 0, NULL), NOVA_MV_INVALID_ARGUMENT);
    RESULT(nova_mv_rx_get(&rx, 0, NULL), NOVA_MV_INVALID_ARGUMENT);
    RESULT(nova_mv_packet_validate(NULL), NOVA_MV_INVALID_ARGUMENT);
}

int main(void)
{
    test_roundtrip_all_sizes_and_chunks();
    test_tx_ownership();
    test_chunk_reorder_overlap_and_atomicity();
    test_loss_and_resynchronization();
    test_timeouts_and_integrity();
    test_sequence_wrap();
    test_codec_and_malformed_inputs();
    test_invalid_arguments();
    puts("Multiverse software model: TX/RX ownership, chunks, recovery, wrap and codec checks passed");
    return 0;
}
