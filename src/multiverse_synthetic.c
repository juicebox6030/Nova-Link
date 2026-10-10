/* SPDX-License-Identifier: GPL-3.0-only */
#include "nova/multiverse_synthetic.h"
#include <string.h>

static void put16(uint8_t *p, uint16_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8u);
}
static uint16_t get16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8u));
}
static void put32(uint8_t *p, uint32_t value)
{
    for (unsigned i = 0; i < 4u; ++i) p[i] = (uint8_t)(value >> (8u * i));
}
static uint32_t get32(const uint8_t *p)
{
    uint32_t value = 0;
    for (unsigned i = 0; i < 4u; ++i) value |= (uint32_t)p[i] << (8u * i);
    return value;
}
static uint32_t crc32(const uint8_t *bytes, size_t count)
{
    uint32_t crc = UINT32_MAX;
    for (size_t i = 0; i < count; ++i) {
        crc ^= bytes[i];
        for (unsigned bit = 0; bit < 8u; ++bit)
            crc = (crc >> 1u) ^ ((crc & 1u) != 0u ? UINT32_C(0xedb88320) : 0u);
    }
    return crc ^ UINT32_MAX;
}

nova_mv_result_t nova_mv_synthetic_encode(const nova_mv_packet_t *p,
                                        uint8_t *output, size_t capacity,
                                        size_t *written)
{
    nova_mv_result_t result;
    size_t size;
    if (written != NULL) *written = 0;
    if (output == NULL || written == NULL) return NOVA_MV_INVALID_ARGUMENT;
    result = nova_mv_packet_validate(p);
    if (result != NOVA_MV_OK) return result;
    size = 30u + p->count;
    if (capacity < size) return NOVA_MV_BUFFER_TOO_SMALL;
    memcpy(output, "NVS1", 4);
    output[4] = (uint8_t)p->kind;
    output[5] = 0;
    put16(output + 6, p->universe);
    put32(output + 8, p->session);
    put16(output + 12, p->sequence);
    put16(output + 14, p->base_sequence);
    put16(output + 16, p->slot_count);
    put16(output + 18, p->span_start);
    put16(output + 20, p->span_count);
    put16(output + 22, p->offset);
    put16(output + 24, p->count);
    memcpy(output + 26, p->levels, p->count);
    put32(output + size - 4u, crc32(output, size - 4u));
    *written = size;
    return NOVA_MV_OK;
}

nova_mv_result_t nova_mv_synthetic_decode(const uint8_t *bytes, size_t count,
                                        nova_mv_packet_t *packet)
{
    nova_mv_packet_t p = {0};
    if (bytes == NULL || packet == NULL) return NOVA_MV_INVALID_ARGUMENT;
    if (count < 30u || count > NOVA_MV_SYNTHETIC_MAX_BYTES ||
        memcmp(bytes, "NVS1", 4) != 0 || bytes[5] != 0u ||
        crc32(bytes, count - 4u) != get32(bytes + count - 4u)) return NOVA_MV_BAD_PACKET;
    p.kind = (nova_mv_kind_t)bytes[4];
    p.universe = get16(bytes + 6);
    p.session = get32(bytes + 8);
    p.sequence = get16(bytes + 12);
    p.base_sequence = get16(bytes + 14);
    p.slot_count = get16(bytes + 16);
    p.span_start = get16(bytes + 18);
    p.span_count = get16(bytes + 20);
    p.offset = get16(bytes + 22);
    p.count = get16(bytes + 24);
    if (p.count > NOVA_DMX_MAX_SLOTS || count != 30u + p.count ||
        nova_mv_packet_validate(&p) != NOVA_MV_OK) return NOVA_MV_BAD_PACKET;
    memcpy(p.levels, bytes + 26, p.count);
    *packet = p;
    return NOVA_MV_OK;
}
