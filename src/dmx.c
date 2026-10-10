/* SPDX-License-Identifier: GPL-3.0-only */
#include "nova/dmx.h"

#include <string.h>

nova_dmx_result_t nova_dmx_encode(const nova_dmx_frame_t *frame,
                                uint8_t *output, size_t capacity,
                                size_t *written)
{
    size_t packet_size;

    if (written != NULL) {
        *written = 0;
    }
    if (frame == NULL || output == NULL || written == NULL ||
        frame->slot_count > NOVA_DMX_MAX_SLOTS) {
        return NOVA_DMX_INVALID_ARGUMENT;
    }
    packet_size = (size_t)frame->slot_count + 1u;
    if (capacity < packet_size) {
        return NOVA_DMX_BUFFER_TOO_SMALL;
    }
    output[0] = 0x00;
    memcpy(output + 1u, frame->slots, frame->slot_count);
    *written = packet_size;
    return NOVA_DMX_OK;
}

void nova_dmx_rx_reset(nova_dmx_rx_t *rx)
{
    if (rx != NULL) {
        memset(rx, 0, sizeof(*rx));
        rx->state = NOVA_DMX_WAIT_BREAK;
    }
}

nova_dmx_result_t nova_dmx_rx_break(nova_dmx_rx_t *rx, uint32_t duration_us,
                                  nova_dmx_frame_t *completed)
{
    nova_dmx_result_t result = NOVA_DMX_OK;

    if (rx == NULL || completed == NULL) {
        return NOVA_DMX_INVALID_ARGUMENT;
    }
    if (duration_us < NOVA_DMX_RX_BREAK_MIN_US) {
        nova_dmx_rx_reset(rx);
        return NOVA_DMX_INVALID_TIMING;
    }
    if (rx->state == NOVA_DMX_READ_SLOTS) {
        *completed = rx->pending;
        result = NOVA_DMX_FRAME_READY;
    }
    /* Only the written prefix can be non-zero; keep the zero-tail invariant cheaply. */
    memset(rx->pending.slots, 0, rx->pending.slot_count);
    rx->pending.slot_count = 0;
    rx->state = NOVA_DMX_WAIT_MARK;
    return result;
}

nova_dmx_result_t nova_dmx_rx_mark(nova_dmx_rx_t *rx, uint32_t duration_us)
{
    if (rx == NULL) {
        return NOVA_DMX_INVALID_ARGUMENT;
    }
    if (rx->state != NOVA_DMX_WAIT_MARK) {
        rx->state = NOVA_DMX_DISCARD;
        return NOVA_DMX_INVALID_STATE;
    }
    if (duration_us < NOVA_DMX_RX_MARK_MIN_US) {
        rx->state = NOVA_DMX_DISCARD;
        return NOVA_DMX_INVALID_TIMING;
    }
    rx->state = NOVA_DMX_WAIT_START_CODE;
    return NOVA_DMX_OK;
}

nova_dmx_result_t nova_dmx_rx_bytes(nova_dmx_rx_t *rx,
                                  const uint8_t *bytes, size_t count)
{
    size_t offset = 0;

    if (rx == NULL || (bytes == NULL && count != 0u)) {
        return NOVA_DMX_INVALID_ARGUMENT;
    }
    if (count == 0u) {
        return NOVA_DMX_OK;
    }
    if (rx->state == NOVA_DMX_WAIT_BREAK || rx->state == NOVA_DMX_DISCARD) {
        return NOVA_DMX_IGNORED;
    }
    if (rx->state == NOVA_DMX_WAIT_MARK) {
        rx->state = NOVA_DMX_DISCARD;
        return NOVA_DMX_INVALID_STATE;
    }
    if (rx->state == NOVA_DMX_WAIT_START_CODE) {
        if (bytes[0] != 0x00) {
            rx->state = NOVA_DMX_DISCARD;
            return NOVA_DMX_UNSUPPORTED_START_CODE;
        }
        rx->state = NOVA_DMX_READ_SLOTS;
        offset = 1u;
    }
    if (count - offset > NOVA_DMX_MAX_SLOTS - rx->pending.slot_count) {
        rx->state = NOVA_DMX_DISCARD;
        return NOVA_DMX_TOO_MANY_SLOTS;
    }
    memcpy(rx->pending.slots + rx->pending.slot_count,
           bytes + offset, count - offset);
    rx->pending.slot_count += (uint16_t)(count - offset);
    return NOVA_DMX_OK;
}
