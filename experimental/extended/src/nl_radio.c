/**
 * @file nl_radio.c
 * @brief Radio co-processor core: scheduler, TX/RX queues, link commands.
 */
#include "nova_link/nl_radio.h"
#include "nova_link/nl_fragment.h"
#include "nova_link/nl_log.h"

#include <string.h>

#define NL_RADIO_MAX_PRIORITY 8u

/* ---- Helpers ----------------------------------------------------------- */

static uint32_t band_freq(const nl_radio_t *r, uint8_t zone, uint8_t band)
{
    const nl_zone_rf_t *z = &r->plan.zone[zone];
    return band == NL_BAND_2G4 ? z->ghz24_hz : z->subghz_hz;
}

/** True if the zone has a frequency usable in the configured band mode. */
static bool zone_usable(const nl_radio_t *r, uint8_t zone)
{
    switch (r->params.band) {
    case NL_BAND_SUBGHZ: return r->plan.zone[zone].subghz_hz != 0;
    case NL_BAND_2G4: return r->plan.zone[zone].ghz24_hz != 0;
    default:
        return r->plan.zone[zone].subghz_hz != 0 || r->plan.zone[zone].ghz24_hz != 0;
    }
}

static bool mgmt_active(nl_radio_t *r, nl_time_us_t now)
{
    if (r->mgmt_heard && !nl_time_before(now, r->mgmt_until)) {
        r->mgmt_heard = false;
    }
    return r->mgmt_heard;
}

static uint8_t zone_weight(nl_radio_t *r, uint8_t zone, nl_time_us_t now)
{
    if (!zone_usable(r, zone)) {
        return 0;
    }
    uint8_t w = r->plan.zone[zone].priority;
    if (w > NL_RADIO_MAX_PRIORITY) {
        w = NL_RADIO_MAX_PRIORITY;
    }
    if (w == 0) {
        bool tx_wants_slot =
            r->txq_len[zone] > 0 &&
            (zone == NL_META_ZONE || r->params.tx_policy == NL_TX_IN_SLOT);
        bool mgmt = zone == NL_META_ZONE && mgmt_active(r, now);
        if (tx_wants_slot || mgmt) {
            w = 1;
        }
    }
    return w;
}

/**
 * Pick the zone for the next listen slot (smooth weighted round-robin).
 * @return Zone, or -1 if nothing can be scheduled.
 */
static int pick_slot_zone(nl_radio_t *r, nl_time_us_t now)
{
    uint8_t w[NL_NUM_ZONES];
    int total = 0;
    for (uint8_t z = 0; z < NL_NUM_ZONES; z++) {
        w[z] = zone_weight(r, z, now);
        total += w[z];
    }
    if (total == 0) {
        /* Nothing enabled: park on zone 0 so discovery still works. */
        return zone_usable(r, NL_META_ZONE) ? NL_META_ZONE : -1;
    }
    int best = -1;
    for (uint8_t z = 0; z < NL_NUM_ZONES; z++) {
        if (w[z] == 0) {
            r->swrr_cw[z] = 0;
            continue;
        }
        r->swrr_cw[z] = (int16_t)(r->swrr_cw[z] + w[z]);
        /* Ties go to a zone other than the previous slot's, so a zone that
         * just (re)joined, e.g. zone 0 right after a discovery visit, does
         * not get two slots in a row. */
        if (best < 0 || r->swrr_cw[z] > r->swrr_cw[best] ||
            (r->swrr_cw[z] == r->swrr_cw[best] && best == r->cur_zone)) {
            best = z;
        }
    }
    r->swrr_cw[best] = (int16_t)(r->swrr_cw[best] - total);
    return best;
}

static void start_slot(nl_radio_t *r, nl_time_us_t now)
{
    int z;
    uint32_t disc = r->params.discovery_interval_us;
    int32_t since = nl_time_diff(now, r->last_meta_slot);
    /* Negative means the stamp is over 2^31 us old: overdue as well. */
    if (disc != 0 && zone_usable(r, NL_META_ZONE) &&
        (since >= nl_time_span(disc) || since < 0)) {
        z = NL_META_ZONE; /* discovery visit; leaves the SWRR state alone */
    } else {
        z = pick_slot_zone(r, now);
    }
    if (z < 0) {
        r->slot_active = false;
        return;
    }
    r->cur_zone = (uint8_t)z;
    r->slot_active = true;
    if (z == NL_META_ZONE) {
        r->last_meta_slot = now;
    }
    r->slot_end = now + r->params.dwell_us;

    if (r->params.band == NL_BAND_DUAL) {
        uint8_t bit = (uint8_t)(1u << z);
        bool want_24 = (r->rx_band_toggle & bit) != 0;
        r->rx_band_toggle ^= bit;
        uint8_t band = want_24 ? NL_BAND_2G4 : NL_BAND_SUBGHZ;
        if (band_freq(r, (uint8_t)z, band) == 0) {
            band = want_24 ? NL_BAND_SUBGHZ : NL_BAND_2G4;
        }
        r->cur_band = band;
    } else {
        r->cur_band = r->params.band;
    }
}

/* ---- TX queue ---------------------------------------------------------- */

static void txq_remove(nl_radio_t *r, uint8_t zone, uint8_t idx)
{
    uint8_t n = r->txq_len[zone];
    if (idx + 1u < n) {
        memmove(&r->txq[zone][idx], &r->txq[zone][idx + 1],
                (size_t)(n - idx - 1u) * sizeof(r->txq[zone][0]));
    }
    r->txq_len[zone] = (uint8_t)(n - 1u);
}

int nl_radio_queue_tx(nl_radio_t *r, const uint8_t *frag, size_t len,
                      nl_time_us_t now)
{
    if (frag == NULL || len < NL_FRAGMENT_HEADER_SIZE || len > NL_MAX_FRAGMENT) {
        return NL_ERR_SIZE;
    }
    uint8_t zone = nl_fragment_zone(frag[0]);
    if (r->undo_zone == zone) {
        r->undo_valid = false; /* indices may shift */
    }
    if (r->txq_len[zone] >= NL_RADIO_TXQ_DEPTH) {
        txq_remove(r, zone, 0); /* evict the oldest: newest data wins */
        r->stats.tx_dropped++;
    }
    nl_radio_txq_entry_t *e = &r->txq[zone][r->txq_len[zone]++];
    memcpy(e->data, frag, len);
    /* The radio owns the originID so its own-echo filter always matches. */
    e->data[0] = nl_fragment_make_header(r->params.origin_id, zone,
                                         nl_fragment_flags(frag[0]));
    e->len = (uint8_t)len;
    e->sends = 0;
    uint8_t repeats = r->params.tx_repeats;
    if (zone == NL_META_ZONE && r->params.mgmt_repeats != 0) {
        repeats = r->params.mgmt_repeats;
    }
    e->repeats_left = repeats > 0 ? repeats : 1;
    e->second_band = 0;
    e->defers = 0;
    e->next_due = now;
    return NL_OK;
}

uint8_t nl_radio_tx_pending(const nl_radio_t *r)
{
    unsigned n = 0;
    for (uint8_t z = 0; z < NL_NUM_ZONES; z++) {
        n += r->txq_len[z];
    }
    return (uint8_t)(n > 255u ? 255u : n);
}

/**
 * Choose the due entry of @p zone to send next: an unfinished dual-band
 * pair first, then the fewest sends, ties to the oldest.
 * Tracks the earliest future due time in @p earliest.
 * @return Entry index, or -1 if nothing is due.
 */
static int pick_tx_entry(const nl_radio_t *r, uint8_t zone, nl_time_us_t now,
                         nl_time_us_t *earliest, bool *have_earliest)
{
    if (r->txq_len[zone] == 0 || !zone_usable(r, zone)) {
        return -1;
    }
    int best = -1;
    for (uint8_t i = 0; i < r->txq_len[zone]; i++) {
        const nl_radio_txq_entry_t *e = &r->txq[zone][i];
        if (e->second_band) {
            return i;
        }
        if (nl_time_before(now, e->next_due)) {
            if (!*have_earliest || nl_time_before(e->next_due, *earliest)) {
                *earliest = e->next_due;
                *have_earliest = true;
            }
            continue;
        }
        if (best < 0 || e->sends < r->txq[zone][best].sends) {
            best = i;
        }
    }
    return best;
}

static void emit_tx(nl_radio_t *r, uint8_t zone, uint8_t idx, nl_time_us_t now,
                    nl_radio_action_t *act)
{
    nl_radio_txq_entry_t *e = &r->txq[zone][idx];
    bool complete = true;
    uint8_t band;

    r->undo_valid = true;
    r->undo_removed = false;
    r->undo_zone = zone;
    r->undo_idx = idx;
    r->undo_entry = *e;
    act->cca = r->params.cca_backoff_us != 0 && e->defers < NL_RADIO_CCA_MAX_DEFERS;
    e->defers = 0;

    if (r->params.band == NL_BAND_DUAL) {
        bool has_sub = r->plan.zone[zone].subghz_hz != 0;
        bool has_24 = r->plan.zone[zone].ghz24_hz != 0;
        if (e->second_band) {
            band = NL_BAND_2G4;
            e->second_band = 0;
        } else if (has_sub && has_24) {
            band = NL_BAND_SUBGHZ;
            e->second_band = 1;
            complete = false;
        } else {
            band = has_sub ? NL_BAND_SUBGHZ : NL_BAND_2G4;
        }
    } else {
        band = r->params.band;
    }

    memcpy(r->tx_scratch, e->data, e->len);
    act->type = NL_ACT_TX;
    act->zone = zone;
    act->band = band;
    act->freq_hz = band_freq(r, zone, band);
    act->data = r->tx_scratch;
    act->len = e->len;
    act->until = now;
    r->stats.tx_sent++;
    if (zone == NL_META_ZONE) {
        /* Management is conversational: listen for replies after speaking. */
        r->mgmt_heard = true;
        r->mgmt_until = now + r->params.mgmt_hold_us;
    }

    if (complete) {
        e->sends++;
        e->next_due = now + r->params.repeat_interval_us +
                      nl_rand_upto(&r->rng, r->params.repeat_jitter_us);
        if (--e->repeats_left == 0) {
            txq_remove(r, zone, idx);
            r->undo_removed = true;
        }
    }
}

/**
 * Emit a TX action if policy allows one now.
 * @return true if @p act was filled.
 */
/*
 * With listen before talk, devices that waited for the same packet to end
 * would all find the channel clear at once. Each holds its next TX for its
 * own random 0..cca_backoff_us after any packet it hears.
 */
static bool tx_held(const nl_radio_t *r, nl_time_us_t now, nl_time_us_t *earliest,
                    bool *have_earliest)
{
    if (!r->rx_hold || !nl_time_before(now, r->rx_hold_until)) {
        return false;
    }
    *earliest = r->rx_hold_until;
    *have_earliest = true;
    return true;
}

static bool try_tx(nl_radio_t *r, nl_time_us_t now, nl_radio_action_t *act,
                   nl_time_us_t *earliest, bool *have_earliest)
{
    if (r->params.tx_policy == NL_TX_IN_SLOT) {
        if (!r->slot_active) {
            return false;
        }
        int i = pick_tx_entry(r, r->cur_zone, now, earliest, have_earliest);
        if (i < 0 || tx_held(r, now, earliest, have_earliest)) {
            return false;
        }
        emit_tx(r, r->cur_zone, (uint8_t)i, now, act);
        return true;
    }

    /* Immediate: rotate fairly over zones 1..7, zone 0 last. */
    int found_zone = -1, found_idx = -1;
    for (uint8_t k = 0; k < NL_NUM_ZONES - 1u; k++) {
        uint8_t z = (uint8_t)(1u + (r->tx_rr + k) % (NL_NUM_ZONES - 1u));
        int i = pick_tx_entry(r, z, now, earliest, have_earliest);
        if (i >= 0 && found_zone < 0) {
            found_zone = z;
            found_idx = i;
        }
    }
    if (found_zone >= 0) {
        r->tx_rr = (uint8_t)((unsigned)found_zone % (NL_NUM_ZONES - 1u)); /* next zone */
    } else {
        found_idx = pick_tx_entry(r, NL_META_ZONE, now, earliest, have_earliest);
        if (found_idx >= 0) {
            found_zone = NL_META_ZONE;
        }
    }
    if (found_zone < 0 || tx_held(r, now, earliest, have_earliest)) {
        return false;
    }
    emit_tx(r, (uint8_t)found_zone, (uint8_t)found_idx, now, act);
    return true;
}

/* ---- Public API -------------------------------------------------------- */

void nl_radio_init(nl_radio_t *r)
{
    memset(r, 0, sizeof(*r));
    nl_radio_params_default(&r->params);
    nl_tracker_init(&r->tracker, r->params.tracker_stale_us);
    r->fw.proto_version = NL_LINK_PROTOCOL_VERSION;
    r->fw.fw_major = NL_VERSION_MAJOR;
    r->fw.fw_minor = NL_VERSION_MINOR;
    r->fw.fw_patch = NL_VERSION_PATCH;
    r->rng = nl_rand_seed(r->params.origin_id);
}

void nl_radio_seed(nl_radio_t *r, uint32_t entropy)
{
    r->rng = nl_rand_seed(r->rng ^ entropy);
}

static void apply_params(nl_radio_t *r, const nl_radio_params_t *p)
{
    bool origin_changed = p->origin_id != r->params.origin_id;
    r->params = *p;
    r->tracker.stale_us = p->tracker_stale_us;
    if (origin_changed) {
        r->rng = nl_rand_seed(r->rng ^ ((uint32_t)p->origin_id << 24));
        /* Re-stamp queued fragments with the new originID. */
        for (uint8_t z = 0; z < NL_NUM_ZONES; z++) {
            for (uint8_t i = 0; i < r->txq_len[z]; i++) {
                uint8_t *h = &r->txq[z][i].data[0];
                *h = nl_fragment_make_header(p->origin_id, z, nl_fragment_flags(*h));
            }
        }
    }
    r->config_flags |= NL_RADIO_CFG_PARAMS;
}

static void apply_plan(nl_radio_t *r, const nl_zone_plan_t *plan)
{
    r->plan = *plan;
    memset(r->swrr_cw, 0, sizeof(r->swrr_cw));
    r->slot_active = false; /* re-pick on the next action */
    r->last_meta_slot = 0;
    r->config_flags |= NL_RADIO_CFG_PLAN;
}

void nl_radio_configure(nl_radio_t *r, const nl_radio_params_t *params,
                        const nl_zone_plan_t *plan)
{
    if (params != NULL) {
        apply_params(r, params);
    }
    if (plan != NULL) {
        apply_plan(r, plan);
    }
}

void nl_radio_next_action(nl_radio_t *r, nl_time_us_t now, nl_radio_action_t *act)
{
    memset(act, 0, sizeof(*act));
    r->undo_valid = false;

    if (!(r->config_flags & NL_RADIO_CFG_PLAN)) {
        act->type = NL_ACT_IDLE;
        act->until = now + r->params.dwell_us;
        return;
    }

    if (!r->slot_active || !nl_time_before(now, r->slot_end)) {
        start_slot(r, now);
    }

    nl_time_us_t earliest = 0;
    bool have_earliest = false;
    if (try_tx(r, now, act, &earliest, &have_earliest)) {
        return;
    }

    nl_time_us_t until = r->slot_active ? r->slot_end : now + r->params.dwell_us;
    if (have_earliest && nl_time_before(earliest, until)) {
        until = earliest;
    }
    if (!r->slot_active) {
        act->type = NL_ACT_IDLE;
        act->until = until;
        return;
    }
    act->type = NL_ACT_RX;
    act->zone = r->cur_zone;
    act->band = r->cur_band;
    act->freq_hz = band_freq(r, r->cur_zone, r->cur_band);
    act->until = until;
}

int nl_radio_tx_busy(nl_radio_t *r, nl_time_us_t now)
{
    if (!r->undo_valid) {
        return NL_ERR_EMPTY;
    }
    r->undo_valid = false;
    uint8_t zone = r->undo_zone;
    nl_radio_txq_entry_t e = r->undo_entry;
    e.defers++;
    e.next_due = now + 1u + nl_rand_upto(&r->rng, r->params.cca_backoff_us);
    if (r->undo_removed) {
        uint8_t n = r->txq_len[zone];
        uint8_t idx = r->undo_idx <= n ? r->undo_idx : n;
        if (n >= NL_RADIO_TXQ_DEPTH) {
            r->stats.tx_dropped++; /* cannot happen without an interleaved push */
        } else {
            memmove(&r->txq[zone][idx + 1], &r->txq[zone][idx],
                    (size_t)(n - idx) * sizeof(r->txq[zone][0]));
            r->txq[zone][idx] = e;
            r->txq_len[zone] = (uint8_t)(n + 1u);
        }
    } else {
        r->txq[zone][r->undo_idx] = e;
    }
    r->stats.tx_sent--;
    r->cca_busy++;
    return NL_OK;
}

static void rxq_push(nl_radio_t *r, const uint8_t *data, size_t len)
{
    if (r->rxq_count >= NL_RADIO_RXQ_DEPTH) {
        /* Drop the oldest so the host always sees the newest data. */
        r->rxq_head = (uint8_t)((r->rxq_head + 1u) % NL_RADIO_RXQ_DEPTH);
        r->rxq_count--;
        r->stats.rx_dropped++;
    }
    uint8_t slot = (uint8_t)((r->rxq_head + r->rxq_count) % NL_RADIO_RXQ_DEPTH);
    memcpy(r->rxq[slot], data, len);
    r->rxq_lens[slot] = (uint8_t)len;
    r->rxq_count++;
}

void nl_radio_rx_packet(nl_radio_t *r, const uint8_t *data, size_t len,
                        nl_time_us_t now)
{
    if (data == NULL || len < NL_FRAGMENT_HEADER_SIZE || len > NL_MAX_FRAGMENT) {
        r->stats.rx_ignored++;
        return;
    }
    uint8_t origin = nl_fragment_origin(data[0]);
    uint8_t zone = nl_fragment_zone(data[0]);
    uint8_t flags = nl_fragment_flags(data[0]);

    if (origin == r->params.origin_id) {
        r->stats.rx_ignored++; /* our own transmission or an ID clash */
        return;
    }
    if (r->params.cca_backoff_us != 0) {
        r->rx_hold = true;
        r->rx_hold_until = now + nl_rand_upto(&r->rng, r->params.cca_backoff_us);
    }
    if (zone != NL_META_ZONE && r->plan.zone[zone].priority == 0) {
        r->stats.rx_ignored++; /* zone shares a frequency but is not ours */
        return;
    }

    if (flags & NL_FLAG_MGMT_LISTEN) {
        r->mgmt_heard = true;
        r->mgmt_until = now + r->params.mgmt_hold_us;
    }
    if ((flags & NL_FLAG_BURST) && r->slot_active && zone == r->cur_zone) {
        nl_time_us_t ext = now + r->params.burst_extend_us;
        if (nl_time_before(r->slot_end, ext)) {
            r->slot_end = ext;
        }
    }

    if (nl_tracker_check(&r->tracker, origin, zone, data[1], now) != NL_TRACK_NEW) {
        r->stats.rx_dup++;
        return;
    }
    r->stats.rx_ok++;
    rxq_push(r, data, len);
}

void nl_radio_get_status(const nl_radio_t *r, nl_radio_status_t *out)
{
    *out = r->stats;
    out->proto_version = NL_LINK_PROTOCOL_VERSION;
    out->flags = 0;
    if (r->rxq_count > 0) {
        out->flags |= NL_STATUS_F_RX_PENDING;
    }
    if ((r->config_flags & (NL_RADIO_CFG_PARAMS | NL_RADIO_CFG_PLAN)) ==
        (NL_RADIO_CFG_PARAMS | NL_RADIO_CFG_PLAN)) {
        out->flags |= NL_STATUS_F_CONFIGURED;
    }
    out->rx_queue_len = r->rxq_count;
    out->tx_queue_len = nl_radio_tx_pending(r);
}

static void set_outbox(nl_radio_t *r, uint8_t cmd, const uint8_t *data, size_t len)
{
    int n = nl_link_encode(cmd, data, len, r->outbox, sizeof(r->outbox));
    r->outbox_len = n > 0 ? (uint8_t)n : 0;
}

static void handle_frame(nl_radio_t *r, const nl_link_frame_t *f, nl_time_us_t now)
{
    uint8_t buf[NL_LINK_MAX_DATA];
    int n;

    switch (f->cmd) {
    case NL_CMD_PING:
        n = nl_link_pong_encode(&r->fw, buf, sizeof(buf));
        set_outbox(r, NL_RSP_PONG, buf, (size_t)n);
        break;

    case NL_CMD_PULL:
        if (r->rxq_count == 0) {
            set_outbox(r, NL_RSP_FRAGMENT, NULL, 0);
        } else {
            uint8_t h = r->rxq_head;
            set_outbox(r, NL_RSP_FRAGMENT, r->rxq[h], r->rxq_lens[h]);
            r->rxq_head = (uint8_t)((h + 1u) % NL_RADIO_RXQ_DEPTH);
            r->rxq_count--;
        }
        break;

    case NL_CMD_PUSH:
        if (nl_radio_queue_tx(r, f->data, f->len, now) != NL_OK) {
            NL_LOGW("radio", "PUSH with bad fragment length %u", f->len);
        }
        break;

    case NL_CMD_STATUS: {
        nl_radio_status_t st;
        nl_radio_get_status(r, &st);
        n = nl_radio_status_encode(&st, buf, sizeof(buf));
        set_outbox(r, NL_RSP_STATUS, buf, (size_t)n);
        break;
    }

    case NL_CMD_ZONE_CONFIG: {
        nl_zone_plan_t plan;
        if (nl_zone_plan_decode(f->data, f->len, &plan) == NL_OK) {
            apply_plan(r, &plan);
        } else {
            NL_LOGW("radio", "rejected ZONE_CONFIG (len %u)", f->len);
        }
        break;
    }

    case NL_CMD_RADIO_CONFIG: {
        nl_radio_params_t p;
        if (nl_radio_params_decode(f->data, f->len, &p) == NL_OK) {
            apply_params(r, &p);
        } else {
            NL_LOGW("radio", "rejected RADIO_CONFIG (len %u)", f->len);
        }
        break;
    }

    default:
        NL_LOGW("radio", "unknown link command 0x%02X", f->cmd);
        break;
    }
}

void nl_radio_spi_complete(nl_radio_t *r, const uint8_t *rx, size_t len,
                           nl_time_us_t now)
{
    /* Whatever was in the outbox has just been clocked out. */
    r->outbox_len = 0;

    while (len > 0) {
        nl_link_frame_t f;
        size_t used = 0;
        int rc = nl_link_decode(rx, len, &f, &used);
        if (rc == NL_OK) {
            handle_frame(r, &f, now);
        } else if (rc == NL_ERR_CRC) {
            NL_LOGW("radio", "link frame CRC error");
        }
        if (rc != NL_OK || used == 0 || used > len) {
            break;
        }
        rx += used;
        len -= used;
    }
}
