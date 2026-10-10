#include <string.h>
#include "internal.h"

void nl_stream_init(nl_stream_tracker *tracker, uint64_t idle_timeout_us)
{
    if (tracker == NULL) return;
    memset(tracker, 0, sizeof(*tracker));
    tracker->idle_timeout_us = idle_timeout_us;
}

nl_status nl_stream_check_valid(const nl_stream_tracker *tracker, const nl_fragment *fragment, uint64_t now_us)
{
    uint8_t origin = fragment->origin, zone = fragment->zone, delta;
    uint64_t accepted_at;
    if ((tracker->seen[origin] & (uint8_t)(1u << zone)) == 0u) return NL_OK;
    accepted_at = tracker->accepted_at_us[origin][zone];
    if (now_us < accepted_at) return NL_ERR_ARGUMENT;
    if (tracker->idle_timeout_us != 0u && now_us - accepted_at >= tracker->idle_timeout_us)
        return NL_OK;
    delta = (uint8_t)(fragment->sequence - tracker->sequence[origin][zone]);
    if (delta == 0u) return NL_ERR_DUPLICATE;
    return delta < 128u ? NL_OK : NL_ERR_STALE;
}

void nl_stream_commit(nl_stream_tracker *tracker, const nl_fragment *fragment, uint64_t now_us)
{
    tracker->seen[fragment->origin] |= (uint8_t)(1u << fragment->zone);
    tracker->sequence[fragment->origin][fragment->zone] = fragment->sequence;
    tracker->accepted_at_us[fragment->origin][fragment->zone] = now_us;
}

nl_status nl_stream_check(const nl_stream_tracker *tracker, const nl_fragment *fragment, uint64_t now_us)
{
    nl_status status = nl_fragment_validate(fragment);
    if (tracker == NULL) return NL_ERR_ARGUMENT;
    if (status != NL_OK) return status;
    return nl_stream_check_valid(tracker, fragment, now_us);
}

nl_status nl_stream_accept(nl_stream_tracker *tracker, const nl_fragment *fragment, uint64_t now_us)
{
    nl_status status = nl_stream_check(tracker, fragment, now_us);
    if (status == NL_OK) nl_stream_commit(tracker, fragment, now_us);
    return status;
}

nl_status nl_stream_reset_origin(nl_stream_tracker *tracker, uint8_t origin)
{
    if (tracker == NULL || origin >= NL_ORIGIN_COUNT) return NL_ERR_ARGUMENT;
    tracker->seen[origin] = 0;
    return NL_OK;
}
