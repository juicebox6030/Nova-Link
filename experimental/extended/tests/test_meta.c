#include "nl_test.h"

#include "nova_link/nl_meta.h"

static void test_queue_pack(void)
{
    nl_meta_queue_t q;
    nl_meta_queue_init(&q);
    CHECK(!nl_meta_queue_pending(&q));
    uint8_t v[NL_META_MAX_VALUE];
    memset(v, 0x5A, sizeof(v));

    CHECK_EQ(nl_meta_queue_push(&q, 0x10, v, 40), NL_OK); /* 42 bytes */
    CHECK_EQ(nl_meta_queue_push(&q, 0x11, v, 40), NL_OK); /* 42 -> 84 */
    CHECK_EQ(nl_meta_queue_push(&q, 0x12, v, 20), NL_OK); /* 22 -> would be 106 */
    CHECK(nl_meta_queue_pending(&q));

    uint8_t out[NL_MAX_PAYLOAD];
    CHECK_EQ(nl_meta_queue_pack(&q, out, sizeof(out)), 84);
    CHECK_EQ(out[0], 0x10);
    CHECK_EQ(out[1], 40);
    CHECK_EQ(out[42], 0x11);
    CHECK_EQ(nl_meta_queue_pack(&q, out, sizeof(out)), 22);
    CHECK_EQ(out[0], 0x12);
    CHECK(!nl_meta_queue_pending(&q));
    CHECK_EQ(nl_meta_queue_pack(&q, out, sizeof(out)), 0);
}

static void test_queue_max_record_fits_payload(void)
{
    nl_meta_queue_t q;
    nl_meta_queue_init(&q);
    uint8_t v[NL_META_MAX_VALUE] = {0};
    CHECK_EQ(nl_meta_queue_push(&q, 1, v, NL_META_MAX_VALUE), NL_OK);
    CHECK_EQ(nl_meta_queue_push(&q, 1, v, NL_META_MAX_VALUE + 1), NL_ERR_SIZE);
    uint8_t out[NL_MAX_PAYLOAD];
    CHECK_EQ(nl_meta_queue_pack(&q, out, sizeof(out)), NL_MAX_PAYLOAD);
}

static void test_queue_full(void)
{
    nl_meta_queue_t q;
    nl_meta_queue_init(&q);
    uint8_t v[NL_META_MAX_VALUE] = {0};
    int pushed = 0;
    while (nl_meta_queue_push(&q, 1, v, NL_META_MAX_VALUE) == NL_OK) {
        pushed++;
    }
    CHECK_EQ(pushed, NL_META_QUEUE_BYTES / NL_MAX_PAYLOAD);
    CHECK_EQ(q.dropped, 1);
}

static void test_remove_type(void)
{
    nl_meta_queue_t q;
    nl_meta_queue_init(&q);
    CHECK_EQ(nl_meta_queue_push(&q, 1, (const uint8_t *)"a", 1), NL_OK);
    CHECK_EQ(nl_meta_queue_push(&q, 2, (const uint8_t *)"bb", 2), NL_OK);
    CHECK_EQ(nl_meta_queue_push(&q, 1, (const uint8_t *)"ccc", 3), NL_OK);
    CHECK_EQ(nl_meta_queue_push(&q, 3, NULL, 0), NL_OK);
    nl_meta_queue_remove_type(&q, 1);
    uint8_t out[NL_MAX_PAYLOAD];
    size_t n = nl_meta_queue_pack(&q, out, sizeof(out));
    const uint8_t expect[] = {2, 2, 'b', 'b', 3, 0};
    CHECK_EQ(n, sizeof(expect));
    CHECK_MEM(out, expect, sizeof(expect));
}

static void test_iter(void)
{
    const uint8_t buf[] = {1, 2, 'h', 'i', 0x80, 0, 5, 1, 'x'};
    nl_meta_iter_t it;
    uint8_t type, len;
    const uint8_t *v;
    nl_meta_iter_init(&it, buf, sizeof(buf));
    CHECK_EQ(nl_meta_iter_next(&it, &type, &v, &len), 1);
    CHECK_EQ(type, 1);
    CHECK_EQ(len, 2);
    CHECK_MEM(v, "hi", 2);
    CHECK_EQ(nl_meta_iter_next(&it, &type, &v, &len), 1);
    CHECK_EQ(type, 0x80);
    CHECK_EQ(len, 0);
    CHECK_EQ(nl_meta_iter_next(&it, &type, &v, &len), 1);
    CHECK_EQ(type, 5);
    CHECK_EQ(nl_meta_iter_next(&it, &type, &v, &len), 0);

    /* Record length runs past the end: error, then stops. */
    const uint8_t bad[] = {1, 1, 'a', 2, 9, 'b'};
    nl_meta_iter_init(&it, bad, sizeof(bad));
    CHECK_EQ(nl_meta_iter_next(&it, &type, &v, &len), 1);
    CHECK_EQ(nl_meta_iter_next(&it, &type, &v, &len), NL_ERR_PROTO);
    CHECK_EQ(nl_meta_iter_next(&it, &type, &v, &len), 0);

    /* Lone type byte. */
    nl_meta_iter_init(&it, bad, 1);
    CHECK_EQ(nl_meta_iter_next(&it, &type, &v, &len), NL_ERR_PROTO);
}

static void test_claims_codec(void)
{
    nl_meta_claim_t c[3] = {{1, 2, 0x1234}, {5, 1, 0xBEEF}, {7, 3, 0}};
    uint8_t buf[NL_META_MAX_VALUE];
    CHECK_EQ(nl_meta_encode_claims(c, 3, buf, sizeof(buf)), 12);
    const uint8_t expect[] = {1, 2, 0x34, 0x12, 5, 1, 0xEF, 0xBE, 7, 3, 0, 0};
    CHECK_MEM(buf, expect, sizeof(expect));

    nl_meta_claim_t d[3];
    CHECK_EQ(nl_meta_decode_claims(buf, 12, d, 3), 3);
    CHECK_EQ(d[1].zone, 5);
    CHECK_EQ(d[1].mode, 1);
    CHECK_EQ(d[1].plugin_type, 0xBEEF);
    CHECK_EQ(nl_meta_decode_claims(buf, 11, d, 3), NL_ERR_PROTO);
    CHECK_EQ(nl_meta_decode_claims(buf, 12, d, 2), NL_ERR_SIZE);
    CHECK_EQ(nl_meta_decode_claims(buf, 0, d, 3), 0);

    nl_meta_claim_t many[25] = {{0}};
    CHECK_EQ(nl_meta_encode_claims(many, 24, buf, sizeof(buf)), 96);
    CHECK_EQ(nl_meta_encode_claims(many, 25, buf, sizeof(buf)), NL_ERR_SIZE);
}

static void test_device_codec(void)
{
    nl_meta_device_t dev = {.proto_version = 1, .fw_major = 0, .fw_minor = 2,
                            .fw_patch = 3};
    memcpy(dev.name, "stage-left", 11);
    uint8_t buf[NL_META_MAX_VALUE];
    int n = nl_meta_encode_device(&dev, buf, sizeof(buf));
    CHECK_EQ(n, 4 + 10);
    nl_meta_device_t d;
    CHECK_EQ(nl_meta_decode_device(buf, (size_t)n, &d), NL_OK);
    CHECK_STR(d.name, "stage-left");
    CHECK_EQ(d.fw_minor, 2);

    /* Name of exactly 24 chars, and an unterminated 25-char buffer. */
    memset(dev.name, 'N', sizeof(dev.name));
    n = nl_meta_encode_device(&dev, buf, sizeof(buf));
    CHECK_EQ(n, 4 + 24);
    CHECK_EQ(nl_meta_decode_device(buf, (size_t)n, &d), NL_OK);
    CHECK_EQ(strlen(d.name), 24);
    CHECK_EQ(nl_meta_decode_device(buf, 3, &d), NL_ERR_PROTO);
    CHECK_EQ(nl_meta_decode_device(buf, 4 + 25, &d), NL_ERR_PROTO);
}

int main(void)
{
    RUN(test_queue_pack);
    RUN(test_queue_max_record_fits_payload);
    RUN(test_queue_full);
    RUN(test_remove_type);
    RUN(test_iter);
    RUN(test_claims_codec);
    RUN(test_device_codec);
    return nl_test_finish();
}
