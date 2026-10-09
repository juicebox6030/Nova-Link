#ifndef NOVA_LINK_STREAM_H
#define NOVA_LINK_STREAM_H

#include <stdbool.h>
#include "nova_link/fragment.h"

/** @file stream.h Latest-only, wrap-aware tracking for all 64 origin/zone streams. */
typedef struct {
    bool seen;
    uint8_t sequence;
    uint64_t accepted_at_us;
} nl_stream_entry;

typedef struct {
    uint64_t idle_timeout_us; /**< Zero disables automatic restart after inactivity. */
    nl_stream_entry entries[NL_ORIGIN_COUNT][NL_ZONE_COUNT];
} nl_stream_tracker;

void nl_stream_init(nl_stream_tracker *tracker, uint64_t idle_timeout_us);
/** Inspect without committing: use this before attempting a bounded queue write.
 * A modulo-256 advance of 1..127 is new; 128..255 is stale. The clock must be monotonic.
 */
nl_status nl_stream_check(const nl_stream_tracker *tracker, const nl_fragment *fragment, uint64_t now_us);
/** Commit only after successful delivery/queueing. */
nl_status nl_stream_accept(nl_stream_tracker *tracker, const nl_fragment *fragment, uint64_t now_us);
/** Forget a sender after an explicit session restart. */
nl_status nl_stream_reset_origin(nl_stream_tracker *tracker, uint8_t origin);

#endif
