#ifndef NOVA_FUZZ_H
#define NOVA_FUZZ_H
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/nova_link.h"

/* Invariant violations abort so libFuzzer saves the input as a crash. */
#define REQUIRE(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "%s:%d: invariant failed: %s\n", __FILE__, __LINE__, #condition); \
        abort(); \
    } \
} while (0)

/* Reads bytes off the front of the fuzz input; returns 0 once it is exhausted. */
typedef struct {
    const uint8_t *data;
    size_t size;
} fuzz_input;

static inline uint8_t take(fuzz_input *in)
{
    uint8_t value = 0;
    if (in->size > 0) {
        value = in->data[0];
        ++in->data;
        --in->size;
    }
    return value;
}

static inline uint32_t take32(fuzz_input *in)
{
    uint32_t value = take(in);
    value = value << 8 | take(in);
    value = value << 8 | take(in);
    return value << 8 | take(in);
}

/* Copy up to `limit` bytes; returns the count copied. */
static inline size_t take_bytes(fuzz_input *in, uint8_t *out, size_t limit)
{
    size_t n = limit < in->size ? limit : in->size;
    memcpy(out, in->data, n);
    in->data += n;
    in->size -= n;
    return n;
}

static inline int fragments_equal(const nl_fragment *a, const nl_fragment *b)
{
    return a->origin == b->origin && a->zone == b->zone && a->flags == b->flags &&
           a->sequence == b->sequence && a->payload_size == b->payload_size &&
           memcmp(a->payload, b->payload, a->payload_size) == 0;
}

static inline int frames_equal(const nl_frame *a, const nl_frame *b)
{
    return a->command == b->command && a->data_size == b->data_size &&
           memcmp(a->data, b->data, a->data_size) == 0;
}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);
#endif
