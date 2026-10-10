#include "test.h"
#include "nova_link/capture_plugin.h"

typedef struct {
    nl_capture_context *capture;
    nl_status result;
    unsigned calls, accepted;
    char last[1024];
    bool exercise_reentry;
} sink;

static nl_status output(void *context, const char *jsonl, size_t length)
{
    sink *state = context;
    ++state->calls;
    CHECK(length < sizeof(state->last));
    CHECK(jsonl[length] == '\0');
    memcpy(state->last, jsonl, length + 1u);
    if (state->exercise_reentry) {
        const nl_capture_observation observation = {
            .frequency_hz = UINT32_C(2400000000), .profile = "reentry"
        };
        STATUS(nl_capture_submit(state->capture, &observation), NL_ERR_BUSY);
        STATUS(nl_capture_flush(state->capture), NL_ERR_BUSY);
        STATUS(nl_host_unregister(state->capture->host, state->capture->plugin), NL_ERR_BUSY);
    }
    if (state->result == NL_OK) ++state->accepted;
    return state->result;
}

static void register_capture(nl_host *host, nl_capture_context *capture,
                             char *buffer, size_t capacity, sink *state,
                             nl_module_instance *instance)
{
    nl_capture_config config = {.buffer = buffer, .capacity = capacity,
        .output = output, .output_context = state};
    nl_module module;
    STATUS(nl_host_init_plugins(host, 1, 100), NL_OK);
    STATUS(nl_capture_init(capture, &config), NL_OK);
    state->capture = capture;
    module = nl_capture_module(capture);
    CHECK(strcmp(module.name, "capture") == 0 && module.kind == NL_MODULE_SERVICE);
    CHECK(module.service == capture && module.require_count == 0);
    STATUS(nl_module_register(host, &module, instance), NL_OK);
}

static void golden_and_backpressure(bool emit)
{
    static const char expected[] = "{\"timestamp_us\":18446744073709551615,\"frequency_hz\":2483500000,"
        "\"profile\":\"candidate\\\"\\\\\\u000a\\u0001-\303\251\",\"stimulus\":\"channel_1_32\","
        "\"payload_hex\":\"007fff80\",\"crc\":\"bad\",\"rssi_dbm\":-32768}\n";
    char buffer[1024], copy[1024];
    char profile[] = "candidate\"\\\n\001-\303\251";
    char stimulus[] = "channel_1_32";
    uint8_t payload[] = {0x00, 0x7f, 0xff, 0x80};
    nl_capture_observation observation = {.timestamp_us = UINT64_MAX,
        .frequency_hz = UINT32_C(2483500000), .profile = profile, .stimulus = stimulus,
        .payload = payload, .payload_length = sizeof(payload), .crc = NL_CAPTURE_CRC_BAD,
        .has_rssi = true, .rssi_dbm = INT16_MIN};
    nl_host host;
    nl_capture_context capture;
    nl_module_instance instance = {0};
    sink state = {.result = NL_ERR_FULL, .exercise_reentry = true};
    register_capture(&host, &capture, buffer, sizeof(buffer), &state, &instance);
    STATUS(nl_capture_submit(&capture, &observation), NL_OK);
    CHECK(state.calls == 0 && nl_capture_pending(&capture));
    CHECK(strcmp(buffer, expected) == 0 && capture.pending_length == strlen(expected));
    memcpy(copy, buffer, strlen(buffer) + 1u);
    memset(profile, 'x', sizeof(profile) - 1u);
    memset(stimulus, 'y', sizeof(stimulus) - 1u);
    memset(payload, 0, sizeof(payload));
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_BUSY);
    STATUS(nl_module_unregister(&instance), NL_ERR_BUSY);
    STATUS(nl_capture_flush(&capture), NL_ERR_FULL);
    CHECK(state.accepted == 0 && strcmp(state.last, copy) == 0 && nl_capture_pending(&capture));
    state.result = NL_ERR_FORMAT;
    STATUS(nl_host_poll(&host, 10), NL_OK);
    CHECK(capture.last_status == NL_ERR_FORMAT && nl_capture_pending(&capture));
    CHECK(strcmp(buffer, expected) == 0 && state.calls == 2 && state.accepted == 0);
    state.result = NL_OK;
    STATUS(nl_host_poll(&host, 11), NL_OK);
    CHECK(capture.last_status == NL_OK && !nl_capture_pending(&capture));
    CHECK(state.accepted == 1 && state.calls == 3);
    if (emit) fputs(state.last, stdout);
    STATUS(nl_capture_flush(&capture), NL_ERR_EMPTY);
    STATUS(nl_module_unregister(&instance), NL_OK);
    CHECK(capture.host == NULL && capture.plugin == NL_PLUGIN_ID_NONE && !capture.have_timestamp);
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ACCESS);
    STATUS(nl_capture_flush(&capture), NL_ERR_ACCESS);
}

static void validation_and_capacity(bool emit)
{
    static const char minimal[] = "{\"timestamp_us\":0,\"frequency_hz\":2400000000,\"profile\":\"p\","
        "\"stimulus\":\"unspecified\",\"payload_hex\":\"\",\"crc\":\"unknown\",\"rssi_dbm\":null}\n";
    char buffer[1024], original[1024];
    nl_capture_context capture;
    nl_host host;
    nl_module_instance instance = {0};
    sink state = {0};
    nl_capture_observation observation = {.frequency_hz = UINT32_C(2400000000), .profile = "p"};
    nl_capture_config bad = {.buffer = buffer, .capacity = sizeof(buffer), .output = output};
    STATUS(nl_capture_init(NULL, &bad), NL_ERR_ARGUMENT);
    STATUS(nl_capture_init(&capture, NULL), NL_ERR_ARGUMENT);
    bad.buffer = NULL;
    STATUS(nl_capture_init(&capture, &bad), NL_ERR_ARGUMENT);
    bad.buffer = buffer; bad.capacity = 0;
    STATUS(nl_capture_init(&capture, &bad), NL_ERR_ARGUMENT);
    bad.capacity = sizeof(buffer); bad.output = NULL;
    STATUS(nl_capture_init(&capture, &bad), NL_ERR_ARGUMENT);
    bad.output = output; bad.buffer = (char *)&capture;
    STATUS(nl_capture_init(&capture, &bad), NL_ERR_ARGUMENT);
    CHECK(!nl_capture_pending(NULL));
    STATUS(nl_capture_flush(NULL), NL_ERR_ARGUMENT);
    STATUS(nl_capture_submit(NULL, &observation), NL_ERR_ARGUMENT);
    register_capture(&host, &capture, buffer, strlen(minimal) + 1u, &state, &instance);
    STATUS(nl_capture_submit(&capture, NULL), NL_ERR_ARGUMENT);
    STATUS(nl_capture_submit(&capture, &observation), NL_OK);
    CHECK(strcmp(buffer, minimal) == 0);
    STATUS(nl_capture_flush(&capture), NL_OK);
    if (emit) fputs(state.last, stdout);
    memcpy(original, buffer, strlen(buffer) + 1u);
    observation.timestamp_us = 1;
    observation.profile = "pp";
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_SIZE);
    CHECK(!nl_capture_pending(&capture) && capture.last_timestamp_us == 0);
    CHECK(strcmp(buffer, original) == 0);
    observation.profile = " ";
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.profile = "\t\r\n\v\f";
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.profile = "\302\240\342\200\203\034";
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.profile = "\300\257";
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.profile = "\355\240\200";
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.profile = "\364\220\200\200";
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.profile = "\342\202";
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.profile = "p"; observation.stimulus = "";
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.stimulus = NULL; observation.frequency_hz = UINT32_C(2399999999);
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.frequency_hz = UINT32_C(2483500001);
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.frequency_hz = UINT32_C(2400000000); observation.crc = (nl_capture_crc)99;
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.crc = NL_CAPTURE_CRC_OK; observation.payload_length = 1;
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.payload_length = 0; observation.profile = buffer;
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.profile = "p"; observation.payload = (const uint8_t *)buffer; observation.payload_length = 1;
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_ARGUMENT);
    observation.payload_length = SIZE_MAX;
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_SIZE);
    STATUS(nl_module_unregister(&instance), NL_OK);
    memset(&instance, 0, sizeof(instance));
    register_capture(&host, &capture, buffer, strlen(minimal), &state, &instance);
    observation = (nl_capture_observation){.frequency_hz = UINT32_C(2400000000), .profile = "p"};
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_SIZE);
    CHECK(!nl_capture_pending(&capture) && !capture.have_timestamp && buffer[0] == '\0');
    STATUS(nl_module_unregister(&instance), NL_OK);
    memset(&instance, 0, sizeof(instance));
    register_capture(&host, &capture, buffer, 1, &state, &instance);
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_SIZE);
    STATUS(nl_module_unregister(&instance), NL_OK);
}

static void timestamps_and_ownership(void)
{
    char buffer[1024];
    nl_capture_context capture;
    nl_capture_observation observation = {.timestamp_us = 7,
        .frequency_hz = UINT32_C(2400000000), .profile = "p", .crc = NL_CAPTURE_CRC_OK};
    nl_host host, other;
    nl_module_instance instance = {0};
    nl_plugin plugin;
    nl_plugin_id duplicate = NL_PLUGIN_ID_NONE;
    sink state = {0};
    register_capture(&host, &capture, buffer, sizeof(buffer), &state, &instance);
    plugin = nl_capture_plugin(&capture);
    STATUS(nl_host_register(&host, &plugin, &duplicate), NL_ERR_BUSY);
    CHECK(capture.host == &host && capture.plugin == instance.id);
    STATUS(nl_host_init_plugins(&other, 2, 100), NL_OK);
    STATUS(nl_host_register(&other, &plugin, &duplicate), NL_ERR_BUSY);
    CHECK(capture.host == &host && capture.plugin == instance.id);
    STATUS(nl_capture_submit(&capture, &observation), NL_OK);
    STATUS(nl_capture_flush(&capture), NL_OK);
    observation.timestamp_us = 6;
    STATUS(nl_capture_submit(&capture, &observation), NL_ERR_STALE);
    CHECK(!capture.pending && capture.last_timestamp_us == 7);
    observation.timestamp_us = 7;
    STATUS(nl_capture_submit(&capture, &observation), NL_OK);
    STATUS(nl_capture_flush(&capture), NL_OK);
    STATUS(nl_module_unregister(&instance), NL_OK);
    {
        nl_module module = nl_capture_module(&capture);
        STATUS(nl_module_register(&host, &module, &instance), NL_OK);
    }
    observation.timestamp_us = 0;
    STATUS(nl_capture_submit(&capture, &observation), NL_OK);
    STATUS(nl_capture_flush(&capture), NL_OK);
    STATUS(nl_module_unregister(&instance), NL_OK);
}

static void preserve_all_payload_bytes(void)
{
    char buffer[1024];
    uint8_t payload[256];
    static const char hex[] = "0123456789abcdef";
    nl_capture_context capture;
    nl_host host;
    nl_module_instance instance = {0};
    sink state = {0};
    nl_capture_observation observation = {.frequency_hz = UINT32_C(2450000000), .profile = "candidate",
        .payload = payload, .payload_length = sizeof(payload), .crc = NL_CAPTURE_CRC_OK};
    const char *encoded;
    size_t i;
    for (i = 0; i < sizeof(payload); ++i) payload[i] = (uint8_t)i;
    register_capture(&host, &capture, buffer, sizeof(buffer), &state, &instance);
    STATUS(nl_capture_submit(&capture, &observation), NL_OK);
    encoded = strstr(buffer, "\"payload_hex\":\"");
    CHECK(encoded != NULL);
    encoded += strlen("\"payload_hex\":\"");
    for (i = 0; i < sizeof(payload); ++i) {
        CHECK(encoded[2u * i] == hex[payload[i] >> 4u]);
        CHECK(encoded[2u * i + 1u] == hex[payload[i] & 0x0fu]);
    }
    CHECK(encoded[sizeof(payload) * 2u] == '"');
    STATUS(nl_capture_flush(&capture), NL_OK);
    STATUS(nl_module_unregister(&instance), NL_OK);
}

typedef struct { nl_capture_context *capture; } consumer;

static nl_status fail_with_record(nl_host *host, nl_plugin_id id, void *context)
{
    consumer *state = context;
    const nl_capture_observation observation = {.frequency_hz = UINT32_C(2400000000), .profile = "startup"};
    (void)host; (void)id;
    STATUS(nl_capture_submit(state->capture, &observation), NL_OK);
    return NL_ERR_FORMAT;
}

static void failed_startup_cleanup(void)
{
    char buffer[1024];
    nl_capture_context capture;
    nl_capture_config config = {.buffer = buffer, .capacity = sizeof(buffer), .output = output};
    nl_host host;
    nl_module service, application;
    const nl_module *manifest[2];
    nl_module_instance instances[2] = {{0}};
    const char *requires[] = {"capture"};
    consumer state = {.capture = &capture};
    sink out = {.capture = &capture, .result = NL_ERR_FULL};
    config.output_context = &out;
    STATUS(nl_host_init_plugins(&host, 1, 100), NL_OK);
    STATUS(nl_capture_init(&capture, &config), NL_OK);
    service = nl_capture_module(&capture);
    application = (nl_module){.name = "failing-consumer", .version = "1", .kind = NL_MODULE_APPLICATION,
        .requires = requires, .require_count = 1,
        .hooks = {.start = fail_with_record, .context = &state}};
    manifest[0] = &application; manifest[1] = &service;
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_ERR_FORMAT);
    CHECK(!instances[0].active && !instances[1].active);
    CHECK(!capture.pending && capture.host == NULL && capture.plugin == NL_PLUGIN_ID_NONE);
    CHECK(buffer[0] == '\0' && out.calls == 0 && !capture.have_timestamp);
    service.hooks = nl_capture_plugin(NULL);
    STATUS(nl_module_register(&host, &service, &instances[1]), NL_ERR_ARGUMENT);
    CHECK(!instances[1].active && capture.host == NULL);
    service = nl_capture_module(&capture);
    STATUS(nl_module_register(&host, &service, &instances[1]), NL_OK);
    STATUS(nl_module_unregister(&instances[1]), NL_OK);
}

int main(int argc, char **argv)
{
    bool emit = argc == 2 && strcmp(argv[1], "--emit-json") == 0;
    validation_and_capacity(emit);
    golden_and_backpressure(emit);
    timestamps_and_ownership();
    preserve_all_payload_bytes();
    failed_startup_cleanup();
    return EXIT_SUCCESS;
}
