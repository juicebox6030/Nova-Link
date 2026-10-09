/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef NOVA_DMX_H
#define NOVA_DMX_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** @file dmx.h
 * Portable DMX level framing for a future Multiverse host adapter.
 * The board adapter supplies physical BREAK/MARK timing and UART events.
 * This library does not implement Multiverse RF, RDM, or a UART driver.
 */

#define NOVA_DMX_MAX_SLOTS 512u
#define NOVA_DMX_MAX_PACKET_BYTES (1u + NOVA_DMX_MAX_SLOTS)
#define NOVA_DMX_BAUD 250000u
#define NOVA_DMX_DATA_BITS 8u
#define NOVA_DMX_STOP_BITS 2u
#define NOVA_DMX_TX_BREAK_MIN_US 92u
#define NOVA_DMX_TX_MARK_MIN_US 12u
#define NOVA_DMX_RX_BREAK_MIN_US 88u
#define NOVA_DMX_RX_MARK_MIN_US 8u

/** A null-start-code DMX packet. Slot index 0 represents DMX channel 1.
 * UART serialization carries no universe number, SHoW ID, or SHoW Key;
 * those settings belong to the external Multiverse transceiver.
 */
typedef struct {
    uint16_t slot_count;
    uint8_t slots[NOVA_DMX_MAX_SLOTS];
} nova_dmx_frame_t;

typedef enum {
    NOVA_DMX_OK = 0,
    NOVA_DMX_FRAME_READY,
    NOVA_DMX_IGNORED,
    NOVA_DMX_INVALID_ARGUMENT,
    NOVA_DMX_BUFFER_TOO_SMALL,
    NOVA_DMX_INVALID_TIMING,
    NOVA_DMX_INVALID_STATE,
    NOVA_DMX_UNSUPPORTED_START_CODE,
    NOVA_DMX_TOO_MANY_SLOTS
} nova_dmx_result_t;

typedef enum {
    NOVA_DMX_WAIT_BREAK = 0,
    NOVA_DMX_WAIT_MARK,
    NOVA_DMX_WAIT_START_CODE,
    NOVA_DMX_READ_SLOTS,
    NOVA_DMX_DISCARD
} nova_dmx_rx_state_t;

/** Caller-owned, allocation-free receive state. Treat fields as private.
 * Call from one task, or serialize access in the board adapter.
 */
typedef struct {
    nova_dmx_rx_state_t state;
    nova_dmx_frame_t pending;
} nova_dmx_rx_t;

/** Encode a null start code followed by exactly slot_count bytes.
 * No BREAK or MARK is encoded: the board must drive these on the wire.
 * On error, output is untouched and *written is zero (when non-null).
 * Frame and output storage must not overlap.
 */
nova_dmx_result_t nova_dmx_encode(const nova_dmx_frame_t *frame,
                                uint8_t *output, size_t capacity,
                                size_t *written);

/** Reset synchronization and discard any incomplete packet.
 * Invoke after UART overflow, parity/framing errors, or loss of input.
 */
void nova_dmx_rx_reset(nova_dmx_rx_t *rx);

/** Report a measured BREAK, after feeding all bytes preceding that BREAK.
 * A qualifying BREAK completes the preceding packet and starts the next.
 * completed is written only for NOVA_DMX_FRAME_READY. Its storage must not
 * overlap rx. A short BREAK drops the pending packet and synchronization.
 * A completed frame may contain 0..512 slots; bytes beyond slot_count are zero.
 */
nova_dmx_result_t nova_dmx_rx_break(nova_dmx_rx_t *rx, uint32_t duration_us,
                                  nova_dmx_frame_t *completed);

/** Report the measured MARK after BREAK, before delivering the start code.
 * A UART adapter may supply its validated timing rather than measuring it
 * here. An invalid MARK discards the packet until the next valid BREAK.
 */
nova_dmx_result_t nova_dmx_rx_mark(nova_dmx_rx_t *rx, uint32_t duration_us);

/** Feed UART bytes in wire order, excluding BREAK/framing-error bytes.
 * Only start code 0x00 is accepted. Alternate start codes, including RDM,
 * and packets exceeding 512 slots are discarded in their entirety.
 * UART read boundaries and inter-slot gaps do not complete a packet.
 */
nova_dmx_result_t nova_dmx_rx_bytes(nova_dmx_rx_t *rx,
                                  const uint8_t *bytes, size_t count);

#ifdef __cplusplus
}
#endif
#endif
