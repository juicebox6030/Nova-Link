#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include "nova_link/nova_link.h"
#include "nova_link/counter_plugin.h"
#include "nova_link/radio_plugin.h"

static void require(nl_status status, const char *operation)
{
    if (status != NL_OK) {
        fprintf(stderr, "%s: %s\n", operation, nl_status_name(status));
        exit(EXIT_FAILURE);
    }
}

static nl_status exchange(void *context, const nl_frame *request,
                          nl_frame *response, nl_pull_token *token)
{
    nl_frame decoded;
    uint8_t bytes[NL_FRAME_MAX];
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

int main(void)
{
    nl_host sender, receiver;
    nl_radio tx_radio, rx_radio;
    nl_counter_context tx = {.transmitter = true, .zone = 1};
    nl_counter_context rx = {.zone = 1};
    nl_radio_link tx_link, rx_link;
    nl_radio_link_config tx_config = {.exchange = exchange, .commit = commit,
                                      .context = &tx_radio, .poll_budget = 16};
    nl_radio_link_config rx_config = {.exchange = exchange, .commit = commit,
                                      .context = &rx_radio, .poll_budget = 16};
    nl_module tx_module = nl_counter_module(&tx), rx_module = nl_counter_module(&rx);
    nl_module tx_transport, rx_transport;
    const nl_module *tx_manifest[] = {&tx_module, &tx_transport};
    const nl_module *rx_manifest[] = {&rx_module, &rx_transport};
    nl_module_instance tx_instances[2] = {0}, rx_instances[2] = {0};
    uint8_t bytes[NL_FRAME_MAX];
    nl_fragment outgoing, incoming;
    nl_window window;
    size_t size;
    unsigned i;
    uint64_t now_us = 0;
    require(nl_radio_init(&tx_radio, 2, 1000, 500, 0), "TX radio init");
    require(nl_radio_init(&rx_radio, 2, 1000, 500, 0), "RX radio init");
    require(nl_radio_set_rx_policy(&rx_radio, NL_RX_LATEST_PER_STREAM), "Counter RX policy");
    require(nl_host_init_plugins(&sender, 1, 0), "Sender base init");
    require(nl_host_init_plugins(&receiver, 2, 0), "Receiver base init");
    require(nl_radio_link_init(&tx_link, &tx_config), "TX transport init");
    require(nl_radio_link_init(&rx_link, &rx_config), "RX transport init");
    tx_transport = nl_radio_link_module(&tx_link);
    rx_transport = nl_radio_link_module(&rx_link);
    require(nl_modules_start(&sender, tx_manifest, tx_instances, 2), "Start TX manifest");
    require(nl_modules_start(&receiver, rx_manifest, rx_instances, 2), "Start RX manifest");
    puts("NOVA-LINK in-memory simulation (logical time, two copies per RF fragment)");
    for (i = 0; i < 300; ++i) {
        require(nl_host_poll(&sender, now_us), "Sender poll");
        require(tx.last_status, "Counter send");
        require(nl_radio_next_window(&tx_radio, now_us, &window), "Zone window");
        require(nl_radio_prepare_tx(&tx_radio, now_us, &outgoing, &window), "Prepare RF TX");
        require(nl_fragment_encode(&outgoing, bytes, sizeof(bytes), &size), "RF serialize");
        require(nl_fragment_decode(bytes, size, &incoming), "RF deserialize");
        require(nl_radio_receive(&rx_radio, &incoming, now_us), "First RF copy");
        if (nl_radio_receive(&rx_radio, &incoming, now_us) != NL_ERR_DUPLICATE) return EXIT_FAILURE;
        require(nl_radio_pop_tx(&tx_radio, window.zone, &outgoing), "Complete TX ownership");
        require(nl_host_poll(&receiver, now_us), "Receiver transport/plugin poll");
        if (rx_link.last_status != NL_OK && rx_link.last_status != NL_ERR_EMPTY)
            require(rx_link.last_status, "Receive handoff");
        if (rx.deliveries != i + 1u || rx.last_value != i) return EXIT_FAILURE;
        now_us += window.duration_us;
    }
    printf("Delivered %u counters, last=%" PRIu32 "; discarded %" PRIu64 " duplicate copies.\n",
        rx.deliveries, rx.last_value, rx_radio.stats.duplicates);
    printf("Sequence wrapped at 256. Logical duration=%" PRIu64 " us.\n", now_us);
    printf("Portable state sizes on this build: host=%zu bytes, radio=%zu bytes.\n",
        sizeof(nl_host), sizeof(nl_radio));
    require(nl_modules_stop(tx_instances, 2), "Stop TX manifest");
    require(nl_modules_stop(rx_instances, 2), "Stop RX manifest");
    return EXIT_SUCCESS;
}
