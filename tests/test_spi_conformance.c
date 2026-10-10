/* SPDX-License-Identifier: GPL-3.0-only */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/plugin_conformance.h"
#include "nova_link/spi_virtual.h"

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(EXIT_FAILURE); } } while (0)

typedef struct {
    bool transport_subject, seeded, delivered;
    unsigned lifetime;
    nl_conformance_case test_case;
    nl_radio radio;
    nl_spi_slave slave;
    nl_spi_virtual device;
    nl_spi_backend backend;
    nl_radio_link link;
    nl_radio_link_config config;
    nl_module modules[2];
    nl_fragment workload;
    uint8_t retained[NL_FRAME_MAX];
    size_t retained_size;
} spi_fixture;

static nl_status build(spi_fixture *state, nl_conformance_fixture *fixture)
{
    nl_spi_driver driver;
    nl_status status;
    state->seeded = state->delivered = false;
    status = nl_radio_init(&state->radio, 2u, 1000u, 0u, 0u);
    if (status != NL_OK) return status;
    status = nl_spi_slave_init(&state->slave, &state->radio);
    if (status != NL_OK) return status;
    status = nl_spi_virtual_init(&state->device, &state->slave, 10u);
    if (status != NL_OK) return status;
    driver = nl_spi_virtual_driver(&state->device);
    status = nl_spi_backend_init(&state->backend, &driver);
    if (status != NL_OK) return status;
    status = nl_spi_backend_link_config(&state->backend, 2u, &state->config);
    if (status != NL_OK) return status;
    status = nl_radio_link_init(&state->link, &state->config);
    if (status != NL_OK) return status;
    state->modules[0] = nl_spi_backend_module(&state->backend);
    state->modules[1] = nl_spi_backend_link_module(&state->link);
    fixture->modules[0] = &state->modules[0];
    fixture->modules[1] = &state->modules[1];
    fixture->count = 2u;
    fixture->subject = state->transport_subject ? 1u : 0u;
    fixture->max_attempts_per_poll = 1u;
    fixture->recovery_polls = 2u;
    fixture->restart_polls = 2u;
    state->workload = (nl_fragment){.origin = 1u, .zone = 1u,
        .sequence = state->lifetime == 0u ? 17u : 0u, .payload_size = 5u,
        .payload = {0xAA, 0x00, 0xFF, 0x81, 0x42}};
    state->workload.payload[4] = state->lifetime == 0u ? 0x42u : 0x73u;
    return NL_OK;
}

static nl_status prepare(void *context, nl_conformance_fixture *fixture,
                         nl_conformance_case test_case)
{
    spi_fixture *state = context;
    state->test_case = test_case;
    state->lifetime = 0u;
    return build(state, fixture);
}

static nl_status seed(void *context, nl_conformance_fixture *fixture)
{
    spi_fixture *state = context;
    nl_frame request;
    nl_status status;
    (void)fixture;
    status = nl_frame_from_fragment(NL_COMMAND_PUSH, &state->workload, &request);
    if (status != NL_OK) return status;
    status = nl_frame_encode(&request, state->retained, sizeof(state->retained),
                             &state->retained_size);
    if (status != NL_OK) return status;
    /* Exercise the live transport's installed host send callback, rather than
     * synthesizing backend counters or calling a replacement implementation. */
    status = state->link.host->send(state->link.host->send_context, &state->workload);
    if (status == NL_OK) state->seeded = true;
    return status;
}

static nl_status drain(spi_fixture *state)
{
    nl_fragment discarded;
    while (state->radio.tx[1].count != 0u) {
        nl_status status = nl_radio_pop_tx(&state->radio, 1u, &discarded);
        if (status != NL_OK) return status;
    }
    return NL_OK;
}

static nl_status verify_delivery(spi_fixture *state)
{
    nl_fragment received;
    if (state->delivered) return state->radio.tx[1].count == 0u ? NL_OK : NL_ERR_CONFLICT;
    if (state->backend.stats.tx_accepted != 1u || state->backend.stats.tx_completed != 1u ||
        state->radio.tx[1].count != 1u || state->backend.tx_pending ||
        nl_radio_pop_tx(&state->radio, 1u, &received) != NL_OK ||
        received.origin != state->workload.origin || received.zone != state->workload.zone ||
        received.sequence != state->workload.sequence ||
        received.payload_size != state->workload.payload_size ||
        memcmp(received.payload, state->workload.payload, received.payload_size) != 0)
        return NL_ERR_CONFLICT;
    state->delivered = true;
    return NL_OK;
}

static nl_status inspect(void *context, const nl_conformance_fixture *fixture,
                         nl_conformance_checkpoint checkpoint)
{
    spi_fixture *state = context;
    if (checkpoint == NL_CONFORMANCE_STOPPED || checkpoint == NL_CONFORMANCE_ROLLED_BACK) {
        if (state->backend.running || state->backend.started || state->backend.host != NULL ||
            state->backend.tx_pending || state->backend.inflight || state->backend.rx_pending ||
            state->backend.abort_pending || state->device.started ||
            !nl_spi_virtual_drained(&state->device) || state->link.host != NULL || state->link.pending)
            return NL_ERR_CONFLICT;
        if (state->seeded) return verify_delivery(state);
        return state->radio.tx[1].count == 0u ? NL_OK : NL_ERR_CONFLICT;
    }
    if (!state->backend.running || state->backend.host != &fixture->host ||
        !state->device.started || state->link.host != &fixture->host ||
        fixture->host.send_context != &state->link) return NL_ERR_CONFLICT;
    if (checkpoint == NL_CONFORMANCE_BLOCKED) {
        if (!state->backend.tx_pending || state->backend.tx_size != state->retained_size ||
            memcmp(state->backend.tx, state->retained, state->retained_size) != 0 ||
            state->backend.stats.tx_accepted != 1u || state->backend.stats.tx_completed != 0u ||
            state->workload.sequence != 17u) return NL_ERR_CONFLICT;
        if (state->test_case == NL_CONFORMANCE_BACKPRESSURE &&
            state->radio.tx[1].count != NL_RADIO_TX_DEPTH) return NL_ERR_CONFLICT;
    }
    if (checkpoint == NL_CONFORMANCE_RECOVERED || checkpoint == NL_CONFORMANCE_RESTARTED)
        return verify_delivery(state);
    return NL_OK;
}

static nl_status control(void *context, nl_conformance_fixture *fixture,
                         nl_conformance_action action)
{
    spi_fixture *state = context;
    switch (action) {
    case NL_CONFORMANCE_PENDING_ON:
    case NL_CONFORMANCE_SEED_WORK:
        return seed(context, fixture);
    case NL_CONFORMANCE_PENDING_OFF:
        if (nl_host_poll(&fixture->host, 1u) != NL_OK ||
            nl_host_poll(&fixture->host, 11u) != NL_OK) return NL_ERR_CONFLICT;
        return verify_delivery(state);
    case NL_CONFORMANCE_PRESSURE_ON:
        for (unsigned i = 0; i < NL_RADIO_TX_DEPTH; ++i) {
            nl_fragment filler = {.origin = 2u, .zone = 1u, .sequence = (uint8_t)i};
            nl_status status = nl_radio_enqueue(&state->radio, &filler);
            if (status != NL_OK) return status;
        }
        return NL_OK;
    case NL_CONFORMANCE_PRESSURE_OFF:
        return drain(state);
    }
    return NL_ERR_ARGUMENT;
}

static nl_status measure(void *context, const nl_conformance_fixture *fixture,
                         nl_conformance_metrics *metrics)
{
    spi_fixture *state = context;
    (void)fixture;
    metrics->attempts = state->device.stats.begins;
    metrics->accepted = state->backend.stats.tx_completed;
    return NL_OK;
}

static nl_status reinitialize(void *context, nl_conformance_fixture *fixture)
{
    spi_fixture *state = context;
    if (!nl_spi_virtual_drained(&state->device) || state->backend.host != NULL ||
        state->radio.tx[1].count != 0u || !state->delivered) return NL_ERR_CONFLICT;
    ++state->lifetime;
    return build(state, fixture);
}

static void finish(void *context, nl_conformance_fixture *fixture)
{
    spi_fixture *state = context;
    /* Explicitly cancel test ownership if an assertion failed. Keep descriptors
     * and contexts alive until every remaining registration has stopped. */
    if (state->backend.host != NULL)
        state->modules[0].hooks.stop(&fixture->host, state->backend.plugin, &state->backend);
    (void)nl_modules_stop(fixture->instances, fixture->count);
    (void)drain(state);
}

static void report(void *context, const char *adapter, nl_conformance_case test_case,
                   nl_status status, const char *detail)
{
    (void)context;
    if (status != NL_OK)
        fprintf(stderr, "%s/%s: %s\n", adapter, nl_conformance_case_name(test_case), detail);
}

int main(void)
{
    for (unsigned subject = 0; subject < 2u; ++subject) {
        spi_fixture state = {.transport_subject = subject != 0u};
        const nl_conformance_adapter adapter = {
            .name = subject == 0u ? "actual-spi-backend" : "actual-spi-radio-link",
            .capabilities = NL_CONFORMANCE_CAN_PENDING | NL_CONFORMANCE_CAN_BACKPRESSURE |
                            NL_CONFORMANCE_CAN_RESTART,
            .context = &state, .prepare = prepare, .inspect = inspect, .control = control,
            .measure = measure, .reinitialize = reinitialize, .seed_restart_work = seed,
            .finish = finish};
        nl_conformance_result result;
        CHECK(nl_plugin_conformance_run(&adapter, &result, report, NULL) == NL_OK);
        CHECK(result.passed == NL_CONFORMANCE_CASE_COUNT && result.failed == 0u &&
              result.skipped == 0u && result.alias_checks == 1u);
    }
    puts("Actual SPI backend and radio-link: all 14 lifecycle, rollback, dependency, pending, bounded backpressure and fresh restart contracts passed.");
    return EXIT_SUCCESS;
}
