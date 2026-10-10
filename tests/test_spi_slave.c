#include "test.h"
#include "nova_link/spi_slave.h"

static const uint8_t pull[] = {0xAA, 0x01, 0x02};

static void requests(void)
{
    nl_radio radio;
    nl_spi_slave slave;
    nl_frame frame;
    nl_fragment input = fragment(1, 1, 7), output;
    uint8_t bytes[NL_FRAME_MAX + 1u], response[NL_FRAME_MAX];
    size_t size, response_size = 123;
    nl_pull_token receipt = 456;
    unsigned i;
    STATUS(nl_spi_slave_init(NULL, &radio), NL_ERR_ARGUMENT);
    STATUS(nl_spi_slave_init(&slave, NULL), NL_ERR_ARGUMENT);
    STATUS(nl_radio_init(&radio, 2, 1000, 0, 0), NL_OK);
    STATUS(nl_spi_slave_init(&slave, &radio), NL_OK);
    STATUS(nl_frame_from_fragment(NL_COMMAND_PUSH, &input, &frame), NL_OK);
    STATUS(nl_frame_encode(&frame, bytes, sizeof(bytes), &size), NL_OK);
    for (i = 0; i < size; ++i) {
        nl_status status = nl_spi_slave_exchange(&slave, bytes, i,
            response, sizeof(response), &response_size, &receipt);
        CHECK(status != NL_OK);
        CHECK(response_size == 123 && receipt == 456);
        CHECK(radio.tx[1].count == 0);
    }
    bytes[size] = 0;
    STATUS(nl_spi_slave_exchange(&slave, bytes, size + 1u, response,
        sizeof(response), &response_size, &receipt), NL_ERR_SIZE);
    CHECK(radio.tx[1].count == 0);
    STATUS(nl_spi_slave_exchange(&slave, bytes, sizeof(bytes), response,
        sizeof(response), &response_size, &receipt), NL_ERR_SIZE);
    STATUS(nl_spi_slave_exchange(&slave, pull, sizeof(pull), response,
        sizeof(response), &response_size, &receipt), NL_ERR_EMPTY);
    CHECK(response_size == 123 && receipt == 456);
    for (i = 0; i < NL_RADIO_TX_DEPTH; ++i) {
        STATUS(nl_spi_slave_exchange(&slave, bytes, size, response,
            sizeof(response), &response_size, &receipt), NL_OK);
        CHECK(response_size == 0 && receipt == 0);
    }
    response_size = 123;
    receipt = 456;
    STATUS(nl_spi_slave_exchange(&slave, bytes, size, response,
        sizeof(response), &response_size, &receipt), NL_ERR_FULL);
    CHECK(response_size == 123 && receipt == 456);
    CHECK(radio.tx[1].count == NL_RADIO_TX_DEPTH);
    STATUS(nl_radio_pop_tx(&radio, 1, &output), NL_OK);
    same_fragment(&input, &output);
    bytes[0] = 0;
    STATUS(nl_spi_slave_exchange(&slave, bytes, size, response,
        sizeof(response), &response_size, &receipt), NL_ERR_FORMAT);
}

static void receipts(void)
{
    nl_radio radio;
    nl_spi_slave slave;
    nl_fragment input = fragment(1, 1, 7), output;
    uint8_t response[NL_FRAME_MAX], again[NL_FRAME_MAX];
    size_t size = 123, again_size;
    nl_pull_token receipt = 456, again_receipt;
    STATUS(nl_radio_init(&radio, 2, 1000, 0, 0), NL_OK);
    STATUS(nl_radio_set_rx_policy(&radio, NL_RX_LATEST_PER_STREAM), NL_OK);
    STATUS(nl_spi_slave_init(&slave, &radio), NL_OK);
    STATUS(nl_radio_receive(&radio, &input, 0), NL_OK);
    memset(response, 0x55, sizeof(response));
    STATUS(nl_spi_slave_exchange(&slave, pull, sizeof(pull), response, 1,
        &size, &receipt), NL_ERR_SIZE);
    CHECK(size == 123 && receipt == 456 && response[0] == 0x55);
    CHECK(!nl_spi_slave_pending(&slave) && nl_radio_ready(&radio));
    STATUS(nl_spi_slave_exchange(&slave, pull, sizeof(pull), response,
        sizeof(response), &size, &receipt), NL_OK);
    CHECK(nl_spi_slave_pending(&slave) && nl_radio_ready(&radio));
    STATUS(nl_spi_slave_exchange(&slave, pull, sizeof(pull), again,
        sizeof(again), &again_size, &again_receipt), NL_OK);
    CHECK(size == again_size && receipt == again_receipt);
    CHECK(memcmp(response, again, size) == 0);
    STATUS(nl_spi_slave_cancel(&slave, receipt + 1u), NL_ERR_STALE);
    STATUS(nl_spi_slave_commit(&slave, receipt + 1u), NL_ERR_STALE);
    CHECK(nl_spi_slave_pending(&slave));
    STATUS(nl_spi_slave_cancel(&slave, receipt), NL_OK);
    CHECK(!nl_spi_slave_pending(&slave) && nl_radio_ready(&radio));
    again_receipt = receipt;
    STATUS(nl_spi_slave_exchange(&slave, pull, sizeof(pull), response,
        sizeof(response), &size, &receipt), NL_OK);
    CHECK(receipt != again_receipt);
    STATUS(nl_spi_slave_commit(&slave, again_receipt), NL_ERR_STALE);
    CHECK(nl_spi_slave_pending(&slave));
    input.sequence = 8;
    STATUS(nl_radio_receive(&radio, &input, 1), NL_OK);
    /* Queue replacement cannot mutate the response already owned by the peer. */
    STATUS(nl_spi_slave_exchange(&slave, pull, sizeof(pull), again,
        sizeof(again), &again_size, &again_receipt), NL_OK);
    CHECK(size == again_size && receipt == again_receipt);
    CHECK(memcmp(response, again, size) == 0);
    STATUS(nl_spi_slave_commit(&slave, receipt), NL_ERR_STALE);
    CHECK(!nl_spi_slave_pending(&slave) && nl_radio_ready(&radio));
    STATUS(nl_spi_slave_exchange(&slave, pull, sizeof(pull), response,
        sizeof(response), &size, &again_receipt), NL_OK);
    CHECK(again_receipt != receipt);
    STATUS(nl_spi_slave_commit(&slave, receipt), NL_ERR_STALE);
    CHECK(nl_spi_slave_pending(&slave));
    STATUS(nl_spi_slave_commit(&slave, again_receipt), NL_OK);
    CHECK(!nl_spi_slave_pending(&slave) && !nl_radio_ready(&radio));
    STATUS(nl_spi_slave_commit(&slave, again_receipt), NL_ERR_STALE);
    input.sequence = 9;
    STATUS(nl_radio_receive(&radio, &input, 2), NL_OK);
    STATUS(nl_spi_slave_exchange(&slave, pull, sizeof(pull), response,
        sizeof(response), &size, &receipt), NL_OK);
    STATUS(nl_radio_pull(&radio, &output), NL_OK);
    STATUS(nl_spi_slave_commit(&slave, receipt), NL_ERR_EMPTY);
    CHECK(!nl_spi_slave_pending(&slave));
    input.sequence = 10;
    STATUS(nl_radio_receive(&radio, &input, 3), NL_OK);
    slave.next_receipt = UINT64_MAX;
    STATUS(nl_spi_slave_exchange(&slave, pull, sizeof(pull), response,
        sizeof(response), &size, &receipt), NL_OK);
    CHECK(receipt == UINT64_MAX);
    STATUS(nl_spi_slave_cancel(&slave, receipt), NL_OK);
    size = 123;
    receipt = 456;
    STATUS(nl_spi_slave_exchange(&slave, pull, sizeof(pull), response,
        sizeof(response), &size, &receipt), NL_ERR_SIZE);
    CHECK(size == 123 && receipt == 456 && nl_radio_ready(&radio));
}

static void complete_sizes(void)
{
    nl_radio radio;
    nl_spi_slave slave;
    nl_fragment input = fragment(1, 1, 0), output;
    nl_frame frame;
    uint8_t bytes[NL_FRAME_MAX], response[NL_FRAME_MAX];
    size_t size, response_size;
    nl_pull_token receipt;
    unsigned count, i;
    STATUS(nl_radio_init(&radio, 2, 1000, 0, 0), NL_OK);
    STATUS(nl_spi_slave_init(&slave, &radio), NL_OK);
    for (i = 0; i < NL_PAYLOAD_MAX; ++i) input.payload[i] = (uint8_t)i;
    for (count = 0; count <= NL_PAYLOAD_MAX; ++count) {
        input.sequence = (uint8_t)count;
        input.payload_size = (uint8_t)count;
        STATUS(nl_frame_from_fragment(NL_COMMAND_PUSH, &input, &frame), NL_OK);
        STATUS(nl_frame_encode(&frame, bytes, sizeof(bytes), &size), NL_OK);
        CHECK(size == (size_t)count + 5u);
        STATUS(nl_spi_slave_exchange(&slave, bytes, size, response,
            sizeof(response), &response_size, &receipt), NL_OK);
        STATUS(nl_radio_pop_tx(&radio, 1, &output), NL_OK);
        same_fragment(&input, &output);
        STATUS(nl_radio_receive(&radio, &output, count), NL_OK);
        STATUS(nl_spi_slave_exchange(&slave, pull, sizeof(pull), response,
            sizeof(response), &response_size, &receipt), NL_OK);
        CHECK(response_size == size);
        STATUS(nl_frame_decode(response, response_size, &frame), NL_OK);
        CHECK(frame.command == NL_COMMAND_FRAGMENT);
        STATUS(nl_frame_to_fragment(&frame, &output), NL_OK);
        same_fragment(&input, &output);
        STATUS(nl_spi_slave_commit(&slave, receipt), NL_OK);
    }
}

int main(void)
{
    requests();
    receipts();
    complete_sizes();
    return EXIT_SUCCESS;
}
