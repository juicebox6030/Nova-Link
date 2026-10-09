#include <string.h>
#include "nova_link/stream.h"

void nl_stream_init(nl_stream_tracker *tracker, uint64_t idle_timeout_us)
{
    if (tracker == NULL) return;
    memset(tracker, 0, sizeof(*tracker));
    tracker->idle_timeout_us = idle_timeout_us;
}

nl_status nl_stream_check(const nl_stream_tracker *tracker, const nl_fragment *fragment, uint64_t now_us)
{
    const nl_stream_entry *entry;
    uint8_t delta;
    nl_status status = nl_fragment_validate(fragment);
    if (tracker == NULL) return NL_ERR_ARGUMENT;
    if (status != NL_OK) return status;
    entry = &tracker->entries[fragment->origin][fragment->zone];
    if (!entry->seen) return NL_OK;
    if (now_us < entry->accepted_at_us) return NL_ERR_ARGUMENT;
    if (tracker->idle_timeout_us != 0u && now_us - entry->accepted_at_us >= tracker->idle_timeout_us)
        return NL_OK;
    delta = (uint8_t)(fragment->sequence - entry->sequence);
    if (delta == 0u) return NL_ERR_DUPLICATE;
    return delta < 128u ? NL_OK : NL_ERR_STALE;
}

nl_status nl_stream_accept(nl_stream_tracker *tracker, const nl_fragment *fragment, uint64_t now_us)
{
    nl_stream_entry *entry;
    nl_status status = nl_stream_check(tracker, fragment, now_us);
    if (status != NL_OK) return status;
    entry = &tracker->entries[fragment->origin][fragment->zone];
    entry->seen = true;
    entry->sequence = fragment->sequence;
    entry->accepted_at_us = now_us;
    return NL_OK;
}

nl_status nl_stream_reset_origin(nl_stream_tracker *tracker, uint8_t origin)
{
    if (tracker == NULL || origin >= NL_ORIGIN_COUNT) return NL_ERR_ARGUMENT;
    memset(tracker->entries[origin], 0, sizeof(tracker->entries[origin]));
    return NL_OK;
}
