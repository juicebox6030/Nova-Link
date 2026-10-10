#ifndef NOVA_LINK_STREAM_H
#define NOVA_LINK_STREAM_H

#include <stdbool.h>
#include "nova_link/fragment.h"

/** @file stream.h Latest-only, wrap-aware tracking for all 64 origin/zone streams. */
/* Parallel arrays avoid 7 padding bytes per stream (592 vs 1032 bytes). */
typedef struct {
    uint64_t idle_timeout_us; /**< Zero disables automatic restart after inactivity. */
    uint64_t accepted_at_us[NL_ORIGIN_COUNT][NL_ZONE_COUNT];
    uint8_t sequence[NL_ORIGIN_COUNT][NL_ZONE_COUNT];
    uint8_t seen[NL_ORIGIN_COUNT]; /**< Bit z set once zone z of that origin is accepted. */
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
