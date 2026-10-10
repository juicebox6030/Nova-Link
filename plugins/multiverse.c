/* SPDX-License-Identifier: GPL-3.0-only */
#include "nova_link/multiverse_plugin.h"
#include <string.h>

static void put16(uint8_t *p, uint16_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8u);
}
static uint16_t get16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8u));
}
static void put32(uint8_t *p, uint32_t value)
{
    for (unsigned i = 0; i < 4u; ++i) p[i] = (uint8_t)(value >> (8u * i));
}
static uint32_t get32(const uint8_t *p)
{
    uint32_t value = 0;
    for (unsigned i = 0; i < 4u; ++i) value |= (uint32_t)p[i] << (8u * i);
    return value;
}
static uint32_t crc32(const uint8_t *bytes, size_t count)
{
    uint32_t crc = UINT32_MAX;
    for (size_t i = 0; i < count; ++i) {
        crc ^= bytes[i];
        for (unsigned bit = 0; bit < 8u; ++bit)
            crc = (crc >> 1u) ^ ((crc & 1u) != 0u ? UINT32_C(0xedb88320) : 0u);
    }
    return crc ^ UINT32_MAX;
}

nova_mv_result_t nl_multiverse_payload_encode(const nova_mv_packet_t *p,
                                            uint8_t *output, size_t capacity,
                                            size_t *written)
{
    nova_mv_result_t result;
    size_t size;
    if (written != NULL) *written = 0;
    if (output == NULL || written == NULL) return NOVA_MV_INVALID_ARGUMENT;
    result = nova_mv_packet_validate(p);
    if (result != NOVA_MV_OK) return result;
    if (p->count > NL_MULTIVERSE_CHUNK_SLOTS) return NOVA_MV_BAD_PACKET;
    size = NL_MULTIVERSE_HEADER_BYTES + p->count;
    if (capacity < size) return NOVA_MV_BUFFER_TOO_SMALL;
    memcpy(output, "NLM1", 4);
    output[4] = (uint8_t)p->kind;
    output[5] = 0;
    put16(output + 6, p->universe);
    put32(output + 8, p->session);
    put16(output + 12, p->sequence);
    put16(output + 14, p->base_sequence);
    put16(output + 16, p->slot_count);
    put16(output + 18, p->span_start);
    put16(output + 20, p->span_count);
    put16(output + 22, p->offset);
    memcpy(output + 24, p->levels, p->count);
    put32(output + size - 4u, crc32(output, size - 4u));
    *written = size;
    return NOVA_MV_OK;
}

nova_mv_result_t nl_multiverse_payload_decode(const uint8_t *bytes, size_t size,
                                            nova_mv_packet_t *packet)
{
    nova_mv_packet_t p = {0};
    if (bytes == NULL || packet == NULL) return NOVA_MV_INVALID_ARGUMENT;
    if (size < NL_MULTIVERSE_HEADER_BYTES || size > NL_PAYLOAD_MAX ||
        memcmp(bytes, "NLM1", 4) != 0 || bytes[5] != 0u ||
        crc32(bytes, size - 4u) != get32(bytes + size - 4u)) return NOVA_MV_BAD_PACKET;
    p.kind = (nova_mv_kind_t)bytes[4];
    p.universe = get16(bytes + 6);
    p.session = get32(bytes + 8);
    p.sequence = get16(bytes + 12);
    p.base_sequence = get16(bytes + 14);
    p.slot_count = get16(bytes + 16);
    p.span_start = get16(bytes + 18);
    p.span_count = get16(bytes + 20);
    p.offset = get16(bytes + 22);
    p.count = (uint16_t)(size - NL_MULTIVERSE_HEADER_BYTES);
    if (nova_mv_packet_validate(&p) != NOVA_MV_OK) return NOVA_MV_BAD_PACKET;
    memcpy(p.levels, bytes + 24, p.count);
    *packet = p;
    return NOVA_MV_OK;
}

nova_mv_result_t nl_multiverse_init(nl_multiverse_context *c,
                                  const nl_multiverse_config *config)
{
    nova_mv_tx_config_t tx;
    nova_mv_rx_config_t rx;
    if (c == NULL || config == NULL || config->zone == 0u ||
        config->zone >= NL_ZONE_COUNT || config->universe == 0u ||
        config->universe > 63999u) return NOVA_MV_INVALID_ARGUMENT;
    if (config->role == NL_MULTIVERSE_TX) {
        if (config->chunks_per_tick == 0u || config->chunks_per_tick > 8u ||
            config->interval_us == 0u || config->full_interval_us < config->interval_us)
            return NOVA_MV_INVALID_ARGUMENT;
    } else if (config->role == NL_MULTIVERSE_RX) {
        if (config->peer_origin >= NL_ORIGIN_COUNT || config->loss_timeout_us == 0u ||
            config->assembly_timeout_us == 0u) return NOVA_MV_INVALID_ARGUMENT;
    } else return NOVA_MV_INVALID_ARGUMENT;
    /* Copy config before clearing, including if config refers to c->config. */
    {
        nl_multiverse_config saved = *config;
        memset(c, 0, sizeof(*c));
        c->config = saved;
    }
    c->id = NL_PLUGIN_ID_NONE;
    c->last_result = NOVA_MV_OK;
    if (c->config.role == NL_MULTIVERSE_TX) {
        tx.universe = c->config.universe;
        tx.session = c->config.session;
        tx.chunk_slots = NL_MULTIVERSE_CHUNK_SLOTS;
        tx.interval_us = c->config.interval_us;
        tx.full_interval_us = c->config.full_interval_us;
        (void)nova_mv_tx_init(&c->tx, &tx);
    } else {
        rx.universe = c->config.universe;
        rx.session = c->config.session;
        rx.loss_timeout_us = c->config.loss_timeout_us;
        rx.assembly_timeout_us = c->config.assembly_timeout_us;
        (void)nova_mv_rx_init(&c->rx, &rx);
    }
    c->initialized = true;
    return NOVA_MV_OK;
}

static nl_status start(nl_host *host, nl_plugin_id id, void *context)
{
    nl_multiverse_context *c = context;
    nl_status status;
    if (c == NULL || !c->initialized || c->stopped) return NL_ERR_ARGUMENT;
    if (c->active) return NL_ERR_BUSY;
    if (c->config.role == NL_MULTIVERSE_RX && c->config.peer_origin == host->origin)
        return NL_ERR_CONFLICT;
    status = nl_host_claim(host, id, c->config.zone,
        c->config.role == NL_MULTIVERSE_TX ? NL_ZONE_EXCLUSIVE : NL_ZONE_READ_ONLY);
    if (status != NL_OK) return status;
    c->owner = host;
    c->id = id;
    c->active = true;
    return NL_OK;
}

static void stop(nl_host *host, nl_plugin_id id, void *context)
{
    nl_multiverse_context *c = context;
    /* Host also calls stop after failed starts; never stop a different owner. */
    if (c == NULL || !c->active || c->owner != host || c->id != id) return;
    c->active = false;
    c->stopped = true;
    c->owner = NULL;
    c->id = NL_PLUGIN_ID_NONE;
}

static void receive(nl_host *host, nl_plugin_id id, const nl_fragment *fragment,
                    void *context)
{
    nl_multiverse_context *c = context;
    nova_mv_packet_t packet;
    (void)id;
    if (!c->active || c->config.role != NL_MULTIVERSE_RX ||
        fragment->zone != c->config.zone) return;
    c->last_result = nova_mv_rx_tick(&c->rx, host->callback_now_us);
    if (c->last_result != NOVA_MV_OK) return;
    if (fragment->origin != c->config.peer_origin) {
        ++c->stats.filtered_origins;
        c->last_result = NOVA_MV_FILTERED;
        return;
    }
    if (fragment->flags != 0u) {
        ++c->stats.bad_flags;
        c->last_result = NOVA_MV_BAD_PACKET;
        return;
    }
    c->last_result = nl_multiverse_payload_decode(fragment->payload,
                                                fragment->payload_size, &packet);
    if (c->last_result != NOVA_MV_OK) {
        ++c->stats.bad_payloads;
        return;
    }
    c->last_result = nova_mv_rx_receive(&c->rx, &packet, NOVA_MV_INTEGRITY_OK,
                                       host->callback_now_us, NULL);
}

static void tick(nl_host *host, nl_plugin_id id, uint64_t now_us, void *context)
{
    nl_multiverse_context *c = context;
    nova_mv_packet_t packet;
    uint8_t bytes[NL_PAYLOAD_MAX];
    size_t size;
    uint64_t token;
    if (!c->active) return;
    if (c->config.role == NL_MULTIVERSE_RX) {
        c->last_result = nova_mv_rx_tick(&c->rx, now_us);
        return;
    }
    for (unsigned i = 0; i < c->config.chunks_per_tick; ++i) {
        c->last_result = nova_mv_tx_prepare(&c->tx, now_us, &packet, &token);
        if (c->last_result != NOVA_MV_PACKET_READY) return;
        c->last_result = nl_multiverse_payload_encode(&packet, bytes, sizeof(bytes), &size);
        if (c->last_result != NOVA_MV_OK) return;
        c->last_send_status = nl_host_send(host, id, c->config.zone, 0, bytes, size);
        c->last_result = nova_mv_tx_complete(&c->tx, token, c->last_send_status == NL_OK, now_us);
        if (c->last_send_status != NL_OK) {
            if (c->last_send_status == NL_ERR_FULL || c->last_send_status == NL_ERR_BUSY)
                ++c->stats.backpressure;
            else ++c->stats.send_errors;
            return;
        }
        /* Never begin a second update in the same host tick, even if forced. */
        if (!c->tx.active) return;
    }
}

nl_plugin nl_multiverse_plugin(nl_multiverse_context *context)
{
    nl_plugin plugin = {.start = start, .receive = receive, .tick = tick,
                        .stop = stop, .context = context};
    return plugin;
}

nl_module nl_multiverse_module(nl_multiverse_context *context)
{
    static const char *const dependencies[] = {"radio-link"};
    nl_module module = {.name = "multiverse", .version = "1",
                        .kind = NL_MODULE_APPLICATION,
                        .requires = dependencies, .require_count = 1};
    if (context != NULL) {
        context->module_zone.zone = context->config.zone;
        context->module_zone.mode = context->config.role == NL_MULTIVERSE_TX ?
            NL_ZONE_EXCLUSIVE : NL_ZONE_READ_ONLY;
        module.zones = &context->module_zone;
        module.zone_count = 1;
    }
    module.hooks = nl_multiverse_plugin(context);
    return module;
}

nova_mv_result_t nl_multiverse_submit(nl_multiverse_context *c,
                                    const nova_dmx_frame_t *frame)
{
    if (c == NULL || !c->initialized || c->stopped || c->config.role != NL_MULTIVERSE_TX)
        return NOVA_MV_INVALID_ARGUMENT;
    return nova_mv_tx_submit(&c->tx, frame);
}

void nl_multiverse_force_full(nl_multiverse_context *c)
{
    if (c != NULL && c->initialized && !c->stopped && c->config.role == NL_MULTIVERSE_TX)
        nova_mv_tx_force_full(&c->tx);
}

nova_mv_result_t nl_multiverse_get(nl_multiverse_context *c, uint64_t now_us,
                                 nova_dmx_frame_t *frame)
{
    if (c == NULL || !c->initialized || !c->active || c->config.role != NL_MULTIVERSE_RX)
        return NOVA_MV_INVALID_ARGUMENT;
    return nova_mv_rx_get(&c->rx, now_us, frame);
}

nova_mv_result_t nl_multiverse_bind(nl_multiverse_context *c,
                                  uint8_t peer_origin, uint32_t session)
{
    nova_mv_result_t result;
    if (c == NULL || !c->initialized || !c->active || c->config.role != NL_MULTIVERSE_RX ||
        peer_origin >= NL_ORIGIN_COUNT || peer_origin == c->owner->origin ||
        c->owner->dispatching || c->owner->sending || c->owner->lifecycle_busy ||
        c->owner->logging || c->owner->polling) return NOVA_MV_INVALID_ARGUMENT;
    result = nova_mv_rx_bind(&c->rx, session);
    if (result == NOVA_MV_OK) {
        c->config.peer_origin = peer_origin;
        c->config.session = session;
    }
    return result;
}
