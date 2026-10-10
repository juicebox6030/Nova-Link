/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef NOVA_MULTIVERSE_SYNTHETIC_H
#define NOVA_MULTIVERSE_SYNTHETIC_H

#include "nova/multiverse.h"

#ifdef __cplusplus
extern "C" {
#endif

/** @file multiverse_synthetic.h
 * TEST-ONLY codec. NVS1 bytes have NO Multiverse on-air compatibility.
 * No PHY or hardware submission is provided. Never send these bytes to fixtures.
 * Layout: magic[4], kind[1], reserved-zero[1], universe[2], session[4],
 * sequence[2], base[2], slots[2], span_start[2], span_count[2], offset[2],
 * count[2], levels[count], CRC-32/ISO-HDLC[4]. All integers little-endian.
 * CRC protects all preceding bytes. Maximum size = 30 + 512 bytes.
 */
#define NOVA_MV_SYNTHETIC_PROFILE "nova-mv-synthetic-v1"
#define NOVA_MV_SYNTHETIC_MAX_BYTES (30u + NOVA_DMX_MAX_SLOTS)

/** On error, output is untouched and written is zero. No overlapping storage. */
nova_mv_result_t nova_mv_synthetic_encode(const nova_mv_packet_t *packet,
                                        uint8_t *output, size_t capacity,
                                        size_t *written);
/** Strict framing/length/CRC/semantic checks; output untouched on error. */
nova_mv_result_t nova_mv_synthetic_decode(const uint8_t *bytes, size_t count,
                                        nova_mv_packet_t *packet);
#ifdef __cplusplus
}
#endif
#endif
