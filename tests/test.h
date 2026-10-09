#ifndef NOVA_TEST_H
#define NOVA_TEST_H
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/nova_link.h"

/* Unlike assert(), these checks remain active in Release builds. */
#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "%s:%d: check failed: %s\n", __FILE__, __LINE__, #condition); \
        exit(EXIT_FAILURE); \
    } \
} while (0)
#define STATUS(expression, expected) do { \
    nl_status test_status_ = (expression); \
    if (test_status_ != (expected)) { \
        fprintf(stderr, "%s:%d: %s: got %s, expected %s\n", __FILE__, __LINE__, \
            #expression, nl_status_name(test_status_), nl_status_name(expected)); \
        exit(EXIT_FAILURE); \
    } \
} while (0)

static inline nl_fragment fragment(uint8_t origin, uint8_t zone, uint8_t sequence)
{
    nl_fragment value = {0};
    value.origin = origin;
    value.zone = zone;
    value.sequence = sequence;
    value.payload_size = 3;
    value.payload[0] = 0;
    value.payload[1] = NL_TRANSPORT_SYNC;
    value.payload[2] = 0xFF;
    return value;
}

static inline void same_fragment(const nl_fragment *a, const nl_fragment *b)
{
    CHECK(a->origin == b->origin);
    CHECK(a->zone == b->zone);
    CHECK(a->flags == b->flags);
    CHECK(a->sequence == b->sequence);
    CHECK(a->payload_size == b->payload_size);
    CHECK(memcmp(a->payload, b->payload, a->payload_size) == 0);
}
#endif
