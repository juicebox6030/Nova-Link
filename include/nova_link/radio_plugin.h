#ifndef NOVA_LINK_RADIO_PLUGIN_H
#define NOVA_LINK_RADIO_PLUGIN_H

#include "nova_link/host.h"
#include "nova_link/module.h"
#include "nova_link/radio.h"

/** @file radio_plugin.h Lifecycle-managed native PUSH/PULL transport provider.
 * This adapter carries native NOVA-LINK frames, not proprietary Multiverse RF.
 * Storage and physical serialization/device access belong to the application.
 */

typedef struct {
    /** PUSH: NL_OK means the backend accepted TX ownership; an error must not
     * enqueue it. PULL: NL_OK fills response and token; EMPTY means no data.
     * Response/token are always non-NULL and are ignored for PUSH.
     * With commit configured, retain the exact PULL response until commit,
     * or report its invalidation through commit returning STALE/EMPTY.
     * Without commit, a successful PULL transfers ownership into link storage.
     */
    nl_status (*exchange)(void *context, const nl_frame *request,
                          nl_frame *response, nl_pull_token *token);
    /** Optional transactional acknowledgement. STALE/EMPTY means this receipt
     * no longer owns backend data; forget it and pull the replacement. Other
     * errors retain ownership and permit retry of the same response/token.
     * Successful acknowledgement
     * also discards terminally undeliverable frames (including malformed data).
     */
    nl_status (*commit)(void *context, const nl_frame *response, nl_pull_token token);
    /** Optional backend initialization and rollback/drain cleanup. Stop is called
     * even after start fails, but never when another provider prevented attach.
     */
    nl_status (*start)(void *context);
    void (*stop)(void *context);
    /** Optional shutdown veto for application-owned queues or device operations. */
    nl_status (*can_stop)(void *context);
    void *context;
    uint16_t poll_budget; /**< Maximum RX receipt attempts per host poll; nonzero. */
} nl_radio_link_config;

typedef struct {
    uint64_t tx_accepted;
    uint64_t tx_errors;
    uint64_t rx_pulled;
    uint64_t rx_delivered;
    uint64_t rx_discarded;
    uint64_t receive_retries;
    uint64_t exchange_errors;
    uint64_t commit_errors;
    uint64_t commit_abandoned; /**< Receipts invalidated by backend STALE/EMPTY. */
    uint64_t commits;
} nl_radio_link_stats;

typedef struct {
    nl_radio_link_config config;
    nl_radio_link_stats stats;
    nl_status last_status;
    nl_status last_receive_status;
    nl_host *host;
    nl_plugin_id plugin;
    nl_frame pending_response;
    nl_pull_token pending_token;
    bool pending;
    bool settled;
    bool backend_started;
    bool exchanging;
} nl_radio_link;

/** Initialize caller-owned storage before registration. Do not reinitialize an
 * active context or one holding pending backend ownership. Calls are serialized.
 */
nl_status nl_radio_link_init(nl_radio_link *link, const nl_radio_link_config *config);
/** Register this descriptor on a host initialized with nl_host_init_plugins().
 * Receive errors other than BUSY are terminal: count/discard, then commit them,
 * so an unwanted zone, duplicate, stale, conflict or malformed head cannot stall
 * the queue. BUSY and retryable commit errors retain the response; successful delivery is
 * never repeated during commit retries. Unregister vetoes any pending response.
 */
nl_plugin nl_radio_link_plugin(nl_radio_link *link);
/** Default manifest descriptor; name may be replaced for a separate instance. */
nl_module nl_radio_link_module(nl_radio_link *link);

#endif
