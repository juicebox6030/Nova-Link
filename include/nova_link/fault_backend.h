#ifndef NOVA_LINK_FAULT_BACKEND_H
#define NOVA_LINK_FAULT_BACKEND_H

#include "nova_link/radio_plugin.h"

/** @file fault_backend.h Optional deterministic developer support, not device I/O.
 * Caller-owned storage, serialized calls, FIFO native queues and logical times.
 * Never mutate public radio/transfer storage while it owns work. No RF or SPI
 * timings, packet loss inference or proprietary Multiverse compatibility.
 */
typedef enum {
    NL_FAULT_CLEAN, NL_FAULT_DELAYED, NL_FAULT_DISCONNECTED,
    NL_FAULT_CONGESTED, NL_FAULT_COMMIT_RETRY
} nl_fault_profile;

typedef struct {
    uint8_t active_mask;
    uint32_t slot_us;
    uint64_t transfer_delay_us, commit_delay_us;
    uint32_t commit_failures;
    bool connected;
} nl_fault_options;

typedef struct {
    uint64_t pushes, rejected_pushes, offline_pushes;
    uint64_t receipts, commits, commit_retries, invalidations, stale_commits;
    uint64_t starts, stops, restarts;
    uint64_t canceled_pushes, canceled_receipts; /**< Startup rollback only. */
} nl_fault_stats;

typedef struct {
    nl_radio radio;
    nl_fault_options options;
    nl_fault_stats stats;
    uint64_t now, commit_at;
    nl_frame receipt;
    nl_pull_token receipt_token;
    uint32_t commit_failures;
    unsigned incoming;
    bool connected, committing, in_flight, started;
} nl_fault_backend;

typedef struct {
    nl_fragment original, outgoing;
    uint8_t bytes[NL_FRAGMENT_MAX], original_bytes[NL_FRAGMENT_MAX];
    size_t size, original_size;
    uint64_t complete_at, delay, completed, blocked, rejected;
    nl_fault_backend *sender, *receiver;
    bool pending;
} nl_fault_transfer;

/** Direct send/poll adapter for generated transport plugins. Same retained
 * receipt contract as radio-link, without attaching another host transport.
 * Each adapter belongs to exactly one lifecycle provider. Distinct adapters
 * attempting to acquire the same backend fail safely without stopping its owner.
 */
typedef struct {
    nl_fault_backend *backend;
    nl_radio_link_config config;
    nl_radio_link_stats stats;
    nl_frame response;
    nl_pull_token token;
    bool pending, settled, owns_backend;
} nl_fault_adapter;

nl_status nl_fault_adapter_init(nl_fault_adapter *adapter, nl_fault_backend *backend,
                                uint16_t poll_budget);
/** Recommended radio-link binding: adapter owns this one provider lifecycle;
 * failed startup of another adapter cannot stop its backend. Use either this
 * framed binding or direct callbacks for a given adapter, never two providers.
 */
nl_radio_link_config nl_fault_adapter_link_config(nl_fault_adapter *adapter);
nl_status nl_fault_adapter_start(void *context);
void nl_fault_adapter_stop(void *context);
nl_status nl_fault_adapter_can_stop(void *context);
nl_status nl_fault_adapter_send(void *context, const nl_fragment *fragment);
void nl_fault_adapter_poll(nl_host *host, uint64_t now_us, void *context);

/** Presets use logical microseconds: CLEAN=0/0, DELAYED=400/900,
 * CONGESTED=400/4000; DISCONNECTED starts offline; COMMIT_RETRY fails three
 * commits with BUSY. Delays are transfer/commit. Default mask=2, slot=1000.
 * Application controls event schedule and production; no wall-clock I/O.
 */
nl_status nl_fault_profile_options(nl_fault_profile profile, nl_fault_options *options);
/** Initialize fresh storage; never reinitialize storage owning queues/receipts. */
nl_status nl_fault_backend_init(nl_fault_backend *backend, const nl_fault_options *options);
/** Lifecycle callbacks for an ordinary radio-link module. poll_budget > 0.
 * Exactly one config/provider lifecycle may reference this backend. Do not
 * attach the same backend through another link or direct adapter concurrently;
 * raw callback context cannot distinguish ownership of two provider lifecycles.
 * Use distinct nl_fault_adapter instances for safely competing direct adapters.
 */
nl_radio_link_config nl_fault_backend_link_config(nl_fault_backend *backend, uint16_t poll_budget);
/** Monotonic logical clock; equal times are allowed. */
nl_status nl_fault_backend_set_time(nl_fault_backend *backend, uint64_t now_us);
void nl_fault_backend_set_connected(nl_fault_backend *backend, bool connected);
void nl_fault_backend_fail_commits(nl_fault_backend *backend, uint32_t attempts);
/** Explicitly discard the currently retained RX head, preserving later heads.
 * Its old commit returns STALE, even with a new receipt queued. The link must
 * poll to abandon its retained receipt before shutdown/restart.
 */
nl_status nl_fault_backend_invalidate_receipt(nl_fault_backend *backend);
/** True only when TX/RX queues, receipts, incoming and outgoing transfers drain. */
bool nl_fault_backend_drained(const nl_fault_backend *backend);
/** Reset native scheduling/dedup only after stopping and draining. Receipt token
 * allocation remains monotonic, preventing old receipts from popping new data.
 * Host native stream tracking and application sessions are reset separately.
 */
nl_status nl_fault_backend_restart(nl_fault_backend *backend);
/** Initialize fresh/drained transfer storage. Exactly one outgoing transfer per
 * backend; multiple incoming transfers are allowed. It must outlive pending work.
 * Drive transfers only after manifest startup succeeds. Startup rollback cancels
 * queued native work, and cannot cancel cross-backend transfers already driven.
 */
nl_status nl_fault_transfer_init(nl_fault_transfer *transfer, uint64_t delay_us);
/** Set both logical clocks and advance at most one FIFO transfer. First step
 * freezes bytes, a later step completes (even for zero delay). OK=completed,
 * EMPTY=no current-window TX; BUSY=delay/offline/pending started; FULL=RX full.
 * Receiver duplicate/stale/access rejection completes TX and increments rejected.
 * A pending transfer is bound to the same two backends. Native queue acceptance
 * and simulated completion are distinct; no host RX dispatch occurs here.
 */
nl_status nl_fault_transfer_step(nl_fault_backend *sender, nl_fault_backend *receiver,
                                 nl_fault_transfer *transfer, uint64_t now_us);

#endif
