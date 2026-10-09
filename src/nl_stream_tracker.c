/**
 * @file nl_stream_tracker.c
 * @brief Sequence-number deduplication.
 */
#include "nova_link/nl_stream_tracker.h"
#include "nova_link/nl_fragment.h"

#include <string.h>

void nl_tracker_init(nl_stream_tracker_t *t, uint32_t stale_us)
{
    memset(t, 0, sizeof(*t));
    t->stale_us = stale_us;
}

void nl_tracker_reset(nl_stream_tracker_t *t)
{
    memset(t->stream, 0, sizeof(t->stream));
}

nl_track_result_t nl_tracker_check(nl_stream_tracker_t *t, uint8_t origin,
                                   uint8_t zone, uint8_t seq, nl_time_us_t now)
{
    nl_stream_entry_t *e = &t->stream[origin & 0x07u][zone & 0x07u];

    bool expired = e->valid && t->stale_us != 0 &&
                   nl_time_diff(now, e->last_time) > nl_time_span(t->stale_us);

    if (e->valid && !expired) {
        int cmp = nl_seq_cmp(seq, e->last_seq);
        if (cmp == 0) {
            t->duplicates++;
            return NL_TRACK_DUPLICATE;
        }
        if (cmp < 0) {
            t->old++;
            return NL_TRACK_OLD;
        }
    }
    e->valid = 1;
    e->last_seq = seq;
    e->last_time = now;
    t->accepted++;
    return NL_TRACK_NEW;
}
