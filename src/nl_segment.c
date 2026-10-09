/**
 * @file nl_segment.c
 * @brief Message segmentation and reassembly.
 */
#include "nova_link/nl_segment.h"

#include <string.h>

int nl_seg_count(size_t msg_len)
{
    if (msg_len > NL_SEG_MAX_MESSAGE) {
        return NL_ERR_SIZE;
    }
    if (msg_len == 0) {
        return 1;
    }
    return (int)((msg_len + NL_SEG_DATA_MAX - 1) / NL_SEG_DATA_MAX);
}

int nl_seg_build(const uint8_t *msg, size_t msg_len, uint8_t index, uint8_t *out,
                 size_t cap)
{
    if ((msg_len > 0 && msg == NULL) || out == NULL) {
        return NL_ERR_ARG;
    }
    int count = nl_seg_count(msg_len);
    if (count < 0) {
        return count;
    }
    if (index >= count) {
        return NL_ERR_ARG;
    }
    size_t off = (size_t)index * NL_SEG_DATA_MAX;
    size_t chunk = msg_len - off;
    if (chunk > NL_SEG_DATA_MAX) {
        chunk = NL_SEG_DATA_MAX;
    }
    if (cap < chunk + 1) {
        return NL_ERR_SIZE;
    }
    out[0] = (uint8_t)((index << 4) | (count - 1));
    if (chunk > 0) {
        memcpy(&out[1], &msg[off], chunk);
    }
    return (int)(chunk + 1);
}

void nl_reasm_init(nl_reasm_t *r, uint8_t *buf, size_t cap)
{
    memset(r, 0, sizeof(*r));
    r->buf = buf;
    r->cap = cap;
}

int nl_reasm_feed(nl_reasm_t *r, uint8_t seq, const uint8_t *payload, size_t len,
                  const uint8_t **msg, size_t *msg_len)
{
    if (payload == NULL || len < 1 || len > NL_MAX_PAYLOAD) {
        return NL_ERR_PROTO;
    }
    uint8_t index = payload[0] >> 4;
    uint8_t last = payload[0] & 0x0Fu;
    uint8_t count = (uint8_t)(last + 1);
    size_t chunk = len - 1;

    if (index > last || count > NL_SEG_MAX_SEGMENTS ||
        (index < last && chunk != NL_SEG_DATA_MAX) ||
        (index == last && count > 1 && chunk == 0)) {
        return NL_ERR_PROTO;
    }

    uint8_t base = (uint8_t)(seq - index);
    if (!r->active || base != r->base_seq || count != r->count) {
        if (r->active) {
            r->aborted++;
        }
        r->active = true;
        r->base_seq = base;
        r->count = count;
        r->mask = 0;
        r->total_len = 0;
    }

    size_t off = (size_t)index * NL_SEG_DATA_MAX;
    if (off + chunk > r->cap) {
        r->active = false;
        r->aborted++;
        return NL_ERR_SIZE;
    }
    memcpy(&r->buf[off], &payload[1], chunk);
    r->mask = (uint16_t)(r->mask | (1u << index));
    if (index == last) {
        r->total_len = off + chunk;
    }

    if (r->mask == (uint16_t)((1u << count) - 1u)) {
        r->active = false;
        r->completed++;
        if (msg != NULL) {
            *msg = r->buf;
        }
        if (msg_len != NULL) {
            *msg_len = r->total_len;
        }
        return 1;
    }
    return 0;
}
