/* SPDX-License-Identifier: GPL-3.0-only */
#include "nova/dmx.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Keep checks active in Release builds as well as Debug builds. */
#define CHECK(expression) do { \
    if (!(expression)) { \
        fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #expression); \
        exit(1); \
    } \
} while (0)

static void start_packet(nova_dmx_rx_t *rx)
{
    nova_dmx_frame_t completed;
    CHECK(nova_dmx_rx_break(rx, 100, &completed) == NOVA_DMX_OK);
    CHECK(nova_dmx_rx_mark(rx, 12) == NOVA_DMX_OK);
}

static void test_roundtrip(void)
{
    nova_dmx_frame_t frame = {0};
    nova_dmx_frame_t completed;
    nova_dmx_rx_t rx;
    uint8_t packet[NOVA_DMX_MAX_PACKET_BYTES];
    size_t written;

    /* Includes short universes, exact chunk boundaries, and all 512 slots. */
    for (unsigned slots = 0; slots <= NOVA_DMX_MAX_SLOTS; ++slots) {
        frame.slot_count = (uint16_t)slots;
        for (unsigned i = 0; i < slots; ++i) {
            frame.slots[i] = (uint8_t)(i * 37u + slots);
        }
        CHECK(nova_dmx_encode(&frame, packet, sizeof(packet), &written) == NOVA_DMX_OK);
        CHECK(written == slots + 1u);
        CHECK(packet[0] == 0);
        nova_dmx_rx_reset(&rx);
        start_packet(&rx);
        for (size_t offset = 0; offset < written;) {
            size_t chunk = written - offset;
            if (chunk > 17u) {
                chunk = 17u;
            }
            CHECK(nova_dmx_rx_bytes(&rx, packet + offset, chunk) == NOVA_DMX_OK);
            offset += chunk;
        }
        memset(&completed, 0xAA, sizeof(completed));
        CHECK(nova_dmx_rx_break(&rx, 88, &completed) == NOVA_DMX_FRAME_READY);
        CHECK(completed.slot_count == slots);
        CHECK(memcmp(completed.slots, frame.slots, slots) == 0);
        for (size_t i = slots; i < NOVA_DMX_MAX_SLOTS; ++i) {
            CHECK(completed.slots[i] == 0);
        }
    }
}

static void test_invalid_packets_and_recovery(void)
{
    nova_dmx_rx_t rx;
    nova_dmx_frame_t completed = {0};
    const uint8_t valid[] = {0x00, 0xAA, 0x55};
    uint8_t oversized[NOVA_DMX_MAX_PACKET_BYTES + 1u] = {0};
    const uint8_t alternate_codes[] = {0xCC, 0x17, 0xFF};

    nova_dmx_rx_reset(&rx);
    CHECK(nova_dmx_rx_bytes(&rx, valid, sizeof(valid)) == NOVA_DMX_IGNORED);
    start_packet(&rx);
    CHECK(nova_dmx_rx_bytes(&rx, valid, sizeof(valid)) == NOVA_DMX_OK);
    CHECK(nova_dmx_rx_break(&rx, 87, &completed) == NOVA_DMX_INVALID_TIMING);
    CHECK(nova_dmx_rx_bytes(&rx, valid, sizeof(valid)) == NOVA_DMX_IGNORED);
    start_packet(&rx);
    CHECK(nova_dmx_rx_bytes(&rx, oversized, sizeof(oversized)) == NOVA_DMX_TOO_MANY_SLOTS);
    CHECK(nova_dmx_rx_break(&rx, 88, &completed) == NOVA_DMX_OK);
    CHECK(nova_dmx_rx_mark(&rx, 7) == NOVA_DMX_INVALID_TIMING);
    CHECK(nova_dmx_rx_bytes(&rx, valid, sizeof(valid)) == NOVA_DMX_IGNORED);

    for (size_t i = 0; i < sizeof(alternate_codes); ++i) {
        start_packet(&rx);
        CHECK(nova_dmx_rx_bytes(&rx, alternate_codes + i, 1) == NOVA_DMX_UNSUPPORTED_START_CODE);
        CHECK(nova_dmx_rx_bytes(&rx, valid, sizeof(valid)) == NOVA_DMX_IGNORED);
    }
    start_packet(&rx);
    CHECK(nova_dmx_rx_bytes(&rx, valid, sizeof(valid)) == NOVA_DMX_OK);
    CHECK(nova_dmx_rx_break(&rx, 100, &completed) == NOVA_DMX_FRAME_READY);
    CHECK(completed.slot_count == 2);
    CHECK(completed.slots[0] == 0xAA && completed.slots[1] == 0x55);

    /* Overflow arriving in a later UART chunk still invalidates the packet. */
    CHECK(nova_dmx_rx_mark(&rx, 8) == NOVA_DMX_OK);
    CHECK(nova_dmx_rx_bytes(&rx, oversized, NOVA_DMX_MAX_PACKET_BYTES) == NOVA_DMX_OK);
    CHECK(nova_dmx_rx_bytes(&rx, oversized, 1) == NOVA_DMX_TOO_MANY_SLOTS);
    CHECK(nova_dmx_rx_break(&rx, 88, &completed) == NOVA_DMX_OK);
    CHECK(completed.slot_count == 2); /* no delivery of the rejected packet */
}

static void test_errors(void)
{
    nova_dmx_frame_t frame = {0};
    nova_dmx_frame_t completed;
    nova_dmx_rx_t rx;
    uint8_t output[3] = {0xCC, 0xCC, 0xCC};
    const uint8_t packet[] = {0x00, 0x01};
    size_t written = 99;

    frame.slot_count = 3;
    CHECK(nova_dmx_encode(&frame, output, sizeof(output), &written) == NOVA_DMX_BUFFER_TOO_SMALL);
    CHECK(written == 0 && output[0] == 0xCC && output[2] == 0xCC);
    frame.slot_count = NOVA_DMX_MAX_SLOTS + 1u;
    CHECK(nova_dmx_encode(&frame, output, sizeof(output), &written) == NOVA_DMX_INVALID_ARGUMENT);
    CHECK(nova_dmx_encode(NULL, output, sizeof(output), &written) == NOVA_DMX_INVALID_ARGUMENT);
    CHECK(nova_dmx_encode(&frame, NULL, 0, &written) == NOVA_DMX_INVALID_ARGUMENT);
    CHECK(nova_dmx_encode(&frame, output, sizeof(output), NULL) == NOVA_DMX_INVALID_ARGUMENT);
    nova_dmx_rx_reset(NULL);
    CHECK(nova_dmx_rx_break(NULL, 88, &completed) == NOVA_DMX_INVALID_ARGUMENT);
    CHECK(nova_dmx_rx_mark(NULL, 8) == NOVA_DMX_INVALID_ARGUMENT);
    CHECK(nova_dmx_rx_bytes(NULL, packet, sizeof(packet)) == NOVA_DMX_INVALID_ARGUMENT);
    nova_dmx_rx_reset(&rx);
    CHECK(nova_dmx_rx_bytes(&rx, NULL, 0) == NOVA_DMX_OK);
    CHECK(nova_dmx_rx_bytes(&rx, NULL, 1) == NOVA_DMX_INVALID_ARGUMENT);
    CHECK(nova_dmx_rx_break(&rx, 88, NULL) == NOVA_DMX_INVALID_ARGUMENT);
    CHECK(nova_dmx_rx_mark(&rx, 8) == NOVA_DMX_INVALID_STATE);
    CHECK(nova_dmx_rx_break(&rx, 88, &completed) == NOVA_DMX_OK);
    CHECK(nova_dmx_rx_bytes(&rx, packet, sizeof(packet)) == NOVA_DMX_INVALID_STATE);
    start_packet(&rx);
    CHECK(nova_dmx_rx_bytes(&rx, packet, sizeof(packet)) == NOVA_DMX_OK);
    nova_dmx_rx_reset(&rx); /* UART error must not deliver a partial packet */
    CHECK(nova_dmx_rx_break(&rx, 88, &completed) == NOVA_DMX_OK);
}

int main(void)
{
    test_roundtrip();
    test_invalid_packets_and_recovery();
    test_errors();
    puts("DMX framing and recovery checks passed");
    return 0;
}
