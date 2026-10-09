#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include "nova_link/nova_link.h"
#include "counter.h"

static void require(nl_status status, const char *operation)
{
    if (status != NL_OK) {
        fprintf(stderr, "%s: %s\n", operation, nl_status_name(status));
        exit(EXIT_FAILURE);
    }
}

static nl_status push(void *context, const nl_fragment *fragment)
{
    nl_frame frame, decoded;
    uint8_t bytes[NL_FRAME_MAX];
    size_t size;
    nl_status status = nl_frame_from_fragment(NL_COMMAND_PUSH, fragment, &frame);
    if (status != NL_OK) return status;
    status = nl_frame_encode(&frame, bytes, sizeof(bytes), &size);
    if (status != NL_OK) return status;
    status = nl_frame_decode(bytes, size, &decoded);
    return status == NL_OK ? nl_radio_handle_frame(context, &decoded, NULL, NULL) : status;
}

int main(void)
{
    nl_host sender, receiver;
    nl_radio tx_radio, rx_radio;
    nl_counter_context tx = {true, 1, 0, 0, 0, NL_OK};
    nl_counter_context rx = {false, 1, 0, 0, 0, NL_OK};
    nl_plugin tx_plugin = nl_counter_plugin(&tx), rx_plugin = nl_counter_plugin(&rx);
    nl_plugin_id tx_id, rx_id;
    uint8_t bytes[NL_FRAME_MAX];
    nl_fragment outgoing, incoming;
    nl_frame pull = {0}, response, decoded;
    nl_pull_token token;
    nl_window window;
    size_t size;
    unsigned i;
    uint64_t now_us = 0;
    pull.command = NL_COMMAND_PULL;
    require(nl_radio_init(&tx_radio, 2, 1000, 500, 0), "TX radio init");
    require(nl_radio_init(&rx_radio, 2, 1000, 500, 0), "RX radio init");
    require(nl_radio_set_rx_policy(&rx_radio, NL_RX_LATEST_PER_STREAM), "Counter RX policy");
    require(nl_host_init(&sender, 1, 0, push, &tx_radio), "Sender init");
    require(nl_host_init(&receiver, 2, 0, push, &rx_radio), "Receiver init");
    require(nl_host_register(&sender, &tx_plugin, &tx_id), "Register counter TX");
    require(nl_host_register(&receiver, &rx_plugin, &rx_id), "Register counter RX");
    puts("NOVA-LINK in-memory simulation (logical time, two copies per RF fragment)");
    for (i = 0; i < 300; ++i) {
        require(nl_host_tick(&sender, now_us), "Counter tick");
        require(tx.last_status, "Counter send");
        require(nl_radio_next_window(&tx_radio, now_us, &window), "Zone window");
        require(nl_radio_prepare_tx(&tx_radio, now_us, &outgoing, &window), "Prepare RF TX");
        require(nl_fragment_encode(&outgoing, bytes, sizeof(bytes), &size), "RF serialize");
        require(nl_fragment_decode(bytes, size, &incoming), "RF deserialize");
        require(nl_radio_receive(&rx_radio, &incoming, now_us), "First RF copy");
        if (nl_radio_receive(&rx_radio, &incoming, now_us) != NL_ERR_DUPLICATE) return EXIT_FAILURE;
        require(nl_radio_pop_tx(&tx_radio, window.zone, &outgoing), "Complete TX ownership");
        require(nl_radio_handle_frame(&rx_radio, &pull, &response, &token), "Host pull");
        require(nl_frame_encode(&response, bytes, sizeof(bytes), &size), "Pull serialize");
        require(nl_frame_decode(bytes, size, &decoded), "Pull deserialize");
        require(nl_frame_to_fragment(&decoded, &incoming), "Pull fragment");
        require(nl_host_receive_frame(&receiver, &decoded, now_us), "Plugin dispatch");
        require(nl_radio_commit_pull(&rx_radio, &response, token), "Commit host pull");
        if (rx.deliveries != i + 1u || rx.last_value != i) return EXIT_FAILURE;
        now_us += window.duration_us;
    }
    printf("Delivered %u counters, last=%" PRIu32 "; discarded %" PRIu64 " duplicate copies.\n",
        rx.deliveries, rx.last_value, rx_radio.stats.duplicates);
    printf("Sequence wrapped at 256. Logical duration=%" PRIu64 " us.\n", now_us);
    printf("Portable state sizes on this build: host=%zu bytes, radio=%zu bytes.\n",
        sizeof(nl_host), sizeof(nl_radio));
    require(nl_host_unregister(&sender, tx_id), "Stop TX plugin");
    require(nl_host_unregister(&receiver, rx_id), "Stop RX plugin");
    return EXIT_SUCCESS;
}
