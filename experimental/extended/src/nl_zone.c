/**
 * @file nl_zone.c
 * @brief Local and remote zone claim tables.
 */
#include "nova_link/nl_zone.h"
#include "nova_link/nl_log.h"

#include <string.h>

const char *nl_claim_mode_str(uint8_t mode)
{
    switch (mode) {
    case NL_CLAIM_NONE: return "none";
    case NL_CLAIM_SHARED: return "shared";
    case NL_CLAIM_EXCLUSIVE: return "exclusive";
    case NL_CLAIM_READ_ONLY: return "read-only";
    default: return "?";
    }
}

void nl_claims_init(nl_claim_table_t *t)
{
    memset(t, 0, sizeof(*t));
}

int nl_claims_acquire(nl_claim_table_t *t, uint8_t plugin, uint8_t zone,
                      nl_claim_mode_t mode)
{
    if (plugin >= NL_MAX_PLUGINS || zone >= NL_NUM_ZONES ||
        mode == NL_CLAIM_NONE || mode > NL_CLAIM_READ_ONLY) {
        return NL_ERR_ARG;
    }
    if (zone == NL_META_ZONE) {
        NL_LOGW("zone", "plugin %u: zone 0 cannot be claimed", plugin);
        return NL_ERR_PERM;
    }
    for (uint8_t p = 0; p < NL_MAX_PLUGINS; p++) {
        uint8_t other = t->mode[p][zone];
        if (p == plugin || other == NL_CLAIM_NONE) {
            continue;
        }
        if (other == NL_CLAIM_EXCLUSIVE || mode == NL_CLAIM_EXCLUSIVE) {
            NL_LOGW("zone", "plugin %u: %s claim on zone %u conflicts with plugin %u (%s)",
                    plugin, nl_claim_mode_str((uint8_t)mode), zone, p, nl_claim_mode_str(other));
            return NL_ERR_CONFLICT;
        }
    }
    t->mode[plugin][zone] = (uint8_t)mode;
    return NL_OK;
}

int nl_claims_release(nl_claim_table_t *t, uint8_t plugin, uint8_t zone)
{
    if (plugin >= NL_MAX_PLUGINS || zone >= NL_NUM_ZONES) {
        return NL_ERR_ARG;
    }
    if (t->mode[plugin][zone] == NL_CLAIM_NONE) {
        return NL_ERR_NOT_FOUND;
    }
    t->mode[plugin][zone] = NL_CLAIM_NONE;
    return NL_OK;
}

void nl_claims_release_all(nl_claim_table_t *t, uint8_t plugin)
{
    if (plugin < NL_MAX_PLUGINS) {
        memset(t->mode[plugin], 0, sizeof(t->mode[plugin]));
    }
}

nl_claim_mode_t nl_claims_get(const nl_claim_table_t *t, uint8_t plugin,
                              uint8_t zone)
{
    if (plugin >= NL_MAX_PLUGINS || zone >= NL_NUM_ZONES) {
        return NL_CLAIM_NONE;
    }
    return (nl_claim_mode_t)t->mode[plugin][zone];
}

bool nl_claims_can_send(const nl_claim_table_t *t, uint8_t plugin, uint8_t zone)
{
    nl_claim_mode_t m = nl_claims_get(t, plugin, zone);
    return m == NL_CLAIM_SHARED || m == NL_CLAIM_EXCLUSIVE;
}

uint8_t nl_claims_zone_mask(const nl_claim_table_t *t)
{
    uint8_t mask = 0;
    for (uint8_t p = 0; p < NL_MAX_PLUGINS; p++) {
        for (uint8_t z = 0; z < NL_NUM_ZONES; z++) {
            if (t->mode[p][z] != NL_CLAIM_NONE) {
                mask = (uint8_t)(mask | (1u << z));
            }
        }
    }
    return mask;
}

void nl_remote_claims_init(nl_remote_claims_t *t, uint32_t expiry_us)
{
    memset(t, 0, sizeof(*t));
    t->expiry_us = expiry_us;
}

void nl_remote_claims_update(nl_remote_claims_t *t, uint8_t origin,
                             const nl_meta_claim_t *claims, size_t count,
                             nl_time_us_t now)
{
    if (origin >= NL_NUM_ORIGINS) {
        return;
    }
    nl_remote_claim_t *row = t->claim[origin];
    memset(row, 0, sizeof(t->claim[origin]));
    /* An empty snapshot is still a fresh announcement of "no claims". */
    for (uint8_t z = 0; z < NL_NUM_ZONES; z++) {
        row[z].seen = now;
    }
    for (size_t i = 0; i < count; i++) {
        uint8_t z = claims[i].zone;
        if (z == NL_META_ZONE || z >= NL_NUM_ZONES || claims[i].mode == NL_CLAIM_NONE ||
            claims[i].mode > NL_CLAIM_READ_ONLY) {
            continue;
        }
        nl_remote_claim_t *c = &row[z];
        if (c->mode == NL_CLAIM_NONE) {
            c->mode = claims[i].mode;
            c->plugin_type = claims[i].plugin_type;
            continue;
        }
        if (c->plugin_type != claims[i].plugin_type) {
            c->plugin_type = NL_PLUGIN_TYPE_ANY;
        }
        /* Prefer a mode that transmits: EXCLUSIVE > SHARED > READ_ONLY. */
        if (claims[i].mode == NL_CLAIM_EXCLUSIVE ||
            (claims[i].mode == NL_CLAIM_SHARED && c->mode == NL_CLAIM_READ_ONLY)) {
            c->mode = claims[i].mode;
        }
    }
}

const nl_remote_claim_t *nl_remote_claims_get(const nl_remote_claims_t *t,
                                              uint8_t origin, uint8_t zone,
                                              nl_time_us_t now)
{
    if (origin >= NL_NUM_ORIGINS || zone >= NL_NUM_ZONES) {
        return NULL;
    }
    const nl_remote_claim_t *c = &t->claim[origin][zone];
    if (c->mode == NL_CLAIM_NONE) {
        return NULL;
    }
    if (t->expiry_us != 0 && nl_time_diff(now, c->seen) > nl_time_span(t->expiry_us)) {
        return NULL;
    }
    return c;
}
