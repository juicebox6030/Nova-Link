/* SPDX-License-Identifier: GPL-3.0-only */
#include "nova/dmx.h"

#include <stdio.h>
#include <string.h>

int main(void)
{
    nova_dmx_frame_t tx = {0};
    nova_dmx_frame_t received = {0};
    nova_dmx_rx_t rx;
    uint8_t packet[NOVA_DMX_MAX_PACKET_BYTES];
    size_t written = 0;

    tx.slot_count = NOVA_DMX_MAX_SLOTS;
    for (size_t i = 0; i < tx.slot_count; ++i) {
        tx.slots[i] = (uint8_t)i;
    }
    nova_dmx_rx_reset(&rx);
    if (nova_dmx_encode(&tx, packet, sizeof(packet), &written) != NOVA_DMX_OK ||
        nova_dmx_rx_break(&rx, NOVA_DMX_TX_BREAK_MIN_US, &received) != NOVA_DMX_OK ||
        nova_dmx_rx_mark(&rx, NOVA_DMX_TX_MARK_MIN_US) != NOVA_DMX_OK ||
        nova_dmx_rx_bytes(&rx, packet, 100u) != NOVA_DMX_OK ||
        nova_dmx_rx_bytes(&rx, packet + 100u, written - 100u) != NOVA_DMX_OK ||
        nova_dmx_rx_break(&rx, NOVA_DMX_TX_BREAK_MIN_US, &received) != NOVA_DMX_FRAME_READY ||
        received.slot_count != tx.slot_count ||
        memcmp(received.slots, tx.slots, tx.slot_count) != 0) {
        fputs("DMX software loopback failed\n", stderr);
        return 1;
    }
    printf("DMX software loopback: %zu bytes transmitted, %u slots received.\n",
           written, (unsigned)received.slot_count);
    puts("Simulation only: no UART or Multiverse radio was used.");
    return 0;
}
