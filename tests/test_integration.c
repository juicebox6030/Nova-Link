#include "test.h"

typedef struct { unsigned received; nl_fragment last; } sink;

static nl_status serial_push(void *context, const nl_fragment *value)
{
    nl_radio *radio = context;
    nl_frame request, decoded;
    nl_parser parser;
    uint8_t bytes[NL_FRAME_MAX];
    size_t size, i;
    STATUS(nl_frame_from_fragment(NL_COMMAND_PUSH, value, &request), NL_OK);
    STATUS(nl_frame_encode(&request, bytes, sizeof(bytes), &size), NL_OK);
    nl_parser_reset(&parser);
    for (i = 0; i < size; ++i)
        CHECK(nl_parser_feed(&parser, bytes[i], &decoded) ==
            (i + 1u == size ? NL_PARSE_READY : NL_PARSE_WAIT));
    return nl_radio_handle_frame(radio, &decoded, NULL, NULL);
}

static void delivered(nl_host *host, nl_plugin_id id, const nl_fragment *value, void *context)
{
    sink *state = context;
    (void)host;
    (void)id;
    ++state->received;
    state->last = *value;
}

static void serial_pull(nl_radio *radio, nl_host *host, uint64_t now_us)
{
    const uint8_t pull[] = {0xAA, 0x01, 0x02, 0x0E, 0x7C};
    uint8_t bytes[NL_FRAME_MAX];
    nl_frame request, response, decoded;
    nl_pull_token token;
    nl_fragment value;
    size_t size;
    STATUS(nl_frame_decode(pull, sizeof(pull), &request), NL_OK);
    STATUS(nl_radio_handle_frame(radio, &request, &response, &token), NL_OK);
    STATUS(nl_frame_encode(&response, bytes, sizeof(bytes), &size), NL_OK);
    STATUS(nl_frame_decode(bytes, size, &decoded), NL_OK);
    STATUS(nl_frame_to_fragment(&decoded, &value), NL_OK);
    STATUS(nl_host_receive_frame(host, &decoded, now_us), NL_OK);
    STATUS(nl_radio_commit_pull(radio, &response, token), NL_OK);
    /* Host deduplication also protects against duplicate adapter deliveries. */
    STATUS(nl_host_receive(host, &value, now_us), NL_ERR_DUPLICATE);
}

int main(void)
{
    nl_host sender_host, receiver_host;
    nl_radio sender_radio, receiver_radio;
    nl_plugin writer = {0}, reader = {0};
    sink state = {0};
    nl_plugin_id writer_id, reader_id;
    uint8_t payload[NL_PAYLOAD_MAX], bytes[NL_FRAGMENT_MAX];
    nl_fragment tx, rf, delayed, output;
    nl_window window;
    unsigned i, j;
    size_t size;
    uint64_t now_us = 0;
    STATUS(nl_radio_init(&sender_radio, 2, 1000, 500, 0), NL_OK);
    STATUS(nl_radio_init(&receiver_radio, 2, 1000, 500, 0), NL_OK);
    STATUS(nl_host_init(&sender_host, 5, 0, serial_push, &sender_radio), NL_OK);
    STATUS(nl_host_init(&receiver_host, 6, 0, serial_push, &receiver_radio), NL_OK);
    reader.receive = delivered;
    reader.context = &state;
    STATUS(nl_host_register(&sender_host, &writer, &writer_id), NL_OK);
    STATUS(nl_host_register(&receiver_host, &reader, &reader_id), NL_OK);
    {
        nl_frame request = {0};
        request.command = NL_COMMAND_PULL;
        STATUS(nl_host_receive_frame(&receiver_host, &request, 0), NL_ERR_UNSUPPORTED);
        tx = fragment(5, 1, 0);
        STATUS(nl_frame_from_fragment(NL_COMMAND_PUSH, &tx, &request), NL_OK);
        STATUS(nl_host_receive_frame(&receiver_host, &request, 0), NL_ERR_UNSUPPORTED);
        CHECK(state.received == 0);
    }
    STATUS(nl_host_claim(&sender_host, writer_id, 1, NL_ZONE_EXCLUSIVE), NL_OK);
    STATUS(nl_host_claim(&receiver_host, reader_id, 1, NL_ZONE_READ_ONLY), NL_OK);
    for (i = 0; i < 600u; ++i) {
        for (j = 0; j < sizeof(payload); ++j) payload[j] = (uint8_t)(i + j);
        STATUS(nl_host_send(&sender_host, writer_id, 1, 0, payload, sizeof(payload)), NL_OK);
        STATUS(nl_radio_next_window(&sender_radio, now_us, &window), NL_OK);
        CHECK(window.zone == 1);
        STATUS(nl_radio_prepare_tx(&sender_radio, now_us, &tx, &window), NL_OK);
        STATUS(nl_fragment_encode(&tx, bytes, sizeof(bytes), &size), NL_OK);
        STATUS(nl_fragment_decode(bytes, size, &rf), NL_OK);
        STATUS(nl_radio_pop_tx(&sender_radio, window.zone, &output), NL_OK);
        same_fragment(&tx, &output);
        /* Two bands deliver identical copies; the plugin must see one delivery. */
        STATUS(nl_radio_receive(&receiver_radio, &rf, now_us), NL_OK);
        STATUS(nl_radio_receive(&receiver_radio, &rf, now_us), NL_ERR_DUPLICATE);
        serial_pull(&receiver_radio, &receiver_host, now_us);
        same_fragment(&tx, &state.last);
        CHECK(state.received == i + 1u);
        now_us += window.duration_us;
    }
    /* Newer arrival overtakes an older in-flight RF fragment. */
    STATUS(nl_host_send(&sender_host, writer_id, 1, 0, NULL, 0), NL_OK);
    STATUS(nl_host_send(&sender_host, writer_id, 1, 0, NULL, 0), NL_OK);
    STATUS(nl_radio_next_window(&sender_radio, now_us, &window), NL_OK);
    STATUS(nl_radio_prepare_tx(&sender_radio, now_us, &tx, &window), NL_OK);
    STATUS(nl_radio_pop_tx(&sender_radio, 1, &delayed), NL_OK);
    STATUS(nl_radio_prepare_tx(&sender_radio, now_us, &tx, &window), NL_OK);
    STATUS(nl_radio_pop_tx(&sender_radio, 1, &tx), NL_OK);
    STATUS(nl_radio_receive(&receiver_radio, &tx, now_us), NL_OK);
    STATUS(nl_radio_receive(&receiver_radio, &delayed, now_us), NL_ERR_STALE);
    serial_pull(&receiver_radio, &receiver_host, now_us);
    CHECK(state.received == 601);
    now_us += window.duration_us;
    /* Metadata uses the same complete path without any claim on zone 0. */
    STATUS(nl_host_send(&sender_host, writer_id, 0, NL_FLAG_MGMT_LISTEN, payload, 10), NL_OK);
    STATUS(nl_radio_next_window(&sender_radio, now_us, &window), NL_OK);
    CHECK(window.zone == 0);
    STATUS(nl_radio_prepare_tx(&sender_radio, now_us, &tx, &window), NL_OK);
    STATUS(nl_radio_pop_tx(&sender_radio, 0, &tx), NL_OK);
    STATUS(nl_radio_receive(&receiver_radio, &tx, now_us), NL_OK);
    serial_pull(&receiver_radio, &receiver_host, now_us);
    CHECK(state.received == 602 && state.last.zone == 0);
    CHECK(receiver_radio.stats.duplicates == 600 && receiver_radio.stats.stale == 1);
    STATUS(nl_host_unregister(&sender_host, writer_id), NL_OK);
    STATUS(nl_host_unregister(&receiver_host, reader_id), NL_OK);
    puts("integration: plugin -> framed transport -> scheduled RF bytes -> dedup -> plugin passed");
    return EXIT_SUCCESS;
}
