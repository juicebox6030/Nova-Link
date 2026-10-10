/* Field simulation: N nodes share a TDMA RF channel with loss, duplication and
 * reordering; every host<->co-processor link is a byte-wise SPI/UART model with
 * line noise, bit errors, truncated transactions, lost PULL responses and lost
 * commits. Every bit error must be caught by the SPI frame CRC.
 * Plugins verify end-to-end integrity, exactly-once delivery and ordering.
 * With NOVA_SECURITY the "secure" scenarios seal every air frame and an
 * attacker injects forged frames and replays captured ones; none may get in.
 * A fuzz phase then drives random bytes through every decoder.
 *
 * Usage: nova-field-sim [seed] [ticks]
 */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/nova_link.h"

#define NODES 7u
#define TICK_US 250u
#define SLOT_US 1000u
#define IDLE_US 50000u
#define FLIGHT_MAX 4096u
#define PULLS_PER_TICK 2u
#define SLOW_POLL_TICKS 40u /* node 2: a busy host polling every 10 ms */
#define MAGIC 0x4Eu

typedef struct {
    const char *name;
    double loss, dup, reorder, uart_noise, uart_fault, bit_error, pull_loss, commit_loss, burst;
    double send_rate;
    bool reboot;
    bool exact; /* lossless: every sent fragment must arrive */
    int secure; /* 0, or an nl_secure_mode (needs NOVA_SECURITY) */
    double attack; /* per tick: chance the attacker transmits */
} scenario;

typedef struct {
    uint64_t deliveries[NODES + 1u];
    uint32_t last_counter[NODES + 1u];
    uint8_t last_epoch[NODES + 1u];
    bool seen[NODES + 1u];
    uint64_t gaps, integrity, order, duplicates;
} verifier;

typedef struct {
    uint8_t origin;
    bool powered;
    nl_host host;
    nl_radio radio;
    nl_parser mosi, miso;
    nl_plugin_id writer, reader;
    verifier check;
    uint8_t epoch;
    uint32_t next_counter;
    uint64_t sent, backpressure, uart_faults, last_tx_start;
    bool pending, tx_started;
    uint8_t pending_size, pending_flags;
    uint64_t redelivered, pull_lost, commit_lost;
#if NOVA_SECURITY
    nl_secure sec;
    uint32_t nv_counter;                 /* NV: reserved TX counter */
    uint32_t nv_rx_top[NL_ORIGIN_COUNT]; /* NV: replay floors saved at power loss */
    uint8_t nv_rx_known;
#endif
} node;

#if NOVA_SECURITY
#define AIR_MAX NL_SECURE_AIR_MAX
#else
#define AIR_MAX NL_FRAGMENT_MAX
#endif
#define CAPTURE_MAX 64u

typedef struct { uint64_t at; uint8_t dest, size; bool forged; uint8_t bytes[AIR_MAX]; } flight;

static uint64_t rng_state;
static node nodes[NODES + 1u];
static flight air[FLIGHT_MAX];
static size_t air_count;
static uint64_t now_us;
static uint64_t rf_tx, rf_lost, rf_dup, rf_rx_status[NL_ERR_INTEGRITY + 1];
static uint64_t crc_caught, crc_missed;
/* Attacker: records air frames, replays them and injects forgeries. */
static flight captured[CAPTURE_MAX];
static size_t captured_count;
static uint64_t forged_sent, forged_rejected, replays_sent;

static uint32_t rnd(void)
{
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return (uint32_t)(rng_state >> 32);
}

static bool chance(double p) { return (double)rnd() < p * 4294967296.0; }
static uint32_t below(uint32_t n) { return (uint32_t)(((uint64_t)rnd() * n) >> 32); }

static void fail(const char *what, nl_status status)
{
    fprintf(stderr, "FAIL at t=%" PRIu64 " us: %s (%s)\n", now_us, what, nl_status_name(status));
    exit(EXIT_FAILURE);
}

static void require(nl_status status, const char *what)
{
    if (status != NL_OK) fail(what, status);
}

static uint8_t checksum(const uint8_t *bytes, size_t size)
{
    uint8_t sum = 0x5A;
    size_t i;
    for (i = 0; i < size; ++i) sum = (uint8_t)((sum ^ bytes[i]) * 31u + 7u);
    return sum;
}

/* Payload: [MAGIC][origin][epoch][counter:4 BE][filler...][checksum]. */
static uint8_t make_payload(const node *n, uint8_t size, uint8_t *out)
{
    uint8_t i;
    out[0] = MAGIC;
    out[1] = n->origin;
    out[2] = n->epoch;
    out[3] = (uint8_t)(n->next_counter >> 24);
    out[4] = (uint8_t)(n->next_counter >> 16);
    out[5] = (uint8_t)(n->next_counter >> 8);
    out[6] = (uint8_t)n->next_counter;
    if (size > NL_PAYLOAD_MAX) size = NL_PAYLOAD_MAX;
    for (i = 7; i + 1u < size; ++i) out[i] = (uint8_t)(n->next_counter * 7u + i);
    out[size - 1u] = checksum(out, size - 1u);
    return size;
}

static void on_receive(nl_host *host, nl_plugin_id plugin, const nl_fragment *f, void *context)
{
    verifier *v = context;
    uint32_t counter;
    uint8_t origin, epoch;
    (void)host;
    (void)plugin;
    if (f->payload_size < 8u || f->payload[0] != MAGIC ||
        f->payload[f->payload_size - 1u] != checksum(f->payload, f->payload_size - 1u) ||
        f->payload[1] != f->origin || f->zone != f->origin) {
        ++v->integrity;
        return;
    }
    origin = f->origin;
    epoch = f->payload[2];
    counter = (uint32_t)f->payload[3] << 24 | (uint32_t)f->payload[4] << 16 |
              (uint32_t)f->payload[5] << 8 | f->payload[6];
    if (v->seen[origin] && epoch == v->last_epoch[origin]) {
        if (counter == v->last_counter[origin]) ++v->duplicates;
        else if (counter < v->last_counter[origin]) ++v->order;
        else v->gaps += counter - v->last_counter[origin] - 1u;
    } else if (v->seen[origin] && epoch < v->last_epoch[origin]) {
        ++v->order;
    }
    v->seen[origin] = true;
    v->last_epoch[origin] = epoch;
    v->last_counter[origin] = counter;
    ++v->deliveries[origin];
}

/* Host -> co-processor PUSH over one SPI transaction. */
static nl_status uart_push(void *context, const nl_fragment *fragment);

static const scenario *active;

static void feed_garbage(nl_parser *parser)
{
    nl_frame junk;
    uint32_t i, count = 1u + below(24);
    for (i = 0; i < count; ++i)
        if (nl_parser_feed(parser, (uint8_t)rnd(), &junk) == NL_PARSE_READY &&
            nl_frame_validate(&junk) != NL_OK) fail("parser emitted invalid frame from noise", NL_ERR_FORMAT);
    nl_parser_reset(parser); /* transaction boundary */
}

/* Flip 1-3 bits of an encoded frame in place. CRC-16/CCITT has an (x+1)
 * factor and detects every 1-3 bit error in frames this short.
 */
static void flip_bits(uint8_t *bytes, size_t size)
{
    uint32_t k, flips = 1u + below(3);
    for (k = 0; k < flips; ++k) bytes[below((uint32_t)size)] ^= (uint8_t)(1u << below(8));
}

/* Feed a whole transaction; true only when a frame identical to the sent one
 * came out. A different frame accepted by the parser is an undetected error.
 */
static bool spi_transfer(nl_parser *parser, const uint8_t *bytes, size_t size,
                         const nl_frame *sent, nl_frame *parsed, bool corrupted)
{
    nl_parse_result result = NL_PARSE_WAIT;
    size_t i;
    for (i = 0; i < size && result != NL_PARSE_READY; ++i) result = nl_parser_feed(parser, bytes[i], parsed);
    if (result != NL_PARSE_READY) {
        if (!corrupted) fail("clean frame lost by parser", NL_ERR_FORMAT);
        ++crc_caught;
        nl_parser_reset(parser); /* transaction boundary */
        return false;
    }
    if (i != size || parsed->command != sent->command || parsed->data_size != sent->data_size ||
        memcmp(parsed->data, sent->data, sent->data_size) != 0) {
        ++crc_missed;
        nl_parser_reset(parser);
        return false;
    }
    return true;
}

static nl_status uart_push(void *context, const nl_fragment *fragment)
{
    node *n = context;
    nl_frame frame, parsed;
    uint8_t bytes[NL_FRAME_MAX];
    size_t size, i;
    bool corrupted;
    require(nl_frame_from_fragment(NL_COMMAND_PUSH, fragment, &frame), "encode push");
    require(nl_frame_encode(&frame, bytes, sizeof(bytes), &size), "serialize push");
    if (chance(active->uart_noise)) feed_garbage(&n->mosi);
    if (chance(active->uart_fault)) {
        size_t cut = below((uint32_t)size);
        for (i = 0; i < cut; ++i) (void)nl_parser_feed(&n->mosi, bytes[i], &parsed);
        nl_parser_reset(&n->mosi);
        ++n->uart_faults;
        return NL_ERR_FORMAT; /* adapter reports a failed transaction */
    }
    corrupted = chance(active->bit_error);
    if (corrupted) flip_bits(bytes, size);
    if (!spi_transfer(&n->mosi, bytes, size, &frame, &parsed, corrupted)) {
        ++n->uart_faults;
        return NL_ERR_FORMAT; /* co-processor NAKs; the host retries the send */
    }
    return nl_radio_handle_frame(&n->radio, &parsed, NULL, NULL);
}

#if NOVA_SECURITY
static const uint8_t network_key[16] = {0x4E, 0x6F, 0x76, 0x61, 0x2D, 0x4C, 0x69, 0x6E,
                                        0x6B, 0x20, 0x66, 0x69, 0x65, 0x6C, 0x64, 0x21};

static nl_status persist_counter(void *context, uint32_t reserved_until)
{
    ((node *)context)->nv_counter = reserved_until; /* a real port writes flash here */
    return NL_OK;
}
#endif

static void power_on(node *n)
{
    nl_plugin writer = {0};
    nl_plugin reader = {NULL, on_receive, NULL, NULL, NULL};
    uint8_t zone;
    reader.context = &n->check;
    require(nl_radio_init(&n->radio, 0xFEu, SLOT_US, SLOT_US / 2u, IDLE_US), "radio init");
    if (n->origin == 2u) require(nl_radio_set_rx_policy(&n->radio, NL_RX_LATEST_PER_STREAM), "rx policy");
    require(nl_host_init(&n->host, n->origin, IDLE_US, uart_push, n), "host init");
    nl_parser_reset(&n->mosi);
    nl_parser_reset(&n->miso);
    require(nl_host_register(&n->host, &writer, &n->writer), "register writer");
    require(nl_host_claim(&n->host, n->writer, n->origin, NL_ZONE_EXCLUSIVE), "claim own zone");
    require(nl_host_register(&n->host, &reader, &n->reader), "register reader");
    for (zone = 1; zone <= NODES; ++zone)
        if (zone != n->origin) require(nl_host_claim(&n->host, n->reader, zone, NL_ZONE_READ_ONLY), "claim peer zone");
    n->powered = true;
    n->pending = false;
    n->tx_started = false;
    n->next_counter = 0;
#if NOVA_SECURITY
    if (active->secure) {
        uint8_t o;
        require(nl_secure_init(&n->sec, network_key, (nl_secure_mode)active->secure, n->nv_counter,
                               persist_counter, n), "secure init");
        for (o = 0; o < NL_ORIGIN_COUNT; ++o)
            if (n->nv_rx_known & (1u << o)) require(nl_secure_set_rx_floor(&n->sec, o, n->nv_rx_top[o]), "rx floor");
    }
#endif
}

static void produce(node *n, bool producing)
{
    uint8_t payload[NL_PAYLOAD_MAX];
    nl_status status;
    if (!n->pending) {
        if (!producing || !chance(active->send_rate)) return;
        n->pending = true;
        n->pending_size = (uint8_t)(8u + below(NL_PAYLOAD_MAX - 7u));
        n->pending_flags = chance(active->burst) ? NL_FLAG_BURST : 0u;
    }
    status = nl_host_send(&n->host, n->writer, n->origin, n->pending_flags, payload,
                          make_payload(n, n->pending_size, payload));
    if (status == NL_OK) {
        ++n->next_counter;
        ++n->sent;
        n->pending = false;
    } else if (status == NL_ERR_FULL) {
        ++n->backpressure;
    } else if (status != NL_ERR_FORMAT) {
        fail("host send", status);
    }
}

static void transmit(node *n)
{
    nl_window window;
    nl_fragment fragment;
    nl_status status;
    uint8_t bytes[AIR_MAX];
    size_t size;
    uint8_t dest;
    status = nl_radio_next_window(&n->radio, now_us, &window);
    if (status != NL_OK && status != NL_ERR_BUSY && status != NL_ERR_EMPTY) fail("next window", status);
    status = nl_radio_prepare_tx(&n->radio, now_us, &fragment, &window);
    if (status == NL_ERR_EMPTY || status == NL_ERR_NOT_FOUND) return;
    require(status, "prepare tx");
    if (n->tx_started && window.start_us == n->last_tx_start) return; /* one fragment per window */
    n->tx_started = true;
    n->last_tx_start = window.start_us;
#if NOVA_SECURITY
    if (active->secure) require(nl_secure_seal(&n->sec, &fragment, bytes, sizeof(bytes), &size), "rf seal");
    else
#endif
    require(nl_fragment_encode(&fragment, bytes, sizeof(bytes), &size), "rf encode");
    ++rf_tx;
    if (active->attack > 0.0) { /* the attacker hears everything */
        flight *rec = &captured[captured_count < CAPTURE_MAX ? captured_count++ : below(CAPTURE_MAX)];
        rec->dest = n->origin; /* remembered as the source */
        rec->size = (uint8_t)size;
        memcpy(rec->bytes, bytes, size);
    }
    for (dest = 1; dest <= NODES; ++dest) {
        unsigned copies, c;
        if (dest == n->origin) continue;
        if (chance(active->loss)) { ++rf_lost; continue; }
        copies = chance(active->dup) ? 2u : 1u;
        rf_dup += copies - 1u;
        for (c = 0; c < copies; ++c) {
            flight *slot;
            if (air_count == FLIGHT_MAX) fail("air overflow", NL_ERR_FULL);
            slot = &air[air_count++];
            slot->at = now_us + (chance(active->reorder) ? (1u + below(20)) * SLOT_US : 0u);
            slot->dest = dest;
            slot->forged = false;
            slot->size = (uint8_t)size;
            memcpy(slot->bytes, bytes, size);
        }
    }
    require(nl_radio_pop_tx(&n->radio, window.zone, &fragment), "pop tx");
}

static void deliver_air(void)
{
    size_t i = 0;
    while (i < air_count) {
        flight *f = &air[i];
        if (f->at <= now_us) {
            node *n = &nodes[f->dest];
            if (n->powered) {
                nl_status status;
#if NOVA_SECURITY
                if (active->secure) {
                    status = nl_radio_receive_sealed(&n->radio, &n->sec, f->bytes, f->size, now_us);
                    if (f->forged) {
                        if (status != NL_ERR_INTEGRITY) fail("forged frame accepted", status);
                        ++forged_rejected;
                    } else if (status == NL_ERR_INTEGRITY) {
                        fail("authentic frame rejected", status);
                    }
                } else
#endif
                {
                    nl_fragment fragment;
                    require(nl_fragment_decode(f->bytes, f->size, &fragment), "rf decode");
                    status = nl_radio_receive(&n->radio, &fragment, now_us);
                }
                if (status != NL_OK && status != NL_ERR_DUPLICATE && status != NL_ERR_STALE &&
                    status != NL_ERR_FULL && status != NL_ERR_INTEGRITY) fail("radio receive", status);
                ++rf_rx_status[status];
            }
            *f = air[--air_count]; /* order among same-tick arrivals is irrelevant */
        } else {
            ++i;
        }
    }
}

static void pull(node *n, unsigned limit)
{
    unsigned k;
    for (k = 0; k < limit && nl_radio_ready(&n->radio); ++k) {
        nl_frame request = {0}, response, parsed;
        nl_pull_token token;
        uint8_t bytes[NL_FRAME_MAX];
        size_t size, i, cut;
        bool corrupted;
        nl_status status;
        request.command = NL_COMMAND_PULL;
        require(nl_radio_handle_frame(&n->radio, &request, &response, &token), "pull");
        require(nl_frame_encode(&response, bytes, sizeof(bytes), &size), "serialize pull");
        nl_parser_reset(&n->miso);
        if (chance(active->uart_noise)) feed_garbage(&n->miso);
        if (chance(active->pull_loss)) {
            cut = below((uint32_t)size);
            for (i = 0; i < cut; ++i) (void)nl_parser_feed(&n->miso, bytes[i], &parsed);
            ++n->pull_lost;
            continue; /* host never saw it; radio keeps ownership */
        }
        corrupted = chance(active->bit_error);
        if (corrupted) flip_bits(bytes, size);
        if (!spi_transfer(&n->miso, bytes, size, &response, &parsed, corrupted)) {
            ++n->pull_lost;
            continue; /* rejected by CRC; radio keeps ownership and re-sends */
        }
        status = nl_host_receive_frame(&n->host, &parsed, now_us);
        if (status == NL_ERR_DUPLICATE) ++n->redelivered;
        else require(status, "host receive");
        if (chance(active->commit_loss)) { ++n->commit_lost; continue; }
        require(nl_radio_commit_pull(&n->radio, &parsed, token), "commit pull");
    }
}

/* The attacker replays a captured frame, or forges one: a captured frame with
 * flipped bits, or a well-formed header carrying random bytes.
 */
static void attack(void)
{
    flight *slot;
    if (captured_count == 0u || !chance(active->attack)) return;
    if (air_count == FLIGHT_MAX) fail("air overflow", NL_ERR_FULL);
    slot = &air[air_count++];
    *slot = captured[below((uint32_t)captured_count)];
    slot->at = now_us;
    slot->dest = (uint8_t)(1u + (slot->dest + below(NODES - 1u)) % NODES); /* any node but the source */
    slot->forged = chance(0.5);
    if (!slot->forged) { ++replays_sent; return; }
    ++forged_sent;
    if (chance(0.5)) {
        slot->bytes[below(slot->size)] ^= (uint8_t)(1u << below(8)); /* one bit: never cancels out */
    } else {
        uint32_t k;
        for (k = NL_FRAGMENT_MIN; k < slot->size; ++k) slot->bytes[k] = (uint8_t)rnd();
        slot->bytes[slot->size - 1u] ^= 0x01; /* tamper even if rnd() reproduced the MIC tail */
    }
}

/* Power loss: queues, trackers and sequence numbers are lost; the epoch in the
 * payload lets verifiers distinguish a restart from reordering. A secure node
 * keeps its NV counter and saves its replay floors (brown-out handler).
 */
static void power_off(node *n)
{
    n->powered = false;
    n->epoch = (uint8_t)(n->epoch + 1u);
#if NOVA_SECURITY
    memcpy(n->nv_rx_top, n->sec.rx_top, sizeof(n->nv_rx_top));
    n->nv_rx_known = n->sec.rx_known;
#endif
}

static int run(const scenario *s, uint64_t seed, uint64_t ticks)
{
    uint64_t t, reboot_at = ticks / 2u, reboot_until = 0;
    uint64_t sent_total = 0, delivered_total = 0, expected = 0, coalesced = 0;
    uint64_t integrity = 0, order = 0, duplicates = 0, backpressure = 0;
    uint64_t uart_faults = 0, redelivered = 0, pull_lost = 0, commit_lost = 0, rx_full = 0;
    uint8_t i, j;
    int ok = 1;
    active = s;
    rng_state = seed ? seed : 1u;
    memset(nodes, 0, sizeof(nodes));
    memset(rf_rx_status, 0, sizeof(rf_rx_status));
    air_count = 0;
    captured_count = 0;
    forged_sent = forged_rejected = replays_sent = 0;
    now_us = 0;
    rf_tx = rf_lost = rf_dup = 0;
    for (i = 1; i <= NODES; ++i) {
        nodes[i].origin = i;
        power_on(&nodes[i]);
    }
    /* Run, then drain with producers stopped so in-flight data settles. */
    for (t = 0; t < ticks + 4000u; ++t, now_us += TICK_US) {
        bool producing = t < ticks;
        if (s->reboot && t == reboot_at) {
            power_off(&nodes[3]);
            reboot_until = now_us + 3u * IDLE_US;
        }
        if (s->reboot && !nodes[3].powered && now_us >= reboot_until) {
            uint8_t epoch = nodes[3].epoch;
            uint64_t sent = nodes[3].sent;
            power_on(&nodes[3]);
            nodes[3].epoch = epoch;
            nodes[3].sent = sent;
        }
        if (producing) attack();
        deliver_air();
        for (i = 1; i <= NODES; ++i) {
            node *n = &nodes[i];
            if (!n->powered) continue;
            produce(n, producing);
            transmit(n);
            if (i != 2u) pull(n, PULLS_PER_TICK);
            else if (t % SLOW_POLL_TICKS == 0u) pull(n, NL_RADIO_RX_DEPTH);
            require(nl_host_tick(&n->host, now_us), "host tick");
        }
    }
    for (i = 1; i <= NODES; ++i) {
        const node *n = &nodes[i];
        sent_total += n->sent;
        integrity += n->check.integrity;
        order += n->check.order;
        duplicates += n->check.duplicates;
        backpressure += n->backpressure;
        uart_faults += n->uart_faults;
        redelivered += n->redelivered;
        pull_lost += n->pull_lost;
        commit_lost += n->commit_lost;
        rx_full += n->radio.stats.rx_full;
        coalesced += n->radio.stats.coalesced;
        if (n->radio.rx.count != 0u) { fprintf(stderr, "node %u RX not drained\n", i); ok = 0; }
        if (s->reboot && i != 3u && n->check.last_epoch[3] != nodes[3].epoch) {
            fprintf(stderr, "node %u never resumed node 3 after its reboot\n", i);
            ok = 0;
        }
        for (j = 1; j <= NODES; ++j) {
            if (j == i) continue;
            delivered_total += n->check.deliveries[j];
            expected += nodes[j].sent;
            if (s->exact && i != 2u && n->check.deliveries[j] != nodes[j].sent) {
                fprintf(stderr, "node %u got %" PRIu64 "/%" PRIu64 " from %u\n", i,
                    n->check.deliveries[j], nodes[j].sent, j);
                ok = 0;
            }
        }
        if (s->exact && i == 2u) {
            uint64_t inbound = 0, got = 0;
            for (j = 1; j <= NODES; ++j) {
                if (j == 2u) continue;
                inbound += nodes[j].sent;
                got += n->check.deliveries[j];
            }
            if (got + n->radio.stats.coalesced != inbound) {
                fprintf(stderr, "LATEST node: %" PRIu64 " + %" PRIu64 " coalesced != %" PRIu64 "\n",
                    got, n->radio.stats.coalesced, inbound);
                ok = 0;
            }
        }
    }
    if (integrity || order || duplicates || (s->exact && rx_full)) ok = 0;
#if NOVA_SECURITY
    if (s->secure) {
        uint64_t replayed = 0, too_old = 0;
        for (i = 1; i <= NODES; ++i) {
            replayed += nodes[i].sec.stats.replayed;
            too_old += nodes[i].sec.stats.too_old;
        }
        if (forged_rejected == 0u || replays_sent == 0u) ok = 0;
        printf("  attacker: %" PRIu64 " forgeries, %" PRIu64 " reached a node, all rejected; %" PRIu64
               " replays; counters refused %" PRIu64 " dup + %" PRIu64 " stale\n",
            forged_sent, forged_rejected, replays_sent, replayed, too_old);
    }
#endif
    printf("%-9s %7.3fs %7" PRIu64 " %8" PRIu64 " %6.2f%% %6" PRIu64 " %6" PRIu64 " %5" PRIu64
           " %5" PRIu64 " %5" PRIu64 " %5" PRIu64 " %6" PRIu64 " | integ=%" PRIu64 " order=%" PRIu64
           " dup=%" PRIu64 " %s\n",
        s->name, (double)now_us / 1e6, sent_total, delivered_total,
        expected ? 100.0 * (double)delivered_total / (double)expected : 0.0,
        rf_rx_status[NL_ERR_DUPLICATE], rf_rx_status[NL_ERR_STALE], coalesced, rx_full,
        uart_faults + pull_lost + commit_lost, redelivered, backpressure,
        integrity, order, duplicates, ok ? "PASS" : "FAIL");
    return ok;
}

/* Random bytes through every decoder; all accepted input must round-trip. */
static int fuzz(uint64_t seed, unsigned rounds)
{
    nl_parser parser;
    nl_frame frame, again;
    nl_fragment fragment;
    uint8_t bytes[NL_FRAME_MAX + 16u], out[NL_FRAME_MAX];
    size_t size;
    unsigned r, ready = 0, decoded = 0;
    rng_state = seed ^ 0x9E3779B97F4A7C15u;
    active = &(scenario){"fuzz", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, false, false, 0, 0.0};
    memset(nodes, 0, sizeof(nodes));
    nodes[1].origin = 1;
    power_on(&nodes[1]);
    nl_parser_reset(&parser);
    static const uint8_t commands[] = {NL_COMMAND_PING, NL_COMMAND_PULL, NL_COMMAND_PUSH,
                                       NL_COMMAND_STATUS, NL_COMMAND_FRAGMENT, 0x00, 0xFF};
    uint8_t script[NL_FRAME_MAX];
    size_t script_size = 0, script_at = 0;
    for (r = 0; r < rounds; ++r) {
        uint8_t byte;
        if (script_at == script_size) {
            /* Next: a well-formed-looking frame (often mutated) or raw noise. */
            uint32_t k, len = below(NL_FRAME_BODY_MAX + 2u);
            script_size = 0;
            script_at = 0;
            script[script_size++] = chance(0.9) ? NL_TRANSPORT_SYNC : (uint8_t)rnd();
            script[script_size++] = (uint8_t)len;
            for (k = 0; k < len && script_size < sizeof(script); ++k)
                script[script_size++] = k == 0u ? commands[below(sizeof(commands))] : (uint8_t)rnd();
            if (chance(0.8) && script_size + 2u <= sizeof(script)) { /* usually a valid CRC */
                uint16_t crc = nl_crc16(0xFFFFu, script + 1, script_size - 1u);
                script[script_size++] = (uint8_t)(crc >> 8);
                script[script_size++] = (uint8_t)crc;
            }
            if (chance(0.3)) script[below((uint32_t)script_size)] = (uint8_t)rnd();
        }
        byte = script[script_at++];
        if (nl_parser_feed(&parser, byte, &frame) == NL_PARSE_READY) {
            nl_frame response;
            nl_pull_token token;
            ++ready;
            if (nl_frame_validate(&frame) != NL_OK) { fprintf(stderr, "fuzz: invalid READY frame\n"); return 0; }
            require(nl_frame_encode(&frame, out, sizeof(out), &size), "fuzz re-encode");
            require(nl_frame_decode(out, size, &again), "fuzz re-decode");
            if (again.command != frame.command || again.data_size != frame.data_size ||
                memcmp(again.data, frame.data, frame.data_size) != 0) { fprintf(stderr, "fuzz: frame round trip\n"); return 0; }
            (void)nl_radio_handle_frame(&nodes[1].radio, &frame, &response, &token);
            (void)nl_host_receive_frame(&nodes[1].host, &frame, r);
            if (nl_radio_ready(&nodes[1].radio)) (void)nl_radio_pull(&nodes[1].radio, &fragment);
            (void)nl_radio_pop_tx(&nodes[1].radio, frame.data_size ? (uint8_t)((frame.data[0] >> 2) & 7u) : 0u, &fragment);
        }
        if (below(1000) == 0u) nl_parser_reset(&parser);
    }
    for (r = 0; r < rounds / 8u; ++r) {
        uint32_t i, n = below(sizeof(bytes));
        for (i = 0; i < n; ++i) bytes[i] = (uint8_t)rnd();
        if (nl_frame_decode(bytes, n, &frame) == NL_OK) ++decoded;
        if (nl_fragment_decode(bytes, n, &fragment) == NL_OK) {
            ++decoded;
            require(nl_fragment_encode(&fragment, out, sizeof(out), &size), "fuzz fragment encode");
            if (size != n || memcmp(out, bytes, n) != 0) { fprintf(stderr, "fuzz: fragment round trip\n"); return 0; }
        }
    }
    printf("fuzz: %u parser bytes -> %u frames, %u random buffers decoded, all round-tripped: PASS\n",
        rounds, ready, decoded);
    return 1;
}

int main(int argc, char **argv)
{
    static const scenario scenarios[] = {
        /* name     loss  dup   reord noise fault biterr pullL commL burst rate  reboot exact  secure attack */
        {"ideal",   0.00, 0.00, 0.00, 0.00, 0.00, 0.000, 0.00, 0.00, 0.00, 0.020, false, true,  0, 0.0},
        {"typical", 0.05, 0.10, 0.10, 0.02, 0.01, 0.005, 0.01, 0.01, 0.05, 0.030, false, false, 0, 0.0},
        {"hostile", 0.30, 0.30, 0.30, 0.10, 0.05, 0.050, 0.05, 0.05, 0.20, 0.040, false, false, 0, 0.0},
        {"noisy",   0.02, 0.02, 0.02, 0.05, 0.00, 0.200, 0.00, 0.00, 0.05, 0.030, false, false, 0, 0.0},
        {"reboot",  0.05, 0.10, 0.10, 0.02, 0.01, 0.005, 0.01, 0.01, 0.05, 0.030, true,  false, 0, 0.0},
        {"overload",0.02, 0.05, 0.05, 0.01, 0.01, 0.005, 0.01, 0.01, 0.50, 0.500, false, false, 0, 0.0},
#if NOVA_SECURITY
        {"sec-auth",0.00, 0.00, 0.00, 0.00, 0.00, 0.000, 0.00, 0.00, 0.00, 0.020, false, true,  NL_SECURE_AUTH, 0.05},
        {"sec-enc", 0.05, 0.10, 0.10, 0.02, 0.01, 0.005, 0.01, 0.01, 0.05, 0.030, true,  false, NL_SECURE_ENCRYPT, 0.05},
        {"sec-host",0.30, 0.30, 0.30, 0.10, 0.05, 0.050, 0.05, 0.05, 0.20, 0.040, true,  false, NL_SECURE_ENCRYPT, 0.20},
#endif
    };
    uint64_t seed = argc > 1 ? strtoull(argv[1], NULL, 0) : 0xC0FFEEu;
    uint64_t ticks = argc > 2 ? strtoull(argv[2], NULL, 0) : 200000u;
    size_t i;
    int ok = 1;
    printf("NOVA-LINK field simulation: %u nodes, TDMA %u us slots, seed=0x%" PRIx64 ", %" PRIu64 " ticks\n",
        NODES, SLOT_US, seed, ticks);
    printf("%-9s %8s %7s %8s %7s %6s %6s %5s %5s %5s %5s %6s\n", "scenario", "time", "sent", "deliver",
        "ratio", "rfDup", "stale", "coal", "rxFul", "spiF", "redlv", "bkpr");
    for (i = 0; i < sizeof(scenarios) / sizeof(scenarios[0]); ++i)
        ok &= run(&scenarios[i], seed + i, ticks);
    printf("SPI bit errors: %" PRIu64 " corrupted frames rejected by CRC, %" PRIu64 " undetected: %s\n",
        crc_caught, crc_missed, crc_missed == 0u && crc_caught != 0u ? "PASS" : "FAIL");
    ok &= crc_missed == 0u && crc_caught != 0u;
    ok &= fuzz(seed, 2000000u);
    puts(ok ? "field simulation: PASS" : "field simulation: FAIL");
    return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
