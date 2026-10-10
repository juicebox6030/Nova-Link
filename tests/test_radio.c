#include "test.h"

static void scheduling(void)
{
    nl_scheduler scheduler;
    nl_window window, before;
    unsigned i;
    const uint8_t expected[] = {1, 3, 7, 0, 1, 3, 7, 0};
    STATUS(nl_scheduler_init(&scheduler, 0x8B, 100, 50), NL_ERR_ARGUMENT);
    STATUS(nl_scheduler_init(&scheduler, 0x8A, 0, 0), NL_ERR_ARGUMENT);
    STATUS(nl_scheduler_init(&scheduler, 0x8A, 100, 101), NL_ERR_ARGUMENT);
    STATUS(nl_scheduler_init(&scheduler, 0x8A, UINT32_MAX, 1), NL_ERR_ARGUMENT);
    STATUS(nl_scheduler_init(&scheduler, 0x8A, 100, 50), NL_OK);
    for (i = 0; i < sizeof(expected); ++i) {
        STATUS(nl_scheduler_next(&scheduler, (uint64_t)i * 100u, true, 0, &window), NL_OK);
        CHECK(window.zone == expected[i] && window.duration_us == 100);
        before = window;
        STATUS(nl_scheduler_next(&scheduler, (uint64_t)i * 100u + 99u, true, 0, &window), NL_ERR_BUSY);
        /* Field-wise: struct copies leave padding bytes unspecified. */
        CHECK(window.zone == before.zone && window.start_us == before.start_us &&
              window.duration_us == before.duration_us);
    }
    STATUS(nl_scheduler_next(&scheduler, 898, false, 0, &window), NL_OK);
    CHECK(window.zone == 1 && window.start_us == 898);
    STATUS(nl_scheduler_next(&scheduler, 897, false, 0, &window), NL_ERR_ARGUMENT);
    STATUS(nl_scheduler_next(&scheduler, 998, false, 0x08, &window), NL_OK);
    CHECK(window.zone == 3 && window.duration_us == 150);
    STATUS(nl_scheduler_next(&scheduler, 1098, false, 0, &window), NL_ERR_BUSY);
    STATUS(nl_scheduler_set_active(&scheduler, 0x02), NL_OK);
    STATUS(nl_scheduler_next(&scheduler, 1148, false, 0, &window), NL_OK);
    CHECK(window.zone == 1);
    STATUS(nl_scheduler_set_active(&scheduler, 0), NL_OK);
    STATUS(nl_scheduler_next(&scheduler, 1248, false, 0, &window), NL_ERR_EMPTY);
    STATUS(nl_scheduler_next(&scheduler, 1248, true, 1, &window), NL_OK);
    CHECK(window.zone == 0 && window.duration_us == 150);
    STATUS(nl_scheduler_next(&scheduler, UINT64_MAX, true, 0, &window), NL_ERR_SIZE);
    STATUS(nl_scheduler_init(&scheduler, 0, 100, 0), NL_OK);
    STATUS(nl_scheduler_next(&scheduler, 100, false, 0, &window), NL_ERR_EMPTY);
    STATUS(nl_scheduler_next(&scheduler, 99, false, 0, &window), NL_ERR_ARGUMENT);
}

static void synchronized_burst(void)
{
    nl_radio tx, rx;
    nl_window tx_window, rx_window;
    nl_fragment value = fragment(1, 1, 0), output;
    unsigned i;
    value.flags = NL_FLAG_BURST;
    STATUS(nl_radio_init(&tx, 0x06, 1000, 1000, 0), NL_OK);
    STATUS(nl_radio_init(&rx, 0x06, 1000, 1000, 0), NL_OK);
    STATUS(nl_radio_enqueue(&tx, &value), NL_OK);
    STATUS(nl_radio_next_window(&tx, 0, &tx_window), NL_OK);
    STATUS(nl_radio_next_window(&rx, 0, &rx_window), NL_OK);
    CHECK(tx_window.duration_us == 2000 && rx_window.duration_us == 1000);
    STATUS(nl_radio_receive(&rx, &value, 10), NL_OK);
    STATUS(nl_scheduler_current(&rx.scheduler, 10, &rx_window), NL_OK);
    CHECK(rx_window.duration_us == tx_window.duration_us);
    STATUS(nl_radio_receive(&rx, &value, 500), NL_ERR_DUPLICATE);
    CHECK(rx.scheduler.next_at_us == 2000);
    STATUS(nl_radio_next_window(&rx, 1000, &rx_window), NL_ERR_BUSY);
    STATUS(nl_radio_pop_tx(&tx, 1, &output), NL_OK);
    STATUS(nl_radio_next_window(&tx, 2000, &tx_window), NL_OK);
    STATUS(nl_radio_next_window(&rx, 2000, &rx_window), NL_OK);
    CHECK(tx_window.zone == 2 && rx_window.zone == 2);
    STATUS(nl_scheduler_hold_burst(&rx.scheduler, 1, 2001), NL_ERR_NOT_FOUND);
    STATUS(nl_radio_next_window(&tx, 3000, &tx_window), NL_OK);
    STATUS(nl_radio_next_window(&rx, 3000, &rx_window), NL_OK);
    CHECK(tx_window.zone == 1 && rx_window.zone == 1 && rx_window.duration_us == 1000);
    /* A full receive queue must not suppress the burst's timing information. */
    STATUS(nl_radio_init(&rx, 0x02, 1000, 1000, 0), NL_OK);
    STATUS(nl_radio_next_window(&rx, 0, &rx_window), NL_OK);
    value.flags = 0;
    for (i = 0; i < NL_RADIO_RX_DEPTH; ++i) {
        value.sequence = (uint8_t)i;
        STATUS(nl_radio_receive(&rx, &value, i), NL_OK);
    }
    value.sequence = NL_RADIO_RX_DEPTH;
    value.flags = NL_FLAG_BURST;
    STATUS(nl_radio_receive(&rx, &value, 50), NL_ERR_FULL);
    CHECK(rx.scheduler.next_at_us == 2000);
    STATUS(nl_scheduler_hold_burst(&rx.scheduler, 1, 2000), NL_ERR_NOT_FOUND);
    STATUS(nl_scheduler_init(&rx.scheduler, 2, 1000, 1000), NL_OK);
    STATUS(nl_scheduler_next(&rx.scheduler, UINT64_MAX - 1500u, false, 0, &rx_window), NL_OK);
    STATUS(nl_scheduler_hold_burst(&rx.scheduler, 1, UINT64_MAX - 1400u), NL_ERR_SIZE);
}

static void queues_and_dedup(void)
{
    nl_radio radio;
    nl_fragment value = fragment(1, 1, 0), output;
    nl_window window;
    nl_frame request, response;
    nl_pull_token token;
    unsigned i;
    STATUS(nl_radio_init(&radio, 0x02, 1000, 500, 0), NL_OK);
    for (i = 0; i < NL_RADIO_TX_DEPTH; ++i) {
        value.sequence = (uint8_t)i;
        STATUS(nl_radio_enqueue(&radio, &value), NL_OK);
    }
    STATUS(nl_radio_enqueue(&radio, &value), NL_ERR_FULL);
    STATUS(nl_radio_set_active(&radio, 0), NL_ERR_BUSY);
    STATUS(nl_radio_peek_tx(&radio, 1, &output), NL_OK);
    CHECK(output.sequence == 0 && radio.tx[1].count == NL_RADIO_TX_DEPTH);
    for (i = 0; i < NL_RADIO_TX_DEPTH; ++i) {
        STATUS(nl_radio_pop_tx(&radio, 1, &output), NL_OK);
        CHECK(output.sequence == i);
    }
    STATUS(nl_radio_pop_tx(&radio, 1, &output), NL_ERR_EMPTY);
    value.zone = 2;
    STATUS(nl_radio_enqueue(&radio, &value), NL_ERR_ACCESS);
    STATUS(nl_radio_receive(&radio, &value, 0), NL_ERR_ACCESS);
    value.zone = 1;
    for (i = 0; i < NL_RADIO_RX_DEPTH; ++i) {
        value.sequence = (uint8_t)i;
        STATUS(nl_radio_receive(&radio, &value, i), NL_OK);
    }
    CHECK(nl_radio_ready(&radio));
    STATUS(nl_radio_receive(&radio, &value, 16), NL_ERR_DUPLICATE);
    value.sequence = 0;
    STATUS(nl_radio_receive(&radio, &value, 16), NL_ERR_STALE);
    value.sequence = NL_RADIO_RX_DEPTH;
    STATUS(nl_radio_receive(&radio, &value, 16), NL_ERR_FULL);
    STATUS(nl_radio_pull(&radio, &output), NL_OK);
    CHECK(output.sequence == 0);
    /* A retransmission after queue backpressure must still be accepted. */
    value.flags = NL_FLAG_MGMT_LISTEN | NL_FLAG_BURST;
    STATUS(nl_radio_receive(&radio, &value, 17), NL_OK);
    CHECK(radio.stats.received == 17 && radio.stats.rx_full == 1);
    CHECK(radio.stats.duplicates == 1 && radio.stats.stale == 1 && radio.stats.tx_full == 1);
    STATUS(nl_radio_next_window(&radio, 18, &window), NL_OK);
    /* RX before scheduling must never carry a hold into a future window. */
    CHECK(window.zone == 1 && window.duration_us == 1000);
    STATUS(nl_radio_next_window(&radio, 1018, &window), NL_OK);
    CHECK(window.zone == 0 && window.duration_us == 1000);
    STATUS(nl_radio_next_window(&radio, 2018, &window), NL_OK);
    CHECK(window.zone == 1 && window.duration_us == 1000);
    request = (nl_frame){0};
    request.command = NL_COMMAND_PULL;
    STATUS(nl_radio_handle_frame(&radio, &request, NULL, NULL), NL_ERR_ARGUMENT);
    CHECK(radio.rx.count == NL_RADIO_RX_DEPTH);
    for (i = 1; i <= NL_RADIO_RX_DEPTH; ++i) {
        STATUS(nl_radio_handle_frame(&radio, &request, &response, &token), NL_OK);
        CHECK(response.command == NL_COMMAND_FRAGMENT);
        STATUS(nl_frame_to_fragment(&response, &output), NL_OK);
        CHECK(output.sequence == i);
        {
            nl_frame retry, wrong = response;
            STATUS(nl_radio_handle_frame(&radio, &request, &retry, &token), NL_OK);
            CHECK(memcmp(retry.data, response.data, response.data_size) == 0);
            CHECK(radio.rx.count == NL_RADIO_RX_DEPTH + 1u - i);
            ++wrong.data[1];
            STATUS(nl_radio_commit_pull(&radio, &wrong, token), NL_ERR_STALE);
            STATUS(nl_radio_commit_pull(&radio, &response, token), NL_OK);
        }
    }
    CHECK(!nl_radio_ready(&radio));
    STATUS(nl_radio_handle_frame(&radio, &request, &response, &token), NL_ERR_EMPTY);
    request.command = NL_COMMAND_PING;
    STATUS(nl_radio_handle_frame(&radio, &request, &response, &token), NL_ERR_UNSUPPORTED);
    value.zone = 0;
    value.flags = 0;
    STATUS(nl_frame_from_fragment(NL_COMMAND_PUSH, &value, &request), NL_OK);
    STATUS(nl_radio_handle_frame(&radio, &request, NULL, NULL), NL_OK);
    STATUS(nl_radio_set_active(&radio, 0), NL_OK);
    STATUS(nl_radio_next_window(&radio, 3500, &window), NL_OK);
    CHECK(window.zone == 0);
    STATUS(nl_radio_pop_tx(&radio, 0, &output), NL_OK);
    STATUS(nl_radio_next_window(&radio, 4500, &window), NL_ERR_EMPTY);
    nl_radio_request_management(&radio);
    STATUS(nl_radio_next_window(&radio, 4500, &window), NL_OK);
    CHECK(window.zone == 0);
}

static void latest_updates(void)
{
    nl_radio radio;
    nl_fragment value = fragment(1, 1, 0), output;
    nl_frame staged, next;
    nl_pull_token old_token, next_token;
    unsigned i;
    STATUS(nl_radio_init(&radio, 0x06, 1000, 0, 0), NL_OK);
    STATUS(nl_radio_set_rx_policy(&radio, NL_RX_LATEST_PER_STREAM), NL_OK);
    for (i = 0; i < 20u; ++i) {
        value.sequence = (uint8_t)i;
        value.payload[0] = (uint8_t)i;
        STATUS(nl_radio_receive(&radio, &value, i), NL_OK);
    }
    CHECK(radio.rx.count == 1 && radio.stats.coalesced == 19 && radio.stats.rx_full == 0);
    STATUS(nl_radio_set_rx_policy(&radio, NL_RX_FIFO), NL_ERR_BUSY);
    STATUS(nl_radio_prepare_pull(&radio, &staged, &old_token), NL_OK);
    value.sequence = 20;
    value.payload[0] = 20;
    STATUS(nl_radio_receive(&radio, &value, 20), NL_OK);
    STATUS(nl_radio_commit_pull(&radio, &staged, old_token), NL_ERR_STALE);
    /* A stale response must not match a different revision after sequence wrap. */
    for (i = 0; i < 255u; ++i) {
        ++value.sequence;
        value.payload[0] = 19;
        STATUS(nl_radio_receive(&radio, &value, 21u + i), NL_OK);
    }
    STATUS(nl_radio_prepare_pull(&radio, &next, &next_token), NL_OK);
    CHECK(memcmp(next.data, staged.data, staged.data_size) == 0);
    STATUS(nl_radio_commit_pull(&radio, &staged, old_token), NL_ERR_STALE);
    value.sequence = 20;
    value.payload[0] = 20;
    STATUS(nl_radio_receive(&radio, &value, 276), NL_OK);
    STATUS(nl_radio_prepare_pull(&radio, &next, &next_token), NL_OK);
    STATUS(nl_frame_to_fragment(&next, &output), NL_OK);
    CHECK(output.payload[0] == 20 && radio.rx.count == 1);
    /* Other streams and metadata can use remaining slots despite a busy stream. */
    value.zone = 2;
    STATUS(nl_radio_receive(&radio, &value, 277), NL_OK);
    value.zone = 0;
    STATUS(nl_radio_receive(&radio, &value, 278), NL_OK);
    STATUS(nl_radio_commit_pull(&radio, &next, next_token), NL_OK);
    CHECK(radio.rx.count == 2);
    STATUS(nl_radio_pull(&radio, &output), NL_OK);
    CHECK(output.zone == 2);
    STATUS(nl_radio_pull(&radio, &output), NL_OK);
    CHECK(output.zone == 0);
    STATUS(nl_radio_set_rx_policy(&radio, NL_RX_FIFO), NL_OK);
    STATUS(nl_radio_set_rx_policy(&radio, (nl_rx_policy)99), NL_ERR_ARGUMENT);
    STATUS(nl_radio_set_rx_policy(&radio, NL_RX_LATEST_PER_STREAM), NL_OK);
    /* Coalescing still succeeds at capacity; a new distinct stream gets FULL. */
    for (i = 0; i < NL_RADIO_RX_DEPTH; ++i) {
        value.origin = (uint8_t)(i % 8u);
        value.zone = (uint8_t)(1u + i / 8u);
        value.sequence = 100;
        STATUS(nl_radio_receive(&radio, &value, 300u + i), NL_OK);
    }
    value.origin = 7;
    value.zone = 2;
    value.sequence = 101;
    STATUS(nl_radio_receive(&radio, &value, 316), NL_OK);
    value.zone = 0;
    STATUS(nl_radio_receive(&radio, &value, 317), NL_ERR_FULL);
    CHECK(radio.rx.count == NL_RADIO_RX_DEPTH);
}

static void transmit_burst(void)
{
    nl_radio tx, rx;
    nl_window tx_window, rx_window;
    nl_fragment plain = fragment(1, 1, 0), burst = fragment(1, 1, 1), output;
    unsigned mode;
    burst.flags = NL_FLAG_BURST;
    for (mode = 0; mode < 2u; ++mode) {
        STATUS(nl_radio_init(&tx, 6, 1000, 1000, 0), NL_OK);
        STATUS(nl_radio_init(&rx, 6, 1000, 1000, 0), NL_OK);
        STATUS(nl_radio_prepare_tx(&tx, 0, &output, &tx_window), NL_ERR_NOT_FOUND);
        if (mode == 1u) {
            STATUS(nl_radio_enqueue(&tx, &plain), NL_OK);
            STATUS(nl_radio_enqueue(&tx, &burst), NL_OK);
        }
        STATUS(nl_radio_next_window(&tx, 0, &tx_window), NL_OK);
        STATUS(nl_radio_next_window(&rx, 0, &rx_window), NL_OK);
        CHECK(tx_window.duration_us == 1000);
        if (mode == 1u) {
            STATUS(nl_radio_prepare_tx(&tx, 100, &output, &tx_window), NL_OK);
            CHECK(output.sequence == 0 && tx_window.duration_us == 1000 && tx.tx[1].count == 2);
            STATUS(nl_radio_receive(&rx, &output, 150), NL_OK);
            STATUS(nl_radio_pop_tx(&tx, 1, &output), NL_OK);
        } else {
            /* The first fragment arrives after a window was already selected. */
            STATUS(nl_radio_prepare_tx(&tx, 100, &output, &tx_window), NL_ERR_EMPTY);
            STATUS(nl_radio_enqueue(&tx, &burst), NL_OK);
        }
        STATUS(nl_radio_prepare_tx(&tx, 400, &output, &tx_window), NL_OK);
        CHECK(output.sequence == 1 && tx_window.start_us == 0 && tx_window.duration_us == 2000);
        CHECK(tx.tx[1].count == 1);
        /* Rejected submission leaves ownership and the bounded hold intact. */
        STATUS(nl_radio_prepare_tx(&tx, 410, &output, &tx_window), NL_OK);
        CHECK(tx_window.duration_us == 2000 && tx.tx[1].count == 1);
        STATUS(nl_radio_receive(&rx, &output, 450), NL_OK);
        STATUS(nl_radio_pop_tx(&tx, 1, &output), NL_OK);
        STATUS(nl_scheduler_current(&rx.scheduler, 450, &rx_window), NL_OK);
        CHECK(tx_window.duration_us == rx_window.duration_us);
        STATUS(nl_radio_next_window(&tx, 1000, &tx_window), NL_ERR_BUSY);
        STATUS(nl_radio_next_window(&rx, 1000, &rx_window), NL_ERR_BUSY);
        STATUS(nl_radio_next_window(&tx, 2000, &tx_window), NL_OK);
        STATUS(nl_radio_next_window(&rx, 2000, &rx_window), NL_OK);
        CHECK(tx_window.zone == 2 && rx_window.zone == 2);
        STATUS(nl_radio_prepare_tx(&tx, 3000, &output, &tx_window), NL_ERR_NOT_FOUND);
        STATUS(nl_radio_next_window(&tx, 3000, &tx_window), NL_OK);
        STATUS(nl_radio_next_window(&rx, 3000, &rx_window), NL_OK);
        CHECK(tx_window.duration_us == 1000 && rx_window.duration_us == 1000);
    }
}

static void token_exhaustion(void)
{
    nl_radio radio;
    nl_fragment value = fragment(1, 1, 0), output;
    nl_frame response;
    nl_pull_token token;
    STATUS(nl_radio_init(&radio, 2, 1000, 0, 0), NL_OK);
    STATUS(nl_radio_set_rx_policy(&radio, NL_RX_LATEST_PER_STREAM), NL_OK);
    /* Boundary injection avoids exhausting uint64 revisions by actual traffic. */
    radio.next_rx_token = UINT64_MAX - 1u;
    STATUS(nl_radio_receive(&radio, &value, 0), NL_OK);
    STATUS(nl_radio_prepare_pull(&radio, &response, &token), NL_OK);
    CHECK(token == UINT64_MAX);
    ++value.sequence;
    STATUS(nl_radio_receive(&radio, &value, 1), NL_ERR_SIZE);
    CHECK(radio.rx.count == 1 && radio.stats.received == 1 && radio.stats.coalesced == 0);
    CHECK(radio.streams.sequence[1][1] == 0);
    STATUS(nl_radio_commit_pull(&radio, &response, token), NL_OK);
    STATUS(nl_radio_receive(&radio, &value, 2), NL_ERR_SIZE);
    CHECK(!nl_radio_ready(&radio) && radio.next_rx_token == UINT64_MAX);
    STATUS(nl_radio_pull(&radio, &output), NL_ERR_EMPTY);
}

int main(void)
{
    scheduling();
    synchronized_burst();
    queues_and_dedup();
    latest_updates();
    transmit_burst();
    token_exhaustion();
    puts("radio: timed rotation, metadata, bounded bursts, congestion and SPI commands passed");
    return EXIT_SUCCESS;
}
