#ifndef NOVA_LINK_SPI_BACKEND_H
#define NOVA_LINK_SPI_BACKEND_H

#include "nova_link/radio_plugin.h"

/** @file spi_backend.h Bounded asynchronous native-frame SPI driver service.
 * Uses documented AA/LEN/COMMAND frames. Driver outcomes and receipt tokens are
 * local C metadata: no physical ACK, empty/error bytes, pins or timing invented.
 * Calls are serialized on the host task; callbacks must not reenter this API.
 */
typedef uint64_t nl_spi_transaction;

typedef struct {
    nl_status (*start)(void *context); /**< Optional; failure still invokes stop. */
    /** Cancel/drain ALL ownership, including receipts, before returning. Required.
     * Startup rollback uses this even if ordinary shutdown would be BUSY.
     */
    void (*stop)(void *context);
    nl_status (*can_stop)(void *context); /**< Optional driver-owned-work veto. */
    nl_status (*ready)(void *context, bool *ready); /**< Task-owned INT_READY read. */
    /** NL_OK accepts immutable request storage until finish terminates or stop
     * drains it. Errors accept nothing. Tokens are local, never serialized.
     */
    nl_status (*begin)(void *context, const uint8_t *request, size_t request_size,
                       nl_spi_transaction transaction, uint64_t now_us);
    /** BUSY retains ownership. Other outcomes end request ownership. NL_OK PUSH
     * completes local driver transfer, with zero response bytes/receipt. It does
     * not establish remote radio enqueue or physical ACK. Terminal PUSH errors with
     * uncertain=false MUST guarantee no remote acceptance. uncertain=true
     * latches delivery uncertainty and stops retries pending explicit resolution.
     * PULL NL_OK provides one exact native FRAGMENT and nonzero local receipt;
     * EMPTY accepts no receipt. On other errors no receipt may be acquired.
     * Driver must bound writes to capacity, and retain receipt until settle.
     */
    nl_status (*finish)(void *context, nl_spi_transaction transaction,
                        uint64_t now_us, uint8_t *response, size_t capacity,
                        size_t *response_size, nl_pull_token *receipt, bool *uncertain);
    /** Consume the bound immutable PULL receipt or abort it without dropping
     * radio data. NL_OK/STALE/EMPTY release it; other errors retain it for retry.
     * This local operation does not imply a wire acknowledgement. Required.
     */
    nl_status (*settle)(void *context, nl_pull_token receipt, bool consume);
    void *context;
} nl_spi_driver;

typedef struct {
    uint64_t tx_accepted, tx_completed, tx_retries, tx_uncertain, tx_discarded;
    uint64_t rx_prepared, rx_committed, rx_aborted;
    uint64_t driver_errors, malformed, backward_clocks;
} nl_spi_backend_stats;

typedef struct {
    nl_spi_driver driver;
    nl_spi_backend_stats stats;
    nl_host *host;
    nl_plugin_id plugin;
    nl_status last_status;
    uint64_t now_us;
    nl_spi_transaction next_transaction, transaction;
    uint8_t tx[NL_FRAME_MAX], request[NL_FRAME_MAX], response[NL_FRAME_MAX];
    size_t tx_size, request_size, response_size;
    nl_frame rx_frame;
    nl_pull_token receipt;
    bool running, started, calling, have_clock, prefer_rx;
    bool tx_pending, tx_uncertain, inflight, pulling, rx_pending, abort_pending;
} nl_spi_backend;

/** Initialize inactive caller-owned storage. Keep it and driver context alive.
 * Reinitialization must follow shutdown with all driver ownership drained.
 */
nl_status nl_spi_backend_init(nl_spi_backend *backend, const nl_spi_driver *driver);
/** Resolve an uncertain PUSH from outside host/driver callbacks. retry=true
 * requires external evidence that retransmission is appropriate: it can create
 * duplicates if the peer already accepted it. retry=false discards locally held
 * ownership without claiming delivery. Ordinary shutdown stays BUSY until this
 * decision. No wire acknowledgement or automatic remote reset is introduced.
 */
nl_status nl_spi_backend_resolve_tx(nl_spi_backend *backend, bool retry);
/** SERVICE named spi-backend; host poll progresses at most one begin/finish.
 * While work is pending shutdown is BUSY; startup rollback calls driver.stop.
 */
nl_module nl_spi_backend_module(nl_spi_backend *backend);
/** Configure the existing native radio-link provider to use this backend. */
nl_status nl_spi_backend_link_config(nl_spi_backend *backend, uint16_t poll_budget,
                                     nl_radio_link_config *config);
/** radio-link descriptor requiring spi-backend; rename dependencies together
 * when using custom service names. Initialize link with link_config first.
 */
nl_module nl_spi_backend_link_module(nl_radio_link *link);

#endif
