/* SPDX-License-Identifier: GPL-3.0-only */
#include "nova/multiverse.h"
#include <string.h>

static bool valid_universe(uint16_t universe)
{
    return universe != 0u && universe <= 63999u;
}

static bool newer(uint16_t sequence, uint16_t previous)
{
    uint16_t distance = (uint16_t)(sequence - previous);
    return distance != 0u && distance < 32768u;
}

static bool same_frame(const nova_dmx_frame_t *a, const nova_dmx_frame_t *b)
{
    return a->slot_count == b->slot_count &&
        memcmp(a->slots, b->slots, a->slot_count) == 0;
}

nova_mv_result_t nova_mv_packet_validate(const nova_mv_packet_t *p)
{
    if (p == NULL) return NOVA_MV_INVALID_ARGUMENT;
    if ((p->kind != NOVA_MV_FULL && p->kind != NOVA_MV_DELTA) ||
        !valid_universe(p->universe) || p->slot_count > NOVA_DMX_MAX_SLOTS ||
        p->span_start > p->slot_count ||
        p->span_count > p->slot_count - p->span_start ||
        p->offset > p->span_count || p->count > p->span_count - p->offset ||
        (p->span_count != 0u && p->count == 0u) ||
        (p->span_count == 0u && (p->offset != 0u || p->count != 0u)) ||
        (p->kind == NOVA_MV_FULL && (p->span_start != 0u ||
         p->span_count != p->slot_count || p->base_sequence != 0u)) ||
        (p->kind == NOVA_MV_DELTA && !newer(p->sequence, p->base_sequence)))
        return NOVA_MV_BAD_PACKET;
    return NOVA_MV_OK;
}

nova_mv_result_t nova_mv_tx_init(nova_mv_tx_t *tx, const nova_mv_tx_config_t *config)
{
    if (tx == NULL || config == NULL || !valid_universe(config->universe) ||
        config->chunk_slots == 0u || config->chunk_slots > NOVA_DMX_MAX_SLOTS ||
        config->interval_us == 0u || config->full_interval_us < config->interval_us)
        return NOVA_MV_INVALID_ARGUMENT;
    memset(tx, 0, sizeof(*tx));
    tx->config = *config;
    tx->initialized = true;
    return NOVA_MV_OK;
}

nova_mv_result_t nova_mv_tx_submit(nova_mv_tx_t *tx, const nova_dmx_frame_t *frame)
{
    const nova_dmx_frame_t *owned;
    if (tx == NULL || !tx->initialized || frame == NULL ||
        frame->slot_count > NOVA_DMX_MAX_SLOTS) return NOVA_MV_INVALID_ARGUMENT;
    owned = tx->active ? &tx->frozen : &tx->baseline;
    if (tx->has_desired && !same_frame(&tx->desired, frame) &&
        ((!tx->active && !tx->has_baseline) || !same_frame(&tx->desired, owned)))
        ++tx->stats.coalesced;
    tx->desired.slot_count = frame->slot_count;
    memcpy(tx->desired.slots, frame->slots, frame->slot_count);
    memset(tx->desired.slots + frame->slot_count, 0,
           NOVA_DMX_MAX_SLOTS - frame->slot_count);
    tx->has_desired = true;
    return NOVA_MV_OK;
}

void nova_mv_tx_force_full(nova_mv_tx_t *tx)
{
    if (tx != NULL && tx->initialized) tx->force_full = true;
}

nova_mv_result_t nova_mv_tx_prepare(nova_mv_tx_t *tx, uint64_t now,
                                  nova_mv_packet_t *packet, uint64_t *token)
{
    nova_mv_packet_t *p;
    uint16_t start, end;
    if (tx == NULL || !tx->initialized || packet == NULL || token == NULL)
        return NOVA_MV_INVALID_ARGUMENT;
    if (now < tx->last_now) return NOVA_MV_INVALID_TIME;
    tx->last_now = now;
    if (!tx->has_desired) return NOVA_MV_IDLE;
    if (!tx->active && tx->has_baseline && !tx->force_full &&
        now - tx->last_sent < tx->config.interval_us) return NOVA_MV_IDLE;
    if (!tx->in_flight && tx->next_token == UINT64_MAX) return NOVA_MV_EXHAUSTED;
    p = &tx->pending;
    if (!tx->active) {
        memset(p, 0, sizeof(*p));
        tx->frozen = tx->desired;
        p->universe = tx->config.universe;
        p->session = tx->config.session;
        p->sequence = tx->has_baseline ? (uint16_t)(tx->sequence + 1u) : 0u;
        p->slot_count = tx->frozen.slot_count;
        if (!tx->has_baseline || tx->force_full ||
            tx->baseline.slot_count != p->slot_count ||
            now - tx->last_full >= tx->config.full_interval_us) {
            p->kind = NOVA_MV_FULL;
            p->span_count = p->slot_count;
        } else {
            p->kind = NOVA_MV_DELTA;
            p->base_sequence = tx->sequence;
            start = 0;
            while (start < p->slot_count && tx->frozen.slots[start] == tx->baseline.slots[start]) ++start;
            end = p->slot_count;
            while (end > start && tx->frozen.slots[end - 1u] == tx->baseline.slots[end - 1u]) --end;
            p->span_start = start;
            p->span_count = (uint16_t)(end - start);
        }
        tx->active = true;
        tx->force_full = false;
    }
    if (!tx->in_flight) {
        p->count = (uint16_t)(p->span_count - p->offset);
        if (p->count > tx->config.chunk_slots) p->count = tx->config.chunk_slots;
        memset(p->levels, 0, sizeof(p->levels));
        memcpy(p->levels, tx->frozen.slots + p->span_start + p->offset, p->count);
        tx->token = ++tx->next_token;
        tx->in_flight = true;
    }
    *packet = *p;
    *token = tx->token;
    return NOVA_MV_PACKET_READY;
}

nova_mv_result_t nova_mv_tx_complete(nova_mv_tx_t *tx, uint64_t token,
                                   bool success, uint64_t now)
{
    if (tx == NULL || !tx->initialized) return NOVA_MV_INVALID_ARGUMENT;
    if (now < tx->last_now) return NOVA_MV_INVALID_TIME;
    if (!tx->in_flight || token != tx->token) return NOVA_MV_INVALID_TOKEN;
    tx->last_now = now;
    tx->in_flight = false;
    if (!success) {
        ++tx->stats.retries;
        return NOVA_MV_OK;
    }
    ++tx->stats.packets;
    tx->pending.offset += tx->pending.count;
    if (tx->pending.offset < tx->pending.span_count) return NOVA_MV_OK;
    tx->baseline = tx->frozen;
    tx->sequence = tx->pending.sequence;
    tx->has_baseline = true;
    tx->active = false;
    tx->last_sent = now;
    if (tx->pending.kind == NOVA_MV_FULL) tx->last_full = now;
    ++tx->stats.updates;
    return NOVA_MV_OK;
}

nova_mv_result_t nova_mv_rx_init(nova_mv_rx_t *rx, const nova_mv_rx_config_t *config)
{
    if (rx == NULL || config == NULL || !valid_universe(config->universe) ||
        config->loss_timeout_us == 0u || config->assembly_timeout_us == 0u)
        return NOVA_MV_INVALID_ARGUMENT;
    memset(rx, 0, sizeof(*rx));
    rx->config = *config;
    rx->initialized = true;
    return NOVA_MV_OK;
}

nova_mv_result_t nova_mv_rx_bind(nova_mv_rx_t *rx, uint32_t session)
{
    if (rx == NULL || !rx->initialized) return NOVA_MV_INVALID_ARGUMENT;
    if (rx->active) ++rx->stats.abandoned;
    rx->config.session = session;
    rx->has_frame = rx->has_sequence = rx->synchronized = rx->active = false;
    memset(&rx->frame, 0, sizeof(rx->frame));
    rx->link = NOVA_MV_WAIT_FULL;
    return NOVA_MV_OK;
}

nova_mv_result_t nova_mv_rx_tick(nova_mv_rx_t *rx, uint64_t now)
{
    if (rx == NULL || !rx->initialized) return NOVA_MV_INVALID_ARGUMENT;
    if (now < rx->last_now) return NOVA_MV_INVALID_TIME;
    rx->last_now = now;
    if (rx->active && now - rx->assembly_started >= rx->config.assembly_timeout_us) {
        rx->active = false;
        ++rx->stats.abandoned;
        /* An incomplete delta never modifies the committed base. */
    }
    if (rx->has_frame && now - rx->last_frame >= rx->config.loss_timeout_us) {
        rx->has_frame = rx->synchronized = false;
        if (rx->active) ++rx->stats.abandoned;
        rx->active = false;
        rx->link = NOVA_MV_LOST;
        ++rx->stats.losses;
    }
    return NOVA_MV_OK;
}

static bool same_update(const nova_mv_packet_t *a, const nova_mv_packet_t *b)
{
    return a->kind == b->kind && a->base_sequence == b->base_sequence &&
        a->slot_count == b->slot_count && a->span_start == b->span_start &&
        a->span_count == b->span_count;
}

nova_mv_result_t nova_mv_rx_receive(nova_mv_rx_t *rx, const nova_mv_packet_t *p,
                                  nova_mv_integrity_t integrity, uint64_t now,
                                  nova_dmx_frame_t *completed)
{
    nova_mv_result_t result;
    uint16_t i, index;
    bool contributed = false;
    if (rx == NULL || !rx->initialized || p == NULL ||
        (integrity != NOVA_MV_INTEGRITY_OK && integrity != NOVA_MV_INTEGRITY_BAD &&
         integrity != NOVA_MV_INTEGRITY_UNKNOWN)) return NOVA_MV_INVALID_ARGUMENT;
    result = nova_mv_rx_tick(rx, now);
    if (result != NOVA_MV_OK) return result;
    if (integrity == NOVA_MV_INTEGRITY_BAD) {
        ++rx->stats.bad;
        return NOVA_MV_BAD_PACKET;
    }
    if (integrity == NOVA_MV_INTEGRITY_UNKNOWN) {
        ++rx->stats.unverified;
        return NOVA_MV_UNVERIFIED;
    }
    if (nova_mv_packet_validate(p) != NOVA_MV_OK) {
        ++rx->stats.bad;
        return NOVA_MV_BAD_PACKET;
    }
    if (p->universe != rx->config.universe || p->session != rx->config.session) {
        ++rx->stats.filtered;
        return NOVA_MV_FILTERED;
    }
    if (rx->has_sequence) {
        if (p->sequence == rx->sequence) {
            ++rx->stats.duplicates;
            return NOVA_MV_DUPLICATE;
        }
        if (!newer(p->sequence, rx->sequence)) {
            ++rx->stats.stale;
            return NOVA_MV_STALE;
        }
    }
    if (rx->active && p->sequence != rx->header.sequence &&
        !newer(p->sequence, rx->header.sequence)) {
        ++rx->stats.stale;
        return NOVA_MV_STALE;
    }
    if (rx->active && p->sequence == rx->header.sequence && !same_update(p, &rx->header)) {
        ++rx->stats.bad;
        return NOVA_MV_BAD_PACKET;
    }
    if (p->kind == NOVA_MV_DELTA && (!rx->has_frame || !rx->synchronized ||
        p->base_sequence != rx->sequence || p->slot_count != rx->frame.slot_count)) {
        if (rx->active) ++rx->stats.abandoned;
        rx->active = false;
        rx->synchronized = false;
        if (rx->has_frame) rx->link = NOVA_MV_RECOVERING;
        ++rx->stats.missing_base;
        return NOVA_MV_NEED_FULL;
    }
    if (!rx->active || p->sequence != rx->header.sequence) {
        if (rx->active) ++rx->stats.abandoned;
        rx->header = *p;
        if (p->kind == NOVA_MV_FULL) memset(&rx->assembling, 0, sizeof(rx->assembling));
        else rx->assembling = rx->frame;
        rx->assembling.slot_count = p->slot_count;
        memset(rx->covered, 0, sizeof(rx->covered));
        rx->received = 0;
        rx->assembly_started = now;
        rx->active = true;
    }
    /* Preflight ALL overlaps so a conflicting chunk cannot partially mutate state. */
    for (i = 0; i < p->count; ++i) {
        index = (uint16_t)(p->offset + i);
        if (rx->covered[index] != 0u &&
            rx->assembling.slots[p->span_start + index] != p->levels[i]) {
            ++rx->stats.bad;
            return NOVA_MV_BAD_PACKET;
        }
    }
    for (i = 0; i < p->count; ++i) {
        index = (uint16_t)(p->offset + i);
        if (rx->covered[index] == 0u) {
            rx->assembling.slots[p->span_start + index] = p->levels[i];
            rx->covered[index] = 1;
            ++rx->received;
            contributed = true;
        }
    }
    if (rx->received == p->span_count) {
        rx->frame = rx->assembling;
        rx->sequence = p->sequence;
        rx->last_frame = now;
        rx->has_frame = rx->has_sequence = rx->synchronized = true;
        rx->active = false;
        rx->link = NOVA_MV_LIVE;
        ++rx->stats.frames;
        ++rx->stats.packets;
        if (completed != NULL) *completed = rx->frame;
        return NOVA_MV_FRAME_READY;
    }
    if (!contributed) {
        ++rx->stats.duplicates;
        return NOVA_MV_DUPLICATE;
    }
    ++rx->stats.packets;
    return NOVA_MV_OK;
}

nova_mv_result_t nova_mv_rx_get(nova_mv_rx_t *rx, uint64_t now, nova_dmx_frame_t *frame)
{
    nova_mv_result_t result;
    if (frame == NULL) return NOVA_MV_INVALID_ARGUMENT;
    result = nova_mv_rx_tick(rx, now);
    if (result != NOVA_MV_OK) return result;
    if (!rx->has_frame) return NOVA_MV_NEED_FULL;
    *frame = rx->frame;
    return NOVA_MV_FRAME_READY;
}

const char *nova_mv_result_name(nova_mv_result_t result)
{
    switch (result) {
    case NOVA_MV_OK: return "ok";
    case NOVA_MV_PACKET_READY: return "packet_ready";
    case NOVA_MV_FRAME_READY: return "frame_ready";
    case NOVA_MV_IDLE: return "idle";
    case NOVA_MV_DUPLICATE: return "duplicate";
    case NOVA_MV_STALE: return "stale";
    case NOVA_MV_FILTERED: return "filtered";
    case NOVA_MV_NEED_FULL: return "need_full";
    case NOVA_MV_BAD_PACKET: return "bad_packet";
    case NOVA_MV_UNVERIFIED: return "unverified";
    case NOVA_MV_INVALID_ARGUMENT: return "invalid_argument";
    case NOVA_MV_INVALID_TIME: return "invalid_time";
    case NOVA_MV_INVALID_TOKEN: return "invalid_token";
    case NOVA_MV_EXHAUSTED: return "exhausted";
    case NOVA_MV_BUFFER_TOO_SMALL: return "buffer_too_small";
    default: return "unknown";
    }
}

const char *nova_mv_link_name(nova_mv_link_t link)
{
    switch (link) {
    case NOVA_MV_WAIT_FULL: return "wait_full";
    case NOVA_MV_LIVE: return "live";
    case NOVA_MV_RECOVERING: return "recovering";
    case NOVA_MV_LOST: return "lost";
    default: return "unknown";
    }
}
