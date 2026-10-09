#include <limits.h>
#include <stddef.h>
#include <string.h>
#include "nova_link/scheduler.h"

nl_status nl_scheduler_init(nl_scheduler *scheduler, uint8_t active_mask, uint32_t slot_us, uint32_t burst_extra_us)
{
    if (scheduler == NULL || (active_mask & 1u) != 0u || slot_us == 0u ||
        burst_extra_us > slot_us || burst_extra_us > UINT32_MAX - slot_us) return NL_ERR_ARGUMENT;
    memset(scheduler, 0, sizeof(*scheduler));
    scheduler->active_mask = active_mask;
    scheduler->slot_us = slot_us;
    scheduler->burst_extra_us = burst_extra_us;
    return NL_OK;
}

nl_status nl_scheduler_set_active(nl_scheduler *scheduler, uint8_t active_mask)
{
    if (scheduler == NULL || (active_mask & 1u) != 0u) return NL_ERR_ARGUMENT;
    scheduler->active_mask = active_mask;
    scheduler->visited_mask &= active_mask;
    return NL_OK;
}

nl_status nl_scheduler_next(nl_scheduler *scheduler, uint64_t now_us, bool management_pending,
                            uint8_t burst_mask, nl_window *window)
{
    nl_window selected = {0};
    uint8_t remaining, visited;
    if (scheduler == NULL || window == NULL) return NL_ERR_ARGUMENT;
    if (now_us < scheduler->last_now_us) return NL_ERR_ARGUMENT;
    if (scheduler->started && now_us < scheduler->next_at_us) {
        scheduler->last_now_us = now_us;
        return NL_ERR_BUSY;
    }
    visited = scheduler->visited_mask;
    remaining = (uint8_t)(scheduler->active_mask & (uint8_t)~visited);
    if (remaining == 0u) {
        visited = 0;
        if (!management_pending) remaining = scheduler->active_mask;
    }
    if (remaining == 0u && !management_pending) {
        scheduler->last_now_us = now_us;
        return NL_ERR_EMPTY;
    }
    if (remaining != 0u) {
        for (selected.zone = 1; selected.zone < 8u; ++selected.zone)
            if ((remaining & (uint8_t)(1u << selected.zone)) != 0u) break;
        visited |= (uint8_t)(1u << selected.zone);
    }
    selected.start_us = now_us;
    selected.duration_us = scheduler->slot_us;
    if ((burst_mask & (uint8_t)(1u << selected.zone)) != 0u)
        selected.duration_us += scheduler->burst_extra_us;
    if (now_us > UINT64_MAX - selected.duration_us) return NL_ERR_SIZE;
    scheduler->visited_mask = visited;
    scheduler->next_at_us = now_us + selected.duration_us;
    scheduler->last_now_us = now_us;
    scheduler->started = true;
    scheduler->current_window = selected;
    *window = selected;
    return NL_OK;
}

nl_status nl_scheduler_hold_burst(nl_scheduler *scheduler, uint8_t zone, uint64_t now_us)
{
    uint32_t duration;
    if (scheduler == NULL || zone >= 8u) return NL_ERR_ARGUMENT;
    if (now_us < scheduler->last_now_us) return NL_ERR_ARGUMENT;
    if (!scheduler->started || scheduler->current_window.zone != zone || now_us >= scheduler->next_at_us)
        return NL_ERR_NOT_FOUND;
    duration = scheduler->slot_us + scheduler->burst_extra_us;
    if (scheduler->current_window.start_us > UINT64_MAX - duration) return NL_ERR_SIZE;
    scheduler->current_window.duration_us = duration;
    scheduler->next_at_us = scheduler->current_window.start_us + duration;
    scheduler->last_now_us = now_us;
    return NL_OK;
}

nl_status nl_scheduler_current(const nl_scheduler *scheduler, uint64_t now_us, nl_window *window)
{
    if (scheduler == NULL || window == NULL) return NL_ERR_ARGUMENT;
    if (now_us < scheduler->last_now_us) return NL_ERR_ARGUMENT;
    if (!scheduler->started || now_us >= scheduler->next_at_us) return NL_ERR_NOT_FOUND;
    *window = scheduler->current_window;
    return NL_OK;
}
