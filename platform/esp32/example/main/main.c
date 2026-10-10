/* SPDX-License-Identifier: GPL-3.0-only */
#include "esp_log.h"
#include "nova_link/counter_plugin.h"
#include "nova_link/logger_plugin.h"
#include "nova_link/radio_plugin.h"

/* Persistent, task-owned contexts. No SPI/GPIO/radio/network operations. */
static nl_host host;
static nl_radio_link link;
static nl_logger_context logger;
static nl_counter_context counter = {.zone = 2, .transmitter = false};
static nl_module modules[3];
static nl_module_instance instances[3];

static nl_status no_io_exchange(void *context, const nl_frame *request,
                                nl_frame *response, nl_pull_token *token)
{
    (void)context;
    (void)response;
    (void)token;
    return request->command == NL_COMMAND_PULL ? NL_ERR_EMPTY : NL_ERR_BUSY;
}

static void observe(void *context, nl_log_event event, nl_status result,
                    nl_plugin_id plugin, uint8_t zone)
{
    (void)context;
    (void)event;
    (void)plugin;
    (void)zone;
    ESP_LOGI("nova-check", "plugin event: %s", nl_status_name(result));
}

static bool checked(nl_status result)
{
    if (result == NL_OK) return true;
    ESP_LOGE("nova-check", "startup check: %s", nl_status_name(result));
    return false;
}

void app_main(void)
{
    const nl_radio_link_config config = {.exchange = no_io_exchange,
                                         .poll_budget = 1};
    const nl_module *manifest[3];
    if (!checked(nl_host_init_plugins(&host, 1, 0)) ||
        !checked(nl_radio_link_init(&link, &config)) ||
        !checked(nl_logger_init(&logger, observe, NULL))) return;
    /* Deliberately unordered: the application depends on radio-link. */
    modules[0] = nl_counter_module(&counter);
    modules[1] = nl_logger_module(&logger);
    modules[2] = nl_radio_link_module(&link);
    for (size_t i = 0; i < 3; ++i) manifest[i] = &modules[i];
    if (!checked(nl_modules_start(&host, manifest, instances, 3))) return;
    if (!checked(nl_host_poll(&host, 0))) {
        (void)nl_modules_stop(instances, 3);
        return;
    }
    if (!checked(nl_modules_stop(instances, 3))) return;
    ESP_LOGI("nova-check", "manifest startup/poll/shutdown passed; no radio/transport I/O");
}
