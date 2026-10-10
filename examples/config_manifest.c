/* SPDX-License-Identifier: GPL-3.0-only */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/config_plugin.h"
#include "nova_link/counter_plugin.h"
#include "nova_link/logger_plugin.h"
#include "nova_link/multiverse_plugin.h"
#include "nova_link/radio_plugin.h"

#define INPUT_MAX 8192u
#define ENTRY_MAX 32u
#define MODULE_COUNT 5u
#define UINT_FIELD(key_, required_, min_, max_) \
    {.key = key_, .type = NL_CONFIG_UINT, .required = required_, \
     .minimum = min_, .maximum = max_}
#define ROLE_FIELD \
    {.key = "role", .type = NL_CONFIG_ENUM, .required = true, \
     .choices = roles, .choice_count = 2}
static const char *const roles[] = {"tx", "rx"};
static const nl_config_field host_fields[] = {
    UINT_FIELD("origin", true, 0, 7),
    UINT_FIELD("idle_timeout_us", false, 0, UINT64_MAX)
};
static const nl_config_field radio_fields[] = {
    UINT_FIELD("slot_us", true, 1, UINT32_MAX),
    UINT_FIELD("poll_budget", true, 1, UINT16_MAX)
};
static const nl_config_field logger_fields[] = {
    {.key = "echo", .type = NL_CONFIG_BOOL, .required = true}
};
static const nl_config_field counter_fields[] = {
    ROLE_FIELD, UINT_FIELD("zone", true, 1, 7)
};
static const nl_config_field multiverse_fields[] = {
    ROLE_FIELD, UINT_FIELD("zone", true, 1, 7),
    UINT_FIELD("universe", true, 1, 63999),
    UINT_FIELD("session", true, 0, UINT32_MAX),
    UINT_FIELD("interval_us", false, 1, UINT64_MAX),
    UINT_FIELD("full_interval_us", false, 1, UINT64_MAX),
    UINT_FIELD("chunks_per_tick", false, 1, 8),
    UINT_FIELD("slots", false, 0, NOVA_DMX_MAX_SLOTS),
    UINT_FIELD("initial_level", false, 0, UINT8_MAX),
    UINT_FIELD("peer_origin", false, 0, 7),
    UINT_FIELD("loss_timeout_us", false, 1, UINT64_MAX),
    UINT_FIELD("assembly_timeout_us", false, 1, UINT64_MAX)
};
static const nl_config_section schema[] = {
    {.name = "host", .required = true, .fields = host_fields, .field_count = 2},
    {.name = "radio-link", .required = true, .fields = radio_fields, .field_count = 2},
    {.name = "logger", .required = true, .fields = logger_fields, .field_count = 1},
    {.name = "counter", .required = true, .fields = counter_fields, .field_count = 2},
    {.name = "multiverse", .required = true, .fields = multiverse_fields,
     .field_count = sizeof(multiverse_fields) / sizeof(multiverse_fields[0])}
};

typedef struct {
    uint64_t origin, idle_timeout_us, slot_us, poll_budget, counter_zone;
    uint64_t zone, universe, session, interval_us, full_interval_us;
    uint64_t chunks_per_tick, slots, initial_level;
    uint64_t peer_origin, loss_timeout_us, assembly_timeout_us;
    bool counter_tx, multiverse_tx, echo;
} settings;
typedef struct {
    nl_config_context configuration;
    nl_config_entry entries[ENTRY_MAX];
    nl_host host;
    nl_radio radio;
    nl_radio_link transport;
    nl_counter_context counter;
    nl_multiverse_context multiverse;
    nl_logger_context logger;
    nl_module descriptors[MODULE_COUNT];
    const nl_module *manifest[MODULE_COUNT];
    nl_module_instance instances[MODULE_COUNT];
    bool echo;
    uint64_t events;
} application;

static bool okay(nl_status status, const char *operation)
{
    if (status == NL_OK) return true;
    fprintf(stderr, "%s: %s\n", operation, nl_status_name(status));
    return false;
}
static uint64_t number(const nl_config_context *config, const char *section,
                       const char *key, uint64_t fallback)
{
    uint64_t value = fallback;
    (void)nl_config_uint(config, section, key, &value);
    return value;
}
static bool role_fields(const nl_config_context *config, bool tx)
{
    static const char *const tx_keys[] = {
        "interval_us", "full_interval_us", "chunks_per_tick", "slots", "initial_level"
    };
    static const char *const rx_keys[] = {
        "peer_origin", "loss_timeout_us", "assembly_timeout_us"
    };
    const char *const *required = tx ? tx_keys : rx_keys;
    const char *const *forbidden = tx ? rx_keys : tx_keys;
    size_t forbidden_count = tx ? 3u : 5u;
    for (size_t i = 0; i < 3u; ++i) {
        if (nl_config_value(config, "multiverse", required[i]) == NULL) {
            fprintf(stderr, "multiverse.%s is required for role=%s\n", required[i], tx ? "tx" : "rx");
            return false;
        }
    }
    for (size_t i = 0; i < forbidden_count; ++i) {
        if (nl_config_value(config, "multiverse", forbidden[i]) != NULL) {
            fprintf(stderr, "multiverse.%s is forbidden for role=%s\n", forbidden[i], tx ? "tx" : "rx");
            return false;
        }
    }
    return true;
}
static bool validate(const nl_config_context *config, settings *s)
{
    s->counter_tx = strcmp(nl_config_value(config, "counter", "role"), "tx") == 0;
    s->multiverse_tx = strcmp(nl_config_value(config, "multiverse", "role"), "tx") == 0;
    if (!role_fields(config, s->multiverse_tx)) return false;
    s->origin = number(config, "host", "origin", 0);
    s->idle_timeout_us = number(config, "host", "idle_timeout_us", 0);
    s->slot_us = number(config, "radio-link", "slot_us", 0);
    s->poll_budget = number(config, "radio-link", "poll_budget", 0);
    s->counter_zone = number(config, "counter", "zone", 0);
    s->zone = number(config, "multiverse", "zone", 0);
    s->universe = number(config, "multiverse", "universe", 0);
    s->session = number(config, "multiverse", "session", 0);
    s->interval_us = number(config, "multiverse", "interval_us", 0);
    s->full_interval_us = number(config, "multiverse", "full_interval_us", 0);
    s->chunks_per_tick = number(config, "multiverse", "chunks_per_tick", 0);
    s->slots = number(config, "multiverse", "slots", NOVA_DMX_MAX_SLOTS);
    s->initial_level = number(config, "multiverse", "initial_level", 0);
    s->peer_origin = number(config, "multiverse", "peer_origin", 0);
    s->loss_timeout_us = number(config, "multiverse", "loss_timeout_us", 0);
    s->assembly_timeout_us = number(config, "multiverse", "assembly_timeout_us", 0);
    if (!okay(nl_config_bool(config, "logger", "echo", &s->echo), "logger.echo")) return false;
    if (s->zone == s->counter_zone) {
        fputs("counter.zone and multiverse.zone must differ (different payload protocols)\n", stderr);
        return false;
    }
    if (s->multiverse_tx && s->full_interval_us < s->interval_us) {
        fputs("multiverse.full_interval_us must be >= interval_us\n", stderr);
        return false;
    }
    if (!s->multiverse_tx && s->peer_origin == s->origin) {
        fputs("multiverse.peer_origin must differ from host.origin\n", stderr);
        return false;
    }
    if (!s->multiverse_tx && s->assembly_timeout_us > s->loss_timeout_us) {
        fputs("multiverse.assembly_timeout_us must be <= loss_timeout_us\n", stderr);
        return false;
    }
    return true;
}

static nl_status exchange(void *context, const nl_frame *request,
                          nl_frame *response, nl_pull_token *token)
{
    uint8_t bytes[NL_FRAME_MAX];
    nl_frame decoded;
    size_t size;
    nl_status status = nl_frame_encode(request, bytes, sizeof(bytes), &size);
    if (status != NL_OK) return status;
    status = nl_frame_decode(bytes, size, &decoded);
    if (status != NL_OK) return status;
    status = nl_radio_handle_frame(context, &decoded, response, token);
    if (status != NL_OK || request->command == NL_COMMAND_PUSH) return status;
    status = nl_frame_encode(response, bytes, sizeof(bytes), &size);
    return status == NL_OK ? nl_frame_decode(bytes, size, response) : status;
}
static nl_status commit(void *context, const nl_frame *response, nl_pull_token token)
{
    return nl_radio_commit_pull(context, response, token);
}
static nl_status can_stop(void *context)
{
    const nl_radio *radio = context;
    if (radio->rx.count != 0u) return NL_ERR_BUSY;
    for (size_t zone = 1; zone < 8u; ++zone)
        if (radio->tx[zone].count != 0u) return NL_ERR_BUSY;
    return NL_OK;
}
static void drain(void *context)
{
    nl_radio *radio = context;
    nl_fragment discarded;
    for (uint8_t zone = 1; zone < 8u; ++zone)
        while (nl_radio_pop_tx(radio, zone, &discarded) == NL_OK) {}
    while (nl_radio_pull(radio, &discarded) == NL_OK) {}
}
static void observe(void *context, nl_log_event event, nl_status status,
                    nl_plugin_id plugin, uint8_t zone)
{
    application *app = context;
    ++app->events;
    if (app->echo)
        printf("event=%u plugin=%u zone=%u status=%s\n", (unsigned)event,
               (unsigned)plugin, (unsigned)zone, nl_status_name(status));
}
static bool initialize(application *app, const settings *s)
{
    static const char *const config_dependency[] = {"configuration"};
    static const char *const app_dependencies[] = {"radio-link", "logger", "configuration"};
    uint8_t active = (uint8_t)((1u << (unsigned)s->zone) | (1u << (unsigned)s->counter_zone));
    nl_radio_link_config radio_config = {.exchange = exchange, .commit = commit,
        .stop = drain, .can_stop = can_stop, .context = &app->radio,
        .poll_budget = (uint16_t)s->poll_budget};
    nl_multiverse_config mv_config = {
        .role = s->multiverse_tx ? NL_MULTIVERSE_TX : NL_MULTIVERSE_RX,
        .zone = (uint8_t)s->zone, .peer_origin = (uint8_t)s->peer_origin,
        .universe = (uint16_t)s->universe, .session = (uint32_t)s->session,
        .interval_us = s->interval_us, .full_interval_us = s->full_interval_us,
        .loss_timeout_us = s->loss_timeout_us, .assembly_timeout_us = s->assembly_timeout_us,
        .chunks_per_tick = (uint8_t)s->chunks_per_tick
    };
    nova_mv_result_t result;
    app->echo = s->echo;
    if (!okay(nl_host_init_plugins(&app->host, (uint8_t)s->origin, s->idle_timeout_us), "Host init") ||
        !okay(nl_radio_init(&app->radio, active, (uint32_t)s->slot_us, 0, s->idle_timeout_us), "Radio init") ||
        !okay(nl_radio_link_init(&app->transport, &radio_config), "Transport init") ||
        !okay(nl_logger_init(&app->logger, observe, app), "Logger init")) return false;
    result = nl_multiverse_init(&app->multiverse, &mv_config);
    if (result != NOVA_MV_OK) {
        fprintf(stderr, "Multiverse init: %s\n", nova_mv_result_name(result));
        return false;
    }
    app->counter.transmitter = s->counter_tx;
    app->counter.zone = (uint8_t)s->counter_zone;
    /* Intentionally unordered: providers must start before their consumers. */
    app->descriptors[0] = nl_multiverse_module(&app->multiverse);
    app->descriptors[1] = nl_counter_module(&app->counter);
    app->descriptors[2] = nl_logger_module(&app->logger);
    app->descriptors[3] = nl_radio_link_module(&app->transport);
    app->descriptors[4] = nl_config_module(&app->configuration);
    for (size_t i = 0; i < MODULE_COUNT; ++i) {
        if (i < 2u) {
            app->descriptors[i].requires = app_dependencies;
            app->descriptors[i].require_count = 3;
        } else if (i < 4u) {
            app->descriptors[i].requires = config_dependency;
            app->descriptors[i].require_count = 1;
        }
        app->manifest[i] = &app->descriptors[i];
    }
    return true;
}
static bool run(application *app, const settings *s)
{
    nova_dmx_frame_t frame = {0};
    uint64_t serialized = 0;
    bool success = true;
    if (s->multiverse_tx) {
        frame.slot_count = (uint16_t)s->slots;
        memset(frame.slots, (int)s->initial_level, frame.slot_count);
        if (nl_multiverse_submit(&app->multiverse, &frame) != NOVA_MV_OK) return false;
    }
    if (!okay(nl_modules_start(&app->host, app->manifest, app->instances, MODULE_COUNT), "Manifest startup"))
        return false;
    puts("Started 5 compiled plugins from validated configuration; native NLM1 only, no Multiverse RF.");
    success = okay(nl_host_poll(&app->host, 0), "Offline poll");
    if (s->counter_tx && !okay(app->counter.last_status, "Counter queue acceptance")) success = false;
    if (s->multiverse_tx && !okay(app->multiverse.last_send_status, "DMX queue acceptance")) success = false;
    for (uint8_t zone = 1; zone < 8u; ++zone) {
        nl_fragment fragment, decoded;
        uint8_t bytes[NL_FRAGMENT_MAX];
        size_t size;
        while (nl_radio_pop_tx(&app->radio, zone, &fragment) == NL_OK) {
            if (!okay(nl_fragment_encode(&fragment, bytes, sizeof(bytes), &size), "Native encode") ||
                !okay(nl_fragment_decode(bytes, size, &decoded), "Native decode")) success = false;
            ++serialized;
        }
    }
    /* The offline backend deliberately discards accepted TX after serialization.
     * Draining fulfills local ownership; it does not establish peer delivery. */
    if (!okay(nl_modules_stop(app->instances, MODULE_COUNT), "Manifest shutdown")) success = false;
    printf("Accepted TX fragments=%" PRIu64 "; serialized/drained=%" PRIu64
           "; log events=%" PRIu64 "; RX receives no injected traffic.\n",
           app->transport.stats.tx_accepted, serialized, app->events);
    return success;
}

int main(int argc, char **argv)
{
    static application app;
    char text[INPUT_MAX + 1u];
    settings parsed = {0};
    nl_config_error error;
    nl_status status;
    size_t size;
    FILE *input;
    if (argc != 2) {
        fprintf(stderr, "Usage: %s CONFIG.ini\n", argv[0]);
        return 2;
    }
    input = fopen(argv[1], "rb");
    if (input == NULL) {
        perror(argv[1]);
        return EXIT_FAILURE;
    }
    size = fread(text, 1, sizeof(text), input);
    if (ferror(input)) {
        fprintf(stderr, "%s: input read failed\n", argv[1]);
        (void)fclose(input);
        return EXIT_FAILURE;
    }
    if (fclose(input) != 0) {
        fprintf(stderr, "%s: input close failed\n", argv[1]);
        return EXIT_FAILURE;
    }
    if (size > INPUT_MAX) {
        fprintf(stderr, "Configuration exceeds %u bytes\n", INPUT_MAX);
        return EXIT_FAILURE;
    }
    status = nl_config_parse(&app.configuration, text, size, app.entries, ENTRY_MAX,
                            schema, sizeof(schema) / sizeof(schema[0]), &error);
    if (status != NL_OK) {
        fprintf(stderr, "Configuration line %zu [%s] %s: %s\n", error.line,
                error.section, error.key, nl_status_name(status));
        return EXIT_FAILURE;
    }
    if (!validate(&app.configuration, &parsed) || !initialize(&app, &parsed)) return EXIT_FAILURE;
    return run(&app, &parsed) ? EXIT_SUCCESS : EXIT_FAILURE;
}
