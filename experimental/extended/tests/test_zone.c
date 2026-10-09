#include "nl_test.h"

#include "nova_link/nl_zone.h"

static void test_claim_rules(void)
{
    nl_claim_table_t t;
    nl_claims_init(&t);
    CHECK_EQ(nl_claims_acquire(&t, 0, 0, NL_CLAIM_SHARED), NL_ERR_PERM);
    CHECK(nl_test_log_contains(NL_LOG_WARN, "zone 0 cannot be claimed"));

    CHECK_EQ(nl_claims_acquire(&t, 0, 1, NL_CLAIM_SHARED), NL_OK);
    CHECK_EQ(nl_claims_acquire(&t, 1, 1, NL_CLAIM_SHARED), NL_OK);
    CHECK_EQ(nl_claims_acquire(&t, 2, 1, NL_CLAIM_READ_ONLY), NL_OK);
    CHECK_EQ(nl_claims_acquire(&t, 3, 1, NL_CLAIM_EXCLUSIVE), NL_ERR_CONFLICT);

    CHECK_EQ(nl_claims_acquire(&t, 0, 2, NL_CLAIM_EXCLUSIVE), NL_OK);
    CHECK_EQ(nl_claims_acquire(&t, 1, 2, NL_CLAIM_READ_ONLY), NL_ERR_CONFLICT);
    CHECK_EQ(nl_claims_acquire(&t, 1, 2, NL_CLAIM_SHARED), NL_ERR_CONFLICT);
    /* The owner can change its own mode. */
    CHECK_EQ(nl_claims_acquire(&t, 0, 2, NL_CLAIM_SHARED), NL_OK);
    CHECK_EQ(nl_claims_acquire(&t, 1, 2, NL_CLAIM_SHARED), NL_OK);

    CHECK(nl_claims_can_send(&t, 0, 1));
    CHECK(!nl_claims_can_send(&t, 2, 1)); /* read-only */
    CHECK(!nl_claims_can_send(&t, 4, 1)); /* no claim */
    CHECK_EQ(nl_claims_get(&t, 2, 1), NL_CLAIM_READ_ONLY);

    CHECK_EQ(nl_claims_acquire(&t, NL_MAX_PLUGINS, 1, NL_CLAIM_SHARED), NL_ERR_ARG);
    CHECK_EQ(nl_claims_acquire(&t, 0, 8, NL_CLAIM_SHARED), NL_ERR_ARG);
    CHECK_EQ(nl_claims_acquire(&t, 0, 3, NL_CLAIM_NONE), NL_ERR_ARG);
    CHECK_EQ(nl_claims_acquire(&t, 0, 3, (nl_claim_mode_t)4), NL_ERR_ARG);
}

static void test_release_and_mask(void)
{
    nl_claim_table_t t;
    nl_claims_init(&t);
    CHECK_EQ(nl_claims_zone_mask(&t), 0);
    nl_claims_acquire(&t, 0, 1, NL_CLAIM_SHARED);
    nl_claims_acquire(&t, 0, 5, NL_CLAIM_READ_ONLY);
    nl_claims_acquire(&t, 1, 7, NL_CLAIM_EXCLUSIVE);
    CHECK_EQ(nl_claims_zone_mask(&t), (1 << 1) | (1 << 5) | (1 << 7));
    CHECK_EQ(nl_claims_release(&t, 0, 5), NL_OK);
    CHECK_EQ(nl_claims_release(&t, 0, 5), NL_ERR_NOT_FOUND);
    nl_claims_release_all(&t, 1);
    CHECK_EQ(nl_claims_zone_mask(&t), 1 << 1);
    /* Exclusive released: another plugin can now take it. */
    CHECK_EQ(nl_claims_acquire(&t, 2, 7, NL_CLAIM_EXCLUSIVE), NL_OK);
}

static void test_remote_claims(void)
{
    nl_remote_claims_t r;
    nl_remote_claims_init(&r, 1000);
    nl_meta_claim_t c[] = {{1, NL_CLAIM_SHARED, 0x10}, {0, NL_CLAIM_SHARED, 0x10},
                           {9, NL_CLAIM_SHARED, 0x10}, {3, 7, 0x10}};
    nl_remote_claims_update(&r, 2, c, 4, 0);
    const nl_remote_claim_t *e = nl_remote_claims_get(&r, 2, 1, 10);
    CHECK(e != NULL);
    CHECK_EQ(e->plugin_type, 0x10);
    CHECK(nl_remote_claims_get(&r, 2, 0, 10) == NULL); /* zone 0 ignored */
    CHECK(nl_remote_claims_get(&r, 2, 3, 10) == NULL); /* bad mode ignored */
    CHECK(nl_remote_claims_get(&r, 3, 1, 10) == NULL); /* other origin */
    CHECK(nl_remote_claims_get(&r, 2, 1, 1001) == NULL); /* expired */

    /* A new snapshot replaces the old one entirely. */
    nl_meta_claim_t c2[] = {{4, NL_CLAIM_READ_ONLY, 0x20}};
    nl_remote_claims_update(&r, 2, c2, 1, 2000);
    CHECK(nl_remote_claims_get(&r, 2, 1, 2000) == NULL);
    CHECK(nl_remote_claims_get(&r, 2, 4, 2000) != NULL);
}

static void test_remote_merge_duplicates(void)
{
    nl_remote_claims_t r;
    nl_remote_claims_init(&r, 0);
    /* Two plugins on one zone: read-only of type A, shared of type B. */
    nl_meta_claim_t c[] = {{2, NL_CLAIM_READ_ONLY, 0xA}, {2, NL_CLAIM_SHARED, 0xB},
                           {3, NL_CLAIM_SHARED, 0xC}, {3, NL_CLAIM_SHARED, 0xC}};
    nl_remote_claims_update(&r, 1, c, 4, 0);
    const nl_remote_claim_t *e = nl_remote_claims_get(&r, 1, 2, 0);
    CHECK(e != NULL);
    CHECK_EQ(e->mode, NL_CLAIM_SHARED);
    CHECK_EQ(e->plugin_type, NL_PLUGIN_TYPE_ANY);
    e = nl_remote_claims_get(&r, 1, 3, 0);
    CHECK_EQ(e->plugin_type, 0xC);
    /* No expiry when expiry_us is 0. */
    CHECK(nl_remote_claims_get(&r, 1, 3, 0x7FFFFFFFu) != NULL);
}

int main(void)
{
    RUN(test_claim_rules);
    RUN(test_release_and_mask);
    RUN(test_remote_claims);
    RUN(test_remote_merge_duplicates);
    return nl_test_finish();
}
