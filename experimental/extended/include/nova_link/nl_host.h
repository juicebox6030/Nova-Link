/**
 * @file nl_host.h
 * @brief Host core (ESP32-S3): plugin registry, zone claims, dispatch,
 *        Zone 0 metadata, and radio configuration.
 *
 * The host never talks to hardware directly. It reaches the radio through an
 * nl_link_ops_t (normally the SPI driver in nl_spi_link.h; tests and the
 * simulator wire it straight to an nl_radio_t).
 *
 * All functions must be called from one task/thread. Plugins may call the
 * send/claim/meta functions from inside their callbacks.
 *
 * Typical use:
 * @code
 * static nl_host_t host;
 * nl_host_config_t cfg;
 * nl_host_config_default(&cfg);
 * cfg.origin_id = 2;
 * nl_host_init(&host, &cfg, &link_ops);
 * nl_host_set_rf(&host, &params, &plan);
 * nl_host_register(&host, &my_plugin);    // plugin init claims zones
 * for (;;) nl_host_poll(&host, now_us());
 * @endcode
 */
#ifndef NL_HOST_H
#define NL_HOST_H

#include "nl_common.h"
#include "nl_fragment.h"
#include "nl_link.h"
#include "nl_meta.h"
#include "nl_stream_tracker.h"
#include "nl_zone.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct nl_host nl_host_t;

/** Abstract connection to the radio co-processor. */
typedef struct {
    /** Queue one encoded DataFragment for transmission. */
    int (*push)(void *ctx, const uint8_t *frag, size_t len);
    /** Fetch one received fragment. @return length (>0), 0 if none, or < 0. */
    int (*pull)(void *ctx, uint8_t *buf, size_t cap);
    /** INT_READY state. NULL means "unknown": the host pulls until empty. */
    bool (*rx_pending)(void *ctx);
    /** Send scheduler parameters and zone plan. */
    int (*configure)(void *ctx, const nl_radio_params_t *params,
                     const nl_zone_plan_t *plan);
    /** Read radio status (optional, may be NULL). */
    int (*status)(void *ctx, nl_radio_status_t *st);
    void *ctx;
} nl_link_ops_t;

/** A plugin compiled into the firmware. The definition must outlive the host. */
typedef struct {
    const char *name;
    /** Identifies the payload format. Announced in claim snapshots so remote
     *  hosts can reject payloads meant for a different plugin type. */
    uint16_t type_id;
    /** Called from nl_host_register(); claim zones here. Return < 0 to abort. */
    int (*init)(nl_host_t *host, uint8_t slot, void *user);
    /** A new (deduplicated) fragment on a zone this plugin claims. */
    void (*on_fragment)(nl_host_t *host, uint8_t slot, const nl_fragment_t *frag,
                        void *user);
    /** A Zone 0 PLUGIN_DATA record addressed to this plugin's type_id. */
    void (*on_meta)(nl_host_t *host, uint8_t slot, uint8_t origin,
                    const uint8_t *data, size_t len, void *user);
    /** Called once per nl_host_poll(). */
    void (*on_tick)(nl_host_t *host, uint8_t slot, nl_time_us_t now, void *user);
    /** Called from nl_host_unregister(). */
    void (*deinit)(nl_host_t *host, uint8_t slot, void *user);
    void *user;
} nl_plugin_def_t;

/** Host tuning. Defaults from nl_host_config_default(). */
typedef struct {
    uint8_t origin_id;             /**< This device's originID (0..7). */
    char name[25];                 /**< Announced device name. */
    uint32_t announce_interval_us; /**< Device + claim announce period (0 = off). */
    uint32_t announce_jitter_us;   /**< Each period is shortened by a random
                                        0..N us, so devices powered up together
                                        drift apart instead of colliding forever.
                                        Values >= announce_interval_us are
                                        reduced to half the interval.
                                        A device that does not know us yet (a
                                        new peer, or one whose NL_META_PEERS
                                        record lacks our bit) is answered after
                                        a random 0..N us (capped at half the
                                        radio's mgmt_hold_us) so every device
                                        does not reply at once. */
    uint32_t announce_boot_spread_us; /**< Delay the first announcement after
                                        start by a random 0..N us, so devices
                                        powered up together do not all
                                        announce in the same instant
                                        (0 = announce on the first poll). */
    uint8_t announce_ramp_steps;   /**< After start, the first N periods are
                                        shortened to interval/2^N, /2^(N-1),
                                        ... /2, so a device powered up among
                                        others gets several chances to be
                                        heard before settling (0 = off). */
    uint32_t rand_seed;            /**< Jitter seed; pass hardware entropy
                                        (0 = derive from originID and name). */
    uint32_t meta_interval_us;     /**< Minimum gap between Zone 0 fragments. */
    uint32_t meta_lead_us;         /**< Delay before the first Zone 0 fragment of a
                                        batch, so MGMT_LISTEN on regular fragments
                                        can pull receivers onto zone 0 first. */
    uint32_t mgmt_flag_hold_us;    /**< Keep setting MGMT_LISTEN this long after
                                        the last Zone 0 fragment. */
    uint32_t status_interval_us;   /**< Radio status poll period (0 = off). */
    uint32_t remote_claim_expiry_us; /**< Forget remote claims after this. */
    uint32_t peer_expiry_us;       /**< Forget remote devices after this. */
    uint32_t tracker_stale_us;     /**< Host-side dedup stream expiry. */
    bool check_remote_types;       /**< Drop fragments whose sender announced a
                                        different plugin type for the zone. */
    uint8_t max_pull_per_poll;     /**< Bound on fragments pulled per poll
                                        (>= 1; nl_host_init() rejects 0). */
} nl_host_config_t;

/** Called for every new fragment before dispatch (live monitor / logging). */
typedef void (*nl_rx_monitor_t)(nl_host_t *host, const nl_fragment_t *frag,
                                nl_time_us_t now, void *user);
/** Called for every Zone 0 record received (including unknown types). */
typedef void (*nl_meta_hook_t)(nl_host_t *host, uint8_t origin, uint8_t type,
                               const uint8_t *value, uint8_t len, void *user);

/** A remote device learned from DEVICE_ANNOUNCE. */
typedef struct {
    bool valid;
    nl_meta_device_t info;
    nl_time_us_t last_seen;
} nl_host_peer_t;

/** Host counters. */
typedef struct {
    uint32_t rx_fragments;     /**< New fragments received. */
    uint32_t rx_duplicates;    /**< Dropped by the host stream tracker. */
    uint32_t rx_invalid;       /**< Malformed fragments or meta records. */
    uint32_t rx_undelivered;   /**< No plugin claims the zone. */
    uint32_t rx_type_mismatch; /**< Rejected by remote plugin-type check. */
    uint32_t tx_fragments;     /**< Fragments pushed to the radio. */
    uint32_t tx_denied;        /**< Sends rejected by claim rules. */
    uint32_t tx_errors;        /**< Link push failures. */
    uint32_t meta_fragments;   /**< Zone 0 fragments sent. */
    uint32_t link_errors;      /**< Pull/status/config failures. */
    uint32_t radio_resets;     /**< Radio reported unconfigured; config resent. */
} nl_host_stats_t;

struct nl_host {
    nl_host_config_t cfg;
    nl_link_ops_t link;

    const nl_plugin_def_t *plugins[NL_MAX_PLUGINS];
    nl_claim_table_t claims;
    nl_remote_claims_t remote;
    nl_stream_tracker_t tracker;
    nl_meta_queue_t meta;
    nl_host_peer_t peers[NL_NUM_ORIGINS];

    uint8_t tx_seq[NL_NUM_ZONES];
    nl_radio_params_t params;
    nl_zone_plan_t plan; /**< Frequencies + configured priorities. */
    bool rf_dirty;
    bool announce_dirty;
    bool reply_pending;        /**< A peer is owed an announcement. */
    nl_time_us_t reply_at;
    uint8_t ramp_left;         /**< Shortened announce periods remaining. */

    nl_time_us_t now;
    nl_time_us_t next_announce;
    nl_time_us_t next_meta;
    nl_time_us_t mgmt_flag_until;
    nl_time_us_t next_status;
    bool started;
    uint32_t rng;
    uint32_t last_tx_dropped;
    uint32_t last_rx_dropped;

    nl_rx_monitor_t monitor;
    void *monitor_user;
    nl_meta_hook_t meta_hook;
    void *meta_hook_user;

    nl_host_stats_t stats;
};

void nl_host_config_default(nl_host_config_t *cfg);

/** Initialise the host. @p link is copied. */
int nl_host_init(nl_host_t *host, const nl_host_config_t *cfg,
                 const nl_link_ops_t *link);

/**
 * Set the RF configuration. Frequencies and zone 0 priority are used as
 * given; zones 1..7 are only scheduled while a local plugin claims them,
 * using the configured priority (minimum 1). origin_id is taken from the
 * host config. Sent to the radio on the next poll.
 */
void nl_host_set_rf(nl_host_t *host, const nl_radio_params_t *params,
                    const nl_zone_plan_t *plan);

/** Build the plan actually sent to the radio from claims + configuration. */
void nl_host_effective_plan(const nl_host_t *host, nl_zone_plan_t *out);

/** Register a plugin and run its init. @return slot (>= 0) or < 0. */
int nl_host_register(nl_host_t *host, const nl_plugin_def_t *def);

/** Run deinit, release all of the plugin's claims, and free the slot. */
int nl_host_unregister(nl_host_t *host, uint8_t slot);

/** Find a registered plugin by name. @return slot or NL_ERR_NOT_FOUND. */
int nl_host_find_plugin(const nl_host_t *host, const char *name);

/** Claim a zone for a plugin (see nl_zone.h rules). */
int nl_host_claim(nl_host_t *host, uint8_t slot, uint8_t zone, nl_claim_mode_t mode);

/** Release a claim. */
int nl_host_release(nl_host_t *host, uint8_t slot, uint8_t zone);

/**
 * Send one fragment on a claimed zone. The host fills originID and seqNum,
 * and sets MGMT_LISTEN automatically while metadata is queued.
 * @param host     Host instance.
 * @param slot     Sending plugin's slot.
 * @param zone     Zone 1..7; the plugin needs a shared or exclusive claim.
 * @param payload  Fragment payload.
 * @param len      Payload length, at most NL_MAX_PAYLOAD.
 * @param flags    NL_FLAG_BURST or 0.
 * @return NL_OK, NL_ERR_PERM (no send claim / zone 0), NL_ERR_SIZE, or a
 *         link error.
 */
int nl_host_send(nl_host_t *host, uint8_t slot, uint8_t zone, const uint8_t *payload,
                 size_t len, uint8_t flags);

/**
 * Send a message larger than one payload using nl_segment.h framing.
 * All segments are pushed at once with consecutive seqNums.
 */
int nl_host_send_segmented(nl_host_t *host, uint8_t slot, uint8_t zone,
                           const uint8_t *msg, size_t len);

/** Queue a raw Zone 0 record (any plugin or the application may call this). */
int nl_host_meta_push(nl_host_t *host, uint8_t type, const uint8_t *value, size_t len);

/** Queue a PLUGIN_DATA record tagged with the plugin's type_id. */
int nl_host_meta_send_plugin(nl_host_t *host, uint8_t slot, const uint8_t *data,
                             size_t len);

/** Queue a DEBUG_TEXT record (truncated to fit one record). */
int nl_host_meta_debug(nl_host_t *host, const char *text);

/** Force device + claim announcements on the next poll. */
void nl_host_announce_now(nl_host_t *host);

/**
 * Do all periodic work: push RF config when it changed, pull and dispatch
 * received fragments, send Zone 0 metadata, poll radio status, tick plugins.
 */
void nl_host_poll(nl_host_t *host, nl_time_us_t now);

/** Feed one received fragment directly (used by poll; exposed for tests). */
void nl_host_handle_rx(nl_host_t *host, const uint8_t *data, size_t len,
                       nl_time_us_t now);

void nl_host_set_monitor(nl_host_t *host, nl_rx_monitor_t fn, void *user);
void nl_host_set_meta_hook(nl_host_t *host, nl_meta_hook_t fn, void *user);

/** Live peer for @p origin, or NULL. */
const nl_host_peer_t *nl_host_peer(const nl_host_t *host, uint8_t origin);

#ifdef __cplusplus
}
#endif

#endif /* NL_HOST_H */
