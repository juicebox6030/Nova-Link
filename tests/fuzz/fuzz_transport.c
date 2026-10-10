/* SPI frames, air fragments and the byte-wise SPI parser: decoders must never
 * read out of bounds, anything they accept must re-encode to the same bytes,
 * and the streaming parser must agree with the one-shot decoder.
 */
#include "fuzz.h"

static void frame_roundtrip(const uint8_t *data, size_t size)
{
    nl_frame frame, again;
    nl_parser parser;
    uint8_t bytes[NL_FRAME_MAX];
    size_t encoded, i;
    nl_parse_result result = NL_PARSE_WAIT;
    if (nl_frame_decode(data, size, &frame) != NL_OK) return;
    REQUIRE(nl_frame_validate(&frame) == NL_OK);
    REQUIRE(nl_frame_encode(&frame, bytes, sizeof(bytes), &encoded) == NL_OK);
    REQUIRE(encoded == size && memcmp(bytes, data, size) == 0);
    /* A fresh parser fed the same bytes reports READY exactly at the end. */
    nl_parser_reset(&parser);
    for (i = 0; i < size; ++i) {
        result = nl_parser_feed(&parser, data[i], &again);
        REQUIRE(i + 1 == size || result != NL_PARSE_READY);
    }
    REQUIRE(result == NL_PARSE_READY && frames_equal(&frame, &again));
}

static void fragment_roundtrip(const uint8_t *data, size_t size)
{
    nl_fragment fragment;
    uint8_t bytes[NL_FRAGMENT_MAX];
    size_t encoded;
    nl_frame frame;
    if (nl_fragment_decode(data, size, &fragment) != NL_OK) return;
    REQUIRE(nl_fragment_validate(&fragment) == NL_OK);
    REQUIRE(nl_fragment_encode(&fragment, bytes, sizeof(bytes), &encoded) == NL_OK);
    REQUIRE(encoded == size && memcmp(bytes, data, size) == 0);
    REQUIRE(nl_frame_from_fragment(NL_COMMAND_PUSH, &fragment, &frame) == NL_OK);
    REQUIRE(nl_frame_validate(&frame) == NL_OK);
}

/* Stream the input through one parser; the first byte picks where it resets,
 * as an adapter does at a chip-select edge or timeout.
 */
static void parser_stream(const uint8_t *data, size_t size)
{
    nl_parser parser;
    nl_frame frame, decoded;
    uint8_t bytes[NL_FRAME_MAX];
    size_t encoded, i;
    unsigned reset_every;
    if (size == 0) return;
    reset_every = data[0];
    nl_parser_reset(&parser);
    for (i = 1; i < size; ++i) {
        if (reset_every != 0 && i % reset_every == 0) nl_parser_reset(&parser);
        memset(&frame, 0xA5, sizeof(frame));
        if (nl_parser_feed(&parser, data[i], &frame) != NL_PARSE_READY) continue;
        REQUIRE(nl_frame_validate(&frame) == NL_OK);
        REQUIRE(nl_frame_encode(&frame, bytes, sizeof(bytes), &encoded) == NL_OK);
        REQUIRE(nl_frame_decode(bytes, encoded, &decoded) == NL_OK && frames_equal(&frame, &decoded));
        /* The frame just completed is exactly the last `encoded` input bytes. */
        REQUIRE(i + 1 >= encoded && memcmp(bytes, data + i + 1 - encoded, encoded) == 0);
    }
}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    frame_roundtrip(data, size);
    fragment_roundtrip(data, size);
    parser_stream(data, size);
    return 0;
}
