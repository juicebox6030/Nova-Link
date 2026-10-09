#include "nl_test.h"

#include "nova_link/nl_link.h"

static void test_crc8_check_value(void)
{
    const uint8_t check[] = "123456789";
    CHECK_EQ(nl_crc8(0, check, 9), 0xF4); /* CRC-8/SMBUS catalogue value */
    CHECK_EQ(nl_crc8(0, NULL, 0), 0x00);
    /* Incremental == one-shot. */
    CHECK_EQ(nl_crc8(nl_crc8(0, check, 4), check + 4, 5), 0xF4);
}

static void test_encode_golden(void)
{
    uint8_t out[16];
    CHECK_EQ(nl_link_encode(NL_CMD_PING, NULL, 0, out, sizeof(out)), 4);
    const uint8_t ping[] = {0xAA, 0x01, 0x00, 0x15};
    CHECK_MEM(out, ping, sizeof(ping));

    const uint8_t data[] = {0x20, 0x05, 0x41};
    CHECK_EQ(nl_link_encode(NL_CMD_PUSH, data, 3, out, sizeof(out)), 7);
    CHECK_EQ(out[0], 0xAA);
    CHECK_EQ(out[1], 0x03);
    CHECK_EQ(out[2], 3);
    CHECK_MEM(&out[3], data, 3);
    CHECK_EQ(out[6], nl_crc8(0, &out[1], 5));
}

static void test_encode_errors(void)
{
    uint8_t big[NL_LINK_MAX_DATA + 1] = {0};
    uint8_t out[NL_LINK_FRAME_MAX + 8];
    CHECK_EQ(nl_link_encode(NL_CMD_PUSH, big, sizeof(big), out, sizeof(out)), NL_ERR_SIZE);
    CHECK_EQ(nl_link_encode(NL_CMD_PUSH, big, 10, out, 13), NL_ERR_SIZE);
    CHECK_EQ(nl_link_encode(NL_CMD_PUSH, big, 10, out, 14), 14);
    CHECK_EQ(nl_link_encode(NL_CMD_PUSH, big, NL_LINK_MAX_DATA, out, sizeof(out)),
             (int)NL_LINK_FRAME_MAX);
}

static void test_decode_with_filler(void)
{
    uint8_t buf[64] = {0};
    const uint8_t data[] = {1, 2, 3, 0xAA, 5};
    int n = nl_link_encode(NL_RSP_FRAGMENT, data, sizeof(data), &buf[7], 40);
    CHECK(n > 0);
    buf[3] = 0xAA; /* stray sync byte in the filler before the frame */
    nl_link_frame_t f;
    size_t used = 0;
    CHECK_EQ(nl_link_decode(buf, sizeof(buf), &f, &used), NL_OK);
    CHECK_EQ(f.cmd, NL_RSP_FRAGMENT);
    CHECK_EQ(f.len, sizeof(data));
    CHECK_MEM(f.data, data, sizeof(data));
    CHECK_EQ(used, 7 + (size_t)n);
}

static void test_decode_errors(void)
{
    uint8_t buf[16];
    nl_link_frame_t f;
    size_t used;
    memset(buf, 0, sizeof(buf));
    CHECK_EQ(nl_link_decode(buf, sizeof(buf), &f, &used), NL_ERR_EMPTY);
    CHECK_EQ(used, sizeof(buf));

    int n = nl_link_encode(NL_CMD_STATUS, NULL, 0, buf, sizeof(buf));
    buf[n - 1] ^= 0x01;
    CHECK_EQ(nl_link_decode(buf, (size_t)n, &f, NULL), NL_ERR_CRC);

    /* Truncated frame. */
    n = nl_link_encode(NL_CMD_PUSH, (const uint8_t *)"abcd", 4, buf, sizeof(buf));
    CHECK_EQ(nl_link_decode(buf, (size_t)n - 1, &f, NULL), NL_ERR_EMPTY);
}

static void test_no_phantom_frame_in_filler(void)
{
    /* "AA 00 00 00" has a correct CRC-8 (init 0); it must not decode. */
    uint8_t zeros[16] = {0};
    zeros[5] = 0xAA;
    nl_link_frame_t f;
    CHECK_EQ(nl_link_decode(zeros, sizeof(zeros), &f, NULL), NL_ERR_EMPTY);
    uint8_t ones[16];
    memset(ones, 0xFF, sizeof(ones));
    ones[2] = 0xAA;
    CHECK_EQ(nl_link_decode(ones, sizeof(ones), &f, NULL), NL_ERR_EMPTY);

    nl_link_parser_t p;
    nl_link_parser_init(&p);
    int frames = 0;
    for (size_t i = 0; i < sizeof(zeros); i++) {
        frames += nl_link_parser_feed(&p, zeros[i]);
    }
    CHECK_EQ(frames, 0);
    CHECK_EQ(p.cmd_errors, 1);
}

static void test_decode_back_to_back(void)
{
    uint8_t buf[64];
    size_t pos = 0;
    pos += (size_t)nl_link_encode(NL_CMD_RADIO_CONFIG, (const uint8_t *)"x", 1, buf, 64);
    pos += (size_t)nl_link_encode(NL_CMD_ZONE_CONFIG, (const uint8_t *)"yz", 2, &buf[pos],
                                  64 - pos);
    nl_link_frame_t f;
    size_t used;
    CHECK_EQ(nl_link_decode(buf, pos, &f, &used), NL_OK);
    CHECK_EQ(f.cmd, NL_CMD_RADIO_CONFIG);
    CHECK_EQ(nl_link_decode(&buf[used], pos - used, &f, NULL), NL_OK);
    CHECK_EQ(f.cmd, NL_CMD_ZONE_CONFIG);
    CHECK_EQ(f.len, 2);
}

static void test_stream_parser(void)
{
    nl_link_parser_t p;
    nl_link_parser_init(&p);
    uint8_t buf[64];
    /* Noise includes a false SYNC followed by an idle-line byte, and a
     * doubled SYNC directly before the real frame. */
    const uint8_t noise[] = {0x00, 0xAA, 0xFF, 0x13, 0xAA};
    int frames = 0;
    for (size_t i = 0; i < sizeof(noise); i++) {
        frames += nl_link_parser_feed(&p, noise[i]);
    }
    int n = nl_link_encode(NL_CMD_PUSH, (const uint8_t *)"hello", 5, buf, sizeof(buf));
    for (int i = 0; i < n; i++) {
        frames += nl_link_parser_feed(&p, buf[i]);
    }
    CHECK_EQ(frames, 1);
    CHECK_EQ(p.frame.cmd, NL_CMD_PUSH);
    CHECK_EQ(p.frame.len, 5);
    CHECK_MEM(p.frame.data, "hello", 5);

    /* Corrupted frame is counted and dropped; the next one still parses. */
    buf[4] ^= 0x40;
    frames = 0;
    for (int i = 0; i < n; i++) {
        frames += nl_link_parser_feed(&p, buf[i]);
    }
    buf[4] ^= 0x40;
    for (int i = 0; i < n; i++) {
        frames += nl_link_parser_feed(&p, buf[i]);
    }
    CHECK_EQ(frames, 1);
    CHECK(p.crc_errors >= 1);
}

static void test_params_roundtrip(void)
{
    nl_radio_params_t p, d;
    nl_radio_params_default(&p);
    memset(&d, 0, sizeof(d)); /* padding bytes compare equal */
    p.origin_id = 6;
    p.band = NL_BAND_DUAL;
    p.tx_policy = NL_TX_IN_SLOT;
    p.tx_repeats = 2;
    p.dwell_us = 123456;
    p.tracker_stale_us = 0xA5A5A5A5u;
    p.mgmt_repeats = 9;
    p.cca_backoff_us = 0x12345678u;
    uint8_t buf[NL_RADIO_PARAMS_WIRE_SIZE];
    CHECK_EQ(nl_radio_params_encode(&p, buf, sizeof(buf)), NL_RADIO_PARAMS_WIRE_SIZE);
    CHECK_EQ(nl_radio_params_decode(buf, sizeof(buf), &d), NL_OK);
    CHECK_MEM(&d, &p, sizeof(p));

    CHECK_EQ(nl_radio_params_decode(buf, sizeof(buf) - 1, &d), NL_ERR_SIZE);
    buf[3] = 0; /* tx_repeats 0 */
    CHECK_EQ(nl_radio_params_decode(buf, sizeof(buf), &d), NL_ERR_ARG);
    buf[3] = 1;
    buf[0] = 8; /* origin out of range */
    CHECK_EQ(nl_radio_params_decode(buf, sizeof(buf), &d), NL_ERR_ARG);
    buf[0] = 0;
    buf[1] = 3; /* band */
    CHECK_EQ(nl_radio_params_decode(buf, sizeof(buf), &d), NL_ERR_ARG);
}

static void test_plan_roundtrip(void)
{
    nl_zone_plan_t p, d;
    memset(&p, 0, sizeof(p));
    for (int z = 0; z < NL_NUM_ZONES; z++) {
        p.zone[z].priority = (uint8_t)z;
        p.zone[z].subghz_hz = 903000000u + 3000000u * (uint32_t)z;
        p.zone[z].ghz24_hz = 2405000000u + 10000000u * (uint32_t)z;
    }
    uint8_t buf[NL_ZONE_PLAN_WIRE_SIZE];
    CHECK_EQ(nl_zone_plan_encode(&p, buf, sizeof(buf)), NL_ZONE_PLAN_WIRE_SIZE);
    CHECK_EQ(nl_zone_plan_decode(buf, sizeof(buf), &d), NL_OK);
    for (int z = 0; z < NL_NUM_ZONES; z++) {
        CHECK_EQ(d.zone[z].priority, p.zone[z].priority);
        CHECK_EQ(d.zone[z].subghz_hz, p.zone[z].subghz_hz);
        CHECK_EQ(d.zone[z].ghz24_hz, p.zone[z].ghz24_hz);
    }
    /* Little-endian on the wire: zone 0 sub-GHz = 903 MHz = 0x35D2AFC0. */
    const uint8_t z0[] = {0x00, 0xC0, 0xAF, 0xD2, 0x35};
    CHECK_MEM(buf, z0, sizeof(z0));
    CHECK_EQ(nl_zone_plan_encode(&p, buf, sizeof(buf) - 1), NL_ERR_SIZE);
}

static void test_status_pong_roundtrip(void)
{
    nl_radio_status_t s = {.proto_version = 1, .flags = 3, .rx_queue_len = 4,
                           .tx_queue_len = 5, .rx_ok = 1000000, .rx_dup = 7,
                           .rx_dropped = 8, .rx_ignored = 9, .tx_sent = 0xFFFFFFFFu,
                           .tx_dropped = 11};
    nl_radio_status_t sd;
    uint8_t buf[NL_RADIO_STATUS_WIRE_SIZE];
    CHECK_EQ(nl_radio_status_encode(&s, buf, sizeof(buf)), NL_RADIO_STATUS_WIRE_SIZE);
    CHECK_EQ(nl_radio_status_decode(buf, sizeof(buf), &sd), NL_OK);
    CHECK_MEM(&sd, &s, sizeof(s));

    nl_link_pong_t p = {1, 2, 3, 4}, pd;
    CHECK_EQ(nl_link_pong_encode(&p, buf, sizeof(buf)), NL_PONG_WIRE_SIZE);
    CHECK_EQ(nl_link_pong_decode(buf, NL_PONG_WIRE_SIZE, &pd), NL_OK);
    CHECK_MEM(&pd, &p, sizeof(p));
}

int main(void)
{
    RUN(test_crc8_check_value);
    RUN(test_encode_golden);
    RUN(test_encode_errors);
    RUN(test_decode_with_filler);
    RUN(test_decode_errors);
    RUN(test_no_phantom_frame_in_filler);
    RUN(test_decode_back_to_back);
    RUN(test_stream_parser);
    RUN(test_params_roundtrip);
    RUN(test_plan_roundtrip);
    RUN(test_status_pong_roundtrip);
    return nl_test_finish();
}
