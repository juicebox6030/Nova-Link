#include "nl_test.h"

#include "nova_link/nl_segment.h"

static uint8_t msg[NL_SEG_MAX_MESSAGE + 1];

static void fill_msg(void)
{
    for (size_t i = 0; i < sizeof(msg); i++) {
        msg[i] = (uint8_t)(i * 31u + 7u);
    }
}

static void test_count(void)
{
    CHECK_EQ(nl_seg_count(0), 1);
    CHECK_EQ(nl_seg_count(1), 1);
    CHECK_EQ(nl_seg_count(99), 1);
    CHECK_EQ(nl_seg_count(100), 2);
    CHECK_EQ(nl_seg_count(512), 6); /* DMX universe */
    CHECK_EQ(nl_seg_count(NL_SEG_MAX_MESSAGE), NL_SEG_MAX_SEGMENTS);
    CHECK_EQ(nl_seg_count(NL_SEG_MAX_MESSAGE + 1), NL_ERR_SIZE);
}

static void test_build(void)
{
    fill_msg();
    uint8_t out[NL_MAX_PAYLOAD];
    CHECK_EQ(nl_seg_build(msg, 200, 0, out, sizeof(out)), 100);
    CHECK_EQ(out[0], 0x02); /* index 0, last 2 */
    CHECK_MEM(&out[1], msg, 99);
    CHECK_EQ(nl_seg_build(msg, 200, 2, out, sizeof(out)), 3);
    CHECK_EQ(out[0], 0x22);
    CHECK_MEM(&out[1], &msg[198], 2);
    CHECK_EQ(nl_seg_build(msg, 200, 3, out, sizeof(out)), NL_ERR_ARG);
    CHECK_EQ(nl_seg_build(msg, 0, 0, out, sizeof(out)), 1);
    CHECK_EQ(out[0], 0x00);
    CHECK_EQ(nl_seg_build(msg, 200, 0, out, 99), NL_ERR_SIZE);
}

/** Build every segment of a message and feed them in the given order. */
static int roundtrip(size_t len, const uint8_t *order, uint8_t seq0, nl_reasm_t *r,
                     const uint8_t **out, size_t *out_len)
{
    int count = nl_seg_count(len);
    int done = 0;
    for (int k = 0; k < count; k++) {
        uint8_t i = order ? order[k] : (uint8_t)k;
        uint8_t p[NL_MAX_PAYLOAD];
        int n = nl_seg_build(msg, len, i, p, sizeof(p));
        int rc = nl_reasm_feed(r, (uint8_t)(seq0 + i), p, (size_t)n, out, out_len);
        if (rc < 0) {
            return rc;
        }
        done += rc;
    }
    return done;
}

static void test_reassemble_sizes(void)
{
    fill_msg();
    static uint8_t buf[NL_SEG_MAX_MESSAGE];
    nl_reasm_t r;
    nl_reasm_init(&r, buf, sizeof(buf));
    const size_t sizes[] = {0, 1, 98, 99, 100, 198, 199, 512, NL_SEG_MAX_MESSAGE};
    for (size_t k = 0; k < NL_ARRAY_SIZE(sizes); k++) {
        const uint8_t *out = NULL;
        size_t out_len = 12345;
        CHECK_EQ(roundtrip(sizes[k], NULL, (uint8_t)(250 + k), &r, &out, &out_len), 1);
        CHECK_EQ(out_len, sizes[k]);
        if (sizes[k] > 0) {
            CHECK_MEM(out, msg, sizes[k]);
        }
    }
    CHECK_EQ(r.completed, NL_ARRAY_SIZE(sizes));
    CHECK_EQ(r.aborted, 0);
}

static void test_out_of_order(void)
{
    fill_msg();
    uint8_t buf[600];
    nl_reasm_t r;
    nl_reasm_init(&r, buf, sizeof(buf));
    const uint8_t order[] = {5, 0, 3, 1, 4, 2};
    const uint8_t *out;
    size_t out_len;
    CHECK_EQ(roundtrip(512, order, 0, &r, &out, &out_len), 1);
    CHECK_EQ(out_len, 512);
    CHECK_MEM(out, msg, 512);
}

static void test_loss_then_next_message(void)
{
    fill_msg();
    uint8_t buf[600];
    nl_reasm_t r;
    nl_reasm_init(&r, buf, sizeof(buf));
    uint8_t p[NL_MAX_PAYLOAD];
    const uint8_t *out;
    size_t out_len;

    /* Message A (seq 10..12): segment 1 lost. */
    int n = nl_seg_build(msg, 250, 0, p, sizeof(p));
    CHECK_EQ(nl_reasm_feed(&r, 10, p, (size_t)n, &out, &out_len), 0);
    n = nl_seg_build(msg, 250, 2, p, sizeof(p));
    CHECK_EQ(nl_reasm_feed(&r, 12, p, (size_t)n, &out, &out_len), 0);

    /* Message B (seq 13..15) arrives complete: A is abandoned. */
    CHECK_EQ(roundtrip(250, NULL, 13, &r, &out, &out_len), 1);
    CHECK_EQ(r.aborted, 1);
    CHECK_EQ(r.completed, 1);
    CHECK_MEM(out, msg, 250);
}

static void test_duplicate_segment_is_harmless(void)
{
    fill_msg();
    uint8_t buf[600];
    nl_reasm_t r;
    nl_reasm_init(&r, buf, sizeof(buf));
    uint8_t p[NL_MAX_PAYLOAD];
    const uint8_t *out;
    size_t out_len;
    int n = nl_seg_build(msg, 150, 0, p, sizeof(p));
    CHECK_EQ(nl_reasm_feed(&r, 0, p, (size_t)n, &out, &out_len), 0);
    CHECK_EQ(nl_reasm_feed(&r, 0, p, (size_t)n, &out, &out_len), 0);
    n = nl_seg_build(msg, 150, 1, p, sizeof(p));
    CHECK_EQ(nl_reasm_feed(&r, 1, p, (size_t)n, &out, &out_len), 1);
    CHECK_EQ(out_len, 150);
}

static void test_malformed(void)
{
    uint8_t buf[200];
    nl_reasm_t r;
    nl_reasm_init(&r, buf, sizeof(buf));
    uint8_t p[NL_MAX_PAYLOAD] = {0};
    CHECK_EQ(nl_reasm_feed(&r, 0, p, 0, NULL, NULL), NL_ERR_PROTO);
    p[0] = 0x21; /* index 2 > last 1 */
    CHECK_EQ(nl_reasm_feed(&r, 0, p, 10, NULL, NULL), NL_ERR_PROTO);
    p[0] = 0x01; /* non-last segment must be full */
    CHECK_EQ(nl_reasm_feed(&r, 0, p, 50, NULL, NULL), NL_ERR_PROTO);
    p[0] = 0x11; /* last segment of a multi-segment message must not be empty */
    CHECK_EQ(nl_reasm_feed(&r, 0, p, 1, NULL, NULL), NL_ERR_PROTO);
    p[0] = 0x05; /* 6 segments do not fit a 200-byte buffer */
    CHECK_EQ(nl_reasm_feed(&r, 0, p, 100, NULL, NULL), 0);
    p[0] = 0x25;
    CHECK_EQ(nl_reasm_feed(&r, 2, p, 100, NULL, NULL), NL_ERR_SIZE);
}

int main(void)
{
    RUN(test_count);
    RUN(test_build);
    RUN(test_reassemble_sizes);
    RUN(test_out_of_order);
    RUN(test_loss_then_next_message);
    RUN(test_duplicate_segment_is_harmless);
    RUN(test_malformed);
    return nl_test_finish();
}
