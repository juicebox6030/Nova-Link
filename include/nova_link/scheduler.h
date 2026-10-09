#ifndef NOVA_LINK_SCHEDULER_H
#define NOVA_LINK_SCHEDULER_H

#include <stdbool.h>
#include <stdint.h>
#include "nova_link/status.h"

/** @file scheduler.h Deterministic data-zone rounds followed by optional management slots. */
typedef struct { uint8_t zone; uint64_t start_us; uint32_t duration_us; } nl_window;
typedef struct {
    uint8_t active_mask;
    uint8_t visited_mask;
    uint32_t slot_us;
    uint32_t burst_extra_us;
    uint64_t next_at_us;
    uint64_t last_now_us;
    bool started;
    nl_window current_window;
} nl_scheduler;

nl_status nl_scheduler_init(nl_scheduler *scheduler, uint8_t active_mask, uint32_t slot_us, uint32_t burst_extra_us);
/** Apply zone interest, removing abandoned visits without resetting current timing. */
nl_status nl_scheduler_set_active(nl_scheduler *scheduler, uint8_t active_mask);
/** Pick one due window. A late caller starts now, avoiding catch-up bursts.
 * Metadata runs after each data round if requested, or alone when no data zones exist.
 * Burst can extend a slot once by at most slot_us; it cannot hold a zone indefinitely.
 */
nl_status nl_scheduler_next(nl_scheduler *scheduler, uint64_t now_us, bool management_pending,
                            uint8_t burst_mask, nl_window *window);
/** Extend the CURRENT matching window once, relative to its original start.
 * A receiver must call this while the burst-bearing frame's zone window is open.
 * Repeated requests never add another extension. Returns NOT_FOUND outside it.
 */
nl_status nl_scheduler_hold_burst(nl_scheduler *scheduler, uint8_t zone, uint64_t now_us);
/** Read the current window after RX flags may have extended its deadline. */
nl_status nl_scheduler_current(const nl_scheduler *scheduler, uint64_t now_us, nl_window *window);

#endif
