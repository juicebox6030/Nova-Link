#include "nova_link/nova_link.h"
#include "nova/dmx.h"
#include "nova/multiverse.h"
#include "nova_link/counter_plugin.h"
#include "nova_link/logger_plugin.h"
#include "nova_link/multiverse_plugin.h"
#include "nova_link/radio_plugin.h"
#include "nova_link/config_plugin.h"
#include "nova_link/fault_backend.h"
#include "nova_link/plugin_conformance.h"
#include "nova_link/capture_plugin.h"

static nl_status capture_output(void *context, const char *jsonl, size_t length)
{
    unsigned *calls = context;
    if (jsonl == NULL || length == 0u || jsonl[length - 1u] != '\n')
        return NL_ERR_FORMAT;
    ++*calls;
    return *calls == 1u ? NL_ERR_BUSY : NL_OK;
}

static int capture_service(void)
{
    nl_host host;
    nl_capture_context capture;
    char buffer[512];
    unsigned calls = 0;
    nl_capture_config config = {buffer, sizeof(buffer), capture_output, &calls};
    nl_capture_observation observation = {
        .timestamp_us = 1, .frequency_hz = UINT32_C(2400000000),
        .profile = "candidate-phy", .crc = NL_CAPTURE_CRC_UNKNOWN};
    nl_module module;
    nl_module_instance instance = {0};
    if (nl_host_init_plugins(&host, 1, 0) != NL_OK ||
        nl_capture_init(&capture, &config) != NL_OK) return 1;
    module = nl_capture_module(&capture);
    if (nl_module_register(&host, &module, &instance) != NL_OK ||
        nl_capture_submit(&capture, &observation) != NL_OK ||
        nl_capture_flush(&capture) != NL_ERR_BUSY ||
        !nl_capture_pending(&capture) ||
        nl_module_unregister(&instance) != NL_ERR_BUSY ||
        nl_host_poll(&host, 100) != NL_OK || calls != 2u ||
        nl_capture_pending(&capture) ||
        nl_module_unregister(&instance) != NL_OK || capture.host != NULL)
        return 1;
    return 0;
}

static int developer_support(void)
{
    nl_fault_options options;
    nl_fault_backend backend;
    nl_radio_link link;
    nl_host host;
    nl_module module;
    nl_module_instance instance = {0};
    const nl_module *manifest[] = {&module};
    nl_radio_link_config config;
    if (nl_fault_profile_options(NL_FAULT_DISCONNECTED, &options) != NL_OK ||
        nl_fault_backend_init(&backend, &options) != NL_OK ||
        nl_fault_backend_set_time(&backend, 100) != NL_OK ||
        nl_fault_backend_set_time(&backend, 99) != NL_ERR_ARGUMENT ||
        !nl_fault_backend_drained(&backend) ||
        nl_conformance_case_name(NL_CONFORMANCE_LIFECYCLE) == NULL)
        return 1;
    config = nl_fault_backend_link_config(&backend, 2);
    if (nl_radio_link_init(&link, &config) != NL_OK ||
        nl_host_init_plugins(&host, 1, 0) != NL_OK) return 1;
    module = nl_radio_link_module(&link);
    if (nl_modules_start(&host, manifest, &instance, 1) != NL_OK ||
        !backend.started || nl_host_poll(&host, 100) != NL_OK ||
        nl_fault_backend_restart(&backend) != NL_ERR_BUSY ||
        nl_modules_stop(&instance, 1) != NL_OK || backend.started ||
        host.send != NULL || nl_fault_backend_restart(&backend) != NL_OK ||
        backend.stats.restarts != 1u)
        return 1;
    return 0;
}

static nl_status exchange(void *context, const nl_frame *request,
                          nl_frame *response, nl_pull_token *token)
{
    return nl_radio_handle_frame(context, request, response, token);
}
static nl_status commit(void *context, const nl_frame *response, nl_pull_token token)
{
    return nl_radio_commit_pull(context, response, token);
}
static void observe(void *context, nl_log_event event, nl_status status,
                    nl_plugin_id plugin, uint8_t zone)
{
    unsigned *events = context;
    (void)event; (void)status; (void)plugin; (void)zone;
    ++*events;
}

static int plugins(void)
{
    nl_host host;
    nl_radio radio;
    nl_radio_link link;
    nl_logger_context logger;
    nl_multiverse_context mv;
    nl_counter_context counter = {.transmitter = true, .zone = 2};
    nl_config_context settings = {0};
    nl_config_entry entries[1];
    const nl_config_field fields[] = {
        {.key = "origin", .type = NL_CONFIG_UINT, .required = true,
         .minimum = 0, .maximum = 7}
    };
    const nl_config_section sections[] = {
        {.name = "host", .required = true, .fields = fields, .field_count = 1}
    };
    static const char input[] = "[host]\norigin=1\n";
    uint64_t configured_origin = 0;
    nova_dmx_frame_t dmx = {0};
    nl_multiverse_config config = {.role = NL_MULTIVERSE_TX, .zone = 1,
        .universe = 1, .session = 42, .interval_us = 1000,
        .full_interval_us = 5000, .chunks_per_tick = 8};
    nl_radio_link_config backend = {.exchange = exchange, .commit = commit,
        .context = &radio, .poll_budget = 16};
    nl_module modules[5];
    const nl_module *manifest[5];
    nl_module_instance instances[5] = {0};
    unsigned events = 0;
    if (nl_config_parse(&settings, input, sizeof(input) - 1u, entries, 1,
                        sections, 1, NULL) != NL_OK ||
        nl_config_uint(&settings, "host", "origin", &configured_origin) != NL_OK ||
        configured_origin != 1u ||
        nl_host_init_plugins(&host, (uint8_t)configured_origin, 0) != NL_OK ||
        nl_radio_init(&radio, 6, 1000, 0, 0) != NL_OK ||
        nl_radio_link_init(&link, &backend) != NL_OK ||
        nl_logger_init(&logger, observe, &events) != NL_OK ||
        nl_multiverse_init(&mv, &config) != NOVA_MV_OK) return 1;
    modules[0] = nl_multiverse_module(&mv);
    modules[1] = nl_counter_module(&counter);
    modules[2] = nl_radio_link_module(&link);
    modules[3] = nl_logger_module(&logger);
    modules[4] = nl_config_module(&settings);
    for (unsigned i = 0; i < 5; ++i) manifest[i] = &modules[i];
    if (nl_modules_start(&host, manifest, instances, 5) != NL_OK ||
        nl_module_find(&host, "radio-link") == NULL ||
        nl_module_find(&host, "configuration") == NULL || !settings.active ||
        nl_multiverse_submit(&mv, &dmx) != NOVA_MV_OK ||
        nl_host_poll(&host, 0) != NL_OK ||
        radio.tx[1].count != 1u || radio.tx[2].count != 1u || events == 0u ||
        nl_modules_stop(instances, 5) != NL_OK || settings.active ||
        host.send != NULL || host.log != NULL)
        return 1;
    return 0;
}
int main(void)
{
    nl_fragment fragment = {0};
    uint8_t bytes[NL_FRAGMENT_MAX];
    size_t size = 0;
    nova_dmx_frame_t dmx = {0};
    size_t dmx_size = 0;
    uint8_t dmx_bytes[NOVA_DMX_MAX_PACKET_BYTES];
    nova_mv_tx_t tx;
    nova_mv_rx_t rx;
    nova_mv_tx_config_t tc = {1, 42, 64, 1000, 5000};
    nova_mv_rx_config_t rc = {1, 42, 10000, 1000};
    nova_mv_packet_t packet;
    uint64_t token;
    if (plugins() != 0 || developer_support() != 0 || capture_service() != 0)
        return 1;
    if (nova_mv_tx_init(&tx, &tc) != NOVA_MV_OK ||
        nova_mv_rx_init(&rx, &rc) != NOVA_MV_OK ||
        nova_mv_tx_submit(&tx, &dmx) != NOVA_MV_OK ||
        nova_mv_tx_prepare(&tx, 0, &packet, &token) != NOVA_MV_PACKET_READY ||
        nova_mv_rx_receive(&rx, &packet, NOVA_MV_INTEGRITY_OK, 0, &dmx) != NOVA_MV_FRAME_READY ||
        nova_mv_tx_complete(&tx, token, true, 0) != NOVA_MV_OK) return 1;
    return nl_fragment_encode(&fragment, bytes, sizeof(bytes), &size) == NL_OK && size == 2u &&
        nova_dmx_encode(&dmx, dmx_bytes, sizeof(dmx_bytes), &dmx_size) == NOVA_DMX_OK &&
        dmx_size == 1u && dmx_bytes[0] == 0u ? 0 : 1;
}
