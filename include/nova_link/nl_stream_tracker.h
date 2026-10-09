/**
 * @file nl_stream_tracker.h
 * @brief Per-(originID, zoneID) sequence tracking and deduplication.
 *
 * Implements docs/stream_tracker.adoc. A fragment is accepted only if its
 * seqNum is newer than the last accepted one for that stream (8-bit serial
 * arithmetic, so 255 -> 0 counts as newer). Repeats and out-of-order older
 * fragments are discarded, which gives plugins "latest data only" semantics.
 *
 * A stream that has been silent for longer than @c stale_us is forgotten, so
 * a sender that rebooted (and restarted its seqNum at 0) is accepted again
 * immediately instead of being dropped for up to 127 fragments.
 *
 * The same tracker runs on the radio (to save SPI bandwidth) and on the host
 * (to protect plugins across radio resets).
 */
#ifndef NL_STREAM_TRACKER_H
#define NL_STREAM_TRACKER_H

#include "nl_common.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Outcome of nl_tracker_check(). */
typedef enum {
    NL_TRACK_NEW = 0,       /**< Newer than anything seen: deliver. */
    NL_TRACK_DUPLICATE = 1, /**< Same seqNum as last accepted: drop. */
    NL_TRACK_OLD = 2,       /**< Older than last accepted: drop. */
} nl_track_result_t;

typedef struct {
    uint8_t last_seq;
    uint8_t valid;
    nl_time_us_t last_time;
} nl_stream_entry_t;

typedef struct {
    nl_stream_entry_t stream[NL_NUM_ORIGINS][NL_NUM_ZONES];
    uint32_t stale_us; /**< 0 disables expiry. */
    uint32_t accepted;
    uint32_t duplicates;
    uint32_t old;
} nl_stream_tracker_t;

/** Initialise an empty tracker. */
void nl_tracker_init(nl_stream_tracker_t *t, uint32_t stale_us);

/** Forget every stream (counters are kept). */
void nl_tracker_reset(nl_stream_tracker_t *t);

/**
 * Check a fragment and, if it is new, record it as the latest.
 * IDs outside 0..7 are masked to 3 bits.
 */
nl_track_result_t nl_tracker_check(nl_stream_tracker_t *t, uint8_t origin,
                                   uint8_t zone, uint8_t seq, nl_time_us_t now);

#ifdef __cplusplus
}
#endif

#endif /* NL_STREAM_TRACKER_H */
