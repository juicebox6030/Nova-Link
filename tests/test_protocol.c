#include "test.h"

static void golden_vectors(void)
{
    nl_fragment value = fragment(5, 3, 0xFE), decoded;
    nl_frame frame, parsed;
    uint8_t bytes[NL_FRAME_MAX];
    const uint8_t golden[] = {0xAA, 0x06, 0x03, 0xAF, 0xFE, 0x00, 0xAA, 0xFF};
    size_t size = 0;
    value.flags = NL_FLAG_BURST | NL_FLAG_MGMT_LISTEN;
    STATUS(nl_frame_from_fragment(NL_COMMAND_PUSH, &value, &frame), NL_OK);
    STATUS(nl_frame_encode(&frame, bytes, sizeof(bytes), &size), NL_OK);
    CHECK(size == sizeof(golden));
    CHECK(memcmp(bytes, golden, size) == 0);
    STATUS(nl_frame_decode(golden, sizeof(golden), &parsed), NL_OK);
    STATUS(nl_frame_to_fragment(&parsed, &decoded), NL_OK);
    same_fragment(&value, &decoded);
}

static void exhaustive_fragments(void)
{
    unsigned header, payload_size, sequence;
    uint8_t bytes[NL_FRAGMENT_MAX];
    nl_fragment input = {0}, output;
    size_t size;
    for (header = 0; header < 256u; ++header) {
        input.origin = (uint8_t)(header >> 5);
        input.zone = (uint8_t)((header >> 2) & 7u);
        input.flags = (uint8_t)(header & 3u);
        for (payload_size = 0; payload_size <= NL_PAYLOAD_MAX; ++payload_size) {
            input.payload_size = (uint8_t)payload_size;
            input.sequence = (uint8_t)(header + payload_size);
            for (sequence = 0; sequence < payload_size; ++sequence)
                input.payload[sequence] = (uint8_t)(sequence ^ header);
            STATUS(nl_fragment_encode(&input, bytes, sizeof(bytes), &size), NL_OK);
            CHECK(bytes[0] == header && size == payload_size + 2u);
            STATUS(nl_fragment_decode(bytes, size, &output), NL_OK);
            same_fragment(&input, &output);
        }
    }
}

static void invalid_inputs(void)
{
    nl_fragment value = fragment(1, 2, 3), unchanged, decoded;
    nl_frame frame = {0}, output, original;
    uint8_t bytes[NL_FRAME_MAX + 1u];
    size_t size = 999;
    memset(bytes, 0x55, sizeof(bytes));
    STATUS(nl_fragment_encode(&value, bytes, 2, &size), NL_ERR_SIZE);
    CHECK(size == 999 && bytes[0] == 0x55);
    value.origin = 8;
    STATUS(nl_fragment_encode(&value, bytes, sizeof(bytes), &size), NL_ERR_ARGUMENT);
    value.origin = 1;
    value.zone = 8;
    STATUS(nl_fragment_validate(&value), NL_ERR_ARGUMENT);
    value.zone = 2;
    value.flags = 4;
    STATUS(nl_fragment_validate(&value), NL_ERR_ARGUMENT);
    value.flags = 0;
    value.payload_size = 101;
    STATUS(nl_fragment_validate(&value), NL_ERR_SIZE);
    STATUS(nl_fragment_validate(NULL), NL_ERR_ARGUMENT);
    decoded = fragment(7, 7, 77);
    unchanged = decoded;
    STATUS(nl_fragment_decode(bytes, 1, &decoded), NL_ERR_SIZE);
    same_fragment(&unchanged, &decoded);
    STATUS(nl_fragment_decode(bytes, NL_FRAGMENT_MAX + 1u, &decoded), NL_ERR_SIZE);
    STATUS(nl_fragment_decode(NULL, 2, &decoded), NL_ERR_ARGUMENT);

    frame.command = NL_COMMAND_PULL;
    STATUS(nl_frame_encode(&frame, bytes, sizeof(bytes), &size), NL_OK);
    CHECK(size == 3 && bytes[1] == 1);
    original = frame;
    output = original;
    bytes[0] = 0;
    STATUS(nl_frame_decode(bytes, size, &output), NL_ERR_FORMAT);
    CHECK(memcmp(&output, &original, sizeof(output)) == 0);
    bytes[0] = NL_TRANSPORT_SYNC;
    bytes[1] = 2;
    STATUS(nl_frame_decode(bytes, size, &output), NL_ERR_SIZE);
    bytes[1] = 1;
    bytes[2] = 0xFF;
    STATUS(nl_frame_decode(bytes, size, &output), NL_ERR_UNSUPPORTED);
    frame.data_size = 1;
    STATUS(nl_frame_validate(&frame), NL_ERR_SIZE);
    frame.command = NL_COMMAND_PUSH;
    STATUS(nl_frame_validate(&frame), NL_ERR_SIZE);
    frame.data_size = 103;
    STATUS(nl_frame_validate(&frame), NL_ERR_SIZE);
    STATUS(nl_frame_from_fragment(NL_COMMAND_PING, &unchanged, &frame), NL_ERR_UNSUPPORTED);
    STATUS(nl_frame_to_fragment(&original, &decoded), NL_ERR_UNSUPPORTED);
}

static void incremental_parser(void)
{
    nl_fragment value = fragment(7, 0, 0xAA), decoded;
    nl_frame input, output;
    nl_parser parser;
    uint8_t bytes[NL_FRAME_MAX], encoded[NL_FRAME_MAX];
    size_t size, i, iteration, encoded_size;
    uint32_t random = 0x12345678u;
    value.payload_size = NL_PAYLOAD_MAX;
    memset(value.payload, NL_TRANSPORT_SYNC, sizeof(value.payload));
    STATUS(nl_frame_from_fragment(NL_COMMAND_FRAGMENT, &value, &input), NL_OK);
    STATUS(nl_frame_encode(&input, bytes, sizeof(bytes), &size), NL_OK);
    CHECK(size == NL_FRAME_MAX && bytes[1] == 103);
    nl_parser_reset(&parser);
    CHECK(nl_parser_feed(&parser, 0, &output) == NL_PARSE_WAIT);
    CHECK(nl_parser_feed(&parser, NL_TRANSPORT_SYNC, &output) == NL_PARSE_WAIT);
    CHECK(nl_parser_feed(&parser, 0, &output) == NL_PARSE_REJECTED);
    for (iteration = 0; iteration < 3; ++iteration) {
        for (i = 0; i < size; ++i)
            CHECK(nl_parser_feed(&parser, bytes[i], &output) ==
                (i + 1u == size ? NL_PARSE_READY : NL_PARSE_WAIT));
        STATUS(nl_frame_to_fragment(&output, &decoded), NL_OK);
        same_fragment(&value, &decoded);
    }
    /* A repeated sync in the length position can begin the next valid frame. */
    CHECK(nl_parser_feed(&parser, NL_TRANSPORT_SYNC, &output) == NL_PARSE_WAIT);
    CHECK(nl_parser_feed(&parser, NL_TRANSPORT_SYNC, &output) == NL_PARSE_REJECTED);
    for (i = 1; i < size; ++i)
        CHECK(nl_parser_feed(&parser, bytes[i], &output) ==
            (i + 1u == size ? NL_PARSE_READY : NL_PARSE_WAIT));
    /* Transaction timeout discards partial data. */
    for (i = 0; i < size / 2u; ++i) (void)nl_parser_feed(&parser, bytes[i], &output);
    nl_parser_reset(&parser);
    for (i = 0; i < size; ++i) (void)nl_parser_feed(&parser, bytes[i], &output);
    STATUS(nl_frame_to_fragment(&output, &decoded), NL_OK);
    same_fragment(&value, &decoded);

    /* Reproducible random byte streams exercise the bounded parser under sanitizers. */
    nl_parser_reset(&parser);
    for (i = 0; i < 200000u; ++i) {
        random = random * 1664525u + 1013904223u;
        if (nl_parser_feed(&parser, (uint8_t)(random >> 24), &output) == NL_PARSE_READY) {
            STATUS(nl_frame_validate(&output), NL_OK);
            STATUS(nl_frame_encode(&output, encoded, sizeof(encoded), &encoded_size), NL_OK);
            STATUS(nl_frame_decode(encoded, encoded_size, &input), NL_OK);
        }
    }
    CHECK(nl_parser_feed(NULL, 0, &output) == NL_PARSE_REJECTED);
    CHECK(nl_parser_feed(&parser, 0, NULL) == NL_PARSE_REJECTED);
}

int main(void)
{
    golden_vectors();
    exhaustive_fragments();
    invalid_inputs();
    incremental_parser();
    puts("protocol: golden vectors, all headers/lengths and parser noise passed");
    return EXIT_SUCCESS;
}
