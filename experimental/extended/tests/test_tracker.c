#include "nl_test.h"

#include "nova_link/nl_stream_tracker.h"

static void test_basic(void)
{
    nl_stream_tracker_t t;
    nl_tracker_init(&t, 0);
    CHECK_EQ(nl_tracker_check(&t, 1, 2, 10, 0), NL_TRACK_NEW);
    CHECK_EQ(nl_tracker_check(&t, 1, 2, 10, 0), NL_TRACK_DUPLICATE);
    CHECK_EQ(nl_tracker_check(&t, 1, 2, 9, 0), NL_TRACK_OLD);
    CHECK_EQ(nl_tracker_check(&t, 1, 2, 12, 0), NL_TRACK_NEW); /* gap is fine */
    CHECK_EQ(nl_tracker_check(&t, 1, 2, 11, 0), NL_TRACK_OLD); /* late arrival */
    CHECK_EQ(t.accepted, 2);
    CHECK_EQ(t.duplicates, 1);
    CHECK_EQ(t.old, 2);
}

static void test_streams_independent(void)
{
    nl_stream_tracker_t t;
    nl_tracker_init(&t, 0);
    CHECK_EQ(nl_tracker_check(&t, 1, 2, 50, 0), NL_TRACK_NEW);
    CHECK_EQ(nl_tracker_check(&t, 1, 3, 50, 0), NL_TRACK_NEW); /* other zone */
    CHECK_EQ(nl_tracker_check(&t, 2, 2, 50, 0), NL_TRACK_NEW); /* other origin */
    CHECK_EQ(nl_tracker_check(&t, 1, 2, 50, 0), NL_TRACK_DUPLICATE);
}

static void test_wraparound(void)
{
    nl_stream_tracker_t t;
    nl_tracker_init(&t, 0);
    for (int i = 0; i < 600; i++) {
        CHECK_EQ(nl_tracker_check(&t, 0, 0, (uint8_t)i, 0), NL_TRACK_NEW);
        CHECK_EQ(nl_tracker_check(&t, 0, 0, (uint8_t)i, 0), NL_TRACK_DUPLICATE);
    }
}

static void test_stale_expiry(void)
{
    nl_stream_tracker_t t;
    nl_tracker_init(&t, 1000);
    CHECK_EQ(nl_tracker_check(&t, 3, 1, 200, 0), NL_TRACK_NEW);
    /* Sender rebooted and restarted at a lower seq: rejected while fresh... */
    CHECK_EQ(nl_tracker_check(&t, 3, 1, 150, 500), NL_TRACK_OLD);
    /* ...rejections do not refresh the entry, so it expires 1 ms after 200. */
    CHECK_EQ(nl_tracker_check(&t, 3, 1, 151, 1001), NL_TRACK_NEW);
    CHECK_EQ(nl_tracker_check(&t, 3, 1, 152, 1500), NL_TRACK_NEW);
}

static void test_stale_across_time_wrap(void)
{
    nl_stream_tracker_t t;
    nl_tracker_init(&t, 1000);
    nl_time_us_t t0 = 0xFFFFFF00u;
    CHECK_EQ(nl_tracker_check(&t, 0, 1, 5, t0), NL_TRACK_NEW);
    CHECK_EQ(nl_tracker_check(&t, 0, 1, 5, t0 + 500u), NL_TRACK_DUPLICATE);
    CHECK_EQ(nl_tracker_check(&t, 0, 1, 5, t0 + 1500u), NL_TRACK_NEW);
}

static void test_stale_huge(void)
{
    /* A stale time above INT32_MAX (e.g. from a RADIO_CONFIG frame) must
     * not wrap negative and expire every entry at once. */
    nl_stream_tracker_t t;
    nl_tracker_init(&t, 0xFFFFFFFFu);
    CHECK_EQ(nl_tracker_check(&t, 0, 1, 5, 0), NL_TRACK_NEW);
    CHECK_EQ(nl_tracker_check(&t, 0, 1, 5, 500), NL_TRACK_DUPLICATE);
    CHECK_EQ(nl_tracker_check(&t, 0, 1, 4, 0x7FFFFFFFu), NL_TRACK_OLD);
}

static void test_reset(void)
{
    nl_stream_tracker_t t;
    nl_tracker_init(&t, 0);
    CHECK_EQ(nl_tracker_check(&t, 0, 0, 1, 0), NL_TRACK_NEW);
    nl_tracker_reset(&t);
    CHECK_EQ(nl_tracker_check(&t, 0, 0, 1, 0), NL_TRACK_NEW);
}

int main(void)
{
    RUN(test_basic);
    RUN(test_streams_independent);
    RUN(test_wraparound);
    RUN(test_stale_expiry);
    RUN(test_stale_across_time_wrap);
    RUN(test_stale_huge);
    RUN(test_reset);
    return nl_test_finish();
}
