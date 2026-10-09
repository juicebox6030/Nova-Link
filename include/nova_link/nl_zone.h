/**
 * @file nl_zone.h
 * @brief Zone claim management (local plugins and remote devices).
 *
 * Claim rules (docs/Zone_Management.md):
 *
 * | Requested \ Held by others | none | READ_ONLY | SHARED | EXCLUSIVE |
 * |----------------------------|------|-----------|--------|-----------|
 * | READ_ONLY                  | ok   | ok        | ok     | conflict  |
 * | SHARED                     | ok   | ok        | ok     | conflict  |
 * | EXCLUSIVE                  | ok   | conflict  | conflict | conflict |
 *
 * - Zone 0 can never be claimed; it is always readable and writable through
 *   the metadata API.
 * - READ_ONLY claims receive but may not transmit.
 * - Rejected claims and send attempts are logged as warnings.
 */
#ifndef NL_ZONE_H
#define NL_ZONE_H

#include "nl_common.h"
#include "nl_meta.h"

#ifdef __cplusplus
extern "C" {
#endif

/** How a plugin holds a zone. */
typedef enum {
    NL_CLAIM_NONE = 0,
    NL_CLAIM_SHARED = 1,    /**< Send + receive; others may share. */
    NL_CLAIM_EXCLUSIVE = 2, /**< Send + receive; no other plugin may claim. */
    NL_CLAIM_READ_ONLY = 3, /**< Receive only. */
} nl_claim_mode_t;

/** Return "none", "shared", "exclusive", or "read-only". */
const char *nl_claim_mode_str(uint8_t mode);

/** Local claim table: mode per (plugin slot, zone). */
typedef struct {
    uint8_t mode[NL_MAX_PLUGINS][NL_NUM_ZONES];
} nl_claim_table_t;

void nl_claims_init(nl_claim_table_t *t);

/**
 * Acquire or change a claim.
 * @return NL_OK, NL_ERR_ARG, NL_ERR_PERM (zone 0), or NL_ERR_CONFLICT.
 */
int nl_claims_acquire(nl_claim_table_t *t, uint8_t plugin, uint8_t zone,
                      nl_claim_mode_t mode);

/** Release a claim. @return NL_OK or NL_ERR_NOT_FOUND. */
int nl_claims_release(nl_claim_table_t *t, uint8_t plugin, uint8_t zone);

/** Release every claim held by a plugin. */
void nl_claims_release_all(nl_claim_table_t *t, uint8_t plugin);

/** Mode held by @p plugin on @p zone. */
nl_claim_mode_t nl_claims_get(const nl_claim_table_t *t, uint8_t plugin,
                              uint8_t zone);

/** True if @p plugin may transmit on @p zone. */
bool nl_claims_can_send(const nl_claim_table_t *t, uint8_t plugin, uint8_t zone);

/** Bitmask of zones (bit n = zone n) with at least one local claim. */
uint8_t nl_claims_zone_mask(const nl_claim_table_t *t);

/* ---- Remote claim map -------------------------------------------------- */

/** plugin_type value meaning "several plugin types share this zone". */
#define NL_PLUGIN_TYPE_ANY 0xFFFFu

/** What one remote origin announced for one zone. */
typedef struct {
    uint8_t mode;         /**< nl_claim_mode_t; NONE = not announced. */
    uint16_t plugin_type;
    nl_time_us_t seen;    /**< Time of the announcement. */
} nl_remote_claim_t;

/**
 * Claim snapshots received from other devices via NL_META_CLAIM_ANNOUNCE.
 * Used to drop payloads from a plugin type that does not match the local
 * consumer (docs/Zone_Management.md: "avoid plugins receiving invalid
 * payloads").
 */
typedef struct {
    nl_remote_claim_t claim[NL_NUM_ORIGINS][NL_NUM_ZONES];
    uint32_t expiry_us; /**< Entries older than this are ignored (0 = never). */
} nl_remote_claims_t;

void nl_remote_claims_init(nl_remote_claims_t *t, uint32_t expiry_us);

/**
 * Replace everything known about @p origin with a new snapshot. A zone
 * listed several times keeps the strongest sending mode, and its plugin
 * type becomes NL_PLUGIN_TYPE_ANY if the entries disagree.
 */
void nl_remote_claims_update(nl_remote_claims_t *t, uint8_t origin,
                             const nl_meta_claim_t *claims, size_t count,
                             nl_time_us_t now);

/** Look up a live claim, or NULL if none is known / it expired. */
const nl_remote_claim_t *nl_remote_claims_get(const nl_remote_claims_t *t,
                                              uint8_t origin, uint8_t zone,
                                              nl_time_us_t now);

#ifdef __cplusplus
}
#endif

#endif /* NL_ZONE_H */
