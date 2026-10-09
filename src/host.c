#include <string.h>
#include "nova_link/host.h"

#define GENERATION_MAX 0x00FFFFFFu

static uint8_t plugin_index(nl_plugin_id plugin)
{
    return (uint8_t)(plugin & 0xFFu);
}

static nl_plugin_id plugin_handle(const nl_host *host, uint8_t index)
{
    return (host->plugins[index].generation << 8) | index;
}

static void retire_slot(nl_plugin_slot *slot)
{
    uint32_t generation = slot->generation + 1u;
    memset(slot, 0, sizeof(*slot));
    slot->generation = generation;
}

static bool registered(const nl_host *host, nl_plugin_id plugin)
{
    uint8_t index = plugin_index(plugin);
    return host != NULL && index < NL_PLUGIN_MAX &&
        host->plugins[index].state != NL_PLUGIN_FREE &&
        host->plugins[index].generation == (plugin >> 8);
}

static void log_event(nl_host *host, nl_log_event event, nl_status status, nl_plugin_id plugin, uint8_t zone)
{
    if (host->log != NULL && !host->logging) {
        host->logging = true;
        host->log(host->log_context, event, status, plugin, zone);
        host->logging = false;
    }
}

nl_status nl_host_init(nl_host *host, uint8_t origin, uint64_t idle_timeout_us, nl_send_fn send, void *context)
{
    if (host == NULL || origin >= NL_ORIGIN_COUNT || send == NULL) return NL_ERR_ARGUMENT;
    memset(host, 0, sizeof(*host));
    host->origin = origin;
    host->send = send;
    host->send_context = context;
    nl_zones_init(&host->zones);
    nl_stream_init(&host->streams, idle_timeout_us);
    return NL_OK;
}

void nl_host_set_logger(nl_host *host, nl_log_fn log, void *context)
{
    if (host == NULL || host->logging) return;
    host->log = log;
    host->log_context = context;
}

nl_status nl_host_register(nl_host *host, const nl_plugin *plugin, nl_plugin_id *id)
{
    uint8_t slot;
    nl_plugin_id handle;
    nl_plugin *callbacks;
    nl_status status = NL_OK;
    if (host == NULL || plugin == NULL || id == NULL) return NL_ERR_ARGUMENT;
    if (host->dispatching || host->lifecycle_busy || host->sending || host->logging) return NL_ERR_BUSY;
    for (slot = 0; slot < NL_PLUGIN_MAX; ++slot)
        if (host->plugins[slot].state == NL_PLUGIN_FREE && host->plugins[slot].generation <= GENERATION_MAX) break;
    if (slot == NL_PLUGIN_MAX) return NL_ERR_FULL;
    host->plugins[slot].callbacks = *plugin;
    callbacks = &host->plugins[slot].callbacks;
    host->plugins[slot].state = NL_PLUGIN_STARTING;
    handle = plugin_handle(host, slot);
    host->lifecycle_busy = true;
    if (callbacks->start != NULL) status = callbacks->start(host, handle, callbacks->context);
    if (status != NL_OK) {
        if (callbacks->stop != NULL) {
            host->plugins[slot].state = NL_PLUGIN_STOPPING;
            callbacks->stop(host, handle, callbacks->context);
        }
        nl_zones_release_plugin(&host->zones, slot);
        retire_slot(&host->plugins[slot]);
    } else {
        host->plugins[slot].state = NL_PLUGIN_ACTIVE;
        *id = handle;
    }
    host->lifecycle_busy = false;
    log_event(host, NL_LOG_START, status, handle, 0);
    return status;
}

nl_status nl_host_unregister(nl_host *host, nl_plugin_id plugin)
{
    nl_plugin_slot *slot;
    if (host == NULL) return NL_ERR_ARGUMENT;
    if (host->dispatching || host->lifecycle_busy || host->sending || host->logging) return NL_ERR_BUSY;
    if (!registered(host, plugin)) return NL_ERR_NOT_FOUND;
    slot = &host->plugins[plugin_index(plugin)];
    host->lifecycle_busy = true;
    slot->state = NL_PLUGIN_STOPPING;
    if (slot->callbacks.stop != NULL) slot->callbacks.stop(host, plugin, slot->callbacks.context);
    nl_zones_release_plugin(&host->zones, plugin_index(plugin));
    retire_slot(slot);
    host->lifecycle_busy = false;
    return NL_OK;
}

nl_status nl_host_claim(nl_host *host, nl_plugin_id plugin, uint8_t zone, nl_zone_mode mode)
{
    nl_status status;
    if (!registered(host, plugin)) return NL_ERR_NOT_FOUND;
    if (host->logging || host->plugins[plugin_index(plugin)].state == NL_PLUGIN_STOPPING) return NL_ERR_BUSY;
    status = nl_zones_claim(&host->zones, plugin_index(plugin), zone, mode);
    if (status != NL_OK) log_event(host, NL_LOG_ACCESS, status, plugin, zone);
    return status;
}

nl_status nl_host_release(nl_host *host, nl_plugin_id plugin, uint8_t zone)
{
    nl_status status;
    if (!registered(host, plugin)) return NL_ERR_NOT_FOUND;
    if (host->logging) return NL_ERR_BUSY;
    status = nl_zones_release(&host->zones, plugin_index(plugin), zone);
    if (status != NL_OK) log_event(host, NL_LOG_ACCESS, status, plugin, zone);
    return status;
}

nl_status nl_host_send(nl_host *host, nl_plugin_id plugin, uint8_t zone, uint8_t flags,
                       const uint8_t *payload, size_t size)
{
    nl_fragment fragment = {0};
    nl_status status;
    if (host == NULL || zone >= NL_ZONE_COUNT ||
        (flags & ~NL_FLAGS_MASK) != 0u || (payload == NULL && size != 0u)) return NL_ERR_ARGUMENT;
    if (size > NL_PAYLOAD_MAX) return NL_ERR_SIZE;
    if (!registered(host, plugin)) return NL_ERR_NOT_FOUND;
    if (host->plugins[plugin_index(plugin)].state != NL_PLUGIN_ACTIVE || host->sending || host->lifecycle_busy || host->logging)
        return NL_ERR_BUSY;
    if (!nl_zones_can_write(&host->zones, plugin_index(plugin), zone)) {
        log_event(host, NL_LOG_ACCESS, NL_ERR_ACCESS, plugin, zone);
        return NL_ERR_ACCESS;
    }
    fragment.origin = host->origin;
    fragment.zone = zone;
    fragment.flags = flags;
    fragment.sequence = host->next_sequence[zone];
    fragment.payload_size = (uint8_t)size;
    if (size != 0u) memcpy(fragment.payload, payload, size);
    host->sending = true;
    status = host->send(host->send_context, &fragment);
    host->sending = false;
    if (status == NL_OK) ++host->next_sequence[zone];
    else log_event(host, NL_LOG_SEND, status, plugin, zone);
    return status;
}

nl_status nl_host_receive(nl_host *host, const nl_fragment *fragment, uint64_t now_us)
{
    uint8_t plugin;
    uint16_t recipients = 0;
    nl_status status;
    if (host == NULL) return NL_ERR_ARGUMENT;
    if (host->dispatching || host->lifecycle_busy || host->sending || host->logging) return NL_ERR_BUSY;
    status = nl_fragment_validate(fragment);
    if (status != NL_OK) return status;
    if (fragment->origin == host->origin) {
        log_event(host, NL_LOG_RECEIVE, NL_ERR_CONFLICT, NL_PLUGIN_ID_NONE, fragment->zone);
        return NL_ERR_CONFLICT;
    }
    for (plugin = 0; plugin < NL_PLUGIN_MAX; ++plugin)
        if (host->plugins[plugin].state == NL_PLUGIN_ACTIVE &&
            host->plugins[plugin].callbacks.receive != NULL &&
            nl_zones_can_read(&host->zones, plugin, fragment->zone))
            recipients |= (uint16_t)(1u << plugin);
    if (recipients == 0u) return NL_ERR_NOT_FOUND;
    status = nl_stream_accept(&host->streams, fragment, now_us);
    if (status != NL_OK) {
        log_event(host, NL_LOG_RECEIVE, status, NL_PLUGIN_ID_NONE, fragment->zone);
        return status;
    }
    host->dispatching = true;
    for (plugin = 0; plugin < NL_PLUGIN_MAX; ++plugin) {
        nl_plugin *callbacks = &host->plugins[plugin].callbacks;
        if ((recipients & (uint16_t)(1u << plugin)) != 0u)
            callbacks->receive(host, plugin_handle(host, plugin), fragment, callbacks->context);
    }
    host->dispatching = false;
    return NL_OK;
}

nl_status nl_host_receive_frame(nl_host *host, const nl_frame *frame, uint64_t now_us)
{
    nl_fragment fragment;
    nl_status status;
    if (host == NULL || frame == NULL) return NL_ERR_ARGUMENT;
    status = nl_frame_validate(frame);
    if (status != NL_OK) return status;
    if (frame->command != NL_COMMAND_FRAGMENT) return NL_ERR_UNSUPPORTED;
    status = nl_frame_to_fragment(frame, &fragment);
    return status == NL_OK ? nl_host_receive(host, &fragment, now_us) : status;
}

nl_status nl_host_tick(nl_host *host, uint64_t now_us)
{
    uint8_t plugin;
    if (host == NULL) return NL_ERR_ARGUMENT;
    if (host->dispatching || host->lifecycle_busy || host->sending || host->logging) return NL_ERR_BUSY;
    host->dispatching = true;
    for (plugin = 0; plugin < NL_PLUGIN_MAX; ++plugin) {
        nl_plugin *callbacks = &host->plugins[plugin].callbacks;
        if (host->plugins[plugin].state == NL_PLUGIN_ACTIVE && callbacks->tick != NULL)
            callbacks->tick(host, plugin_handle(host, plugin), now_us, callbacks->context);
    }
    host->dispatching = false;
    return NL_OK;
}
