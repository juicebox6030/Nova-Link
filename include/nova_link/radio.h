#ifndef NOVA_LINK_RADIO_H
#define NOVA_LINK_RADIO_H

#include "nova_link/queue.h"
#include "nova_link/scheduler.h"
#include "nova_link/stream.h"
#include "nova_link/transport.h"

/** @file radio.h Portable co-processor model; adapters own all SPI/GPIO/PHY I/O. */
/* Concurrency: the core takes no locks. Every nl_radio_* call on one radio
 * (and any nl_secure state used with it) must come from a single task, or the
 * caller must serialize them. Interrupt handlers must not call into the core;
 * they only move bytes into an adapter-owned ring that the task drains.
 */
/* Queue depths are build-time tunables; TX storage is 8 zones x depth x 105 B. */
#ifndef NL_RADIO_TX_DEPTH
#define NL_RADIO_TX_DEPTH 8u
#endif
#ifndef NL_RADIO_RX_DEPTH
#define NL_RADIO_RX_DEPTH 16u
#endif
typedef enum { NL_RX_FIFO, NL_RX_LATEST_PER_STREAM } nl_rx_policy;
/** Adapter-local receipt; never sent on the wire. Valid for one radio lifetime. */
typedef uint64_t nl_pull_token;
typedef struct {
    uint64_t received;
    uint64_t duplicates;
    uint64_t stale;
    uint64_t rx_full;
    uint64_t tx_full;
    uint64_t coalesced;
} nl_radio_stats;
typedef struct {
    nl_scheduler scheduler;
    nl_stream_tracker streams;
    nl_queue tx[8];
    nl_fragment tx_storage[8][NL_RADIO_TX_DEPTH];
    nl_queue rx;
    nl_fragment rx_storage[NL_RADIO_RX_DEPTH];
    nl_pull_token rx_tokens[NL_RADIO_RX_DEPTH];
    nl_pull_token next_rx_token;
    nl_radio_stats stats;
    bool management_listen;
    nl_rx_policy rx_policy;
} nl_radio;

nl_status nl_radio_init(nl_radio *radio, uint8_t active_mask, uint32_t slot_us,
                        uint32_t burst_extra_us, uint64_t idle_timeout_us);
/** Cannot disable a zone with queued TX. Drain it before changing subscriptions. */
nl_status nl_radio_set_active(nl_radio *radio, uint8_t active_mask);
/** Change RX policy only while empty. FIFO is the default; latest mode replaces
 * an already queued (origin, zone) value without consuming another queue slot.
 * Use latest mode only for self-contained state updates, never fragment groups.
 */
nl_status nl_radio_set_rx_policy(nl_radio *radio, nl_rx_policy policy);
nl_status nl_radio_enqueue(nl_radio *radio, const nl_fragment *fragment);
/** Validate, deduplicate, then queue. Queue overflow does not consume a sequence. */
nl_status nl_radio_receive(nl_radio *radio, const nl_fragment *fragment, uint64_t now_us);
bool nl_radio_ready(const nl_radio *radio);
nl_status nl_radio_pull(nl_radio *radio, nl_fragment *fragment);
/** Prepare a PULL response without removing RX data. Retry after an aborted transfer. */
nl_status nl_radio_prepare_pull(const nl_radio *radio, nl_frame *response, nl_pull_token *token);
/** Remove the matching prepared head once the adapter completes ownership transfer.
 * A mismatched/stale response never removes another fragment.
 */
nl_status nl_radio_commit_pull(nl_radio *radio, const nl_frame *response, nl_pull_token token);
nl_status nl_radio_next_window(nl_radio *radio, uint64_t now_us, nl_window *window);
/** Prepare the current window's TX head without removing it. A BURST head holds
 * the current sender window, including late enqueue or a second TX in one slot.
 * Use before every PHY submission; outputs include the refreshed deadline.
 * The adapter must ensure peers process the first BURST announcement before
 * their original slot closes, including RX/clock margins, and enforce airtime
 * and completion limits itself.
 */
nl_status nl_radio_prepare_tx(nl_radio *radio, uint64_t now_us, nl_fragment *fragment, nl_window *window);
/** Inspect a zone's queue without applying timing flags; use prepare_tx for submission. */
nl_status nl_radio_peek_tx(const nl_radio *radio, uint8_t zone, nl_fragment *fragment);
/** Pop only once the adapter has taken ownership. */
nl_status nl_radio_pop_tx(nl_radio *radio, uint8_t zone, nl_fragment *fragment);
void nl_radio_request_management(nl_radio *radio);
/** Handle PUSH (no response) and PULL (prepared FRAGMENT response or EMPTY).
 * PULL requires nl_radio_commit_pull() after the adapter transfers ownership.
 * PING/STATUS wire responses remain unspecified and return UNSUPPORTED.
 */
nl_status nl_radio_handle_frame(nl_radio *radio, const nl_frame *request, nl_frame *response, nl_pull_token *token);

#endif
