/* SPDX-License-Identifier: GPL-3.0-only */
#include "test.h"
#include "nova_link/multiverse_plugin.h"

#define MV(expression, expected) do { \
    nova_mv_result_t result_ = (expression); \
    if (result_ != (expected)) { \
        fprintf(stderr, "%s:%d: %s: got %s, expected %s\n", __FILE__, __LINE__, \
                #expression, nova_mv_result_name(result_), nova_mv_result_name(expected)); \
        exit(EXIT_FAILURE); \
    } \
} while (0)

typedef struct {
    nl_radio *radio;
    nl_fragment attempted;
    unsigned attempts;
} bridge;

typedef struct {
    nl_host sender, receiver;
    nl_radio tx_radio, rx_radio;
    bridge transport;
    nl_multiverse_context tx, rx;
    nl_plugin_id tx_id, rx_id;
    uint64_t now;
} fixture;

/* Exercise the specified native frame serialization and decoding. */
static nl_status push(void *context, const nl_fragment *value)
{
    bridge *transport = context;
    nl_frame frame, decoded;
    uint8_t bytes[NL_FRAME_MAX];
    size_t size;
    nl_status result;
    transport->attempted = *value;
    ++transport->attempts;
    result = nl_frame_from_fragment(NL_COMMAND_PUSH, value, &frame);
    if (result != NL_OK) return result;
    result = nl_frame_encode(&frame, bytes, sizeof(bytes), &size);
    if (result != NL_OK) return result;
    result = nl_frame_decode(bytes, size, &decoded);
    if (result != NL_OK) return result;
    return nl_radio_handle_frame(transport->radio, &decoded, NULL, NULL);
}

static nl_multiverse_config config(nl_multiverse_role role, uint8_t zone,
                                   uint16_t universe)
{
    nl_multiverse_config value = {0};
    value.role = role;
    value.zone = zone;
    value.peer_origin = 1;
    value.universe = universe;
    value.session = 42;
    value.interval_us = 100;
    value.full_interval_us = 100000;
    value.loss_timeout_us = 1000000;
    value.assembly_timeout_us = 100000;
    value.chunks_per_tick = 8;
    return value;
}

static void setup(fixture *f)
{
    nl_multiverse_config tx_config = config(NL_MULTIVERSE_TX, 1, 1);
    nl_multiverse_config rx_config = config(NL_MULTIVERSE_RX, 1, 1);
    nl_plugin plugin;
    memset(f, 0, sizeof(*f));
    STATUS(nl_radio_init(&f->tx_radio, 2, 1000, 500, 0), NL_OK);
    STATUS(nl_radio_init(&f->rx_radio, 2, 1000, 500, 0), NL_OK);
    CHECK(f->rx_radio.rx_policy == NL_RX_FIFO);
    f->transport.radio = &f->tx_radio;
    STATUS(nl_host_init(&f->sender, 1, 0, push, &f->transport), NL_OK);
    STATUS(nl_host_init(&f->receiver, 2, 0, push, &f->transport), NL_OK);
    MV(nl_multiverse_init(&f->tx, &tx_config), NOVA_MV_OK);
    MV(nl_multiverse_init(&f->rx, &rx_config), NOVA_MV_OK);
    plugin = nl_multiverse_plugin(&f->tx);
    STATUS(nl_host_register(&f->sender, &plugin, &f->tx_id), NL_OK);
    plugin = nl_multiverse_plugin(&f->rx);
    STATUS(nl_host_register(&f->receiver, &plugin, &f->rx_id), NL_OK);
}

static void teardown(fixture *f)
{
    STATUS(nl_host_unregister(&f->sender, f->tx_id), NL_OK);
    STATUS(nl_host_unregister(&f->receiver, f->rx_id), NL_OK);
}

static nova_dmx_frame_t levels(uint16_t slots, unsigned seed)
{
    nova_dmx_frame_t frame = {0};
    frame.slot_count = slots;
    for (unsigned i = 0; i < slots; ++i)
        frame.slots[i] = (uint8_t)(seed + i * 73u);
    return frame;
}

static void same_levels(const nova_dmx_frame_t *a, const nova_dmx_frame_t *b)
{
    CHECK(a->slot_count == b->slot_count);
    CHECK(memcmp(a->slots, b->slots, sizeof(a->slots)) == 0);
}

static void acquire(fixture *f, const nova_dmx_frame_t *expected)
{
    nova_dmx_frame_t received;
    MV(nl_multiverse_get(&f->rx, f->now, &received), NOVA_MV_FRAME_READY);
    same_levels(&received, expected);
}

/* RF fragment bytes -> RX FIFO -> framed PULL -> host -> plugin. */
static void deliver(fixture *f, const nl_fragment *outgoing)
{
    nl_fragment incoming;
    nl_frame pull = {0}, response, decoded;
    uint8_t bytes[NL_FRAME_MAX];
    nl_pull_token token;
    size_t size;
    CHECK(outgoing->payload_size <= NL_PAYLOAD_MAX);
    STATUS(nl_fragment_encode(outgoing, bytes, sizeof(bytes), &size), NL_OK);
    STATUS(nl_fragment_decode(bytes, size, &incoming), NL_OK);
    STATUS(nl_radio_receive(&f->rx_radio, &incoming, f->now), NL_OK);
    STATUS(nl_radio_receive(&f->rx_radio, &incoming, f->now), NL_ERR_DUPLICATE);
    pull.command = NL_COMMAND_PULL;
    STATUS(nl_radio_handle_frame(&f->rx_radio, &pull, &response, &token), NL_OK);
    STATUS(nl_frame_encode(&response, bytes, sizeof(bytes), &size), NL_OK);
    STATUS(nl_frame_decode(bytes, size, &decoded), NL_OK);
    STATUS(nl_host_receive_frame(&f->receiver, &decoded, f->now), NL_OK);
    STATUS(nl_radio_commit_pull(&f->rx_radio, &response, token), NL_OK);
    CHECK(!nl_radio_ready(&f->rx_radio));
}

static void transfer_one(fixture *f, bool drop)
{
    nl_fragment outgoing, owned;
    nl_window window;
    nl_status result;
    do {
        STATUS(nl_radio_next_window(&f->tx_radio, f->now, &window), NL_OK);
        result = nl_radio_prepare_tx(&f->tx_radio, f->now, &outgoing, &window);
        if (result == NL_ERR_EMPTY) f->now += window.duration_us;
    } while (result == NL_ERR_EMPTY);
    STATUS(result, NL_OK);
    if (!drop) deliver(f, &outgoing);
    STATUS(nl_radio_pop_tx(&f->tx_radio, window.zone, &owned), NL_OK);
    same_fragment(&owned, &outgoing);
    f->now += window.duration_us;
}

static void transfer_all(fixture *f)
{
    while (f->tx_radio.tx[1].count != 0u || f->tx_radio.tx[2].count != 0u)
        transfer_one(f, false);
}

static nl_fragment packet_fragment(const nova_mv_packet_t *packet, uint8_t origin,
                                   uint8_t sequence)
{
    nl_fragment value = {0};
    size_t size;
    value.origin = origin;
    value.zone = 1;
    value.sequence = sequence;
    MV(nl_multiverse_payload_encode(packet, value.payload, sizeof(value.payload), &size), NOVA_MV_OK);
    value.payload_size = (uint8_t)size;
    return value;
}

static void codec(void)
{
    /* Independently generated with Python struct.pack('<BBHIHHHHHH') and
     * zlib.crc32; never generated by the implementation being tested. */
    static const uint8_t golden[] = {
        0x4e, 0x4c, 0x4d, 0x31, 0x00, 0x00, 0x34, 0x12,
        0x04, 0x03, 0x02, 0x01, 0xcd, 0xab, 0x00, 0x00,
        0x03, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00,
        0x00, 0x7e, 0xff, 0xf5, 0x35, 0x63, 0x64
    };
    nova_mv_packet_t packet = {0}, decoded, sentinel;
    uint8_t bytes[NL_PAYLOAD_MAX], saved[NL_PAYLOAD_MAX];
    size_t written = 999;
    packet.kind = NOVA_MV_FULL;
    packet.universe = 0x1234;
    packet.session = UINT32_C(0x01020304);
    packet.sequence = 0xabcd;
    packet.slot_count = packet.span_count = packet.count = 3;
    packet.levels[0] = 0;
    packet.levels[1] = 0x7e;
    packet.levels[2] = 0xff;
    MV(nl_multiverse_payload_encode(&packet, bytes, sizeof(bytes), &written), NOVA_MV_OK);
    CHECK(written == sizeof(golden) && memcmp(bytes, golden, written) == 0);
    MV(nl_multiverse_payload_decode(golden, sizeof(golden), &decoded), NOVA_MV_OK);
    CHECK(decoded.universe == packet.universe && decoded.session == packet.session);
    CHECK(decoded.sequence == packet.sequence && decoded.count == 3);
    CHECK(memcmp(decoded.levels, packet.levels, 3) == 0);
    memset(&sentinel, 0xa5, sizeof(sentinel));
    for (size_t i = 0; i < sizeof(golden); ++i) {
        memcpy(bytes, golden, sizeof(golden));
        bytes[i] ^= 1u;
        decoded = sentinel;
        MV(nl_multiverse_payload_decode(bytes, sizeof(golden), &decoded), NOVA_MV_BAD_PACKET);
        CHECK(memcmp(&decoded, &sentinel, sizeof(decoded)) == 0);
    }
    for (size_t size = 0; size < sizeof(golden); ++size)
        MV(nl_multiverse_payload_decode(golden, size, &decoded), NOVA_MV_BAD_PACKET);
    memset(bytes, 0xa5, sizeof(bytes));
    memcpy(saved, bytes, sizeof(saved));
    MV(nl_multiverse_payload_encode(&packet, bytes, sizeof(golden) - 1u, &written), NOVA_MV_BUFFER_TOO_SMALL);
    CHECK(written == 0 && memcmp(bytes, saved, sizeof(bytes)) == 0);
    packet.slot_count = packet.span_count = packet.count = NL_MULTIVERSE_CHUNK_SLOTS;
    MV(nl_multiverse_payload_encode(&packet, bytes, sizeof(bytes), &written), NOVA_MV_OK);
    CHECK(written == 100);
    MV(nl_multiverse_payload_decode(bytes, written, &decoded), NOVA_MV_OK);
    packet.slot_count = packet.span_count = packet.count = NL_MULTIVERSE_CHUNK_SLOTS + 1u;
    MV(nl_multiverse_payload_encode(&packet, bytes, sizeof(bytes), &written), NOVA_MV_BAD_PACKET);
    CHECK(written == 0);
    MV(nl_multiverse_payload_decode(NULL, 0, &decoded), NOVA_MV_INVALID_ARGUMENT);
    MV(nl_multiverse_payload_decode(golden, sizeof(golden), NULL), NOVA_MV_INVALID_ARGUMENT);
}

static void lifecycle(void)
{
    fixture f;
    nl_host other;
    nl_multiverse_context contender;
    nl_multiverse_config value = config(NL_MULTIVERSE_TX, 1, 1);
    nl_plugin plugin;
    nl_plugin_id failed = NL_PLUGIN_ID_NONE;
    nova_dmx_frame_t frame = levels(1, 1), output;
    setup(&f);
    plugin = nl_multiverse_plugin(&f.tx);
    STATUS(nl_host_register(&f.sender, &plugin, &failed), NL_ERR_BUSY);
    CHECK(failed == NL_PLUGIN_ID_NONE && f.tx.active && !f.tx.stopped);
    CHECK(f.tx.owner == &f.sender && f.tx.id == f.tx_id);
    STATUS(nl_host_init(&other, 3, 0, push, &f.transport), NL_OK);
    STATUS(nl_host_register(&other, &plugin, &failed), NL_ERR_BUSY);
    CHECK(f.tx.active && f.tx.owner == &f.sender);
    MV(nl_multiverse_init(&contender, &value), NOVA_MV_OK);
    plugin = nl_multiverse_plugin(&contender);
    STATUS(nl_host_register(&f.sender, &plugin, &failed), NL_ERR_CONFLICT);
    CHECK(!contender.active && !contender.stopped);
    value = config(NL_MULTIVERSE_RX, 2, 1);
    value.peer_origin = f.receiver.origin;
    MV(nl_multiverse_init(&contender, &value), NOVA_MV_OK);
    plugin = nl_multiverse_plugin(&contender);
    STATUS(nl_host_register(&f.receiver, &plugin, &failed), NL_ERR_CONFLICT);
    CHECK(!contender.active && !contender.stopped);
    MV(nl_multiverse_submit(&f.tx, &frame), NOVA_MV_OK);
    STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
    transfer_all(&f);
    acquire(&f, &frame);
    teardown(&f);
    CHECK(f.tx.stopped && f.rx.stopped && !f.tx.active && !f.rx.active);
    CHECK(nl_zones_active_mask(&f.sender.zones) == 0);
    MV(nl_multiverse_submit(&f.tx, &frame), NOVA_MV_INVALID_ARGUMENT);
    memset(&output, 0xa5, sizeof(output));
    frame = output;
    MV(nl_multiverse_get(&f.rx, f.now, &output), NOVA_MV_INVALID_ARGUMENT);
    CHECK(memcmp(&frame, &output, sizeof(output)) == 0);
    plugin = nl_multiverse_plugin(&f.tx);
    STATUS(nl_host_register(&f.sender, &plugin, &failed), NL_ERR_ARGUMENT);
    value = config(NL_MULTIVERSE_TX, 1, 1);
    value.session++;
    MV(nl_multiverse_init(&f.tx, &value), NOVA_MV_OK);
    plugin = nl_multiverse_plugin(&f.tx);
    STATUS(nl_host_register(&f.sender, &plugin, &f.tx_id), NL_OK);
    STATUS(nl_host_unregister(&f.sender, f.tx_id), NL_OK);
    value.zone = 0;
    MV(nl_multiverse_init(&contender, &value), NOVA_MV_INVALID_ARGUMENT);
    value.zone = 1;
    value.chunks_per_tick = 9;
    MV(nl_multiverse_init(&contender, &value), NOVA_MV_INVALID_ARGUMENT);
}

static void all_slots(void)
{
    fixture f;
    nova_dmx_frame_t previous = {0};
    setup(&f);
    for (unsigned slots = 0; slots <= NOVA_DMX_MAX_SLOTS; ++slots) {
        nova_dmx_frame_t frame = levels((uint16_t)slots, slots);
        uint64_t commits = f.rx.rx.stats.frames;
        MV(nl_multiverse_submit(&f.tx, &frame), NOVA_MV_OK);
        STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
        CHECK(f.tx_radio.tx[1].count == (slots == 0u ? 1u : (slots + 71u) / 72u));
        while (f.tx_radio.tx[1].count != 0u) {
            bool last = f.tx_radio.tx[1].count == 1u;
            transfer_one(&f, false);
            CHECK(f.rx.rx.stats.frames == commits + (last ? 1u : 0u));
            if (last) acquire(&f, &frame);
            else acquire(&f, &previous);
        }
        previous = frame;
    }
    CHECK(f.rx.rx.stats.frames == 513);
    CHECK(f.rx_radio.stats.duplicates > 256);
    CHECK(f.rx.stats.bad_payloads == 0);
    teardown(&f);
}

static void queue_pressure(void)
{
    fixture f;
    nova_dmx_frame_t a = levels(512, 1), b = levels(512, 2), c = levels(512, 3);
    nl_fragment filler = fragment(1, 1, 0), ignored, retry;
    setup(&f);
    for (unsigned i = 0; i < NL_RADIO_TX_DEPTH - 1u; ++i)
        STATUS(nl_radio_enqueue(&f.tx_radio, &filler), NL_OK);
    MV(nl_multiverse_submit(&f.tx, &a), NOVA_MV_OK);
    STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
    CHECK(f.tx.stats.backpressure == 1 && f.tx.tx.active && !f.tx.tx.has_baseline);
    retry = f.transport.attempted;
    CHECK(retry.sequence == 1);
    MV(nl_multiverse_submit(&f.tx, &b), NOVA_MV_OK);
    MV(nl_multiverse_submit(&f.tx, &c), NOVA_MV_OK);
    STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
    same_fragment(&retry, &f.transport.attempted);
    CHECK(f.tx.stats.backpressure == 2);
    for (unsigned i = 0; i < NL_RADIO_TX_DEPTH - 1u; ++i)
        STATUS(nl_radio_pop_tx(&f.tx_radio, 1, &ignored), NL_OK);
    transfer_all(&f);
    CHECK(f.rx.rx.stats.frames == 0);
    STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
    CHECK(f.tx.tx.stats.retries == 2);
    CHECK(f.tx.tx.stats.coalesced == 1);
    CHECK(f.tx_radio.tx[1].count == 7);
    transfer_all(&f);
    acquire(&f, &a);
    STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
    transfer_all(&f);
    acquire(&f, &c);
    CHECK(f.rx.rx.stats.frames == 2 && f.tx.tx.stats.updates == 2);
    teardown(&f);
}

static void loss_recovery(void)
{
    fixture f;
    nova_dmx_frame_t a = levels(512, 1), b = levels(512, 2), output, sentinel;
    uint64_t before;
    setup(&f);
    MV(nl_multiverse_submit(&f.tx, &a), NOVA_MV_OK);
    STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
    transfer_all(&f);
    acquire(&f, &a);
    before = f.rx.rx.last_frame;
    MV(nl_multiverse_submit(&f.tx, &b), NOVA_MV_OK);
    STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
    transfer_one(&f, false);
    transfer_one(&f, true);
    transfer_all(&f);
    CHECK(f.rx.rx.stats.frames == 1);
    acquire(&f, &a);
    f.now = before + f.rx.config.loss_timeout_us;
    STATUS(nl_host_tick(&f.receiver, f.now), NL_OK);
    CHECK(f.rx.rx.link == NOVA_MV_LOST && f.rx.rx.stats.losses == 1);
    memset(&output, 0xa5, sizeof(output));
    sentinel = output;
    MV(nl_multiverse_get(&f.rx, f.now, &output), NOVA_MV_NEED_FULL);
    CHECK(memcmp(&output, &sentinel, sizeof(output)) == 0);
    nl_multiverse_force_full(&f.tx);
    STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
    transfer_all(&f);
    acquire(&f, &b);
    CHECK(f.rx.rx.link == NOVA_MV_LIVE && f.rx.rx.stats.frames == 2);
    teardown(&f);
}

static void filters_and_binding(void)
{
    fixture f;
    nova_mv_packet_t p = {0};
    nl_fragment wire;
    nova_dmx_frame_t expected = levels(3, 9);
    setup(&f);
    p.kind = NOVA_MV_FULL;
    p.universe = 1;
    p.session = 42;
    p.slot_count = p.span_count = p.count = 3;
    memcpy(p.levels, expected.slots, 3);
    wire = packet_fragment(&p, 3, 0);
    deliver(&f, &wire);
    CHECK(f.rx.stats.filtered_origins == 1 && f.rx.rx.stats.frames == 0);
    p.session = 43;
    wire = packet_fragment(&p, 1, 0);
    deliver(&f, &wire);
    CHECK(f.rx.last_result == NOVA_MV_FILTERED);
    p.session = 42;
    p.universe = 2;
    wire = packet_fragment(&p, 1, 1);
    deliver(&f, &wire);
    CHECK(f.rx.last_result == NOVA_MV_FILTERED);
    p.universe = 1;
    wire = packet_fragment(&p, 1, 2);
    wire.flags = NL_FLAG_BURST;
    deliver(&f, &wire);
    CHECK(f.rx.stats.bad_flags == 1 && f.rx.rx.stats.frames == 0);
    wire = packet_fragment(&p, 1, 3);
    wire.payload[24] ^= 1u; /* Valid native framing cannot conceal a failed NLM1 application CRC. */
    deliver(&f, &wire);
    CHECK(f.rx.stats.bad_payloads == 1 && f.rx.rx.stats.frames == 0);
    wire = packet_fragment(&p, 1, 4);
    deliver(&f, &wire);
    acquire(&f, &expected);
    CHECK(f.rx.rx.stats.frames == 1);
    MV(nl_multiverse_bind(&f.rx, 2, 43), NOVA_MV_INVALID_ARGUMENT);
    MV(nl_multiverse_bind(&f.rx, 1, 43), NOVA_MV_OK);
    MV(nl_multiverse_get(&f.rx, f.now, &expected), NOVA_MV_NEED_FULL);
    wire = packet_fragment(&p, 1, 5);
    deliver(&f, &wire);
    CHECK(f.rx.last_result == NOVA_MV_FILTERED);
    p.session = 43;
    wire = packet_fragment(&p, 1, 6);
    deliver(&f, &wire);
    expected = levels(3, 9);
    acquire(&f, &expected);
    CHECK(f.rx.rx.stats.frames == 2);
    teardown(&f);
}

static void clock_and_restart(void)
{
    fixture f;
    nova_dmx_frame_t frame = levels(3, 8), output, sentinel;
    nova_mv_packet_t packet = {0};
    nl_fragment wire;
    unsigned attempts;
    setup(&f);
    f.now = 100;
    MV(nl_multiverse_submit(&f.tx, &frame), NOVA_MV_OK);
    STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
    transfer_all(&f);
    acquire(&f, &frame);
    STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
    transfer_all(&f);
    acquire(&f, &frame);
    memset(&output, 0xa5, sizeof(output));
    sentinel = output;
    MV(nl_multiverse_get(&f.rx, f.now - 1u, &output), NOVA_MV_INVALID_TIME);
    CHECK(memcmp(&output, &sentinel, sizeof(output)) == 0);
    attempts = f.transport.attempts;
    STATUS(nl_host_tick(&f.sender, 0), NL_OK);
    CHECK(f.tx.last_result == NOVA_MV_INVALID_TIME);
    CHECK(f.transport.attempts == attempts);
    MV(nl_multiverse_bind(&f.rx, 1, 43), NOVA_MV_OK);
    packet.kind = NOVA_MV_FULL;
    packet.universe = 1;
    packet.session = 43;
    packet.slot_count = packet.span_count = packet.count = 3;
    memcpy(packet.levels, frame.slots, 3);
    wire = packet_fragment(&packet, 1, 0);
    /* Binding model history does not implicitly discard shared native history. */
    STATUS(nl_radio_receive(&f.rx_radio, &wire, f.now), NL_ERR_STALE);
    STATUS(nl_stream_check(&f.receiver.streams, &wire, f.now), NL_ERR_STALE);
    STATUS(nl_stream_reset_origin(&f.receiver.streams, 1), NL_OK);
    STATUS(nl_radio_receive(&f.rx_radio, &wire, f.now), NL_ERR_STALE);
    STATUS(nl_stream_reset_origin(&f.rx_radio.streams, 1), NL_OK);
    deliver(&f, &wire);
    acquire(&f, &frame);
    CHECK(f.rx.rx.sequence == 0 && f.rx.rx.stats.frames == 3);
    teardown(&f);
}

static void assembly_deadline(void)
{
    fixture f;
    nova_mv_packet_t packet = {0};
    nl_fragment wire;
    nova_dmx_frame_t output, sentinel;
    setup(&f);
    packet.kind = NOVA_MV_FULL;
    packet.universe = 1;
    packet.session = 42;
    packet.slot_count = packet.span_count = 73;
    packet.count = 72;
    memset(packet.levels, 9, 72);
    f.now = 100;
    wire = packet_fragment(&packet, 1, 0);
    deliver(&f, &wire);
    CHECK(f.rx.rx.active && f.rx.rx.stats.frames == 0);
    f.now += f.rx.config.assembly_timeout_us - 1u;
    wire = packet_fragment(&packet, 1, 1);
    deliver(&f, &wire);
    CHECK(f.rx.last_result == NOVA_MV_DUPLICATE);
    CHECK(f.rx.rx.active);
    ++f.now;
    STATUS(nl_host_tick(&f.receiver, f.now), NL_OK);
    CHECK(!f.rx.rx.active && f.rx.rx.stats.abandoned == 1);
    memset(&output, 0xa5, sizeof(output));
    sentinel = output;
    MV(nl_multiverse_get(&f.rx, f.now, &output), NOVA_MV_NEED_FULL);
    CHECK(memcmp(&output, &sentinel, sizeof(output)) == 0);
    teardown(&f);
}

static void independent_universes(void)
{
    fixture f;
    nl_multiverse_context tx2, rx2;
    nl_multiverse_config value = config(NL_MULTIVERSE_TX, 2, 2);
    nl_plugin plugin;
    nl_plugin_id tx_id, rx_id;
    nova_dmx_frame_t a = levels(512, 7), b = levels(512, 99), output;
    setup(&f);
    STATUS(nl_radio_set_active(&f.tx_radio, 6), NL_OK);
    STATUS(nl_radio_set_active(&f.rx_radio, 6), NL_OK);
    MV(nl_multiverse_init(&tx2, &value), NOVA_MV_OK);
    value.role = NL_MULTIVERSE_RX;
    MV(nl_multiverse_init(&rx2, &value), NOVA_MV_OK);
    plugin = nl_multiverse_plugin(&tx2);
    STATUS(nl_host_register(&f.sender, &plugin, &tx_id), NL_OK);
    plugin = nl_multiverse_plugin(&rx2);
    STATUS(nl_host_register(&f.receiver, &plugin, &rx_id), NL_OK);
    MV(nl_multiverse_submit(&f.tx, &a), NOVA_MV_OK);
    MV(nl_multiverse_submit(&tx2, &b), NOVA_MV_OK);
    STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
    transfer_all(&f);
    acquire(&f, &a);
    MV(nl_multiverse_get(&rx2, f.now, &output), NOVA_MV_FRAME_READY);
    same_levels(&output, &b);
    MV(nl_multiverse_bind(&rx2, 1, 43), NOVA_MV_OK);
    MV(nl_multiverse_get(&rx2, f.now, &output), NOVA_MV_NEED_FULL);
    acquire(&f, &a);
    STATUS(nl_host_unregister(&f.sender, tx_id), NL_OK);
    STATUS(nl_host_unregister(&f.receiver, rx_id), NL_OK);
    teardown(&f);
}

static void sequence_wrap(void)
{
    fixture f;
    nova_dmx_frame_t empty = {0};
    setup(&f);
    MV(nl_multiverse_submit(&f.tx, &empty), NOVA_MV_OK);
    for (unsigned i = 0; i < 65540u; ++i) {
        STATUS(nl_host_tick(&f.sender, f.now), NL_OK);
        CHECK(f.tx_radio.tx[1].count == 1);
        CHECK(f.transport.attempted.sequence == (uint8_t)i);
        transfer_all(&f);
        acquire(&f, &empty);
        CHECK(f.rx.rx.sequence == (uint16_t)i);
    }
    CHECK(f.rx.rx.stats.frames == 65540 && f.rx.rx.stats.stale == 0);
    CHECK(f.rx_radio.stats.duplicates == 65540);
    teardown(&f);
}

int main(void)
{
    codec();
    lifecycle();
    all_slots();
    queue_pressure();
    loss_recovery();
    filters_and_binding();
    clock_and_restart();
    assembly_deadline();
    independent_universes();
    sequence_wrap();
    puts("multiverse plugin: native framed TX/RX, all slot counts, atomic delivery, queue pressure, lifecycle, filtering, loss and sequence wrap passed");
    return EXIT_SUCCESS;
}
