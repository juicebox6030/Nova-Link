/**
 * @file nl_fragment.h
 * @brief DataFragment encoding and decoding.
 *
 * Wire format (see docs/packet_format.adoc):
 *
 * | Byte | Bits | Field                                   |
 * |------|------|-----------------------------------------|
 * | 0    | 7..5 | originID (0..7)                         |
 * | 0    | 4..2 | zoneID (0..7)                           |
 * | 0    | 1    | BURST - receiver should dwell longer    |
 * | 0    | 0    | MGMT_LISTEN - sender has zone 0 data    |
 * | 1    | 7..0 | seqNum                                  |
 * | 2..  |      | payload, 0..100 bytes                   |
 *
 * There is no length field or CRC: the RF PHY (EasyLink) supplies both, and
 * the SPI link frames each fragment with its own length.
 */
#ifndef NL_FRAGMENT_H
#define NL_FRAGMENT_H

#include "nl_common.h"

#ifdef __cplusplus
extern "C" {
#endif

/** @name Header flag bits */
/**@{*/
#define NL_FLAG_BURST 0x02u       /**< Hold this zone longer; more follows. */
#define NL_FLAG_MGMT_LISTEN 0x01u /**< Sender has metadata pending on zone 0. */
#define NL_FLAG_MASK 0x03u
/**@}*/

/** Decoded DataFragment. The payload pointer refers into caller memory. */
typedef struct {
    uint8_t origin_id;      /**< 0..7 */
    uint8_t zone_id;        /**< 0..7 */
    uint8_t flags;          /**< NL_FLAG_* bits */
    uint8_t seq;            /**< Sequence number */
    const uint8_t *payload; /**< Payload bytes (may be NULL when len is 0) */
    uint8_t payload_len;    /**< 0..NL_MAX_PAYLOAD */
} nl_fragment_t;

/** Pack originID, zoneID, and flags into the header byte. */
static inline uint8_t nl_fragment_make_header(uint8_t origin, uint8_t zone,
                                              uint8_t flags)
{
    return (uint8_t)(((origin & 0x07u) << 5) | ((zone & 0x07u) << 2) |
                     (flags & NL_FLAG_MASK));
}

/** Extract fields from a header byte. */
static inline uint8_t nl_fragment_origin(uint8_t hdr) { return (uint8_t)(hdr >> 5); }
static inline uint8_t nl_fragment_zone(uint8_t hdr) { return (uint8_t)((hdr >> 2) & 0x07u); }
static inline uint8_t nl_fragment_flags(uint8_t hdr) { return (uint8_t)(hdr & NL_FLAG_MASK); }

/**
 * Serialize a fragment.
 * @param frag  Fragment to encode. IDs must be 0..7 and flags within mask.
 * @param out   Destination buffer.
 * @param cap   Size of @p out.
 * @return Encoded length (2..102) or a negative nl_status_t.
 */
int nl_fragment_encode(const nl_fragment_t *frag, uint8_t *out, size_t cap);

/**
 * Parse a fragment. The resulting payload pointer aliases @p buf.
 * @return NL_OK, or NL_ERR_SIZE if @p len is outside 2..102.
 */
int nl_fragment_decode(const uint8_t *buf, size_t len, nl_fragment_t *frag);

/**
 * Serial-number comparison for 8-bit sequence numbers (RFC 1982 style).
 * @return Positive if @p a is newer than @p b, 0 if equal, negative if older.
 *         A distance of exactly 128 is treated as older.
 */
static inline int nl_seq_cmp(uint8_t a, uint8_t b)
{
    uint8_t d = (uint8_t)(a - b);
    if (d == 0) {
        return 0;
    }
    return d < 128 ? (int)d : -(int)(uint8_t)(b - a);
}

#ifdef __cplusplus
}
#endif

#endif /* NL_FRAGMENT_H */
