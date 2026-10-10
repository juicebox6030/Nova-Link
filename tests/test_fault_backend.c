/* SPDX-License-Identifier: GPL-3.0-only */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/fault_backend.h"

#define CHECK(value) do { if (!(value)) { fprintf(stderr, "line %d: %s\n", __LINE__, #value); exit(EXIT_FAILURE); } } while (0)
#define STATUS(value, wanted) CHECK((value) == (wanted))

static nl_fragment fragment(uint8_t sequence)
{
    nl_fragment result = {.origin = 1, .zone = 1, .sequence = sequence,
        .payload_size = 1, .payload = {sequence}};
    return result;
}

static nl_radio_link_config initialize(nl_fault_backend *backend, nl_fault_profile profile)
{
    nl_fault_options options;
    nl_radio_link_config config;
    STATUS(nl_fault_profile_options(profile, &options), NL_OK);
    STATUS(nl_fault_backend_init(backend, &options), NL_OK);
    config = nl_fault_backend_link_config(backend, 1);
    STATUS(config.start(config.context), NL_OK);
    return config;
}

static nl_status push(nl_radio_link_config *config, uint8_t sequence)
{
    nl_frame request, response;
    nl_pull_token token;
    nl_fragment value = fragment(sequence);
    STATUS(nl_frame_from_fragment(NL_COMMAND_PUSH, &value, &request), NL_OK);
    return config->exchange(config->context, &request, &response, &token);
}

static void test_profiles_and_rejected_ownership(void)
{
    nl_fault_options options;
    nl_fault_backend backend;
    nl_radio_link_config config;
    nl_fragment before, after;
    uint8_t old_bytes[NL_FRAGMENT_MAX], new_bytes[NL_FRAGMENT_MAX];
    size_t old_size, new_size;
    STATUS(nl_fault_profile_options((nl_fault_profile)99, &options), NL_ERR_ARGUMENT);
    STATUS(nl_fault_profile_options(NL_FAULT_CLEAN, NULL), NL_ERR_ARGUMENT);
    config = initialize(&backend, NL_FAULT_DISCONNECTED);
    STATUS(push(&config, 0), NL_ERR_BUSY);
    CHECK(backend.radio.tx[1].count == 0 && backend.stats.offline_pushes == 1);
    nl_fault_backend_set_connected(&backend, true);
    for (uint8_t sequence = 0; sequence < NL_RADIO_TX_DEPTH; ++sequence)
        STATUS(push(&config, sequence), NL_OK);
    STATUS(nl_radio_peek_tx(&backend.radio, 1, &before), NL_OK);
    STATUS(nl_fragment_encode(&before, old_bytes, sizeof(old_bytes), &old_size), NL_OK);
    STATUS(push(&config, 8), NL_ERR_FULL);
    STATUS(nl_radio_peek_tx(&backend.radio, 1, &after), NL_OK);
    STATUS(nl_fragment_encode(&after, new_bytes, sizeof(new_bytes), &new_size), NL_OK);
    CHECK(old_size == new_size && memcmp(old_bytes, new_bytes, old_size) == 0);
    CHECK(backend.stats.pushes == 8 && backend.stats.rejected_pushes == 2);
    STATUS(config.can_stop(config.context), NL_ERR_BUSY);
    STATUS(nl_fault_backend_restart(&backend), NL_ERR_BUSY);
    /* Direct stop models forced startup rollback, ordinary lifecycle vetoes it. */
    config.stop(config.context);
    CHECK(nl_fault_backend_drained(&backend) && backend.stats.canceled_pushes == 8);
    STATUS(nl_fault_backend_restart(&backend), NL_OK);
    STATUS(nl_fault_backend_set_time(&backend, 50), NL_OK);
    STATUS(nl_fault_backend_set_time(&backend, 49), NL_ERR_ARGUMENT);
    CHECK(backend.now == 50);
}

static void test_delayed_fifo_and_congestion(void)
{
    nl_fault_backend sender, receiver, third;
    nl_radio_link_config tx = initialize(&sender, NL_FAULT_CLEAN);
    nl_radio_link_config rx = initialize(&receiver, NL_FAULT_CLEAN);
    nl_radio_link_config other = initialize(&third, NL_FAULT_CLEAN);
    nl_fault_transfer transfer, competing;
    nl_fragment value, pulled;
    STATUS(nl_fault_transfer_init(&transfer, 400), NL_OK);
    STATUS(nl_fault_transfer_init(&competing, 0), NL_OK);
    for (uint8_t sequence = 0; sequence < NL_RADIO_RX_DEPTH; ++sequence) {
        value = fragment(sequence);
        STATUS(nl_radio_receive(&receiver.radio, &value, 0), NL_OK);
    }
    STATUS(push(&tx, 16), NL_OK);
    STATUS(nl_fault_transfer_step(&sender, &receiver, &transfer, 0), NL_ERR_BUSY);
    CHECK(transfer.pending && sender.in_flight && receiver.incoming == 1);
    STATUS(tx.can_stop(tx.context), NL_ERR_BUSY);
    STATUS(rx.can_stop(rx.context), NL_ERR_BUSY);
    STATUS(nl_fault_transfer_step(&sender, &third, &transfer, 0), NL_ERR_CONFLICT);
    STATUS(nl_fault_transfer_step(&sender, &receiver, &competing, 0), NL_ERR_BUSY);
    STATUS(nl_fault_transfer_step(&sender, &receiver, &transfer, 399), NL_ERR_BUSY);
    STATUS(nl_fault_transfer_step(&sender, &receiver, &transfer, 400), NL_ERR_FULL);
    CHECK(transfer.blocked == 1 && transfer.pending && sender.radio.tx[1].count == 1);
    nl_fault_backend_set_connected(&receiver, false);
    STATUS(nl_fault_transfer_step(&sender, &receiver, &transfer, 500), NL_ERR_BUSY);
    nl_fault_backend_set_connected(&receiver, true);
    STATUS(nl_radio_pull(&receiver.radio, &pulled), NL_OK);
    CHECK(pulled.sequence == 0);
    STATUS(nl_fault_transfer_step(&sender, &receiver, &transfer, 500), NL_OK);
    CHECK(transfer.completed == 1 && !transfer.pending && !sender.in_flight && receiver.incoming == 0);
    for (uint8_t sequence = 1; sequence <= NL_RADIO_RX_DEPTH; ++sequence) {
        STATUS(nl_radio_pull(&receiver.radio, &pulled), NL_OK);
        CHECK(pulled.sequence == sequence);
    }
    CHECK(nl_fault_backend_drained(&sender) && nl_fault_backend_drained(&receiver));
    STATUS(nl_fault_transfer_step(&sender, &receiver, &transfer, 499), NL_ERR_ARGUMENT);
    STATUS(nl_fault_transfer_step(&sender, &receiver, &transfer, 500), NL_ERR_EMPTY);
    tx.stop(tx.context); rx.stop(rx.context); other.stop(other.context);
}

static void test_receipts_restart_and_overflow(void)
{
    nl_fault_backend backend;
    nl_radio_link_config config = initialize(&backend, NL_FAULT_COMMIT_RETRY);
    const nl_frame pull = {.command = NL_COMMAND_PULL};
    nl_frame response, old_response;
    nl_pull_token token, old_token;
    nl_fragment value = fragment(0);
    STATUS(nl_radio_receive(&backend.radio, &value, 0), NL_OK);
    STATUS(config.exchange(config.context, &pull, &response, &token), NL_OK);
    old_response = response; old_token = token;
    for (unsigned i = 0; i < 3; ++i) {
        STATUS(config.commit(config.context, &response, token), NL_ERR_BUSY);
        CHECK(backend.radio.rx.count == 1 && backend.committing);
    }
    CHECK(backend.stats.commit_retries == 3);
    STATUS(nl_fault_backend_invalidate_receipt(&backend), NL_OK);
    CHECK(backend.stats.invalidations == 1 && !backend.committing);
    value = fragment(1);
    STATUS(nl_radio_receive(&backend.radio, &value, 0), NL_OK);
    STATUS(config.commit(config.context, &old_response, old_token), NL_ERR_STALE);
    CHECK(backend.radio.rx.count == 1);
    STATUS(config.exchange(config.context, &pull, &response, &token), NL_OK);
    CHECK(token > old_token);
    STATUS(config.commit(config.context, &old_response, old_token), NL_ERR_STALE);
    CHECK(backend.committing && backend.radio.rx.count == 1);
    response.data[response.data_size - 1] ^= 1u;
    STATUS(config.commit(config.context, &response, token), NL_ERR_CONFLICT);
    response = backend.receipt;
    STATUS(config.commit(config.context, &response, token), NL_OK);
    config.stop(config.context);
    STATUS(nl_fault_backend_restart(&backend), NL_OK);
    STATUS(config.start(config.context), NL_OK);
    value = fragment(0);
    STATUS(nl_radio_receive(&backend.radio, &value, 1), NL_OK);
    STATUS(config.exchange(config.context, &pull, &response, &token), NL_OK);
    CHECK(token > old_token && token > 2);
    STATUS(config.commit(config.context, &old_response, old_token), NL_ERR_STALE);
    CHECK(backend.radio.rx.count == 1);
    STATUS(config.commit(config.context, &response, token), NL_OK);
    backend.options.commit_delay_us = 1;
    STATUS(nl_fault_backend_set_time(&backend, UINT64_MAX), NL_OK);
    value = fragment(1);
    STATUS(nl_radio_receive(&backend.radio, &value, UINT64_MAX), NL_OK);
    STATUS(config.exchange(config.context, &pull, &response, &token), NL_ERR_SIZE);
    CHECK(!backend.committing && backend.radio.rx.count == 1);
    config.stop(config.context);
    CHECK(backend.stats.canceled_receipts == 1 && nl_fault_backend_drained(&backend));
    /* Token exhaustion remains exhausted across restart. */
    backend.radio.next_rx_token = UINT64_MAX;
    STATUS(nl_fault_backend_restart(&backend), NL_OK);
    STATUS(nl_radio_receive(&backend.radio, &value, UINT64_MAX), NL_ERR_SIZE);
}

static nl_status failing_start(nl_host *host, nl_plugin_id plugin, void *context)
{
    nl_radio_link_config *config = context;
    (void)host; (void)plugin;
    STATUS(push(config, 0), NL_OK);
    return NL_ERR_FORMAT;
}

static void test_transactional_rollback(void)
{
    nl_fault_backend backend;
    nl_fault_adapter binding;
    nl_fault_options options;
    nl_radio_link_config config;
    nl_radio_link link;
    nl_host host;
    nl_module_instance instances[2] = {{0}};
    const char *const requirements[] = {"radio-link"};
    nl_module failure = {.name = "failure", .version = "1", .kind = NL_MODULE_APPLICATION,
        .requires = requirements, .require_count = 1, .hooks = {.start = failing_start, .context = &config}};
    nl_module radio;
    const nl_module *manifest[] = {&failure, &radio};
    STATUS(nl_fault_profile_options(NL_FAULT_CLEAN, &options), NL_OK);
    STATUS(nl_fault_backend_init(&backend, &options), NL_OK);
    STATUS(nl_fault_adapter_init(&binding, &backend, 1), NL_OK);
    config = nl_fault_adapter_link_config(&binding);
    STATUS(nl_radio_link_init(&link, &config), NL_OK);
    radio = nl_radio_link_module(&link);
    STATUS(nl_host_init_plugins(&host, 1, 0), NL_OK);
    STATUS(nl_modules_start(&host, manifest, instances, 2), NL_ERR_FORMAT);
    CHECK(host.send == NULL && !backend.started && nl_fault_backend_drained(&backend));
    CHECK(backend.stats.pushes == 1 && backend.stats.canceled_pushes == 1 && backend.stats.stops == 1);
    STATUS(nl_fault_backend_restart(&backend), NL_OK);
}

static nl_status app_start(nl_host *host, nl_plugin_id plugin, void *context)
{
    (void)context;
    return nl_host_claim(host, plugin, 1, NL_ZONE_READ_ONLY);
}

static void app_receive(nl_host *host, nl_plugin_id plugin, const nl_fragment *value, void *context)
{
    unsigned *received = context;
    (void)host; (void)plugin; (void)value;
    ++*received;
}

static void test_direct_adapter_once(void)
{
    nl_fault_backend backend;
    nl_fault_options options;
    nl_fault_adapter adapter;
    nl_host host;
    nl_plugin_id app_id;
    unsigned received = 0;
    nl_plugin app = {.start = app_start, .receive = app_receive, .context = &received};
    nl_fragment value = fragment(0);
    STATUS(nl_fault_profile_options(NL_FAULT_COMMIT_RETRY, &options), NL_OK);
    STATUS(nl_fault_backend_init(&backend, &options), NL_OK);
    STATUS(nl_fault_adapter_init(&adapter, &backend, 1), NL_OK);
    STATUS(nl_fault_adapter_start(&adapter), NL_OK);
    STATUS(nl_host_init(&host, 2, 0, nl_fault_adapter_send, &adapter), NL_OK);
    STATUS(nl_host_register(&host, &app, &app_id), NL_OK);
    STATUS(nl_radio_receive(&backend.radio, &value, 0), NL_OK);
    for (uint64_t now = 0; now < 3; ++now) {
        nl_fault_adapter_poll(&host, now, &adapter);
        CHECK(received == 1 && adapter.pending && adapter.settled);
        STATUS(nl_fault_adapter_can_stop(&adapter), NL_ERR_BUSY);
    }
    STATUS(nl_fault_backend_invalidate_receipt(&backend), NL_OK);
    value = fragment(1);
    STATUS(nl_radio_receive(&backend.radio, &value, 3), NL_OK);
    nl_fault_adapter_poll(&host, 3, &adapter);
    CHECK(received == 1 && !adapter.pending && backend.radio.rx.count == 1);
    nl_fault_adapter_poll(&host, 4, &adapter);
    CHECK(received == 2 && !adapter.pending && adapter.stats.commit_abandoned == 1);
    CHECK(adapter.stats.rx_delivered == 2 && adapter.stats.commits == 1);
    STATUS(nl_fault_adapter_can_stop(&adapter), NL_OK);
    STATUS(nl_host_unregister(&host, app_id), NL_OK);
    nl_fault_adapter_stop(&adapter);
    STATUS(nl_fault_backend_restart(&backend), NL_OK);
}

static void test_transfer_overflow_and_immutable(void)
{
    nl_fault_backend sender, receiver;
    nl_radio_link_config tx = initialize(&sender, NL_FAULT_CLEAN);
    nl_radio_link_config rx = initialize(&receiver, NL_FAULT_CLEAN);
    nl_fault_transfer transfer;
    STATUS(nl_fault_transfer_init(&transfer, 1), NL_OK);
    STATUS(push(&tx, 0), NL_OK);
    STATUS(nl_fault_transfer_step(&sender, &receiver, &transfer, UINT64_MAX), NL_ERR_SIZE);
    CHECK(!transfer.pending && !sender.in_flight && receiver.incoming == 0);
    tx.stop(tx.context); rx.stop(rx.context);
    tx = initialize(&sender, NL_FAULT_CLEAN);
    rx = initialize(&receiver, NL_FAULT_CLEAN);
    STATUS(push(&tx, 0), NL_OK);
    STATUS(nl_fault_transfer_step(&sender, &receiver, &transfer, 0), NL_ERR_BUSY);
    sender.radio.tx_storage[1][sender.radio.tx[1].head].payload[0] ^= 1u;
    STATUS(nl_fault_transfer_step(&sender, &receiver, &transfer, 1), NL_ERR_CONFLICT);
    CHECK(transfer.pending && sender.radio.tx[1].count == 1 && receiver.radio.rx.count == 0);
    sender.radio.tx_storage[1][sender.radio.tx[1].head].payload[0] ^= 1u;
    STATUS(nl_fault_transfer_step(&sender, &receiver, &transfer, 1), NL_OK);
    tx.stop(tx.context); rx.stop(rx.context);
}

static void test_competing_adapter_cleanup(void)
{
    nl_fault_backend backend;
    nl_fault_options options;
    nl_fault_adapter owner, competitor;
    nl_fragment value = fragment(0);
    STATUS(nl_fault_profile_options(NL_FAULT_CLEAN, &options), NL_OK);
    STATUS(nl_fault_backend_init(&backend, &options), NL_OK);
    STATUS(nl_fault_adapter_init(&owner, &backend, 1), NL_OK);
    STATUS(nl_fault_adapter_init(&competitor, &backend, 1), NL_OK);
    STATUS(nl_fault_adapter_start(&owner), NL_OK);
    STATUS(nl_fault_adapter_send(&owner, &value), NL_OK);
    STATUS(nl_fault_adapter_start(&competitor), NL_ERR_BUSY);
    nl_fault_adapter_stop(&competitor); /* Failed lifecycle startup cleanup. */
    CHECK(owner.owns_backend && !competitor.owns_backend && backend.started);
    CHECK(backend.radio.tx[1].count == 1 && backend.stats.stops == 0);
    STATUS(nl_fault_adapter_can_stop(&owner), NL_ERR_BUSY);
    STATUS(nl_fault_adapter_send(&competitor, &value), NL_ERR_NOT_FOUND);
    nl_fault_adapter_stop(&owner); /* Force rollback of owner's queued work. */
    CHECK(nl_fault_backend_drained(&backend) && backend.stats.canceled_pushes == 1);
    STATUS(nl_fault_adapter_start(&competitor), NL_OK);
    STATUS(nl_fault_adapter_can_stop(&competitor), NL_OK);
    nl_fault_adapter_stop(&competitor);
}

static void test_competing_framed_binding_cleanup(void)
{
    nl_fault_backend backend;
    nl_fault_options options;
    nl_fault_adapter bindings[2];
    nl_radio_link links[2];
    nl_radio_link_config configs[2];
    nl_host hosts[2];
    nl_module modules[2];
    nl_module_instance instances[2] = {{0}};
    nl_fragment value = fragment(0), discarded;
    STATUS(nl_fault_profile_options(NL_FAULT_CLEAN, &options), NL_OK);
    STATUS(nl_fault_backend_init(&backend, &options), NL_OK);
    for (unsigned index = 0; index < 2; ++index) {
        STATUS(nl_fault_adapter_init(&bindings[index], &backend, 1), NL_OK);
        configs[index] = nl_fault_adapter_link_config(&bindings[index]);
        STATUS(nl_radio_link_init(&links[index], &configs[index]), NL_OK);
        modules[index] = nl_radio_link_module(&links[index]);
        STATUS(nl_host_init_plugins(&hosts[index], (uint8_t)(index + 1u), 0), NL_OK);
    }
    STATUS(nl_module_register(&hosts[0], &modules[0], &instances[0]), NL_OK);
    STATUS(nl_fault_adapter_send(&bindings[0], &value), NL_OK);
    STATUS(nl_module_register(&hosts[1], &modules[1], &instances[1]), NL_ERR_BUSY);
    CHECK(hosts[1].send == NULL && !instances[1].active && !bindings[1].owns_backend);
    CHECK(backend.started && backend.radio.tx[1].count == 1 && backend.stats.stops == 0);
    CHECK(hosts[0].send != NULL && instances[0].active && bindings[0].owns_backend);
    STATUS(nl_module_unregister(&instances[0]), NL_ERR_BUSY);
    STATUS(nl_radio_pop_tx(&backend.radio, 1, &discarded), NL_OK);
    STATUS(nl_module_unregister(&instances[0]), NL_OK);
    CHECK(backend.stats.stops == 1 && nl_fault_backend_drained(&backend));
    STATUS(nl_fault_backend_restart(&backend), NL_OK);
    STATUS(nl_module_register(&hosts[1], &modules[1], &instances[1]), NL_OK);
    STATUS(nl_module_unregister(&instances[1]), NL_OK);
}

int main(void)
{
    test_profiles_and_rejected_ownership();
    test_delayed_fifo_and_congestion();
    test_receipts_restart_and_overflow();
    test_transactional_rollback();
    test_direct_adapter_once();
    test_transfer_overflow_and_immutable();
    test_competing_adapter_cleanup();
    test_competing_framed_binding_cleanup();
    puts("deterministic fault backend: FIFO ownership, rejection, invalidation, restart and clocks passed");
    return EXIT_SUCCESS;
}
