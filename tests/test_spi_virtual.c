/* SPDX-License-Identifier: GPL-3.0-only */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/spi_virtual.h"
#include "nova_link/counter_plugin.h"

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(EXIT_FAILURE); } } while (0)
#define OK(x) CHECK((x) == NL_OK)

static nl_fragment fragment(unsigned sequence)
{
    nl_fragment f = {.origin = 1, .zone = 1, .sequence = (uint8_t)sequence,
        .payload_size = 4, .payload = {0xAA, 0x31, 0xAA, 0x51}};
    return f;
}

static void duplex_progress(void)
{
    nl_host host;
    nl_radio radio;
    nl_spi_slave slave;
    nl_spi_slave unbound = {0};
    nl_spi_virtual device;
    nl_spi_driver driver;
    nl_spi_backend backend;
    nl_radio_link link;
    nl_radio_link_config config;
    nl_counter_context counter = {.transmitter = true, .zone = 1};
    nl_module modules[3];
    const nl_module *manifest[3];
    nl_module_instance instances[3] = {{0}};
    unsigned injected = 0;
    uint64_t now;
    OK(nl_host_init_plugins(&host, 1, 0));
    CHECK(nl_spi_virtual_init(&device, &unbound, 400) == NL_ERR_ARGUMENT);
    OK(nl_radio_init(&radio, 2, 1000, 0, 0));
    OK(nl_spi_slave_init(&slave, &radio));
    OK(nl_spi_virtual_init(&device, &slave, 400));
    driver = nl_spi_virtual_driver(&device);
    OK(nl_spi_backend_init(&backend, &driver));
    OK(nl_spi_backend_link_config(&backend, 2, &config));
    OK(nl_radio_link_init(&link, &config));
    modules[0] = nl_counter_module(&counter);
    modules[1] = nl_spi_backend_link_module(&link);
    modules[2] = nl_spi_backend_module(&backend);
    for (unsigned i = 0; i < 3; ++i) manifest[i] = &modules[i];
    OK(nl_modules_start(&host, manifest, instances, 3));
    for (now = 0; now < 100000u && counter.deliveries < 20u; now += 100) {
        nl_fragment f;
        if (injected < 20u && now % 2000u == 0u) {
            f = fragment(injected);
            f.origin = 2;
            OK(nl_radio_receive(&radio, &f, now));
            ++injected;
        }
        OK(nl_host_poll(&host, now));
        if (radio.tx[1].count != 0u) OK(nl_radio_pop_tx(&radio, 1, &f));
    }
    CHECK(counter.deliveries == 20u && backend.stats.tx_completed >= 20u);
    CHECK(now < 100000u && radio.rx.count <= NL_RADIO_RX_DEPTH);
    counter.transmitter = false;
    while (backend.tx_pending || backend.inflight || link.pending || radio.rx.count != 0u) {
        nl_fragment f;
        CHECK(now < 110000u);
        now += 100;
        OK(nl_host_poll(&host, now));
        if (radio.tx[1].count != 0u) OK(nl_radio_pop_tx(&radio, 1, &f));
    }
    OK(nl_modules_stop(instances, 3));
}

static void transport_recovery(void)
{
    nl_host host;
    nl_radio radio;
    nl_spi_slave slave;
    nl_spi_virtual device;
    nl_spi_driver driver;
    nl_spi_backend backend;
    nl_radio_link link;
    nl_radio_link_config config;
    nl_counter_context counter = {.zone = 1};
    nl_module modules[3];
    const nl_module *manifest[3];
    nl_module_instance instances[3] = {{0}};
    nl_fragment f = fragment(1), incoming = fragment(0), popped;
    nl_frame request, response;
    nl_pull_token receipt;
    uint8_t original[NL_FRAME_MAX];
    size_t original_size;
    nl_spi_transaction transaction;
    OK(nl_host_init_plugins(&host, 1, 0));
    OK(nl_radio_init(&radio, 2, 1000, 0, 0));
    OK(nl_spi_slave_init(&slave, &radio));
    OK(nl_spi_virtual_init(&device, &slave, 400));
    driver = nl_spi_virtual_driver(&device);
    OK(nl_spi_backend_init(&backend, &driver));
    OK(nl_spi_backend_link_config(&backend, 2, &config));
    OK(nl_radio_link_init(&link, &config));
    modules[0] = nl_counter_module(&counter);
    modules[1] = nl_spi_backend_link_module(&link);
    modules[2] = nl_spi_backend_module(&backend);
    for (unsigned i = 0; i < 3; ++i) manifest[i] = &modules[i];
    OK(nl_modules_start(&host, manifest, instances, 3));

    OK(nl_frame_from_fragment(NL_COMMAND_PUSH, &f, &request));
    OK(config.exchange(config.context, &request, &response, &receipt));
    OK(nl_spi_virtual_fault_next(&device, NL_SPI_VIRTUAL_PUSH_REJECTED));
    OK(nl_host_poll(&host, 100));
    OK(nl_host_poll(&host, 500));
    CHECK(backend.tx_pending && !backend.tx_uncertain && radio.tx[1].count == 0u);
    OK(nl_host_poll(&host, 600));
    OK(nl_host_poll(&host, 1000));
    CHECK(!backend.tx_pending && backend.stats.tx_retries == 1u);
    OK(nl_radio_pop_tx(&radio, 1, &popped));
    CHECK(popped.sequence == f.sequence && memcmp(popped.payload, f.payload, f.payload_size) == 0);

    f.sequence = 2;
    OK(nl_frame_from_fragment(NL_COMMAND_PUSH, &f, &request));
    OK(config.exchange(config.context, &request, &response, &receipt));
    original_size = backend.tx_size;
    memcpy(original, backend.tx, original_size);
    OK(nl_spi_virtual_fault_next(&device, NL_SPI_VIRTUAL_PUSH_UNCERTAIN_BEFORE_ACCEPT));
    OK(nl_host_poll(&host, 1100));
    OK(nl_host_poll(&host, 1500));
    CHECK(backend.tx_uncertain && radio.tx[1].count == 0u);
    CHECK(modules[2].hooks.can_stop(&host, backend.plugin, &backend) == NL_ERR_BUSY);
    incoming.origin = 2;
    OK(nl_radio_receive(&radio, &incoming, 1500));
    OK(nl_host_poll(&host, 1600));
    OK(nl_host_poll(&host, 2000));
    CHECK(counter.deliveries == 1u && backend.stats.rx_committed == 1u);
    CHECK(backend.tx_uncertain && radio.tx[1].count == 0u);
    OK(nl_spi_backend_resolve_tx(&backend, true));
    OK(nl_host_poll(&host, 2100));
    CHECK(device.request_size == original_size && memcmp(device.request, original, original_size) == 0);
    OK(nl_host_poll(&host, 2500));
    OK(nl_radio_pop_tx(&radio, 1, &popped));
    CHECK(popped.sequence == f.sequence);

    f.sequence = 3;
    OK(nl_frame_from_fragment(NL_COMMAND_PUSH, &f, &request));
    OK(config.exchange(config.context, &request, &response, &receipt));
    OK(nl_spi_virtual_fault_next(&device, NL_SPI_VIRTUAL_PUSH_UNCERTAIN));
    OK(nl_host_poll(&host, 2600));
    OK(nl_host_poll(&host, 3000));
    CHECK(backend.tx_uncertain && radio.tx[1].count == 1u);
    transaction = backend.transaction;
    OK(nl_host_poll(&host, 3100));
    OK(nl_host_poll(&host, 3200));
    CHECK(backend.transaction == transaction && radio.tx[1].count == 1u);
    OK(nl_spi_backend_resolve_tx(&backend, false));
    OK(nl_radio_pop_tx(&radio, 1, &popped));
    CHECK(popped.sequence == f.sequence);
    OK(nl_modules_stop(instances, 3));

    /* Driver and host clock restart together; receipt/transaction history stays. */
    OK(nl_modules_start(&host, manifest, instances, 3));
    f.sequence = 4;
    OK(nl_frame_from_fragment(NL_COMMAND_PUSH, &f, &request));
    OK(config.exchange(config.context, &request, &response, &receipt));
    OK(nl_host_poll(&host, 0));
    CHECK(backend.inflight && backend.transaction > transaction);
    OK(nl_host_poll(&host, 400));
    OK(nl_radio_pop_tx(&radio, 1, &popped));
    CHECK(popped.sequence == f.sequence);
    CHECK(backend.stats.tx_uncertain == 2u && backend.stats.tx_discarded == 1u);
    CHECK(backend.stats.tx_completed == 3u && backend.stats.driver_errors == 3u);
    OK(nl_modules_stop(instances, 3));
}

int main(void)
{
    nl_radio radio, peer;
    nl_spi_slave slave;
    nl_spi_virtual device;
    nl_spi_driver driver;
    nl_spi_virtual_air air;
    nl_frame frame;
    nl_fragment f = fragment(0), popped;
    uint8_t bytes[NL_FRAME_MAX], response[NL_FRAME_MAX], original[NL_FRAME_MAX];
    size_t size, response_size;
    nl_pull_token receipt, old_receipt;
    bool ready, uncertain;
    uint64_t now = 100;
    OK(nl_radio_init(&radio, 2, 1000, 0, 0));
    OK(nl_radio_init(&peer, 2, 1000, 0, 0));
    OK(nl_spi_slave_init(&slave, &radio));
    OK(nl_spi_virtual_init(&device, &slave, 400));
    driver = nl_spi_virtual_driver(&device);
    OK(driver.start(driver.context));
    OK(driver.ready(driver.context, &ready));
    CHECK(!ready);
    OK(nl_frame_from_fragment(NL_COMMAND_PUSH, &f, &frame));
    OK(nl_frame_encode(&frame, bytes, sizeof(bytes), &size));
    memcpy(original, bytes, size);
    OK(driver.begin(driver.context, bytes, size, 1, now));
    memset(bytes, 0, size); /* Original caller storage cannot mutate staged bytes. */
    CHECK(radio.tx[1].count == 0u);
    CHECK(driver.finish(driver.context, 2, now, response, sizeof(response), &response_size, &receipt, &uncertain) == NL_ERR_STALE);
    CHECK(driver.finish(driver.context, 1, now + 399u, response, sizeof(response), &response_size, &receipt, &uncertain) == NL_ERR_BUSY);
    CHECK(driver.can_stop(driver.context) == NL_ERR_BUSY);
    nl_spi_virtual_set_connected(&device, false);
    CHECK(driver.finish(driver.context, 1, now + 400u, response, sizeof(response), &response_size, &receipt, &uncertain) == NL_ERR_BUSY);
    CHECK(radio.tx[1].count == 0u && device.active);
    nl_spi_virtual_set_connected(&device, true);
    now += 400;
    OK(driver.finish(driver.context, 1, now, response, sizeof(response), &response_size, &receipt, &uncertain));
    CHECK(response_size == 0u && receipt == 0u && radio.tx[1].count == 1u);
    OK(nl_radio_pop_tx(&radio, 1, &popped));
    CHECK(memcmp(popped.payload, f.payload, f.payload_size) == 0);

    for (unsigned fault = NL_SPI_VIRTUAL_REQUEST_SHORT; fault <= NL_SPI_VIRTUAL_REQUEST_LENGTH; ++fault) {
        OK(nl_spi_virtual_fault_next(&device, (nl_spi_virtual_fault)fault));
        OK(driver.begin(driver.context, original, size, 10u + fault, now));
        now += 400;
        CHECK(driver.finish(driver.context, 10u + fault, now, response, sizeof(response), &response_size, &receipt, &uncertain) != NL_OK);
        CHECK(radio.tx[1].count == 0u && nl_spi_virtual_drained(&device));
    }
    OK(driver.begin(driver.context, original, size, 20, now));
    driver.stop(driver.context); /* Cancel before slave dispatch. */
    CHECK(radio.tx[1].count == 0u && nl_spi_virtual_drained(&device));
    OK(driver.start(driver.context));
    OK(nl_radio_receive(&radio, &f, now));
    OK(driver.ready(driver.context, &ready));
    CHECK(ready);
    frame.command = NL_COMMAND_PULL;
    frame.data_size = 0;
    OK(nl_frame_encode(&frame, bytes, sizeof(bytes), &size));
    for (unsigned fault = NL_SPI_VIRTUAL_RESPONSE_SHORT; fault <= NL_SPI_VIRTUAL_RESPONSE_LENGTH; ++fault) {
        OK(nl_spi_virtual_fault_next(&device, (nl_spi_virtual_fault)fault));
        OK(driver.begin(driver.context, bytes, size, 30u + fault, now));
        now += 400;
        OK(driver.finish(driver.context, 30u + fault, now, response, sizeof(response), &response_size, &receipt, &uncertain));
        CHECK(nl_frame_decode(response, response_size, &frame) != NL_OK);
        CHECK(radio.rx.count == 1u && nl_spi_slave_pending(&slave));
        OK(driver.settle(driver.context, receipt, false));
        CHECK(radio.rx.count == 1u && !nl_spi_slave_pending(&slave));
    }
    OK(driver.begin(driver.context, bytes, size, 40, now));
    now += 400;
    OK(driver.finish(driver.context, 40, now, response, sizeof(response), &response_size, &receipt, &uncertain));
    OK(nl_frame_decode(response, response_size, &frame));
    old_receipt = receipt;
    {
        nl_spi_virtual other;
        CHECK(nl_spi_virtual_init(&other, &slave, 400) == NL_ERR_BUSY);
        CHECK(device.retained && nl_spi_slave_pending(&slave));
    }
    nl_spi_virtual_fail_commits(&device, 2);
    CHECK(driver.settle(driver.context, receipt, true) == NL_ERR_BUSY);
    CHECK(driver.settle(driver.context, receipt, true) == NL_ERR_BUSY);
    nl_spi_virtual_set_connected(&device, false);
    CHECK(driver.settle(driver.context, receipt, true) == NL_ERR_BUSY);
    CHECK(radio.rx.count == 1u);
    nl_spi_virtual_set_connected(&device, true);
    OK(driver.settle(driver.context, receipt, true));
    CHECK(radio.rx.count == 0u);
    OK(driver.ready(driver.context, &ready));
    CHECK(!ready);
    f = fragment(1);
    OK(nl_radio_receive(&radio, &f, now));
    OK(driver.begin(driver.context, bytes, size, 41, now));
    now += 400;
    OK(driver.finish(driver.context, 41, now, response, sizeof(response), &response_size, &receipt, &uncertain));
    CHECK(receipt != old_receipt);
    CHECK(driver.settle(driver.context, old_receipt, true) == NL_ERR_STALE);
    CHECK(radio.rx.count == 1u && device.retained);
    driver.stop(driver.context); /* Cancel prepared receipt, retain native head. */
    CHECK(radio.rx.count == 1u && nl_spi_virtual_drained(&device));
    OK(nl_radio_pull(&radio, &popped));

    /* Native FIFO congestion retains the frozen TX head, sequence and payload. */
    OK(nl_spi_virtual_air_init(&air, 300));
    for (unsigned i = 0; i < NL_RADIO_RX_DEPTH; ++i) {
        f = fragment(i);
        OK(nl_radio_receive(&peer, &f, now));
    }
    f = fragment(NL_RADIO_RX_DEPTH);
    OK(nl_radio_enqueue(&radio, &f));
    CHECK(nl_spi_virtual_air_step(&air, &radio, &peer, now, true) == NL_ERR_BUSY);
    now += 300;
    CHECK(nl_spi_virtual_air_step(&air, &radio, &peer, now, true) == NL_ERR_FULL);
    CHECK(air.pending && radio.tx[1].count == 1u && peer.rx.count == NL_RADIO_RX_DEPTH);
    OK(nl_radio_pull(&peer, &popped));
    OK(nl_spi_virtual_air_step(&air, &radio, &peer, now, true));
    CHECK(!air.pending && radio.tx[1].count == 0u && peer.rx.count == NL_RADIO_RX_DEPTH);
    CHECK(device.stats.malformed_requests == 2u && device.stats.response_faults == 2u);
    CHECK(device.stats.commit_retries == 2u && air.completed == 1u && air.blocked == 1u);
    duplex_progress();
    transport_recovery();
    puts("Virtual SPI: staged immutable bytes, bounded delay, request/response rejection, cancellation, disconnect, receipt retry/stale guards, READY and FIFO backpressure passed.");
    return EXIT_SUCCESS;
}
