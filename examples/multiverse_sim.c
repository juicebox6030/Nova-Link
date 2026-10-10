/* SPDX-License-Identifier: GPL-3.0-only */
#include "nova/multiverse_synthetic.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define REQUIRE(x) do { if (!(x)) { fprintf(stderr, "simulation failed at line %d: %s\n", __LINE__, #x); exit(1); } } while (0)

static uint32_t random_next(uint32_t *state)
{
    *state = *state * UINT32_C(1664525) + UINT32_C(1013904223);
    return *state;
}
static bool number(const char *text, uint32_t *value)
{
    char *end;
    unsigned long parsed;
    if (text[0] < '0' || text[0] > '9') return false;
    errno = 0;
    parsed = strtoul(text, &end, 10);
    if (errno != 0 || *end != '\0' || parsed > UINT32_MAX) return false;
    *value = (uint32_t)parsed;
    return true;
}
static void hex(FILE *file, const uint8_t *bytes, size_t count)
{
    for (size_t i = 0; i < count; ++i) fprintf(file, "%02x", (unsigned)bytes[i]);
}
static void observe(FILE *capture, uint64_t now, const uint8_t *bytes, size_t count,
                    unsigned update, const char *crc, const nova_dmx_frame_t *expected)
{
    if (capture == NULL) return;
    fprintf(capture, "{\"timestamp_us\":%" PRIu64 ",\"frequency_hz\":2405000000,"
            "\"profile\":\"%s\",\"synthetic\":true,\"stimulus\":\"update_%u\","
            "\"crc\":\"%s\",\"payload_hex\":\"", now, NOVA_MV_SYNTHETIC_PROFILE, update, crc);
    hex(capture, bytes, count);
    fputs("\",\"expected_slots_hex\":\"", capture);
    hex(capture, expected->slots, expected->slot_count);
    fputs("\"}\n", capture);
}
static void deliver(nova_mv_rx_t *rx, const nova_mv_packet_t *p, uint64_t now,
                    bool corrupt, bool unknown, unsigned update, FILE *capture,
                    const nova_dmx_frame_t *expected)
{
    uint8_t bytes[NOVA_MV_SYNTHETIC_MAX_BYTES];
    size_t written;
    nova_mv_packet_t decoded = {0};
    nova_dmx_frame_t output;
    nova_mv_integrity_t integrity = unknown ? NOVA_MV_INTEGRITY_UNKNOWN : NOVA_MV_INTEGRITY_OK;
    nova_mv_result_t result;
    REQUIRE(nova_mv_synthetic_encode(p, bytes, sizeof(bytes), &written) == NOVA_MV_OK);
    if (corrupt) bytes[written - 1u] ^= 1u;
    /* 'ok' here is candidate-PHY status: independent software CRC still rejects corruption. */
    observe(capture, now, bytes, written, update, unknown ? "unknown" : "ok", expected);
    if (nova_mv_synthetic_decode(bytes, written, &decoded) != NOVA_MV_OK)
        integrity = NOVA_MV_INTEGRITY_BAD;
    result = nova_mv_rx_receive(rx, &decoded, integrity, now, &output);
    if (result == NOVA_MV_FRAME_READY) {
        REQUIRE(output.slot_count == expected->slot_count);
        REQUIRE(memcmp(output.slots, expected->slots, expected->slot_count) == 0);
    } else REQUIRE(result == NOVA_MV_OK || result == NOVA_MV_DUPLICATE ||
                   result == NOVA_MV_NEED_FULL || result == NOVA_MV_BAD_PACKET ||
                   result == NOVA_MV_UNVERIFIED);
}

int main(int argc, char **argv)
{
    nova_mv_tx_t tx;
    nova_mv_rx_t rx;
    nova_mv_tx_config_t tc = {1, 42, 96, 10000, 50000};
    nova_mv_rx_config_t rc = {1, 42, 100000, 5000};
    nova_dmx_frame_t frame = {0}, final;
    nova_mv_packet_t chunks[6], repeat;
    uint64_t token, repeated_token;
    uint32_t seed = 1, loss = 20;
    unsigned dropped = 0;
    FILE *capture = NULL;
    const char *path = NULL;
    for (int i = 1; i < argc; ++i) {
        if (i + 1 >= argc) goto usage;
        if (strcmp(argv[i], "--capture") == 0) path = argv[++i];
        else if (strcmp(argv[i], "--seed") == 0) {
            if (!number(argv[++i], &seed)) goto usage;
        } else if (strcmp(argv[i], "--loss-percent") == 0) {
            if (!number(argv[++i], &loss) || loss > 100u) goto usage;
        } else goto usage;
    }
    if (path != NULL) {
        capture = fopen(path, "w");
        if (capture == NULL) { perror(path); return 2; }
    }
    REQUIRE(nova_mv_tx_init(&tx, &tc) == NOVA_MV_OK);
    REQUIRE(nova_mv_rx_init(&rx, &rc) == NOVA_MV_OK);
    frame.slot_count = NOVA_DMX_MAX_SLOTS;
    for (unsigned update = 0; update <= 300; ++update) {
        /* Host polls after the prior RF completion plus the refresh interval. */
        uint64_t now = (uint64_t)update * 10100u;
        unsigned count = 0;
        bool drop = update != 300u && update != 0u && random_next(&seed) % 100u < loss;
        frame.slots[(update * 17u) % NOVA_DMX_MAX_SLOTS] = (uint8_t)(update + 1u);
        REQUIRE(nova_mv_tx_submit(&tx, &frame) == NOVA_MV_OK);
        if (update == 300u) nova_mv_tx_force_full(&tx); /* clean final recovery */
        do {
            REQUIRE(count < 6u);
            REQUIRE(nova_mv_tx_prepare(&tx, now + count * 10u, &chunks[count], &token) == NOVA_MV_PACKET_READY);
            REQUIRE(nova_mv_tx_prepare(&tx, now + count * 10u, &repeat, &repeated_token) == NOVA_MV_PACKET_READY);
            REQUIRE(token == repeated_token && memcmp(&repeat, &chunks[count], sizeof(repeat)) == 0);
            if (update % 17u == 3u && count == 0u) {
                REQUIRE(nova_mv_tx_complete(&tx, token, false, now) == NOVA_MV_OK);
                REQUIRE(nova_mv_tx_prepare(&tx, now, &repeat, &repeated_token) == NOVA_MV_PACKET_READY);
                REQUIRE(token != repeated_token && memcmp(&repeat, &chunks[count], sizeof(repeat)) == 0);
                token = repeated_token;
            }
            REQUIRE(nova_mv_tx_complete(&tx, token, true, now + count * 10u) == NOVA_MV_OK);
            ++count;
        } while (tx.active);
        if (drop) { dropped += count; continue; }
        /* Reverse ALL chunks. A completed frame is checked against the exact host snapshot. */
        for (unsigned i = 0; i < count; ++i) {
            uint64_t arrival = now + 100u + i * 20u;
            nova_mv_packet_t *p = &chunks[count - 1u - i];
            bool corrupt = update != 300u && update % 19u == 7u && i == 0u;
            bool unknown = update != 300u && update % 31u == 13u && i == 0u;
            deliver(&rx, p, arrival, corrupt, unknown, update, capture, &frame);
            if (update % 11u == 2u)
                deliver(&rx, p, arrival + 1u, corrupt, unknown, update, capture, &frame);
        }
    }
    REQUIRE(nova_mv_rx_get(&rx, 3030500, &final) == NOVA_MV_FRAME_READY);
    REQUIRE(memcmp(final.slots, frame.slots, frame.slot_count) == 0);
    REQUIRE(nova_mv_rx_tick(&rx, rx.last_frame + rc.loss_timeout_us) == NOVA_MV_OK);
    REQUIRE(rx.link == NOVA_MV_LOST);
    if (capture != NULL && (ferror(capture) || fclose(capture) != 0)) { fputs("capture write failed\n", stderr); return 2; }
    printf("{\"synthetic\":true,\"multiverse_rf_verified\":false,\"tx_updates\":%" PRIu64
           ",\"tx_packets\":%" PRIu64 ",\"submission_retries\":%" PRIu64
           ",\"dropped_packets\":%u,\"rx_frames\":%" PRIu64 ",\"duplicates\":%" PRIu64
           ",\"bad_packets\":%" PRIu64 ",\"unknown_integrity\":%" PRIu64
           ",\"missing_base\":%" PRIu64 ",\"losses\":%" PRIu64
           ",\"final_levels_match\":true,\"loss_detected\":true}\n",
           tx.stats.updates, tx.stats.packets, tx.stats.retries, dropped, rx.stats.frames,
           rx.stats.duplicates, rx.stats.bad, rx.stats.unverified, rx.stats.missing_base, rx.stats.losses);
    return 0;
usage:
    fputs("usage: nova-multiverse-sim [--seed N] [--loss-percent 0..100] [--capture FILE]\n", stderr);
    return 2;
}
