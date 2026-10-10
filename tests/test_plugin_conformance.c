/* SPDX-License-Identifier: GPL-3.0-only */
#include "test.h"
#include "nova_link/plugin_conformance.h"
#include "nova_link/counter_plugin.h"
#include "nova_link/radio_plugin.h"
#include "nova_link/logger_plugin.h"
#include "nova_link/multiverse_plugin.h"
#include "nova_link/config_plugin.h"
#include "nova_link/capture_plugin.h"

typedef enum { SUBJECT_COUNTER, SUBJECT_RADIO, SUBJECT_LOGGER, SUBJECT_MULTIVERSE,
               SUBJECT_CONFIGURATION, SUBJECT_CAPTURE } subject_kind;

typedef struct {
    nl_radio radio;
    unsigned starts, stops;
    uint64_t attempts, accepted;
    bool started, pressure, fail_commit, immutable;
    nl_frame rejected, accepted_frames[8];
    bool has_rejected;
} actual_backend;

typedef struct {
    subject_kind kind;
    nl_conformance_case test_case;
    unsigned lifetime, observed_logs;
    actual_backend backend;
    nl_radio_link link;
    nl_counter_context counter;
    nl_logger_context logger;
    nl_multiverse_context multiverse;
    nova_dmx_frame_t levels;
    nl_config_context configuration;
    nl_config_entry entries[2];
    nl_capture_context capture;
    char capture_buffer[512], capture_rejected[512], capture_accepted[512];
    size_t capture_rejected_length, capture_accepted_length;
    uint64_t capture_attempts, capture_accepts;
    bool capture_reject, capture_immutable;
    nl_module subject, transport;
} factory_fixture;

static const nl_config_field fields[] = {
    {.key = "budget", .type = NL_CONFIG_UINT, .required = true, .minimum = 1, .maximum = 100},
    {.key = "enabled", .type = NL_CONFIG_BOOL, .required = true}
};
static const nl_config_section schema = {
    .name = "plugin", .required = true, .fields = fields, .field_count = 2
};
static const char initial_configuration[] = "[plugin]\nbudget=23\nenabled=true\n";
static const char restarted_configuration[] = "[plugin]\nbudget=57\nenabled=false\n";

static bool same_frame(const nl_frame *left, const nl_frame *right)
{
    uint8_t a[NL_FRAME_MAX], b[NL_FRAME_MAX];
    size_t asize = 0, bsize = 0;
    return nl_frame_encode(left, a, sizeof(a), &asize) == NL_OK &&
        nl_frame_encode(right, b, sizeof(b), &bsize) == NL_OK &&
        asize == bsize && memcmp(a, b, asize) == 0;
}

static void drain_radio(actual_backend *backend)
{
    nl_fragment discarded;
    unsigned zone;
    for (zone = 0; zone < NL_ZONE_COUNT; ++zone)
        while (nl_radio_pop_tx(&backend->radio, (uint8_t)zone, &discarded) == NL_OK) {}
    while (nl_radio_pull(&backend->radio, &discarded) == NL_OK) {}
}

static bool radio_empty(const actual_backend *backend)
{
    unsigned zone;
    if (backend->radio.rx.count != 0u) return false;
    for (zone = 0; zone < NL_ZONE_COUNT; ++zone)
        if (backend->radio.tx[zone].count != 0u) return false;
    return true;
}

static nl_status actual_start(void *context)
{
    actual_backend *backend = context;
    if (backend->started) return NL_ERR_BUSY;
    backend->started = true;
    ++backend->starts;
    return NL_OK;
}

static void actual_stop(void *context)
{
    actual_backend *backend = context;
    drain_radio(backend); /* Startup rollback cancels backend ownership. */
    backend->started = false;
    ++backend->stops;
}

static nl_status actual_can_stop(void *context)
{
    return radio_empty(context) ? NL_OK : NL_ERR_BUSY;
}

static nl_status actual_exchange(void *context, const nl_frame *request,
                                  nl_frame *response, nl_pull_token *token)
{
    actual_backend *backend = context;
    nl_frame decoded;
    nl_fragment completed;
    uint8_t wire[NL_FRAME_MAX];
    size_t size = 0;
    nl_status status = nl_frame_encode(request, wire, sizeof(wire), &size);
    if (status != NL_OK) return status;
    status = nl_frame_decode(wire, size, &decoded);
    if (status != NL_OK) return status;
    if (request->command == NL_COMMAND_PUSH) {
        ++backend->attempts;
        if (backend->accepted >= 8u) return NL_ERR_FULL;
    }
    status = nl_radio_handle_frame(&backend->radio, &decoded, response, token);
    if (request->command != NL_COMMAND_PUSH) return status;
    if (status != NL_OK) {
        if (!backend->has_rejected) {
            backend->rejected = decoded;
            backend->has_rejected = true;
        } else if (!same_frame(&backend->rejected, &decoded)) backend->immutable = false;
        return status;
    }
    backend->accepted_frames[backend->accepted] = decoded;
    ++backend->accepted;
    /* Complete local adapter ownership after real queue acceptance. No RF or
     * peer delivery is claimed. This keeps ordinary lifecycle cases stoppable. */
    status = nl_frame_to_fragment(&decoded, &completed);
    if (status != NL_OK) return status;
    return nl_radio_pop_tx(&backend->radio, completed.zone, &completed);
}

static nl_status actual_commit(void *context, const nl_frame *response, nl_pull_token token)
{
    actual_backend *backend = context;
    return backend->fail_commit ? NL_ERR_BUSY :
        nl_radio_commit_pull(&backend->radio, response, token);
}

static void observe(void *context, nl_log_event event, nl_status status,
                    nl_plugin_id plugin, uint8_t zone)
{
    factory_fixture *state = context;
    (void)event; (void)status; (void)plugin; (void)zone;
    ++state->observed_logs;
}

static const char *expected_capture(const factory_fixture *state)
{
    if (state->test_case == NL_CONFORMANCE_RESTART)
        return state->lifetime == 0u ?
            "{\"timestamp_us\":500,\"frequency_hz\":2400000000,\"profile\":\"candidate-phy\",\"stimulus\":\"unspecified\",\"payload_hex\":\"00aaff\",\"crc\":\"unknown\",\"rssi_dbm\":null}\n" :
            "{\"timestamp_us\":1,\"frequency_hz\":2400000000,\"profile\":\"candidate-phy\",\"stimulus\":\"unspecified\",\"payload_hex\":\"00aaff\",\"crc\":\"unknown\",\"rssi_dbm\":null}\n";
    return "{\"timestamp_us\":50,\"frequency_hz\":2400000000,\"profile\":\"candidate-phy\",\"stimulus\":\"unspecified\",\"payload_hex\":\"00aaff\",\"crc\":\"unknown\",\"rssi_dbm\":null}\n";
}

static nl_status capture_output(void *context, const char *jsonl, size_t length)
{
    factory_fixture *state = context;
    ++state->capture_attempts;
    if (length >= sizeof(state->capture_rejected)) return NL_ERR_SIZE;
    if (state->capture_rejected_length != 0u &&
        (length != state->capture_rejected_length ||
         memcmp(jsonl, state->capture_rejected, length) != 0)) state->capture_immutable = false;
    if (state->capture_reject) {
        if (state->capture_rejected_length == 0u) {
            memcpy(state->capture_rejected, jsonl, length);
            state->capture_rejected[length] = '\0';
            state->capture_rejected_length = length;
        }
        return NL_ERR_BUSY; /* Atomic sink: accepts no bytes on failure. */
    }
    if (state->capture_accepts != 0u) return NL_ERR_FULL;
    memcpy(state->capture_accepted, jsonl, length);
    state->capture_accepted[length] = '\0';
    state->capture_accepted_length = length;
    ++state->capture_accepts;
    return NL_OK;
}

static nl_status seed_capture(factory_fixture *state)
{
    static const uint8_t payload[] = {0x00, 0xAA, 0xFF};
    const nl_capture_observation observation = {
        .timestamp_us = state->test_case == NL_CONFORMANCE_RESTART ?
            (state->lifetime == 0u ? 500u : 1u) : 50u,
        .frequency_hz = UINT32_C(2400000000), .profile = "candidate-phy",
        .payload = payload, .payload_length = sizeof(payload), .crc = NL_CAPTURE_CRC_UNKNOWN
    };
    return nl_capture_submit(&state->capture, &observation);
}

static bool needs_radio(subject_kind kind)
{
    return kind == SUBJECT_COUNTER || kind == SUBJECT_RADIO || kind == SUBJECT_MULTIVERSE;
}

static nl_status build_fixture(factory_fixture *state, nl_conformance_fixture *fixture)
{
    nl_status status;
    if (needs_radio(state->kind)) {
        const nl_radio_link_config config = {
            .exchange = actual_exchange, .commit = actual_commit,
            .start = actual_start, .stop = actual_stop, .can_stop = actual_can_stop,
            .context = &state->backend, .poll_budget = 2
        };
        /* This is used only before first start or after inspected clean stop. */
        memset(&state->backend, 0, sizeof(state->backend));
        state->backend.immutable = true;
        status = nl_radio_init(&state->backend.radio, 0xFEu, 1000, 0, 1000000);
        if (status != NL_OK) return status;
        status = nl_radio_link_init(&state->link, &config);
        if (status != NL_OK) return status;
        state->transport = nl_radio_link_module(&state->link);
    }
    fixture->count = 1;
    fixture->subject = 0;
    fixture->max_attempts_per_poll = 1;
    fixture->recovery_polls = 1;
    switch (state->kind) {
    case SUBJECT_COUNTER:
        state->counter = (nl_counter_context){.transmitter = true, .zone = 1,
            .next_value = UINT32_C(0x11223344)};
        state->subject = nl_counter_module(&state->counter);
        break;
    case SUBJECT_RADIO:
        state->subject = state->transport;
        if (state->test_case == NL_CONFORMANCE_RESTART) {
            nl_fragment input = fragment(2, 1, state->lifetime == 0u ? 100u : 0u);
            static const uint8_t old_value[] = {0xAA, 0xBB, 0xCC, 0xDD};
            static const uint8_t fresh_value[] = {0x10, 0x20, 0x30, 0x40};
            state->counter = (nl_counter_context){.zone = 1};
            state->transport = nl_counter_module(&state->counter);
            input.payload_size = 4;
            memcpy(input.payload, state->lifetime == 0u ? old_value : fresh_value, 4);
            status = nl_radio_receive(&state->backend.radio, &input,
                                      state->lifetime == 0u ? 50u : 150u);
            if (status != NL_OK) return status;
        }
        break;
    case SUBJECT_LOGGER:
        status = nl_logger_init(&state->logger, observe, state);
        if (status != NL_OK) return status;
        state->observed_logs = 0;
        state->subject = nl_logger_module(&state->logger);
        break;
    case SUBJECT_MULTIVERSE: {
        const nl_multiverse_config config = {
            .role = NL_MULTIVERSE_TX, .zone = 1, .universe = 7,
            .session = UINT32_C(0x12345678) + state->lifetime,
            .interval_us = 1000000, .full_interval_us = 2000000, .chunks_per_tick = 2
        };
        unsigned i;
        memset(&state->levels, 0, sizeof(state->levels));
        state->levels.slot_count = 100;
        for (i = 0; i < state->levels.slot_count; ++i)
            state->levels.slots[i] = (uint8_t)(i * 17u + 3u);
        if (nl_multiverse_init(&state->multiverse, &config) != NOVA_MV_OK ||
            nl_multiverse_submit(&state->multiverse, &state->levels) != NOVA_MV_OK)
            return NL_ERR_CONFLICT;
        state->subject = nl_multiverse_module(&state->multiverse);
        fixture->max_attempts_per_poll = 2;
        fixture->expected_accepts = 2;
        break;
    }
    case SUBJECT_CONFIGURATION: {
        const char *text = state->lifetime == 0u ? initial_configuration : restarted_configuration;
        status = nl_config_parse(&state->configuration, text, strlen(text), state->entries,
                                 2, &schema, 1, NULL);
        if (status != NL_OK) return status;
        state->subject = nl_config_module(&state->configuration);
        break;
    }
    case SUBJECT_CAPTURE: {
        const nl_capture_config config = {.buffer = state->capture_buffer,
            .capacity = sizeof(state->capture_buffer), .output = capture_output,
            .output_context = state};
        status = nl_capture_init(&state->capture, &config);
        if (status != NL_OK) return status;
        state->capture_attempts = state->capture_accepts = 0;
        state->capture_rejected_length = state->capture_accepted_length = 0;
        state->capture_reject = false;
        state->capture_immutable = true;
        state->subject = nl_capture_module(&state->capture);
        fixture->recovery_polls = 4;
        break;
    }
    }
    fixture->modules[0] = &state->subject;
    if (state->kind == SUBJECT_COUNTER || state->kind == SUBJECT_MULTIVERSE ||
        (state->kind == SUBJECT_RADIO && state->test_case == NL_CONFORMANCE_RESTART)) {
        fixture->modules[1] = &state->transport; /* Deliberately unordered manifest. */
        fixture->count = 2;
    }
    return NL_OK;
}

static nl_status prepare(void *context, nl_conformance_fixture *fixture,
                         nl_conformance_case test_case)
{
    factory_fixture *state = context;
    subject_kind kind = state->kind;
    memset(state, 0, sizeof(*state)); /* Previous case already finished/stopped. */
    state->kind = kind;
    state->test_case = test_case;
    return build_fixture(state, fixture);
}

#define REQUIRE(condition) do { if (!(condition)) return NL_ERR_CONFLICT; } while (0)
static nl_status inspect(void *context, const nl_conformance_fixture *fixture,
                         nl_conformance_checkpoint checkpoint)
{
    factory_fixture *state = context;
    bool stopped = checkpoint == NL_CONFORMANCE_STOPPED || checkpoint == NL_CONFORMANCE_ROLLED_BACK;
    if (needs_radio(state->kind)) {
        if (stopped) {
            REQUIRE(state->link.host == NULL && !state->link.backend_started && !state->link.pending);
            REQUIRE(!state->backend.started && radio_empty(&state->backend));
            REQUIRE(state->backend.starts == state->backend.stops && state->backend.starts == 1u);
        } else {
            REQUIRE(state->link.host == &fixture->host && state->link.backend_started && state->backend.started);
            REQUIRE(fixture->host.send_context == &state->link);
        }
    }
    if (state->kind == SUBJECT_RADIO && state->test_case == NL_CONFORMANCE_RESTART && stopped) {
        REQUIRE(state->counter.deliveries == 1u);
        REQUIRE(state->counter.last_value == (state->lifetime == 0u ? UINT32_C(0xAABBCCDD) : UINT32_C(0x10203040)));
    }
    if (state->kind == SUBJECT_MULTIVERSE) {
        if (stopped) REQUIRE(!state->multiverse.active && state->multiverse.stopped && state->multiverse.owner == NULL);
        else REQUIRE(state->multiverse.active && state->multiverse.owner == &fixture->host);
    } else if (state->kind == SUBJECT_LOGGER) {
        if (stopped) REQUIRE(fixture->host.log == NULL && fixture->host.log_context == NULL);
        else REQUIRE(fixture->host.log == observe && fixture->host.log_context == state && state->observed_logs > 0u);
    } else if (state->kind == SUBJECT_CONFIGURATION) {
        uint64_t budget = 0;
        bool enabled = true;
        REQUIRE(state->configuration.valid && state->configuration.active == !stopped);
        REQUIRE(state->configuration.owner == (stopped ? NULL : &fixture->host));
        REQUIRE(nl_config_uint(&state->configuration, "plugin", "budget", &budget) == NL_OK);
        REQUIRE(nl_config_bool(&state->configuration, "plugin", "enabled", &enabled) == NL_OK);
        REQUIRE(budget == (state->lifetime == 0u ? 23u : 57u) && enabled == (state->lifetime == 0u));
        if (!stopped) {
            nl_config_context saved = state->configuration;
            nl_config_entry saved_entries[2];
            memcpy(saved_entries, state->entries, sizeof(saved_entries));
            REQUIRE(nl_config_parse(&state->configuration, "bad", 3, state->entries,
                                    2, &schema, 1, NULL) == NL_ERR_BUSY);
            REQUIRE(memcmp(&saved, &state->configuration, sizeof(saved)) == 0);
            REQUIRE(memcmp(saved_entries, state->entries, sizeof(saved_entries)) == 0);
        }
    }
    if (state->kind == SUBJECT_CAPTURE) {
        if (stopped) {
            REQUIRE(state->capture.host == NULL && !nl_capture_pending(&state->capture));
            REQUIRE(!state->capture.have_timestamp && !state->capture.outputting && state->capture.pending_length == 0u);
            REQUIRE(state->capture_buffer[0] == '\0');
            if (checkpoint == NL_CONFORMANCE_ROLLED_BACK)
                REQUIRE(state->capture_attempts == 0u && state->capture_accepts == 0u);
        } else REQUIRE(state->capture.host == &fixture->host && !state->capture.outputting);
        if (checkpoint == NL_CONFORMANCE_BLOCKED) {
            REQUIRE(nl_capture_pending(&state->capture) && state->capture_reject);
            REQUIRE(state->capture.pending_length == strlen(expected_capture(state)));
            REQUIRE(strcmp(state->capture_buffer, expected_capture(state)) == 0);
            REQUIRE(state->capture.have_timestamp && state->capture.last_timestamp_us == 50u);
            REQUIRE(state->capture.last_status == NL_ERR_BUSY && state->capture_accepts == 0u);
            REQUIRE(state->capture_immutable && strcmp(state->capture_rejected, expected_capture(state)) == 0);
        }
        if (checkpoint == NL_CONFORMANCE_RECOVERED || checkpoint == NL_CONFORMANCE_RESTARTED ||
            (checkpoint == NL_CONFORMANCE_STOPPED && state->test_case == NL_CONFORMANCE_RESTART)) {
            REQUIRE(!nl_capture_pending(&state->capture) && state->capture_accepts == 1u);
            REQUIRE(state->capture_accepted_length == strlen(expected_capture(state)));
            REQUIRE(strcmp(state->capture_accepted, expected_capture(state)) == 0 && state->capture_immutable);
        }
        if (checkpoint == NL_CONFORMANCE_RESTARTED) {
            REQUIRE(state->capture_attempts == 1u && state->capture.have_timestamp);
            REQUIRE(state->capture.last_timestamp_us == 1u && state->capture.last_status == NL_OK);
        }
    }
    if (checkpoint == NL_CONFORMANCE_BLOCKED && state->kind == SUBJECT_RADIO) {
        nl_frame actual;
        nl_pull_token token = 0;
        REQUIRE(state->link.pending && state->link.settled && state->backend.radio.rx.count == 1u);
        REQUIRE(nl_radio_prepare_pull(&state->backend.radio, &actual, &token) == NL_OK);
        REQUIRE(token == state->link.pending_token && same_frame(&actual, &state->link.pending_response));
        REQUIRE(state->link.stats.commits == 0u && state->link.stats.rx_discarded == 1u);
    } else if (checkpoint == NL_CONFORMANCE_BLOCKED && state->kind != SUBJECT_CAPTURE) {
        REQUIRE(state->backend.pressure && state->backend.radio.tx[1].count == NL_RADIO_TX_DEPTH);
        REQUIRE(state->backend.immutable && state->backend.has_rejected && state->backend.accepted == 0u);
        REQUIRE(fixture->host.next_sequence[1] == 0u);
        if (state->kind == SUBJECT_COUNTER) {
            REQUIRE(state->counter.next_value == UINT32_C(0x11223344) && state->counter.last_status == NL_ERR_FULL);
        } else {
            REQUIRE(state->multiverse.tx.active && !state->multiverse.tx.has_baseline);
            REQUIRE(state->multiverse.tx.pending.offset == 0u && state->multiverse.tx.pending.sequence == 0u);
            REQUIRE(state->multiverse.tx.frozen.slot_count == state->levels.slot_count);
            REQUIRE(memcmp(state->multiverse.tx.frozen.slots, state->levels.slots, state->levels.slot_count) == 0);
        }
    }
    if (checkpoint == NL_CONFORMANCE_RECOVERED && state->kind != SUBJECT_CAPTURE) {
        REQUIRE(state->backend.immutable && radio_empty(&state->backend));
        REQUIRE(same_frame(&state->backend.rejected, &state->backend.accepted_frames[0]));
        if (state->kind == SUBJECT_COUNTER) {
            nl_fragment accepted;
            static const uint8_t expected[] = {0x11, 0x22, 0x33, 0x44};
            REQUIRE(state->counter.next_value == UINT32_C(0x11223345) && state->counter.last_status == NL_OK);
            REQUIRE(nl_frame_to_fragment(&state->backend.accepted_frames[0], &accepted) == NL_OK);
            REQUIRE(accepted.payload_size == 4u && memcmp(accepted.payload, expected, 4) == 0);
            REQUIRE(fixture->host.next_sequence[1] == 1u);
        } else {
            nova_dmx_frame_t rebuilt = {0};
            unsigned i;
            for (i = 0; i < 2u; ++i) {
                nl_fragment accepted;
                nova_mv_packet_t packet;
                REQUIRE(nl_frame_to_fragment(&state->backend.accepted_frames[i], &accepted) == NL_OK);
                REQUIRE(nl_multiverse_payload_decode(accepted.payload, accepted.payload_size, &packet) == NOVA_MV_OK);
                REQUIRE(accepted.sequence == (uint8_t)i && packet.sequence == 0u && packet.kind == NOVA_MV_FULL);
                REQUIRE(packet.session == state->multiverse.config.session && packet.slot_count == 100u);
                REQUIRE(packet.offset == (i == 0u ? 0u : NL_MULTIVERSE_CHUNK_SLOTS));
                REQUIRE(packet.count == (i == 0u ? NL_MULTIVERSE_CHUNK_SLOTS : 28u));
                memcpy(rebuilt.slots + packet.offset, packet.levels, packet.count);
            }
            REQUIRE(memcmp(rebuilt.slots, state->levels.slots, state->levels.slot_count) == 0);
            REQUIRE(!state->multiverse.tx.active && state->multiverse.tx.has_baseline);
            REQUIRE(state->multiverse.tx.stats.updates == 1u && state->multiverse.tx.stats.packets == 2u);
            REQUIRE(fixture->host.next_sequence[1] == 2u);
        }
    }
    if (checkpoint == NL_CONFORMANCE_RESTARTED) {
        REQUIRE(state->lifetime == 1u);
        if (needs_radio(state->kind)) {
            REQUIRE(radio_empty(&state->backend) && !state->link.pending);
            REQUIRE(state->backend.accepted == state->link.stats.tx_accepted);
        }
        if (state->kind == SUBJECT_RADIO) {
            REQUIRE(state->backend.accepted == 0u && state->backend.attempts == 0u);
            REQUIRE(fixture->host.next_sequence[1] == 0u);
            REQUIRE(state->link.stats.rx_delivered == 1u && state->link.stats.commits == 1u);
            REQUIRE(state->link.stats.rx_discarded == 0u && state->counter.deliveries == 1u);
            REQUIRE(state->counter.last_value == UINT32_C(0x10203040));
            REQUIRE(fixture->host.streams.entries[2][1].seen && fixture->host.streams.entries[2][1].sequence == 0u);
            REQUIRE(state->backend.radio.streams.entries[2][1].seen && state->backend.radio.streams.entries[2][1].sequence == 0u);
        }
        if (state->kind == SUBJECT_COUNTER) {
            nl_fragment accepted;
            static const uint8_t expected[] = {0x11, 0x22, 0x33, 0x44};
            REQUIRE(state->counter.next_value == UINT32_C(0x11223345));
            REQUIRE(state->backend.accepted == 1u && state->backend.attempts == 1u);
            REQUIRE(nl_frame_to_fragment(&state->backend.accepted_frames[0], &accepted) == NL_OK);
            REQUIRE(accepted.sequence == 0u && accepted.payload_size == 4u);
            REQUIRE(memcmp(accepted.payload, expected, sizeof(expected)) == 0);
            REQUIRE(fixture->host.next_sequence[1] == 1u);
        }
        if (state->kind == SUBJECT_MULTIVERSE) {
            unsigned i;
            REQUIRE(state->multiverse.config.session == UINT32_C(0x12345679));
            REQUIRE(!state->multiverse.tx.active && state->multiverse.tx.has_baseline);
            REQUIRE(state->multiverse.tx.stats.updates == 1u && state->backend.accepted == 2u);
            REQUIRE(fixture->host.next_sequence[1] == 2u);
            for (i = 0; i < 2u; ++i) {
                nl_fragment accepted;
                nova_mv_packet_t packet;
                REQUIRE(nl_frame_to_fragment(&state->backend.accepted_frames[i], &accepted) == NL_OK);
                REQUIRE(accepted.sequence == (uint8_t)i);
                REQUIRE(nl_multiverse_payload_decode(accepted.payload, accepted.payload_size, &packet) == NOVA_MV_OK);
                REQUIRE(packet.session == UINT32_C(0x12345679) && packet.sequence == 0u);
                REQUIRE(packet.offset == (i == 0u ? 0u : NL_MULTIVERSE_CHUNK_SLOTS));
                REQUIRE(memcmp(packet.levels, state->levels.slots + packet.offset, packet.count) == 0);
            }
        }
    }
    return NL_OK;
}
#undef REQUIRE

static nl_status control(void *context, nl_conformance_fixture *fixture,
                         nl_conformance_action action)
{
    factory_fixture *state = context;
    nl_fragment queued = fragment(2, 1, 0);
    nl_status status;
    unsigned i;
    if (state->kind == SUBJECT_CAPTURE) {
        switch (action) {
        case NL_CONFORMANCE_PRESSURE_ON:
            state->capture_reject = true;
            return NL_OK;
        case NL_CONFORMANCE_PRESSURE_OFF:
            state->capture_reject = false;
            return NL_OK;
        case NL_CONFORMANCE_SEED_WORK:
            return seed_capture(state);
        case NL_CONFORMANCE_PENDING_ON:
            state->capture_reject = true;
            status = seed_capture(state);
            if (status != NL_OK) return status;
            return nl_capture_flush(&state->capture) == NL_ERR_BUSY ? NL_OK : NL_ERR_CONFLICT;
        case NL_CONFORMANCE_PENDING_OFF:
            state->capture_reject = false;
            return nl_capture_flush(&state->capture);
        }
    }
    switch (action) {
    case NL_CONFORMANCE_PRESSURE_ON:
        state->backend.pressure = true;
        for (i = 0; i < NL_RADIO_TX_DEPTH; ++i) {
            queued.sequence = (uint8_t)i;
            status = nl_radio_enqueue(&state->backend.radio, &queued);
            if (status != NL_OK) return status;
        }
        return NL_OK;
    case NL_CONFORMANCE_PRESSURE_OFF:
        drain_radio(&state->backend);
        state->backend.pressure = false;
        return NL_OK;
    case NL_CONFORMANCE_SEED_WORK:
        /* Both factories were seeded through their real APIs before startup. */
        return NL_OK;
    case NL_CONFORMANCE_PENDING_ON:
        state->backend.fail_commit = true;
        status = nl_radio_receive(&state->backend.radio, &queued, 50);
        return status == NL_OK ? nl_host_poll(&fixture->host, 100) : status;
    case NL_CONFORMANCE_PENDING_OFF:
        state->backend.fail_commit = false;
        return nl_host_poll(&fixture->host, 200);
    }
    return NL_ERR_ARGUMENT;
}

static nl_status measure(void *context, const nl_conformance_fixture *fixture,
                         nl_conformance_metrics *metrics)
{
    factory_fixture *state = context;
    (void)fixture;
    metrics->attempts = state->kind == SUBJECT_CAPTURE ? state->capture_attempts : state->backend.attempts;
    metrics->accepted = state->kind == SUBJECT_CAPTURE ? state->capture_accepts : state->backend.accepted;
    return NL_OK;
}

static nl_status reinitialize(void *context, nl_conformance_fixture *fixture)
{
    factory_fixture *state = context;
    if (needs_radio(state->kind) && (state->backend.started || !radio_empty(&state->backend) || state->link.pending))
        return NL_ERR_BUSY;
    if (state->multiverse.active || state->configuration.active || state->capture.host != NULL ||
        nl_capture_pending(&state->capture)) return NL_ERR_BUSY;
    ++state->lifetime;
    return build_fixture(state, fixture);
}

static nl_status seed_restart_work(void *context, nl_conformance_fixture *fixture)
{
    factory_fixture *state = context;
    (void)fixture;
    return state->kind == SUBJECT_CAPTURE ? seed_capture(state) : NL_OK;
}

static void finish(void *context, nl_conformance_fixture *fixture)
{
    factory_fixture *state = context;
    if (needs_radio(state->kind)) {
        state->backend.fail_commit = false;
        if (state->link.pending && state->link.host != NULL) {
            /* Drain the held receipt through the actual commit path first. */
            STATUS(nl_host_poll(&fixture->host, fixture->host.callback_now_us + 1u), NL_OK);
        }
        drain_radio(&state->backend);
    }
    if (state->kind == SUBJECT_CAPTURE && nl_capture_pending(&state->capture)) {
        state->capture_reject = false;
        STATUS(nl_capture_flush(&state->capture), NL_OK);
    }
    STATUS(nl_modules_stop(fixture->instances, fixture->count), NL_OK);
    if (needs_radio(state->kind)) CHECK(!state->backend.started && !state->link.pending && radio_empty(&state->backend));
    CHECK(!state->multiverse.active && !state->configuration.active && state->capture.host == NULL);
    CHECK(!nl_capture_pending(&state->capture));
}

static void report(void *context, const char *adapter, nl_conformance_case test_case,
                    nl_status status, const char *detail)
{
    (void)context;
    printf("%s: %s: %s (%s)\n", adapter, nl_conformance_case_name(test_case),
           status == NL_OK ? "exercised" : status == NL_ERR_UNSUPPORTED ? "skipped" : "FAILED", detail);
}

int main(void)
{
    static const struct { const char *name; subject_kind kind; unsigned capabilities; unsigned skipped; } subjects[] = {
        {"counter", SUBJECT_COUNTER, NL_CONFORMANCE_CAN_BACKPRESSURE | NL_CONFORMANCE_CAN_RESTART, 1},
        {"radio-link", SUBJECT_RADIO, NL_CONFORMANCE_CAN_PENDING | NL_CONFORMANCE_CAN_RESTART, 1},
        {"logger", SUBJECT_LOGGER, NL_CONFORMANCE_CAN_RESTART, 2},
        {"multiverse", SUBJECT_MULTIVERSE, NL_CONFORMANCE_CAN_BACKPRESSURE | NL_CONFORMANCE_CAN_RESTART, 1},
        {"configuration", SUBJECT_CONFIGURATION, NL_CONFORMANCE_CAN_RESTART, 2},
        {"capture", SUBJECT_CAPTURE, NL_CONFORMANCE_CAN_PENDING | NL_CONFORMANCE_CAN_BACKPRESSURE | NL_CONFORMANCE_CAN_RESTART, 0}
    };
    unsigned exercised = 0, skipped = 0;
    size_t i;
    for (i = 0; i < sizeof(subjects) / sizeof(subjects[0]); ++i) {
        factory_fixture state = {0};
        nl_conformance_result result;
        const nl_conformance_adapter adapter = {
            .name = subjects[i].name, .capabilities = subjects[i].capabilities,
            .context = &state, .prepare = prepare, .inspect = inspect, .control = control,
            .measure = measure, .reinitialize = reinitialize, .seed_restart_work = seed_restart_work,
            .finish = finish
        };
        state.kind = subjects[i].kind;
        STATUS(nl_plugin_conformance_run(&adapter, &result, report, NULL), NL_OK);
        CHECK(result.failed == 0u && result.skipped == subjects[i].skipped);
        CHECK(result.passed + result.skipped == NL_CONFORMANCE_CASE_COUNT);
        CHECK(result.alias_checks == 1u && result.alias_skipped == 0u);
        exercised += result.passed;
        skipped += result.skipped;
    }
    CHECK(exercised == 35u && skipped == 7u);
    printf("Six actual plugin factories: %u exercised contracts; %u explicitly skipped.\n", exercised, skipped);
    return EXIT_SUCCESS;
}
