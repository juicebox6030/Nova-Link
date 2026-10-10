/* SPDX-License-Identifier: GPL-3.0-only */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nova_link/counter_plugin.h"
#include "nova_link/logger_plugin.h"
#include "nova_link/multiverse_plugin.h"
#include "nova_link/radio_plugin.h"

typedef struct {
    nl_host host;
    nl_radio radio;
    nl_radio_link link;
    nl_multiverse_context dmx;
    nl_counter_context counter;
    nl_logger_context logger;
    nl_module descriptors[4];
    const nl_module *manifest[4];
    nl_module_instance instances[4];
    uint64_t log_events;
} node;

static void require(nl_status result, const char *operation)
{
    if (result == NL_OK) return;
    fprintf(stderr, "%s: %s\n", operation, nl_status_name(result));
    exit(EXIT_FAILURE);
}
static void mv_require(nova_mv_result_t result, nova_mv_result_t expected)
{
    if (result == expected) return;
    fprintf(stderr, "model: %s; expected %s\n", nova_mv_result_name(result),
            nova_mv_result_name(expected));
    exit(EXIT_FAILURE);
}
static nl_status exchange(void *context, const nl_frame *request,
                          nl_frame *response, nl_pull_token *token)
{
    uint8_t bytes[NL_FRAME_MAX];
    nl_frame decoded;
    size_t size;
    nl_status result = nl_frame_encode(request, bytes, sizeof(bytes), &size);
    if (result != NL_OK) return result;
    result = nl_frame_decode(bytes, size, &decoded);
    if (result != NL_OK) return result;
    result = nl_radio_handle_frame(context, &decoded, response, token);
    if (result != NL_OK || request->command == NL_COMMAND_PUSH) return result;
    result = nl_frame_encode(response, bytes, sizeof(bytes), &size);
    return result == NL_OK ? nl_frame_decode(bytes, size, response) : result;
}
static nl_status commit(void *context, const nl_frame *response, nl_pull_token token)
{
    return nl_radio_commit_pull(context, response, token);
}
static void observe(void *context, nl_log_event event, nl_status status,
                    nl_plugin_id plugin, uint8_t zone)
{
    uint64_t *events = context;
    (void)event; (void)status; (void)plugin; (void)zone;
    ++*events;
}
static void initialize(node *n, bool transmitter)
{
    static const char *const dependencies[] = {"radio-link", "logger"};
    nl_multiverse_config dmx = {.role = transmitter ? NL_MULTIVERSE_TX : NL_MULTIVERSE_RX,
        .zone = 1, .peer_origin = 1, .universe = 1, .session = 42,
        .interval_us = 1000, .full_interval_us = 10000,
        .loss_timeout_us = 50000, .assembly_timeout_us = 5000, .chunks_per_tick = 8};
    nl_radio_link_config transport = {.exchange = exchange, .commit = commit,
        .context = &n->radio, .poll_budget = 16};
    memset(n, 0, sizeof(*n));
    require(nl_radio_init(&n->radio, 6, 1000, 0, 0), "Radio init");
    require(nl_host_init_plugins(&n->host, transmitter ? 1u : 2u, 0), "Base init");
    require(nl_radio_link_init(&n->link, &transport), "Transport init");
    require(nl_logger_init(&n->logger, observe, &n->log_events), "Logger init");
    mv_require(nl_multiverse_init(&n->dmx, &dmx), NOVA_MV_OK);
    n->counter.transmitter = transmitter;
    n->counter.zone = 2;
    n->descriptors[0] = nl_multiverse_module(&n->dmx);
    n->descriptors[1] = nl_counter_module(&n->counter);
    n->descriptors[2] = nl_radio_link_module(&n->link);
    n->descriptors[3] = nl_logger_module(&n->logger);
    for (unsigned i = 0; i < 2; ++i) {
        n->descriptors[i].requires = dependencies;
        n->descriptors[i].require_count = 2;
    }
    for (unsigned i = 0; i < 4; ++i) n->manifest[i] = &n->descriptors[i];
    require(nl_modules_start(&n->host, n->manifest, n->instances, 4), "Start manifest");
}

int main(void)
{
    static node sender, receiver;
    nova_dmx_frame_t desired = {0}, received;
    nl_fragment outgoing, incoming, discarded;
    nl_window window;
    uint8_t bytes[NL_FRAGMENT_MAX];
    size_t size;
    uint64_t now = 0, dropped = 0, corrupt = 0, observations = 0;
    initialize(&sender, true);
    initialize(&receiver, false);
    desired.slot_count = NOVA_DMX_MAX_SLOTS;
    puts("Uniform module simulation: radio-link + logger + counter + Multiverse DMX");
    puts("Native NLM1 application bytes and logical time; no Multiverse RF or hardware.");
    for (unsigned update = 0; update <= 300; ++update) {
        uint64_t frames = receiver.dmx.rx.stats.frames;
        for (unsigned slot = 0; slot < NOVA_DMX_MAX_SLOTS; ++slot)
            desired.slots[slot] = (uint8_t)(update + slot * 73u);
        mv_require(nl_multiverse_submit(&sender.dmx, &desired), NOVA_MV_OK);
        if (update == 300) nl_multiverse_force_full(&sender.dmx);
        require(nl_host_poll(&sender.host, now), "Sender poll");
        require(sender.dmx.last_send_status, "DMX queue acceptance");
        for (unsigned zone = 1; zone <= 2; ++zone) {
            require(nl_radio_next_window(&sender.radio, now, &window), "Zone window");
            if (window.zone != zone) return EXIT_FAILURE;
            while (sender.radio.tx[zone].count != 0u) {
                require(nl_radio_prepare_tx(&sender.radio, now, &outgoing, &window), "TX prepare");
                require(nl_fragment_encode(&outgoing, bytes, sizeof(bytes), &size), "Native encode");
                require(nl_fragment_decode(bytes, size, &incoming), "Native decode");
                require(nl_radio_pop_tx(&sender.radio, (uint8_t)zone, &discarded), "TX handoff");
                ++observations;
                if (zone == 1u && update != 0u && update != 300u && observations % 17u == 0u) {
                    ++dropped;
                    continue;
                }
                if (zone == 1u && update != 0u && update != 300u && observations % 31u == 0u) {
                    incoming.payload[24] ^= 1u;
                    ++corrupt;
                }
                require(nl_radio_receive(&receiver.radio, &incoming, now), "FIFO receive");
                if (nl_radio_receive(&receiver.radio, &incoming, now) != NL_ERR_DUPLICATE)
                    return EXIT_FAILURE;
            }
            require(nl_host_poll(&receiver.host, now), "Receiver poll");
            now += window.duration_us;
        }
        if (receiver.dmx.rx.stats.frames != frames) {
            mv_require(nl_multiverse_get(&receiver.dmx, now, &received), NOVA_MV_FRAME_READY);
            if (received.slot_count != desired.slot_count ||
                memcmp(received.slots, desired.slots, desired.slot_count) != 0) return EXIT_FAILURE;
        }
        if (receiver.counter.deliveries != update + 1u || receiver.counter.last_value != update)
            return EXIT_FAILURE;
    }
    mv_require(nl_multiverse_get(&receiver.dmx, now, &received), NOVA_MV_FRAME_READY);
    if (memcmp(received.slots, desired.slots, desired.slot_count) != 0) return EXIT_FAILURE;
    now += receiver.dmx.config.loss_timeout_us;
    require(nl_host_poll(&receiver.host, now), "Silence poll");
    mv_require(nl_multiverse_get(&receiver.dmx, now, &received), NOVA_MV_NEED_FULL);
    printf("Delivered %u counters and %" PRIu64 " atomic DMX frames; %" PRIu64
           " drops, %" PRIu64 " corrupt payloads; final state recovered then expired.\n",
           receiver.counter.deliveries, receiver.dmx.rx.stats.frames, dropped, corrupt);
    require(nl_modules_stop(sender.instances, 4), "Stop sender manifest");
    require(nl_modules_stop(receiver.instances, 4), "Stop receiver manifest");
    if (sender.host.send != NULL || receiver.host.log != NULL) return EXIT_FAILURE;
    return EXIT_SUCCESS;
}
