#ifndef NOVA_LINK_FRAGMENT_H
#define NOVA_LINK_FRAGMENT_H

#include <stddef.h>
#include <stdint.h>
#include "nova_link/status.h"

/** @file fragment.h Portable DataFragment codec; struct layout is never sent on wire. */
#define NL_ORIGIN_COUNT 8u
#define NL_ZONE_COUNT 8u
#define NL_PAYLOAD_MAX 100u
#define NL_FRAGMENT_MIN 2u
#define NL_FRAGMENT_MAX (NL_FRAGMENT_MIN + NL_PAYLOAD_MAX)
#define NL_FLAG_MGMT_LISTEN 0x01u
#define NL_FLAG_BURST 0x02u
#define NL_FLAGS_MASK 0x03u

typedef struct {
    uint8_t origin;
    uint8_t zone;
    uint8_t flags;
    uint8_t sequence;
    uint8_t payload_size;
    uint8_t payload[NL_PAYLOAD_MAX];
} nl_fragment;

/** Validate fields without accessing payload bytes beyond payload_size. */
nl_status nl_fragment_validate(const nl_fragment *fragment);
/** Encode [origin:3 | zone:3 | flags:2][sequence][payload]. Outputs unchanged on error. */
nl_status nl_fragment_encode(const nl_fragment *fragment, uint8_t *bytes,
                             size_t capacity, size_t *size);
/** Decode one complete fragment. Outputs unchanged on error. */
nl_status nl_fragment_decode(const uint8_t *bytes, size_t size, nl_fragment *fragment);

#endif
