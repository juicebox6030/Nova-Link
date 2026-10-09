/**
 * @file nl_segment.h
 * @brief Optional segmentation of messages larger than one fragment.
 *
 * Plugins are encouraged to fit their data in one 100-byte payload. When
 * that is impossible (e.g. a full 512-channel DMX universe), this helper
 * splits a message across up to 16 fragments on the same zone.
 *
 * Each segment payload starts with one sub-header byte:
 *
 *     bits 7..4 = segment index (0..15)
 *     bits 3..0 = index of the last segment (count - 1)
 *
 * followed by up to NL_SEG_DATA_MAX bytes. Every segment except the last
 * carries exactly NL_SEG_DATA_MAX bytes. Segments of one message use
 * consecutive seqNums (seq - index is the message identity), and every
 * segment except the last should carry the BURST flag so receivers keep
 * listening on the zone.
 *
 * Because the stream tracker delivers only newer seqNums, a lost segment
 * drops the whole message; the next message replaces it. That matches the
 * "latest data wins" model of live control.
 */
#ifndef NL_SEGMENT_H
#define NL_SEGMENT_H

#include "nl_common.h"

#ifdef __cplusplus
extern "C" {
#endif

#define NL_SEG_DATA_MAX (NL_MAX_PAYLOAD - 1u) /**< 99 bytes per segment. */
#define NL_SEG_MAX_MESSAGE (NL_SEG_DATA_MAX * NL_SEG_MAX_SEGMENTS)

/** Number of segments needed for @p msg_len bytes, or NL_ERR_SIZE. */
int nl_seg_count(size_t msg_len);

/**
 * Build the payload of segment @p index.
 * @return Payload length (sub-header + data), or a negative status.
 */
int nl_seg_build(const uint8_t *msg, size_t msg_len, uint8_t index, uint8_t *out,
                 size_t cap);

/** Reassembly state. The caller owns the buffer; NULL with capacity zero
 * accepts only an empty message. Storage and payload must not overlap. */
typedef struct {
    uint8_t *buf;
    size_t cap;
    bool active;
    uint8_t base_seq;
    uint8_t count;
    uint16_t mask;
    size_t total_len;
    uint32_t completed; /**< Messages delivered. */
    uint32_t aborted;   /**< Partial messages abandoned (a segment was lost). */
} nl_reasm_t;

void nl_reasm_init(nl_reasm_t *r, uint8_t *buf, size_t cap);

/**
 * Feed one segment payload (after deduplication).
 * @param r        Reassembler.
 * @param seq      Fragment seqNum.
 * @param payload  Segment payload (fragment payload).
 * @param len      Payload length.
 * @param msg      Set to the reassembled message when complete.
 * @param msg_len  Set to its length when complete.
 * @return 1 when a message completed, 0 if more segments are needed, or a
 *         negative status for a malformed segment / buffer overflow.
 */
int nl_reasm_feed(nl_reasm_t *r, uint8_t seq, const uint8_t *payload, size_t len,
                  const uint8_t **msg, size_t *msg_len);

#ifdef __cplusplus
}
#endif

#endif /* NL_SEGMENT_H */
