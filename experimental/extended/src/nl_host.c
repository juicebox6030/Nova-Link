/**
 * @file nl_host.c
 * @brief Host core: plugins, claims, dispatch, Zone 0, radio configuration.
 */
#include "nova_link/nl_host.h"
#include "nova_link/nl_log.h"
#include "nova_link/nl_segment.h"

#include <string.h>

/* Largest claim snapshot that fits one TLV record. */
#define NL_HOST_MAX_ANNOUNCED_CLAIMS (NL_META_MAX_VALUE / NL_META_CLAIM_WIRE_SIZE)

void nl_host_config_default(nl_host_config_t *cfg)
{
    memset(cfg, 0, sizeof(*cfg));
    cfg->origin_id = 0;
    memcpy(cfg->name, "nova-link", sizeof("nova-link"));
    cfg->announce_interval_us = 2000000;
    cfg->announce_jitter_us = 250000;
    cfg->announce_boot_spread_us = 100000;
    cfg->announce_ramp_steps = 3;
    cfg->meta_interval_us = 10000;
    cfg->meta_lead_us = 10000;
    cfg->mgmt_flag_hold_us = 50000;
    cfg->status_interval_us = 1000000;
    cfg->remote_claim_expiry_us = 10000000;
    cfg->peer_expiry_us = 10000000;
    cfg->tracker_stale_us = 500000;
    cfg->check_remote_types = true;
    cfg->max_pull_per_poll = NL_RADIO_RXQ_DEPTH;
}

int nl_host_init(nl_host_t *host, const nl_host_config_t *cfg,
                 const nl_link_ops_t *link)
{
    if (host == NULL || cfg == NULL || link == NULL || link->push == NULL ||
        link->pull == NULL || cfg->origin_id >= NL_NUM_ORIGINS ||
        cfg->max_pull_per_poll == 0) {
        return NL_ERR_ARG;
    }
    memset(host, 0, sizeof(*host));
    host->cfg = *cfg;
    host->cfg.name[sizeof(host->cfg.name) - 1] = '\0';
    host->link = *link;
    nl_claims_init(&host->claims);
    nl_remote_claims_init(&host->remote, cfg->remote_claim_expiry_us);
    nl_tracker_init(&host->tracker, cfg->tracker_stale_us);
    nl_meta_queue_init(&host->meta);
    nl_radio_params_default(&host->params);
    host->params.origin_id = cfg->origin_id;
    host->rf_dirty = true;
    host->announce_dirty = true;
    host->ramp_left = cfg->announce_ramp_steps < 16u ? cfg->announce_ramp_steps : 16u;
    uint32_t seed = cfg->rand_seed;
    if (seed == 0) {
        seed = cfg->origin_id;
        for (const char *c = host->cfg.name; *c != '\0'; c++) {
            seed = seed * 31u + (uint8_t)*c;
        }
    }
    host->rng = nl_rand_seed(seed);
    return NL_OK;
}

void nl_host_set_rf(nl_host_t *host, const nl_radio_params_t *params,
                    const nl_zone_plan_t *plan)
{
    if (params != NULL) {
        host->params = *params;
        host->params.origin_id = host->cfg.origin_id;
    }
    if (plan != NULL) {
        host->plan = *plan;
    }
    host->rf_dirty = true;
}

void nl_host_effective_plan(const nl_host_t *host, nl_zone_plan_t *out)
{
    *out = host->plan;
    uint8_t mask = nl_claims_zone_mask(&host->claims);
    for (uint8_t z = 1; z < NL_NUM_ZONES; z++) {
        if (mask & (1u << z)) {
            if (out->zone[z].priority == 0) {
                out->zone[z].priority = 1;
            }
        } else {
            out->zone[z].priority = 0;
        }
    }
}

static bool slot_valid(const nl_host_t *host, uint8_t slot)
{
    return slot < NL_MAX_PLUGINS && host->plugins[slot] != NULL;
}

static void claims_changed(nl_host_t *host)
{
    host->rf_dirty = true;
    host->announce_dirty = true;
}

int nl_host_register(nl_host_t *host, const nl_plugin_def_t *def)
{
    if (def == NULL) {
        return NL_ERR_ARG;
    }
    uint8_t slot;
    for (slot = 0; slot < NL_MAX_PLUGINS; slot++) {
        if (host->plugins[slot] == NULL) {
            break;
        }
    }
    if (slot == NL_MAX_PLUGINS) {
        NL_LOGE("host", "no free plugin slot for '%s'", def->name ? def->name : "?");
        return NL_ERR_FULL;
    }
    host->plugins[slot] = def;
    if (def->init != NULL) {
        NL_PLUGIN_ENTER(slot);
        int rc = def->init(host, slot, def->user);
        NL_PLUGIN_EXIT(slot);
        if (rc < 0) {
            NL_LOGE("host", "plugin '%s' init failed: %s", def->name ? def->name : "?",
                    nl_status_str(rc));
            nl_claims_release_all(&host->claims, slot);
            host->plugins[slot] = NULL;
            claims_changed(host);
            return rc;
        }
    }
    NL_LOGI("host", "plugin '%s' (type 0x%04X) in slot %u", def->name ? def->name : "?",
            def->type_id, slot);
    return slot;
}

int nl_host_unregister(nl_host_t *host, uint8_t slot)
{
    if (!slot_valid(host, slot)) {
        return NL_ERR_NOT_FOUND;
    }
    const nl_plugin_def_t *def = host->plugins[slot];
    if (def->deinit != NULL) {
        NL_PLUGIN_ENTER(slot);
        def->deinit(host, slot, def->user);
        NL_PLUGIN_EXIT(slot);
    }
    nl_claims_release_all(&host->claims, slot);
    host->plugins[slot] = NULL;
    claims_changed(host);
    return NL_OK;
}

int nl_host_find_plugin(const nl_host_t *host, const char *name)
{
    for (uint8_t s = 0; s < NL_MAX_PLUGINS; s++) {
        const nl_plugin_def_t *d = host->plugins[s];
        if (d != NULL && d->name != NULL && name != NULL && strcmp(d->name, name) == 0) {
            return s;
        }
    }
    return NL_ERR_NOT_FOUND;
}

int nl_host_claim(nl_host_t *host, uint8_t slot, uint8_t zone, nl_claim_mode_t mode)
{
    if (!slot_valid(host, slot)) {
        return NL_ERR_ARG;
    }
    int rc = nl_claims_acquire(&host->claims, slot, zone, mode);
    if (rc == NL_OK) {
        claims_changed(host);
    }
    return rc;
}

int nl_host_release(nl_host_t *host, uint8_t slot, uint8_t zone)
{
    if (!slot_valid(host, slot)) {
        return NL_ERR_ARG;
    }
    int rc = nl_claims_release(&host->claims, slot, zone);
    if (rc == NL_OK) {
        claims_changed(host);
    }
    return rc;
}

/* ---- Transmit ---------------------------------------------------------- */

static bool want_mgmt_flag(const nl_host_t *host)
{
    return nl_meta_queue_pending(&host->meta) ||
           nl_time_before(host->now, host->mgmt_flag_until);
}

/** Where push_fragment_in() expects a payload built in place. */
#define FRAG_PAYLOAD(buf) (&(buf)[NL_FRAGMENT_HEADER_SIZE])

/**
 * Encode one fragment into @p buf (NL_MAX_FRAGMENT bytes) and push it.
 * @p payload may be FRAG_PAYLOAD(buf), so callers can build the payload in
 * place instead of in a second stack buffer (nl_fragment_encode memmoves).
 * Claims must already be checked.
 */
static int push_fragment_in(nl_host_t *host, uint8_t *buf, uint8_t zone,
                            const uint8_t *payload, size_t len, uint8_t flags)
{
    if (want_mgmt_flag(host)) {
        flags |= NL_FLAG_MGMT_LISTEN;
    }
    nl_fragment_t f = {
        .origin_id = host->cfg.origin_id,
        .zone_id = zone,
        .flags = flags,
        .seq = host->tx_seq[zone],
        .payload = payload,
        .payload_len = (uint8_t)len,
    };
    int n = nl_fragment_encode(&f, buf, NL_MAX_FRAGMENT);
    if (n < 0) {
        return n;
    }
    int rc = host->link.push(host->link.ctx, buf, (size_t)n);
    if (rc < 0) {
        host->stats.tx_errors++;
        return rc;
    }
    host->tx_seq[zone]++;
    host->stats.tx_fragments++;
    return NL_OK;
}

/** Encode and push one fragment. Claims must already be checked. */
static int push_fragment(nl_host_t *host, uint8_t zone, const uint8_t *payload,
                         size_t len, uint8_t flags)
{
    uint8_t buf[NL_MAX_FRAGMENT];
    return push_fragment_in(host, buf, zone, payload, len, flags);
}

static int check_send(nl_host_t *host, uint8_t slot, uint8_t zone)
{
    if (!slot_valid(host, slot) || zone >= NL_NUM_ZONES) {
        return NL_ERR_ARG;
    }
    if (zone == NL_META_ZONE) {
        NL_LOGW("host", "plugin '%s': zone 0 is sent through the metadata API",
                host->plugins[slot]->name ? host->plugins[slot]->name : "?");
        host->stats.tx_denied++;
        return NL_ERR_PERM;
    }
    if (!nl_claims_can_send(&host->claims, slot, zone)) {
        NL_LOGW("host", "plugin '%s' may not send on zone %u (claim: %s)",
                host->plugins[slot]->name ? host->plugins[slot]->name : "?", zone,
                nl_claim_mode_str((uint8_t)nl_claims_get(&host->claims, slot, zone)));
        host->stats.tx_denied++;
        return NL_ERR_PERM;
    }
    return NL_OK;
}

int nl_host_send(nl_host_t *host, uint8_t slot, uint8_t zone, const uint8_t *payload,
                 size_t len, uint8_t flags)
{
    int rc = check_send(host, slot, zone);
    if (rc != NL_OK) {
        return rc;
    }
    if (len > NL_MAX_PAYLOAD || (len > 0 && payload == NULL)) {
        return NL_ERR_SIZE;
    }
    return push_fragment(host, zone, payload, len, (uint8_t)(flags & NL_FLAG_BURST));
}

int nl_host_send_segmented(nl_host_t *host, uint8_t slot, uint8_t zone,
                           const uint8_t *msg, size_t len)
{
    int rc = check_send(host, slot, zone);
    if (rc != NL_OK) {
        return rc;
    }
    int count = nl_seg_count(len);
    if (count < 0) {
        return count;
    }
    if (count > NL_RADIO_TXQ_DEPTH) {
        NL_LOGW("host", "segmented message of %u segments exceeds radio queue (%u)",
                (unsigned)count, (unsigned)NL_RADIO_TXQ_DEPTH);
        return NL_ERR_SIZE;
    }
    uint8_t buf[NL_MAX_FRAGMENT];
    for (int i = 0; i < count; i++) {
        int n = nl_seg_build(msg, len, (uint8_t)i, FRAG_PAYLOAD(buf), NL_MAX_PAYLOAD);
        if (n < 0) {
            return n;
        }
        uint8_t flags = (i + 1 < count) ? NL_FLAG_BURST : 0;
        rc = push_fragment_in(host, buf, zone, FRAG_PAYLOAD(buf), (size_t)n, flags);
        if (rc != NL_OK) {
            return rc;
        }
    }
    return NL_OK;
}

/* ---- Zone 0 ------------------------------------------------------------ */

int nl_host_meta_push(nl_host_t *host, uint8_t type, const uint8_t *value, size_t len)
{
    bool was_empty = !nl_meta_queue_pending(&host->meta);
    int rc = nl_meta_queue_push(&host->meta, type, value, len);
    if (rc == NL_OK && was_empty) {
        /* Give receivers a chance to see MGMT_LISTEN before zone 0 data. */
        nl_time_us_t ready = host->now + host->cfg.meta_lead_us;
        if (nl_time_before(host->next_meta, ready)) {
            host->next_meta = ready;
        }
    } else if (rc == NL_ERR_FULL) {
        NL_LOGW("host", "metadata queue full, dropped record type 0x%02X", type);
    }
    return rc;
}

int nl_host_meta_send_plugin(nl_host_t *host, uint8_t slot, const uint8_t *data,
                             size_t len)
{
    if (!slot_valid(host, slot) || (len > 0 && data == NULL)) {
        return NL_ERR_ARG;
    }
    if (len > NL_META_MAX_VALUE - 2u) {
        return NL_ERR_SIZE;
    }
    uint8_t v[NL_META_MAX_VALUE];
    nl_put_u16le(v, host->plugins[slot]->type_id);
    if (len > 0) {
        memcpy(&v[2], data, len);
    }
    return nl_host_meta_push(host, NL_META_PLUGIN_DATA, v, len + 2u);
}

int nl_host_meta_debug(nl_host_t *host, const char *text)
{
    if (text == NULL) {
        return NL_ERR_ARG;
    }
    size_t n = strlen(text);
    if (n > NL_META_MAX_VALUE) {
        n = NL_META_MAX_VALUE;
    }
    return nl_host_meta_push(host, NL_META_DEBUG_TEXT, (const uint8_t *)text, n);
}

void nl_host_announce_now(nl_host_t *host)
{
    host->announce_dirty = true;
}

/**
 * Announce again soon, for a device that does not know us yet, instead of
 * making it wait up to a full announce period; it listens on zone 0 for
 * mgmt_hold_us after transmitting there. Every device that heard it answers,
 * so the answers are spread out or they all collide. Terminates: the other
 * device knows us once our answer arrives.
 */
static void schedule_reply(nl_host_t *host, nl_time_us_t now)
{
    if (host->reply_pending) {
        return;
    }
    uint32_t window = host->cfg.announce_jitter_us;
    if (window > host->params.mgmt_hold_us / 2u) {
        window = host->params.mgmt_hold_us / 2u;
    }
    host->reply_pending = true;
    host->reply_at = now + nl_rand_upto(&host->rng, window);
}

/** Bit i set if origin i is a live peer. */
static uint8_t known_peers(const nl_host_t *host)
{
    uint8_t mask = 0;
    for (uint8_t o = 0; o < NL_NUM_ORIGINS; o++) {
        if (o != host->cfg.origin_id && nl_host_peer(host, o) != NULL) {
            mask |= (uint8_t)(1u << o);
        }
    }
    return mask;
}

static void queue_announcements(nl_host_t *host)
{
    uint8_t v[NL_META_MAX_VALUE];

    nl_meta_device_t dev;
    memset(&dev, 0, sizeof(dev));
    dev.proto_version = NL_LINK_PROTOCOL_VERSION;
    dev.fw_major = NL_VERSION_MAJOR;
    dev.fw_minor = NL_VERSION_MINOR;
    dev.fw_patch = NL_VERSION_PATCH;
    memcpy(dev.name, host->cfg.name, sizeof(dev.name));
    int n = nl_meta_encode_device(&dev, v, sizeof(v));
    if (n >= 0) {
        nl_meta_queue_remove_type(&host->meta, NL_META_DEVICE_ANNOUNCE);
        nl_host_meta_push(host, NL_META_DEVICE_ANNOUNCE, v, (size_t)n);
    }
    /* Right after the device record so both share a fragment. */
    v[0] = known_peers(host);
    nl_meta_queue_remove_type(&host->meta, NL_META_PEERS);
    nl_host_meta_push(host, NL_META_PEERS, v, 1);

    nl_meta_claim_t claims[NL_HOST_MAX_ANNOUNCED_CLAIMS];
    size_t count = 0;
    for (uint8_t s = 0; s < NL_MAX_PLUGINS; s++) {
        if (host->plugins[s] == NULL) {
            continue;
        }
        for (uint8_t z = 1; z < NL_NUM_ZONES; z++) {
            uint8_t mode = host->claims.mode[s][z];
            if (mode == NL_CLAIM_NONE) {
                continue;
            }
            if (count == NL_ARRAY_SIZE(claims)) {
                NL_LOGW("host", "claim announcement truncated to %u entries",
                        (unsigned)count);
                goto encode;
            }
            claims[count].zone = z;
            claims[count].mode = mode;
            claims[count].plugin_type = host->plugins[s]->type_id;
            count++;
        }
    }
encode:
    n = nl_meta_encode_claims(claims, count, v, sizeof(v));
    if (n >= 0) {
        nl_meta_queue_remove_type(&host->meta, NL_META_CLAIM_ANNOUNCE);
        nl_host_meta_push(host, NL_META_CLAIM_ANNOUNCE, v, (size_t)n);
    }
}

static void flush_meta(nl_host_t *host)
{
    if (!nl_meta_queue_pending(&host->meta) || nl_time_before(host->now, host->next_meta)) {
        return;
    }
    uint8_t buf[NL_MAX_FRAGMENT];
    size_t n = nl_meta_queue_pack(&host->meta, FRAG_PAYLOAD(buf), NL_MAX_PAYLOAD);
    if (n == 0) {
        return;
    }
    /* Keep flagging for a while so late listeners still find zone 0. */
    host->mgmt_flag_until = host->now + host->cfg.mgmt_flag_hold_us;
    if (push_fragment_in(host, buf, NL_META_ZONE, FRAG_PAYLOAD(buf), n, 0) == NL_OK) {
        host->stats.meta_fragments++;
    }
    host->next_meta = host->now + host->cfg.meta_interval_us;
}

/* ---- Receive ----------------------------------------------------------- */

static void handle_meta(nl_host_t *host, uint8_t origin, const uint8_t *payload,
                        size_t len, nl_time_us_t now)
{
    nl_meta_iter_t it;
    uint8_t type, vlen;
    const uint8_t *v;
    int rc;

    nl_meta_iter_init(&it, payload, len);
    while ((rc = nl_meta_iter_next(&it, &type, &v, &vlen)) == 1) {
        if (host->meta_hook != NULL) {
            host->meta_hook(host, origin, type, v, vlen, host->meta_hook_user);
        }
        switch (type) {
        case NL_META_DEVICE_ANNOUNCE: {
            nl_meta_device_t dev;
            if (nl_meta_decode_device(v, vlen, &dev) == NL_OK) {
                nl_host_peer_t *p = &host->peers[origin];
                if (!p->valid || strcmp(p->info.name, dev.name) != 0) {
                    NL_LOGI("host", "peer %u: '%s' v%u.%u.%u", origin, dev.name,
                            dev.fw_major, dev.fw_minor, dev.fw_patch);
                }
                if (!p->valid) {
                    schedule_reply(host, now);
                }
                p->valid = true;
                p->info = dev;
                p->last_seen = now;
            } else {
                host->stats.rx_invalid++;
            }
            break;
        }
        case NL_META_CLAIM_ANNOUNCE: {
            nl_meta_claim_t claims[NL_HOST_MAX_ANNOUNCED_CLAIMS];
            int n = nl_meta_decode_claims(v, vlen, claims, NL_ARRAY_SIZE(claims));
            if (n >= 0) {
                nl_remote_claims_update(&host->remote, origin, claims, (size_t)n, now);
            } else {
                host->stats.rx_invalid++;
            }
            break;
        }
        case NL_META_PLUGIN_DATA: {
            if (vlen < 2) {
                host->stats.rx_invalid++;
                break;
            }
            uint16_t ptype = nl_get_u16le(v);
            for (uint8_t s = 0; s < NL_MAX_PLUGINS; s++) {
                const nl_plugin_def_t *d = host->plugins[s];
                if (d != NULL && d->on_meta != NULL && d->type_id == ptype) {
                    NL_PLUGIN_ENTER(s);
                    d->on_meta(host, s, origin, v + 2, (size_t)vlen - 2u, d->user);
                    NL_PLUGIN_EXIT(s);
                }
            }
            break;
        }
        case NL_META_CONGESTION:
            if (vlen >= 3) {
                NL_LOGW("host", "peer %u reports congestion: zones 0x%02X, %u dropped",
                        origin, v[0], nl_get_u16le(&v[1]));
            }
            break;
        case NL_META_DEBUG_TEXT:
            NL_LOGI("host", "peer %u: %.*s", origin, (int)vlen, (const char *)v);
            break;
        case NL_META_PEERS:
            if (vlen < 1) {
                host->stats.rx_invalid++;
            } else if ((v[0] & (1u << host->cfg.origin_id)) == 0) {
                /* It missed our announcements (they reach some devices and
                 * not others); without this it waits a full period. */
                schedule_reply(host, now);
            }
            break;
        default:
            break; /* unknown / vendor types are only visible via the hook */
        }
    }
    if (rc < 0) {
        host->stats.rx_invalid++;
    }
}

/** True if the sender's announced plugin type rules out delivery to @p def. */
static bool type_mismatch(const nl_host_t *host, const nl_plugin_def_t *def,
                          uint8_t origin, uint8_t zone, nl_time_us_t now)
{
    if (!host->cfg.check_remote_types) {
        return false;
    }
    const nl_remote_claim_t *rc = nl_remote_claims_get(&host->remote, origin, zone, now);
    if (rc == NULL || rc->mode == NL_CLAIM_READ_ONLY ||
        rc->plugin_type == NL_PLUGIN_TYPE_ANY) {
        return false; /* unknown: give it the benefit of the doubt */
    }
    return rc->plugin_type != def->type_id;
}

void nl_host_handle_rx(nl_host_t *host, const uint8_t *data, size_t len,
                       nl_time_us_t now)
{
    nl_fragment_t f;
    if (nl_fragment_decode(data, len, &f) != NL_OK) {
        host->stats.rx_invalid++;
        return;
    }
    if (f.origin_id == host->cfg.origin_id) {
        return; /* our own echo; the radio normally filters these */
    }
    if (nl_tracker_check(&host->tracker, f.origin_id, f.zone_id, f.seq, now) !=
        NL_TRACK_NEW) {
        host->stats.rx_duplicates++;
        return;
    }
    host->stats.rx_fragments++;

    if (host->monitor != NULL) {
        host->monitor(host, &f, now, host->monitor_user);
    }

    if (f.zone_id == NL_META_ZONE) {
        handle_meta(host, f.origin_id, f.payload, f.payload_len, now);
        return;
    }

    bool delivered = false;
    bool rejected = false;
    for (uint8_t s = 0; s < NL_MAX_PLUGINS; s++) {
        const nl_plugin_def_t *d = host->plugins[s];
        if (d == NULL || host->claims.mode[s][f.zone_id] == NL_CLAIM_NONE) {
            continue;
        }
        if (type_mismatch(host, d, f.origin_id, f.zone_id, now)) {
            rejected = true;
            continue;
        }
        if (d->on_fragment != NULL) {
            NL_PLUGIN_ENTER(s);
            d->on_fragment(host, s, &f, d->user);
            NL_PLUGIN_EXIT(s);
        }
        delivered = true;
    }
    if (!delivered) {
        if (rejected) {
            host->stats.rx_type_mismatch++;
            NL_LOGD("host", "zone %u from origin %u: plugin type mismatch", f.zone_id,
                    f.origin_id);
        } else {
            host->stats.rx_undelivered++;
        }
    }
}

/* ---- Periodic work ----------------------------------------------------- */

static void push_rf_config(nl_host_t *host)
{
    if (!host->rf_dirty || host->link.configure == NULL) {
        host->rf_dirty = false;
        return;
    }
    nl_zone_plan_t plan;
    nl_host_effective_plan(host, &plan);
    int rc = host->link.configure(host->link.ctx, &host->params, &plan);
    if (rc < 0) {
        host->stats.link_errors++;
        NL_LOGW("host", "radio configure failed: %s", nl_status_str(rc));
        return; /* retry next poll */
    }
    host->rf_dirty = false;
}

static void pull_rx(nl_host_t *host, nl_time_us_t now)
{
    uint8_t buf[NL_MAX_FRAGMENT];
    for (uint8_t i = 0; i < host->cfg.max_pull_per_poll; i++) {
        if (host->link.rx_pending != NULL && !host->link.rx_pending(host->link.ctx)) {
            break;
        }
        int n = host->link.pull(host->link.ctx, buf, sizeof(buf));
        if (n < 0) {
            host->stats.link_errors++;
            break;
        }
        if (n == 0) {
            break;
        }
        nl_host_handle_rx(host, buf, (size_t)n, now);
    }
}

static void poll_status(nl_host_t *host)
{
    if (host->link.status == NULL || host->cfg.status_interval_us == 0 ||
        nl_time_before(host->now, host->next_status)) {
        return;
    }
    host->next_status = host->now + host->cfg.status_interval_us;
    nl_radio_status_t st;
    int rc = host->link.status(host->link.ctx, &st);
    if (rc < 0) {
        host->stats.link_errors++;
        return;
    }
    if (!(st.flags & NL_STATUS_F_CONFIGURED)) {
        if (!host->rf_dirty) {
            NL_LOGW("host", "radio lost its configuration (reset?), resending");
            host->stats.radio_resets++;
            host->rf_dirty = true;
        }
        /* A reset radio restarts its counters from zero; resync instead of
         * reporting the wrapped difference as ~4 billion drops. */
        host->last_tx_dropped = st.tx_dropped;
        host->last_rx_dropped = st.rx_dropped;
        return;
    }
    /* Counters that went backwards also mean a reset we did not catch. */
    if ((int32_t)(st.tx_dropped - host->last_tx_dropped) < 0) {
        host->last_tx_dropped = st.tx_dropped;
    }
    if ((int32_t)(st.rx_dropped - host->last_rx_dropped) < 0) {
        host->last_rx_dropped = st.rx_dropped;
    }
    if (st.tx_dropped != host->last_tx_dropped) {
        uint32_t delta = st.tx_dropped - host->last_tx_dropped;
        host->last_tx_dropped = st.tx_dropped;
        uint8_t mask = 0;
        for (uint8_t s = 0; s < NL_MAX_PLUGINS; s++) {
            for (uint8_t z = 1; z < NL_NUM_ZONES; z++) {
                if (host->plugins[s] != NULL && nl_claims_can_send(&host->claims, s, z)) {
                    mask = (uint8_t)(mask | (1u << z));
                }
            }
        }
        uint8_t v[3];
        v[0] = mask;
        nl_put_u16le(&v[1], (uint16_t)(delta > 0xFFFFu ? 0xFFFFu : delta));
        NL_LOGW("host", "radio dropped %u TX fragments", (unsigned)delta);
        nl_meta_queue_remove_type(&host->meta, NL_META_CONGESTION);
        nl_host_meta_push(host, NL_META_CONGESTION, v, sizeof(v));
    }
    if (st.rx_dropped != host->last_rx_dropped) {
        NL_LOGW("host", "radio RX queue overflowed (%u lost); poll faster",
                (unsigned)(st.rx_dropped - host->last_rx_dropped));
        host->last_rx_dropped = st.rx_dropped;
    }
}

void nl_host_poll(nl_host_t *host, nl_time_us_t now)
{
    host->now = now;
    if (!host->started) {
        host->started = true;
        host->next_announce = now;
        host->next_meta = now;
        host->next_status = now + host->cfg.status_interval_us;
        if (host->announce_dirty && host->cfg.announce_boot_spread_us != 0) {
            host->announce_dirty = false;
            host->reply_pending = true;
            host->reply_at = now + nl_rand_upto(&host->rng,
                                                host->cfg.announce_boot_spread_us);
            host->next_announce = host->reply_at;
        }
    }

    push_rf_config(host);
    pull_rx(host, now);

    bool periodic = host->cfg.announce_interval_us != 0 &&
                    !nl_time_before(now, host->next_announce);
    bool reply = host->reply_pending && !nl_time_before(now, host->reply_at);
    if (host->announce_dirty || periodic || reply) {
        queue_announcements(host);
        host->announce_dirty = false;
        host->reply_pending = false;
        if (host->cfg.announce_interval_us != 0) {
            uint32_t interval = host->cfg.announce_interval_us >> host->ramp_left;
            if (host->ramp_left > 0) {
                host->ramp_left--;
            }
            if (interval == 0) {
                interval = 1;
            }
            uint32_t jitter = host->cfg.announce_jitter_us;
            if (jitter >= interval) {
                jitter = interval / 2u;
            }
            host->next_announce = now + interval - nl_rand_upto(&host->rng, jitter);
        }
    }

    poll_status(host);

    for (uint8_t s = 0; s < NL_MAX_PLUGINS; s++) {
        const nl_plugin_def_t *d = host->plugins[s];
        if (d != NULL && d->on_tick != NULL) {
            NL_PLUGIN_ENTER(s);
            d->on_tick(host, s, now, d->user);
            NL_PLUGIN_EXIT(s);
        }
    }

    flush_meta(host);
}

void nl_host_set_monitor(nl_host_t *host, nl_rx_monitor_t fn, void *user)
{
    host->monitor = fn;
    host->monitor_user = user;
}

void nl_host_set_meta_hook(nl_host_t *host, nl_meta_hook_t fn, void *user)
{
    host->meta_hook = fn;
    host->meta_hook_user = user;
}

const nl_host_peer_t *nl_host_peer(const nl_host_t *host, uint8_t origin)
{
    if (origin >= NL_NUM_ORIGINS || !host->peers[origin].valid) {
        return NULL;
    }
    const nl_host_peer_t *p = &host->peers[origin];
    if (host->cfg.peer_expiry_us != 0 &&
        nl_time_diff(host->now, p->last_seen) > nl_time_span(host->cfg.peer_expiry_us)) {
        return NULL;
    }
    return p;
}
