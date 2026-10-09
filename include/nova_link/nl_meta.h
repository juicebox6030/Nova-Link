/**
 * @file nl_meta.h
 * @brief Zone 0 metadata records and the outgoing metadata queue.
 *
 * A zone 0 fragment payload is a sequence of TLV records:
 *
 *     [type u8][len u8][value: len bytes] [type][len][value] ...
 *
 * Several small records are packed into one fragment "as they fit". A
 * record never spans fragments, so its value is at most 98 bytes.
 *
 * Record types 0x01..0x7F are defined by NOVA-LINK; 0x80..0xFF are free for
 * vendor/experimental use. Unknown types are skipped by receivers.
 */
#ifndef NL_META_H
#define NL_META_H

#include "nl_common.h"

#ifdef __cplusplus
extern "C" {
#endif

#define NL_META_TLV_OVERHEAD 2u
#define NL_META_MAX_VALUE (NL_MAX_PAYLOAD - NL_META_TLV_OVERHEAD)

/** Metadata record types. */
typedef enum {
    /** Device discovery: nl_meta_device_t. */
    NL_META_DEVICE_ANNOUNCE = 0x01,
    /** Full snapshot of the sender's zone claims: nl_meta_claim_t[]. */
    NL_META_CLAIM_ANNOUNCE = 0x02,
    /** Plugin-to-plugin data: [plugin_type u16 LE][data]. */
    NL_META_PLUGIN_DATA = 0x03,
    /** Congestion alert: [zone_mask u8][dropped u16 LE]. */
    NL_META_CONGESTION = 0x04,
    /** Human-readable debug text (UTF-8, not NUL-terminated). */
    NL_META_DEBUG_TEXT = 0x05,
    /** Peers the sender currently knows: [origin_mask u8], bit i = origin i.
     *  A device whose bit is clear answers with its own announcements. */
    NL_META_PEERS = 0x06,
    /** First type available for vendor extensions. */
    NL_META_VENDOR_BASE = 0x80,
} nl_meta_type_t;

/** Outgoing metadata queue (FIFO of whole TLV records). */
typedef struct {
    uint8_t buf[NL_META_QUEUE_BYTES];
    uint16_t used;
    uint32_t dropped; /**< Records rejected because the queue was full. */
} nl_meta_queue_t;

void nl_meta_queue_init(nl_meta_queue_t *q);

/** Append a record. @return NL_OK, NL_ERR_SIZE (value too long), NL_ERR_FULL. */
int nl_meta_queue_push(nl_meta_queue_t *q, uint8_t type, const uint8_t *value,
                       size_t len);

/**
 * Remove any queued records of @p type. Used to replace periodic snapshots
 * (e.g. claim announcements) instead of queueing stale copies.
 */
void nl_meta_queue_remove_type(nl_meta_queue_t *q, uint8_t type);

/** True if any record is waiting. */
static inline bool nl_meta_queue_pending(const nl_meta_queue_t *q)
{
    return q->used > 0;
}

/**
 * Move as many whole records as fit into @p out (FIFO order, stops at the
 * first record that does not fit).
 * @return Bytes written (0 if the queue is empty).
 */
size_t nl_meta_queue_pack(nl_meta_queue_t *q, uint8_t *out, size_t cap);

/** Iterator over the TLV records in a zone 0 payload. */
typedef struct {
    const uint8_t *buf;
    size_t len;
    size_t pos;
} nl_meta_iter_t;

void nl_meta_iter_init(nl_meta_iter_t *it, const uint8_t *buf, size_t len);

/**
 * Fetch the next record.
 * @return 1 if a record was returned, 0 at the end, NL_ERR_PROTO if the
 *         remaining bytes are truncated (iteration stops).
 */
int nl_meta_iter_next(nl_meta_iter_t *it, uint8_t *type, const uint8_t **value,
                      uint8_t *len);

/* ---- Structured records ------------------------------------------------ */

/** One entry of a NL_META_CLAIM_ANNOUNCE record (4 bytes on the wire). */
typedef struct {
    uint8_t zone;
    uint8_t mode;         /**< nl_claim_mode_t */
    uint16_t plugin_type; /**< Plugin type ID that owns the zone. */
} nl_meta_claim_t;

#define NL_META_CLAIM_WIRE_SIZE 4u

/** NL_META_DEVICE_ANNOUNCE contents. */
typedef struct {
    uint8_t proto_version;
    uint8_t fw_major, fw_minor, fw_patch;
    char name[25]; /**< NUL-terminated, at most 24 bytes on the wire. */
} nl_meta_device_t;

int nl_meta_encode_claims(const nl_meta_claim_t *claims, size_t count,
                          uint8_t *out, size_t cap);
/** @return Number of entries decoded into @p claims, or a negative status. */
int nl_meta_decode_claims(const uint8_t *value, size_t len,
                          nl_meta_claim_t *claims, size_t max);

int nl_meta_encode_device(const nl_meta_device_t *dev, uint8_t *out, size_t cap);
int nl_meta_decode_device(const uint8_t *value, size_t len, nl_meta_device_t *dev);

#ifdef __cplusplus
}
#endif

#endif /* NL_META_H */
