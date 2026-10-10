/* SPDX-License-Identifier: GPL-3.0-only */
/* Internal text bridge for replay_multiverse.py. No network or device access. */
#include "nova/multiverse_synthetic.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool number(const char *s, uint64_t maximum, uint64_t *value)
{
    char *end;
    uintmax_t n;
    if (s[0] < '0' || s[0] > '9') return false;
    errno = 0;
    n = strtoumax(s, &end, 10);
    if (errno != 0 || *end != '\0' || n > maximum) return false;
    *value = (uint64_t)n;
    return true;
}
static int nibble(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
static bool decode_hex(const char *text, uint8_t *bytes, size_t *size)
{
    size_t length = strlen(text);
    if (strcmp(text, "-") == 0) { *size = 0; return true; }
    if (length % 2u != 0u || length / 2u > NOVA_MV_SYNTHETIC_MAX_BYTES) return false;
    *size = length / 2u;
    for (size_t i = 0; i < *size; ++i) {
        int hi = nibble(text[2u * i]), lo = nibble(text[2u * i + 1u]);
        if (hi < 0 || lo < 0) return false;
        bytes[i] = (uint8_t)(hi * 16 + lo);
    }
    return true;
}
int main(int argc, char **argv)
{
    nova_mv_rx_t rx;
    nova_mv_rx_config_t config;
    uint64_t universe, session, loss, assembly, end;
    char line[1200];
    if (argc != 6 || !number(argv[1], 63999, &universe) || universe == 0u ||
        !number(argv[2], UINT32_MAX, &session) ||
        !number(argv[3], UINT64_MAX, &loss) || loss == 0u ||
        !number(argv[4], UINT64_MAX, &assembly) || assembly == 0u ||
        !number(argv[5], UINT64_MAX, &end)) {
        fputs("usage: nova-multiverse-replay UNIVERSE SESSION LOSS_US ASSEMBLY_US END_US < normalized.txt\nUse tools/replay_multiverse.py for JSONL logs. Synthetic codec only.\n", stderr);
        return 2;
    }
    config.universe = (uint16_t)universe;
    config.session = (uint32_t)session;
    config.loss_timeout_us = loss;
    config.assembly_timeout_us = assembly;
    if (nova_mv_rx_init(&rx, &config) != NOVA_MV_OK) return 2;
    while (fgets(line, sizeof(line), stdin) != NULL) {
        char *timestamp = strtok(line, " \t\r\n");
        char *crc = strtok(NULL, " \t\r\n");
        char *payload = strtok(NULL, " \t\r\n");
        uint8_t bytes[NOVA_MV_SYNTHETIC_MAX_BYTES];
        uint64_t now;
        size_t size;
        nova_mv_packet_t packet = {0};
        nova_dmx_frame_t frame;
        nova_mv_result_t result;
        nova_mv_integrity_t integrity;
        if (timestamp == NULL || crc == NULL || payload == NULL || strtok(NULL, " \t\r\n") != NULL ||
            !number(timestamp, UINT64_MAX, &now) || !decode_hex(payload, bytes, &size)) goto malformed;
        if (strcmp(crc, "ok") == 0) integrity = NOVA_MV_INTEGRITY_OK;
        else if (strcmp(crc, "bad") == 0) integrity = NOVA_MV_INTEGRITY_BAD;
        else if (strcmp(crc, "unknown") == 0) integrity = NOVA_MV_INTEGRITY_UNKNOWN;
        else goto malformed;
        result = nova_mv_synthetic_decode(bytes, size, &packet);
        if (result != NOVA_MV_OK) integrity = NOVA_MV_INTEGRITY_BAD;
        result = nova_mv_rx_receive(&rx, &packet, integrity, now, &frame);
        if (result == NOVA_MV_INVALID_TIME || result == NOVA_MV_INVALID_ARGUMENT) goto malformed;
        printf("{\"timestamp_us\":%" PRIu64 ",\"result\":\"%s\",\"link\":\"%s\"",
               now, nova_mv_result_name(result), nova_mv_link_name(rx.link));
        if (result == NOVA_MV_FRAME_READY) {
            printf(",\"universe\":%u,\"session\":%" PRIu32 ",\"sequence\":%u,\"slots_hex\":\"",
                   (unsigned)config.universe, config.session, (unsigned)rx.sequence);
            for (unsigned i = 0; i < frame.slot_count; ++i) printf("%02x", (unsigned)frame.slots[i]);
            putchar('"');
        }
        puts("}");
    }
    if (ferror(stdin) || nova_mv_rx_tick(&rx, end) != NOVA_MV_OK) goto malformed;
    printf("{\"summary\":true,\"synthetic\":true,\"multiverse_rf_verified\":false,"
           "\"end_us\":%" PRIu64 ",\"link\":\"%s\",\"frames\":%" PRIu64
           ",\"bad\":%" PRIu64 ",\"unverified\":%" PRIu64 ",\"filtered\":%" PRIu64
           ",\"duplicates\":%" PRIu64 ",\"stale\":%" PRIu64 ",\"missing_base\":%" PRIu64
           ",\"abandoned\":%" PRIu64 ",\"losses\":%" PRIu64 "}\n",
           end, nova_mv_link_name(rx.link), rx.stats.frames, rx.stats.bad, rx.stats.unverified,
           rx.stats.filtered, rx.stats.duplicates, rx.stats.stale, rx.stats.missing_base,
           rx.stats.abandoned, rx.stats.losses);
    return ferror(stdout) ? 2 : 0;
malformed:
    fputs("invalid normalized input or non-monotonic/end timestamp\n", stderr);
    return 2;
}
