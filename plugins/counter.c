#include "nova_link/counter_plugin.h"

static nl_status start(nl_host *host, nl_plugin_id id, void *context)
{
    nl_counter_context *counter = context;
    if (counter == NULL) return NL_ERR_ARGUMENT;
    return nl_host_claim(host, id, counter->zone,
        counter->transmitter ? NL_ZONE_EXCLUSIVE : NL_ZONE_READ_ONLY);
}

static void receive(nl_host *host, nl_plugin_id id, const nl_fragment *fragment, void *context)
{
    nl_counter_context *counter = context;
    (void)host;
    (void)id;
    if (fragment->zone != counter->zone || fragment->payload_size != 4u) return;
    counter->last_value = ((uint32_t)fragment->payload[0] << 24) |
        ((uint32_t)fragment->payload[1] << 16) | ((uint32_t)fragment->payload[2] << 8) |
        fragment->payload[3];
    ++counter->deliveries;
}

static void tick(nl_host *host, nl_plugin_id id, uint64_t now_us, void *context)
{
    nl_counter_context *counter = context;
    uint32_t value = counter->next_value;
    uint8_t payload[4];
    (void)now_us;
    if (!counter->transmitter) return;
    payload[0] = (uint8_t)(value >> 24);
    payload[1] = (uint8_t)(value >> 16);
    payload[2] = (uint8_t)(value >> 8);
    payload[3] = (uint8_t)value;
    counter->last_status = nl_host_send(host, id, counter->zone, 0, payload, sizeof(payload));
    if (counter->last_status == NL_OK) ++counter->next_value;
}

nl_plugin nl_counter_plugin(nl_counter_context *context)
{
    nl_plugin plugin = {.start = start, .receive = receive, .tick = tick,
                        .context = context};
    return plugin;
}

nl_module nl_counter_module(nl_counter_context *context)
{
    static const char *const dependencies[] = {"radio-link"};
    nl_module module = {.name = "counter", .version = "1",
                        .kind = NL_MODULE_APPLICATION,
                        .requires = dependencies, .require_count = 1};
    if (context != NULL) {
        context->module_zone.zone = context->zone;
        context->module_zone.mode = context->transmitter ? NL_ZONE_EXCLUSIVE : NL_ZONE_READ_ONLY;
        module.zones = &context->module_zone;
        module.zone_count = 1;
    }
    module.hooks = nl_counter_plugin(context);
    return module;
}
