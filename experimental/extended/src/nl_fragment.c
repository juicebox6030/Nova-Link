/**
 * @file nl_fragment.c
 * @brief DataFragment codec.
 */
#include "nova_link/nl_fragment.h"

#include <string.h>

int nl_fragment_encode(const nl_fragment_t *frag, uint8_t *out, size_t cap)
{
    if (frag == NULL || out == NULL) {
        return NL_ERR_ARG;
    }
    if (frag->origin_id >= NL_NUM_ORIGINS || frag->zone_id >= NL_NUM_ZONES ||
        (frag->flags & ~NL_FLAG_MASK) != 0) {
        return NL_ERR_ARG;
    }
    if (frag->payload_len > NL_MAX_PAYLOAD) {
        return NL_ERR_SIZE;
    }
    if (frag->payload_len > 0 && frag->payload == NULL) {
        return NL_ERR_ARG;
    }
    size_t total = NL_FRAGMENT_HEADER_SIZE + (size_t)frag->payload_len;
    if (cap < total) {
        return NL_ERR_SIZE;
    }
    out[0] = nl_fragment_make_header(frag->origin_id, frag->zone_id, frag->flags);
    out[1] = frag->seq;
    if (frag->payload_len > 0) {
        memmove(&out[2], frag->payload, frag->payload_len);
    }
    return (int)total;
}

int nl_fragment_decode(const uint8_t *buf, size_t len, nl_fragment_t *frag)
{
    if (buf == NULL || frag == NULL) {
        return NL_ERR_ARG;
    }
    if (len < NL_FRAGMENT_HEADER_SIZE || len > NL_MAX_FRAGMENT) {
        return NL_ERR_SIZE;
    }
    frag->origin_id = nl_fragment_origin(buf[0]);
    frag->zone_id = nl_fragment_zone(buf[0]);
    frag->flags = nl_fragment_flags(buf[0]);
    frag->seq = buf[1];
    frag->payload_len = (uint8_t)(len - NL_FRAGMENT_HEADER_SIZE);
    frag->payload = frag->payload_len ? &buf[2] : NULL;
    return NL_OK;
}
