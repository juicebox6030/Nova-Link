#include "nl_test.h"

#include "nova_link/nl_fragment.h"

static void test_header_layout(void)
{
    CHECK_EQ(nl_fragment_make_header(5, 3, NL_FLAG_BURST), 0xAE);
    CHECK_EQ(nl_fragment_make_header(7, 7, NL_FLAG_MASK), 0xFF);
    CHECK_EQ(nl_fragment_make_header(0, 0, 0), 0x00);
    CHECK_EQ(nl_fragment_make_header(0, 0, NL_FLAG_MGMT_LISTEN), 0x01);
    CHECK_EQ(nl_fragment_origin(0xAE), 5);
    CHECK_EQ(nl_fragment_zone(0xAE), 3);
    CHECK_EQ(nl_fragment_flags(0xAE), NL_FLAG_BURST);
}

static void test_roundtrip(void)
{
    uint8_t payload[NL_MAX_PAYLOAD];
    for (size_t i = 0; i < sizeof(payload); i++) {
        payload[i] = (uint8_t)(i * 7 + 1);
    }
    uint8_t buf[NL_MAX_FRAGMENT];
    for (unsigned len = 0; len <= NL_MAX_PAYLOAD; len += 25) {
        nl_fragment_t f = {.origin_id = 6, .zone_id = 2, .flags = NL_FLAG_MGMT_LISTEN,
                           .seq = 200, .payload = payload, .payload_len = (uint8_t)len};
        int n = nl_fragment_encode(&f, buf, sizeof(buf));
        CHECK_EQ(n, 2 + (int)len);
        nl_fragment_t d;
        CHECK_EQ(nl_fragment_decode(buf, (size_t)n, &d), NL_OK);
        CHECK_EQ(d.origin_id, 6);
        CHECK_EQ(d.zone_id, 2);
        CHECK_EQ(d.flags, NL_FLAG_MGMT_LISTEN);
        CHECK_EQ(d.seq, 200);
        CHECK_EQ(d.payload_len, len);
        if (len > 0) {
            CHECK_MEM(d.payload, payload, len);
        } else {
            CHECK(d.payload == NULL);
        }
    }
}

static void test_golden_bytes(void)
{
    const uint8_t payload[] = {0xDE, 0xAD};
    nl_fragment_t f = {.origin_id = 1, .zone_id = 4, .flags = NL_FLAG_BURST, .seq = 0x7F,
                       .payload = payload, .payload_len = 2};
    uint8_t buf[8];
    CHECK_EQ(nl_fragment_encode(&f, buf, sizeof(buf)), 4);
    const uint8_t expect[] = {0x32, 0x7F, 0xDE, 0xAD};
    CHECK_MEM(buf, expect, sizeof(expect));
}

static void test_encode_errors(void)
{
    uint8_t payload[NL_MAX_PAYLOAD + 1] = {0};
    uint8_t buf[NL_MAX_FRAGMENT + 1];
    nl_fragment_t f = {.origin_id = 0, .zone_id = 0, .payload = payload};

    f.payload_len = NL_MAX_PAYLOAD + 1;
    CHECK_EQ(nl_fragment_encode(&f, buf, sizeof(buf)), NL_ERR_SIZE);
    f.payload_len = 10;
    CHECK_EQ(nl_fragment_encode(&f, buf, 11), NL_ERR_SIZE);
    f.origin_id = 8;
    CHECK_EQ(nl_fragment_encode(&f, buf, sizeof(buf)), NL_ERR_ARG);
    f.origin_id = 0;
    f.zone_id = 8;
    CHECK_EQ(nl_fragment_encode(&f, buf, sizeof(buf)), NL_ERR_ARG);
    f.zone_id = 0;
    f.flags = 0x04;
    CHECK_EQ(nl_fragment_encode(&f, buf, sizeof(buf)), NL_ERR_ARG);
    f.flags = 0;
    f.payload = NULL;
    CHECK_EQ(nl_fragment_encode(&f, buf, sizeof(buf)), NL_ERR_ARG);
    f.payload_len = 0;
    CHECK_EQ(nl_fragment_encode(&f, buf, sizeof(buf)), 2);
}

static void test_decode_errors(void)
{
    uint8_t buf[NL_MAX_FRAGMENT + 1] = {0};
    nl_fragment_t f;
    CHECK_EQ(nl_fragment_decode(buf, 0, &f), NL_ERR_SIZE);
    CHECK_EQ(nl_fragment_decode(buf, 1, &f), NL_ERR_SIZE);
    CHECK_EQ(nl_fragment_decode(buf, NL_MAX_FRAGMENT + 1, &f), NL_ERR_SIZE);
    CHECK_EQ(nl_fragment_decode(buf, NL_MAX_FRAGMENT, &f), NL_OK);
    CHECK_EQ(nl_fragment_decode(NULL, 4, &f), NL_ERR_ARG);
}

static void test_encode_in_place(void)
{
    /* Payload may alias the output buffer at offset 2 (memmove). */
    uint8_t buf[8] = {0, 0, 1, 2, 3, 4};
    nl_fragment_t f = {.origin_id = 2, .zone_id = 1, .seq = 9, .payload = &buf[2],
                       .payload_len = 4};
    CHECK_EQ(nl_fragment_encode(&f, buf, sizeof(buf)), 6);
    const uint8_t expect[] = {0x44, 9, 1, 2, 3, 4};
    CHECK_MEM(buf, expect, sizeof(expect));
}

static void test_seq_cmp(void)
{
    CHECK_EQ(nl_seq_cmp(5, 5), 0);
    CHECK(nl_seq_cmp(6, 5) > 0);
    CHECK(nl_seq_cmp(5, 6) < 0);
    CHECK(nl_seq_cmp(0, 255) > 0);   /* wrap */
    CHECK(nl_seq_cmp(255, 0) < 0);
    CHECK(nl_seq_cmp(10, 250) > 0);  /* 16 ahead across the wrap */
    CHECK(nl_seq_cmp(127, 0) > 0);   /* half window */
    CHECK(nl_seq_cmp(129, 0) < 0);   /* more than half: treated as older */
    for (int a = 0; a < 256; a++) {
        for (int d = 1; d < 128; d++) {
            uint8_t b = (uint8_t)(a + d);
            CHECK(nl_seq_cmp(b, (uint8_t)a) > 0);
            CHECK(nl_seq_cmp((uint8_t)a, b) < 0);
        }
    }
}

int main(void)
{
    RUN(test_header_layout);
    RUN(test_roundtrip);
    RUN(test_golden_bytes);
    RUN(test_encode_errors);
    RUN(test_decode_errors);
    RUN(test_encode_in_place);
    RUN(test_seq_cmp);
    return nl_test_finish();
}
