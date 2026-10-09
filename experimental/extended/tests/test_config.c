#include "nl_test.h"

#include "nova_link/nl_config_file.h"
#include "nova_link/nl_ini.h"

/* ======================================================================== */
/* INI parser                                                               */
/* ======================================================================== */

typedef struct {
    bool header; /* section header (key == NULL) */
    char section[NL_INI_MAX_SECTION + 1];
    char key[NL_INI_MAX_KEY + 1];
    char value[NL_INI_MAX_LINE + 1];
    int line;
} rec_t;

static rec_t recs[32];
static int nrecs;
static int stop_at;   /* stop on this entry index (-1 = never) */
static int stop_rc;

static void rec_reset(void)
{
    memset(recs, 0, sizeof(recs));
    nrecs = 0;
    stop_at = -1;
    stop_rc = NL_OK;
}

static int rec_handler(void *user, const char *section, const char *key,
                       const char *value, int line)
{
    int *calls = (int *)user;
    if (calls != NULL) {
        (*calls)++;
    }
    if (nrecs == stop_at) {
        return stop_rc;
    }
    if (nrecs >= (int)NL_ARRAY_SIZE(recs)) {
        return NL_ERR_FULL;
    }
    rec_t *r = &recs[nrecs++];
    r->header = key == NULL;
    r->line = line;
    snprintf(r->section, sizeof(r->section), "%s", section);
    if (key != NULL) {
        CHECK(value != NULL);
        snprintf(r->key, sizeof(r->key), "%s", key);
        snprintf(r->value, sizeof(r->value), "%s", value);
    } else {
        CHECK(value == NULL);
    }
    return NL_OK;
}

static int ini(const char *text, nl_ini_error_t *err)
{
    rec_reset();
    return nl_ini_parse(text, strlen(text), rec_handler, NULL, err);
}

#define CHECK_REC(i, sec, k, v, ln)                                            \
    do {                                                                       \
        CHECK(!recs[i].header);                                                \
        CHECK_STR(recs[i].section, sec);                                       \
        CHECK_STR(recs[i].key, k);                                             \
        CHECK_STR(recs[i].value, v);                                           \
        CHECK_EQ(recs[i].line, ln);                                            \
    } while (0)

#define CHECK_HDR(i, sec, ln)                                                  \
    do {                                                                       \
        CHECK(recs[i].header);                                                 \
        CHECK_STR(recs[i].section, sec);                                       \
        CHECK_EQ(recs[i].line, ln);                                            \
    } while (0)

static void test_ini_basic(void)
{
    const char *text = "; comment\n"
                       "# hash comment\n"
                       "\n"
                       "top = level\n"
                       "  [ radio ]   ; trailing comment\n"
                       "\tkey1=value1\n"
                       "key2   =   spaced value   \n"
                       "key3 = v ; inline\n"
                       "key4 = v # inline hash\n"
                       "key5 = a#b;c\n"
                       "key6 =\n"
                       "key7 = ; only a comment\n"
                       "[zone.3]\n"
                       "name = \"  keep ; # this  \"  ; comment\n"
                       "q = \"\"\n"
                       "eq = a=b\n"
                       "last = no newline";
    nl_ini_error_t err;
    CHECK_EQ(ini(text, &err), NL_OK);
    CHECK_EQ(err.line, 0);
    CHECK_STR(err.msg, "");
    CHECK_EQ(nrecs, 14);
    CHECK_REC(0, "", "top", "level", 4);
    CHECK_HDR(1, "radio", 5);
    CHECK_REC(2, "radio", "key1", "value1", 6);
    CHECK_REC(3, "radio", "key2", "spaced value", 7);
    CHECK_REC(4, "radio", "key3", "v", 8);
    CHECK_REC(5, "radio", "key4", "v", 9);
    CHECK_REC(6, "radio", "key5", "a#b;c", 10);
    CHECK_REC(7, "radio", "key6", "", 11);
    CHECK_REC(8, "radio", "key7", "", 12);
    CHECK_HDR(9, "zone.3", 13);
    CHECK_REC(10, "zone.3", "name", "  keep ; # this  ", 14);
    CHECK_REC(11, "zone.3", "q", "", 15);
    CHECK_REC(12, "zone.3", "eq", "a=b", 16);
    CHECK_REC(13, "zone.3", "last", "no newline", 17);
}

static void test_ini_crlf_and_bom(void)
{
    const char *text = "\xEF\xBB\xBF[a]\r\nk = v\r\n\r\n; c\r\nk2 = \"x\"\r\n";
    CHECK_EQ(ini(text, NULL), NL_OK);
    CHECK_EQ(nrecs, 3);
    CHECK_HDR(0, "a", 1);
    CHECK_REC(1, "a", "k", "v", 2);
    CHECK_REC(2, "a", "k2", "x", 5);

    /* A BOM is only skipped at the very start. */
    nl_ini_error_t err;
    CHECK_EQ(ini("[a]\n\xEF\xBB\xBFk = v\n", &err), NL_ERR_PROTO);
    CHECK_EQ(err.line, 2);
}

static void test_ini_len_and_nul(void)
{
    /* len bounds the input... */
    rec_reset();
    const char *text = "[a]\nk = 1\nj = 2\n";
    CHECK_EQ(nl_ini_parse(text, 9, rec_handler, NULL, NULL), NL_OK);
    CHECK_EQ(nrecs, 2);
    CHECK_REC(1, "a", "k", "1", 2);

    /* ...and so does a NUL, so sizeof(string literal) works. */
    static const char lit[] = "[a]\nk = 1\n";
    rec_reset();
    CHECK_EQ(nl_ini_parse(lit, sizeof(lit), rec_handler, NULL, NULL), NL_OK);
    CHECK_EQ(nrecs, 2);
    static const char mid[] = "[a]\nk = 1\0garbage [[[\n";
    rec_reset();
    CHECK_EQ(nl_ini_parse(mid, sizeof(mid), rec_handler, NULL, NULL), NL_OK);
    CHECK_EQ(nrecs, 2);

    /* Empty input. */
    rec_reset();
    CHECK_EQ(nl_ini_parse(NULL, 0, rec_handler, NULL, NULL), NL_OK);
    CHECK_EQ(nl_ini_parse("", 0, rec_handler, NULL, NULL), NL_OK);
    CHECK_EQ(ini("\n\n  \n\t\n", NULL), NL_OK);
    CHECK_EQ(nrecs, 0);
}

static void test_ini_limits(void)
{
    char text[NL_INI_MAX_LINE * 3];
    nl_ini_error_t err;

    /* Exactly NL_INI_MAX_LINE characters (after trimming) is fine. */
    memset(text, 0, sizeof(text));
    memcpy(text, "\n  k = ", 7);
    memset(text + 7, 'v', NL_INI_MAX_LINE - 4);
    memcpy(text + 7 + NL_INI_MAX_LINE - 4, "   \n", 4);
    CHECK_EQ(ini(text, &err), NL_OK);
    CHECK_EQ(nrecs, 1);
    CHECK_EQ(strlen(recs[0].value), NL_INI_MAX_LINE - 4);
    /* One more is not. */
    memcpy(text + 7 + NL_INI_MAX_LINE - 4, "v  \n", 4);
    CHECK_EQ(ini(text, &err), NL_ERR_SIZE);
    CHECK_EQ(err.line, 2);
    CHECK_STR(err.msg, "line too long");

    /* Long comments are fine. */
    memset(text, 0, sizeof(text));
    text[0] = ';';
    memset(text + 1, 'c', NL_INI_MAX_LINE * 2);
    CHECK_EQ(ini(text, &err), NL_OK);
    text[0] = '#';
    CHECK_EQ(ini(text, &err), NL_OK);

    /* Section name length. */
    memset(text, 0, sizeof(text));
    text[0] = '[';
    memset(text + 1, 's', NL_INI_MAX_SECTION);
    text[1 + NL_INI_MAX_SECTION] = ']';
    CHECK_EQ(ini(text, &err), NL_OK);
    CHECK_EQ(strlen(recs[0].section), NL_INI_MAX_SECTION);
    text[1 + NL_INI_MAX_SECTION] = 's';
    text[2 + NL_INI_MAX_SECTION] = ']';
    CHECK_EQ(ini(text, &err), NL_ERR_SIZE);
    CHECK_STR(err.msg, "section name too long");

    /* Key length. */
    memset(text, 0, sizeof(text));
    memset(text, 'k', NL_INI_MAX_KEY);
    memcpy(text + NL_INI_MAX_KEY, "=1", 2);
    CHECK_EQ(ini(text, &err), NL_OK);
    CHECK_EQ(strlen(recs[0].key), NL_INI_MAX_KEY);
    memset(text, 0, sizeof(text));
    memset(text, 'k', NL_INI_MAX_KEY + 1);
    memcpy(text + NL_INI_MAX_KEY + 1, "=1", 2);
    CHECK_EQ(ini(text, &err), NL_ERR_SIZE);
    CHECK_STR(err.msg, "key too long");
}

static void test_ini_syntax_errors(void)
{
    static const struct {
        const char *text;
        int status;
        int line;
        const char *msg;
    } cases[] = {
        {"[a]\n[b\n", NL_ERR_PROTO, 2, "missing ']' in section header"},
        {"[a] x\n", NL_ERR_PROTO, 1, "unexpected text after ']'"},
        {"[a]]\n", NL_ERR_PROTO, 1, "unexpected text after ']'"},
        {"[]\n", NL_ERR_PROTO, 1, "empty section name"},
        {"[  ]\n", NL_ERR_PROTO, 1, "empty section name"},
        {"[a b]\n", NL_ERR_PROTO, 1, "invalid character in section name"},
        {"[a/b]\n", NL_ERR_PROTO, 1, "invalid character in section name"},
        {"[a]\nk v\n", NL_ERR_PROTO, 2, "expected 'key = value'"},
        {"[a]\n= v\n", NL_ERR_PROTO, 2, "missing key before '='"},
        {"[a]\nmy key = v\n", NL_ERR_PROTO, 2, "invalid character in key"},
        {"[a]\nk\"x = v\n", NL_ERR_PROTO, 2, "invalid character in key"},
        {"[a]\nk = \"abc\n", NL_ERR_PROTO, 2, "unterminated quoted value"},
        {"[a]\nk = \"abc\" d\n", NL_ERR_PROTO, 2, "unexpected text after quoted value"},
        /* Only the first error is reported. */
        {"[a]\nk = 1\n\nbad\n[\n", NL_ERR_PROTO, 4, "expected 'key = value'"},
    };
    for (size_t i = 0; i < NL_ARRAY_SIZE(cases); i++) {
        nl_ini_error_t err;
        int rc = ini(cases[i].text, &err);
        if (rc != cases[i].status || err.line != cases[i].line ||
            strcmp(err.msg, cases[i].msg) != 0) {
            nl_test_fail(__FILE__, __LINE__, "case %u: rc %d line %d msg \"%s\"",
                         (unsigned)i, rc, err.line, err.msg);
        }
    }
}

static void test_ini_handler_stop(void)
{
    const char *text = "[a]\nk = 1\nj = 2\n[b]\nl = 3\n";
    nl_ini_error_t err;
    int calls = 0;

    rec_reset();
    stop_at = 2;
    stop_rc = NL_ERR_FULL;
    CHECK_EQ(nl_ini_parse(text, strlen(text), rec_handler, &calls, &err), NL_ERR_FULL);
    CHECK_EQ(calls, 3);
    CHECK_EQ(err.line, 3);
    CHECK_STR(err.msg, "stopped by handler");

    /* Stopping on a section header. */
    rec_reset();
    calls = 0;
    stop_at = 3;
    stop_rc = NL_ERR_NOT_FOUND;
    CHECK_EQ(nl_ini_parse(text, strlen(text), rec_handler, &calls, &err),
             NL_ERR_NOT_FOUND);
    CHECK_EQ(calls, 4);
    CHECK_EQ(err.line, 4);
}

static void test_ini_args(void)
{
    nl_ini_error_t err;
    CHECK_EQ(nl_ini_parse("[a]", 3, NULL, NULL, &err), NL_ERR_ARG);
    CHECK_EQ(nl_ini_parse(NULL, 3, rec_handler, NULL, &err), NL_ERR_ARG);
    CHECK_EQ(err.line, 0);
    /* err is optional, also on failure. */
    CHECK_EQ(nl_ini_parse("[", 1, rec_handler, NULL, NULL), NL_ERR_PROTO);
}

/* ======================================================================== */
/* Config loader                                                            */
/* ======================================================================== */

static nl_host_config_t g_host;
static nl_radio_params_t g_params;
static nl_zone_plan_t g_plan;
static nl_config_error_t g_err;

static int load(const char *text)
{
    memset(&g_host, 0xA5, sizeof(g_host));
    memset(&g_params, 0xA5, sizeof(g_params));
    memset(&g_plan, 0xA5, sizeof(g_plan));
    memset(&g_err, 0xA5, sizeof(g_err));
    return nl_config_load(text, strlen(text), &g_host, &g_params, &g_plan, &g_err);
}

static void defaults(nl_host_config_t *h, nl_radio_params_t *p, nl_zone_plan_t *z)
{
    nl_host_config_default(h);
    nl_radio_params_default(p);
    nl_config_zone_plan_default(z);
}

static void check_is_default(int line)
{
    nl_host_config_t h;
    nl_radio_params_t p;
    nl_zone_plan_t z;
    defaults(&h, &p, &z);
    if (memcmp(&g_host, &h, sizeof(h)) != 0) {
        nl_test_fail(__FILE__, line, "host config differs from defaults");
    }
    if (memcmp(&g_params, &p, sizeof(p)) != 0) {
        nl_test_fail(__FILE__, line, "radio params differ from defaults");
    }
    if (memcmp(&g_plan, &z, sizeof(z)) != 0) {
        nl_test_fail(__FILE__, line, "zone plan differs from defaults");
    }
}

#define CHECK_DEFAULTS() check_is_default(__LINE__)

/** Expect @p text to fail with @p status on @p line with @p needle in msg. */
static void check_err(const char *text, int status, int line, const char *needle,
                      int src_line)
{
    int rc = load(text);
    if (rc != status || g_err.status != status || g_err.line != line ||
        strstr(g_err.msg, needle) == NULL) {
        nl_test_fail(__FILE__, src_line,
                     "load(\"%s\"): rc %d (want %d) line %d (want %d) msg \"%s\" "
                     "(want \"%s\")",
                     text, rc, status, g_err.line, line, g_err.msg, needle);
    }
    /* Outputs untouched on error. */
    static uint8_t pat[sizeof(g_plan) + sizeof(g_params) + sizeof(g_host)];
    memset(pat, 0xA5, sizeof(pat));
    if (memcmp(&g_plan, pat, sizeof(g_plan)) != 0 ||
        memcmp(&g_params, pat, sizeof(g_params)) != 0 ||
        memcmp(&g_host, pat, sizeof(g_host)) != 0) {
        nl_test_fail(__FILE__, src_line, "outputs modified on error");
    }
}

#define CHECK_ERR(text, status, line, needle) check_err(text, status, line, needle, __LINE__)

static void test_default_plan(void)
{
    nl_zone_plan_t z;
    nl_config_zone_plan_default(&z);
    CHECK_EQ(z.zone[0].subghz_hz, 903000000u);
    CHECK_EQ(z.zone[0].ghz24_hz, 2405000000u);
    CHECK_EQ(z.zone[7].subghz_hz, 924000000u);
    CHECK_EQ(z.zone[7].ghz24_hz, 2475000000u);
    for (int i = 0; i < NL_NUM_ZONES; i++) {
        CHECK_EQ(z.zone[i].priority, 0);
    }
}

static void test_empty_is_default(void)
{
    CHECK_EQ(load(""), NL_OK);
    CHECK_EQ(g_err.status, NL_OK);
    CHECK_EQ(g_err.line, 0);
    CHECK_STR(g_err.msg, "");
    CHECK_DEFAULTS();

    CHECK_EQ(load("; nothing here\n\n[radio]\n[host]\n[zone.5]\n"), NL_OK);
    CHECK_DEFAULTS();

    memset(&g_host, 0, sizeof(g_host));
    CHECK_EQ(nl_config_load(NULL, 0, &g_host, &g_params, &g_plan, NULL), NL_OK);
    CHECK_STR(g_host.name, "nova-link");
}

static void test_every_key(void)
{
    char text[4096];
    int n = snprintf(text, sizeof(text),
                     "[device]\n"
                     "origin_id = 5\n"
                     "name = \" bench rig #2\"\n"
                     "[radio]\n"
                     "band = dual\n"
                     "tx_policy = in_slot\n"
                     "tx_repeats = 7\n"
                     "dwell_us = 3001\n"
                     "burst_extend_us = 4002\n"
                     "mgmt_hold_us = 250003\n"
                     "repeat_interval_us = 1504\n"
                     "tracker_stale_us = 500005\n"
                     "repeat_jitter_us = 1006\n"
                     "discovery_interval_us = 20007\n"
                     "mgmt_repeats = 9\n"
                     "cca_backoff_us = 3008\n"
                     "[host]\n"
                     "announce_interval_us = 2000011\n"
                     "announce_jitter_us = 250012\n"
                     "announce_boot_spread_us = 750020\n"
                     "announce_ramp_steps = 4\n"
                     "rand_seed = 0xDEADBEEF\n"
                     "meta_interval_us = 10013\n"
                     "meta_lead_us = 10014\n"
                     "mgmt_flag_hold_us = 50015\n"
                     "status_interval_us = 1000016\n"
                     "remote_claim_expiry_us = 10000017\n"
                     "peer_expiry_us = 10000018\n"
                     "tracker_stale_us = 500019\n"
                     "check_remote_types = false\n"
                     "max_pull_per_poll = 3\n");
    for (int z = 0; z < NL_NUM_ZONES; z++) {
        /* Even zones in Hz, odd zones in MHz. */
        if (z % 2 == 0) {
            n += snprintf(text + n, sizeof(text) - (size_t)n,
                          "[zone.%d]\npriority = %d\nsubghz_hz = %d\nghz24_hz = %u\n", z,
                          z + 1, 868000000 + z, 2450000000u + (unsigned)z);
        } else {
            n += snprintf(text + n, sizeof(text) - (size_t)n,
                          "[zone.%d]\npriority = %d\nsubghz_mhz = 433.%d25\n"
                          "ghz24_mhz = 2480.%d\n",
                          z, z + 1, z, z);
        }
    }
    CHECK(n > 0 && (size_t)n < sizeof(text));
    CHECK_EQ(load(text), NL_OK);
    CHECK_STR(g_err.msg, "");

    CHECK_EQ(g_host.origin_id, 5);
    CHECK_STR(g_host.name, " bench rig #2");
    CHECK_EQ(g_params.origin_id, 5); /* [device] origin_id feeds both */
    CHECK_EQ(g_params.band, NL_BAND_DUAL);
    CHECK_EQ(g_params.tx_policy, NL_TX_IN_SLOT);
    CHECK_EQ(g_params.tx_repeats, 7);
    CHECK_EQ(g_params.dwell_us, 3001);
    CHECK_EQ(g_params.burst_extend_us, 4002);
    CHECK_EQ(g_params.mgmt_hold_us, 250003);
    CHECK_EQ(g_params.repeat_interval_us, 1504);
    CHECK_EQ(g_params.tracker_stale_us, 500005);
    CHECK_EQ(g_params.repeat_jitter_us, 1006);
    CHECK_EQ(g_params.discovery_interval_us, 20007);
    CHECK_EQ(g_params.mgmt_repeats, 9);
    CHECK_EQ(g_params.cca_backoff_us, 3008);

    CHECK_EQ(g_host.announce_interval_us, 2000011);
    CHECK_EQ(g_host.announce_jitter_us, 250012);
    CHECK_EQ(g_host.announce_boot_spread_us, 750020);
    CHECK_EQ(g_host.announce_ramp_steps, 4);
    CHECK_EQ(g_host.rand_seed, 0xDEADBEEFu);
    CHECK_EQ(g_host.meta_interval_us, 10013);
    CHECK_EQ(g_host.meta_lead_us, 10014);
    CHECK_EQ(g_host.mgmt_flag_hold_us, 50015);
    CHECK_EQ(g_host.status_interval_us, 1000016);
    CHECK_EQ(g_host.remote_claim_expiry_us, 10000017);
    CHECK_EQ(g_host.peer_expiry_us, 10000018);
    CHECK_EQ(g_host.tracker_stale_us, 500019);
    CHECK_EQ(g_host.check_remote_types, false);
    CHECK_EQ(g_host.max_pull_per_poll, 3);

    for (uint32_t z = 0; z < NL_NUM_ZONES; z++) {
        CHECK_EQ(g_plan.zone[z].priority, z + 1);
        if (z % 2 == 0) {
            CHECK_EQ(g_plan.zone[z].subghz_hz, 868000000u + z);
            CHECK_EQ(g_plan.zone[z].ghz24_hz, 2450000000u + z);
        } else {
            CHECK_EQ(g_plan.zone[z].subghz_hz, 433025000u + 100000u * z);
            CHECK_EQ(g_plan.zone[z].ghz24_hz, 2480000000u + 100000u * z);
        }
    }
}

static void test_partial_override(void)
{
    CHECK_EQ(load("[radio]\ndwell_us = 5000\n[zone.2]\npriority = 4\n"), NL_OK);
    nl_host_config_t h;
    nl_radio_params_t p;
    nl_zone_plan_t z;
    defaults(&h, &p, &z);
    p.dwell_us = 5000;
    z.zone[2].priority = 4;
    CHECK_MEM(&g_host, &h, sizeof(h));
    CHECK_MEM(&g_params, &p, sizeof(p));
    CHECK_MEM(&g_plan, &z, sizeof(z));

    /* A shorter name clears the rest of the old one. */
    CHECK_EQ(load("[device]\nname = ab\n"), NL_OK);
    CHECK_STR(g_host.name, "ab");
    for (size_t i = 2; i < sizeof(g_host.name); i++) {
        CHECK_EQ(g_host.name[i], 0);
    }
}

static void test_time_values(void)
{
    static const struct {
        const char *line;
        uint32_t us;
    } cases[] = {
        {"dwell_us = 0", 0},
        {"dwell_us = 1234", 1234},
        {"dwell_us = 007", 7},
        {"dwell_us = 500us", 500},
        {"dwell_us = 500 us", 500},
        {"dwell_us = 2ms", 2000},
        {"dwell_us = 2\tms", 2000},
        {"dwell_us = 1.5ms", 1500},
        {"dwell_us = 0.001ms", 1},
        {"dwell_us = 2s", 2000000},
        {"dwell_us = 0.25s", 250000},
        {"dwell_us = 1.000001s", 1000001},
        {"dwell_us = 1.5000000000s", 1500000}, /* trailing zeros are exact */
        {"dwell_us = 1.0", 1},
        {"dwell_us = 2147483647", 2147483647u},
        {"dwell_us = 2147.483647s", 2147483647u},
        {"dwell = 2ms", 2000},
        {"dwell = 1500us", 1500},
        {"dwell = 3s", 3000000},
        {"burst_extend = 4ms", 4000},
        {"discovery_interval = 1s", 1000000},
    };
    for (size_t i = 0; i < NL_ARRAY_SIZE(cases); i++) {
        char text[96];
        snprintf(text, sizeof(text), "[radio]\n%s\n", cases[i].line);
        int rc = load(text);
        uint32_t got = strncmp(cases[i].line, "burst", 5) == 0 ? g_params.burst_extend_us
                       : strncmp(cases[i].line, "disc", 4) == 0
                           ? g_params.discovery_interval_us
                           : g_params.dwell_us;
        if (rc != NL_OK || got != cases[i].us) {
            nl_test_fail(__FILE__, __LINE__, "\"%s\": rc %d (%s) got %lu want %lu",
                         cases[i].line, rc, g_err.msg, (unsigned long)got,
                         (unsigned long)cases[i].us);
        }
    }
    /* Host times take the same forms. */
    CHECK_EQ(load("[host]\nannounce_interval = 2s\nannounce_jitter_us = 250ms\n"
                  "peer_expiry = 10s\n"),
             NL_OK);
    CHECK_EQ(g_host.announce_interval_us, 2000000);
    CHECK_EQ(g_host.announce_jitter_us, 250000);
    CHECK_EQ(g_host.peer_expiry_us, 10000000);
}

static void test_frequencies(void)
{
    CHECK_EQ(load("[zone.1]\nsubghz_mhz = 903.5\nghz24_mhz = 2483.5\n"), NL_OK);
    CHECK_EQ(g_plan.zone[1].subghz_hz, 903500000u);
    CHECK_EQ(g_plan.zone[1].ghz24_hz, 2483500000u);

    /* Band edges are inclusive. */
    CHECK_EQ(load("[zone.0]\nsubghz_mhz = 300\nghz24_hz = 2400000000\n"
                  "[zone.7]\nsubghz_hz = 1000000000\nghz24_mhz = 2483.500000\n"),
             NL_OK);
    CHECK_EQ(g_plan.zone[0].subghz_hz, 300000000u);
    CHECK_EQ(g_plan.zone[0].ghz24_hz, 2400000000u);
    CHECK_EQ(g_plan.zone[7].subghz_hz, 1000000000u);
    CHECK_EQ(g_plan.zone[7].ghz24_hz, 2483500000u);

    /* Hz resolution in MHz form; 0 = band unused. */
    CHECK_EQ(load("[zone.4]\nsubghz_mhz = 915.000001\nghz24_mhz = 0\n"), NL_OK);
    CHECK_EQ(g_plan.zone[4].subghz_hz, 915000001u);
    CHECK_EQ(g_plan.zone[4].ghz24_hz, 0);
    CHECK_EQ(load("[zone.4]\nsubghz_hz = 0\n"), NL_OK);
    CHECK_EQ(g_plan.zone[4].subghz_hz, 0);
    CHECK_EQ(g_plan.zone[3].subghz_hz, 912000000u); /* others keep defaults */

    /* The same key in different zones is not a duplicate. */
    CHECK_EQ(load("[zone.1]\npriority = 8\n[zone.2]\npriority = 8\n"), NL_OK);
    CHECK_EQ(g_plan.zone[1].priority, 8);
    CHECK_EQ(g_plan.zone[2].priority, 8);
}

static void test_bool_enum_int_forms(void)
{
    static const struct {
        const char *v;
        bool b;
    } bools[] = {{"true", true},  {"TRUE", true},  {"Yes", true}, {"on", true},
                 {"1", true},     {"false", false}, {"No", false}, {"OFF", false},
                 {"0", false}};
    for (size_t i = 0; i < NL_ARRAY_SIZE(bools); i++) {
        char text[64];
        snprintf(text, sizeof(text), "[host]\ncheck_remote_types = %s\n", bools[i].v);
        CHECK_EQ(load(text), NL_OK);
        CHECK_EQ(g_host.check_remote_types, bools[i].b);
    }

    CHECK_EQ(load("[radio]\nband = SubGHz\ntx_policy = IMMEDIATE\n"), NL_OK);
    CHECK_EQ(g_params.band, NL_BAND_SUBGHZ);
    CHECK_EQ(g_params.tx_policy, NL_TX_IMMEDIATE);
    CHECK_EQ(load("[radio]\nband = 2g4\n"), NL_OK);
    CHECK_EQ(g_params.band, NL_BAND_2G4);
    CHECK_EQ(load("[radio]\nband = dual\ntx_policy = in_slot\n"), NL_OK);
    CHECK_EQ(g_params.band, NL_BAND_DUAL);
    CHECK_EQ(g_params.tx_policy, NL_TX_IN_SLOT);

    /* Integer edges, hex. */
    CHECK_EQ(load("[device]\norigin_id = 7\n[radio]\ntx_repeats = 255\n"
                  "[host]\nrand_seed = 4294967295\nmax_pull_per_poll = 0xff\n"),
             NL_OK);
    CHECK_EQ(g_host.origin_id, 7);
    CHECK_EQ(g_params.origin_id, 7);
    CHECK_EQ(g_params.tx_repeats, 255);
    CHECK_EQ(g_host.rand_seed, 0xFFFFFFFFu);
    CHECK_EQ(g_host.max_pull_per_poll, 255);
    CHECK_EQ(load("[host]\nrand_seed = 0Xabc\n"), NL_OK);
    CHECK_EQ(g_host.rand_seed, 0xABC);
    CHECK_EQ(load("[radio]\ntx_repeats = 1\n[zone.0]\npriority = 0\n"), NL_OK);
    CHECK_EQ(g_params.tx_repeats, 1);

    /* Name: max length, quotes, UTF-8 bytes. */
    CHECK_EQ(load("[device]\nname = abcdefghijklmnopqrstuvwx\n"), NL_OK);
    CHECK_STR(g_host.name, "abcdefghijklmnopqrstuvwx");
    CHECK_EQ(load("[device]\nname = \"stage; left\"\n"), NL_OK);
    CHECK_STR(g_host.name, "stage; left");
    CHECK_EQ(load("[device]\nname = B\xC3\xBChne\n"), NL_OK);
    CHECK_STR(g_host.name, "B\xC3\xBChne");

    /* Sections may be reopened; [radio] and [host] tracker_stale_us differ. */
    CHECK_EQ(load("[radio]\ntracker_stale_us = 1\n[host]\ntracker_stale_us = 2\n"
                  "[radio]\ndwell_us = 3\n"),
             NL_OK);
    CHECK_EQ(g_params.tracker_stale_us, 1);
    CHECK_EQ(g_host.tracker_stale_us, 2);
    CHECK_EQ(g_params.dwell_us, 3);
}

static void test_null_outputs_and_args(void)
{
    nl_config_error_t err;
    CHECK_EQ(nl_config_load("[radio]\ndwell_us = 1\n", 20, NULL, NULL, NULL, &err), NL_OK);
    CHECK_EQ(nl_config_load("[radio]\nbad = 1\n", 16, NULL, NULL, NULL, &err),
             NL_ERR_NOT_FOUND);
    CHECK_EQ(err.line, 2);
    CHECK_EQ(nl_config_load("[radio]\nbad = 1\n", 16, NULL, NULL, NULL, NULL),
             NL_ERR_NOT_FOUND);

    /* Only the requested outputs are written. */
    nl_radio_params_t p;
    memset(&p, 0, sizeof(p));
    CHECK_EQ(nl_config_load("[radio]\ntx_repeats = 9\n", 23, NULL, &p, NULL, NULL), NL_OK);
    CHECK_EQ(p.tx_repeats, 9);
    CHECK_EQ(p.dwell_us, 2000);

    memset(&err, 0, sizeof(err));
    CHECK_EQ(nl_config_load(NULL, 4, &g_host, NULL, NULL, &err), NL_ERR_ARG);
    CHECK_EQ(err.status, NL_ERR_ARG);
    CHECK_EQ(err.line, 0);
    CHECK(strstr(err.msg, "NULL") != NULL);
}

static void test_errors_structure(void)
{
    CHECK_ERR("[bogus]\n", NL_ERR_NOT_FOUND, 1, "unknown section [bogus]");
    CHECK_ERR("[radio]\ndwell_us = 1\n\n[Radio]\n", NL_ERR_NOT_FOUND, 4,
              "unknown section [Radio]");
    CHECK_ERR("[zone.8]\n", NL_ERR_NOT_FOUND, 1, "[zone.0] .. [zone.7]");
    CHECK_ERR("[zone.x]\n", NL_ERR_NOT_FOUND, 1, "unknown section [zone.x]");
    CHECK_ERR("[zone.]\n", NL_ERR_NOT_FOUND, 1, "unknown section [zone.]");
    CHECK_ERR("[zone.01]\n", NL_ERR_NOT_FOUND, 1, "unknown section [zone.01]");
    CHECK_ERR("[zone]\n", NL_ERR_NOT_FOUND, 1, "unknown section [zone]");
    CHECK_ERR("[zone.-1]\n", NL_ERR_NOT_FOUND, 1, "unknown section");
    CHECK_ERR("origin_id = 1\n", NL_ERR_NOT_FOUND, 1, "outside of any [section]");
    CHECK_ERR("[radio]\nfoo = 1\n", NL_ERR_NOT_FOUND, 2, "unknown key 'foo' in [radio]");
    CHECK_ERR("[radio]\nDwell_us = 1\n", NL_ERR_NOT_FOUND, 2, "unknown key 'Dwell_us'");
    CHECK_ERR("[radio]\ndwell_ms = 1\n", NL_ERR_NOT_FOUND, 2, "unknown key 'dwell_ms'");
    CHECK_ERR("[radio]\nband_us = 1ms\n", NL_ERR_NOT_FOUND, 2, "unknown key 'band_us'");
    CHECK_ERR("[radio]\ntx_repeat = 1\n", NL_ERR_NOT_FOUND, 2, "unknown key 'tx_repeat'");
    CHECK_ERR("[host]\norigin_id = 1\n", NL_ERR_NOT_FOUND, 2, "it belongs in [device]");
    CHECK_ERR("[radio]\nname = x\n", NL_ERR_NOT_FOUND, 2, "it belongs in [device]");
    CHECK_ERR("[device]\npriority = 1\n", NL_ERR_NOT_FOUND, 2, "it belongs in [zone.N]");
    CHECK_ERR("[zone.1]\ndwell_us = 1\n", NL_ERR_NOT_FOUND, 2, "it belongs in [radio]");
    CHECK_ERR("[radio]\nmax_pull_per_poll = 1\n", NL_ERR_NOT_FOUND, 2,
              "it belongs in [host]");

    /* Syntax errors from the parser keep their message and line. */
    CHECK_ERR("[radio]\ndwell_us 5\n", NL_ERR_PROTO, 2, "expected 'key = value'");
    CHECK_ERR("[radio\n", NL_ERR_PROTO, 1, "missing ']'");
    CHECK_ERR("[device]\nname = \"abc\n", NL_ERR_PROTO, 2, "unterminated quoted value");
    char longline[NL_INI_MAX_LINE + 32];
    memset(longline, 0, sizeof(longline));
    memcpy(longline, "[device]\nname = ", 16);
    memset(longline + 16, 'n', NL_INI_MAX_LINE);
    CHECK_ERR(longline, NL_ERR_SIZE, 2, "line too long");

    /* Duplicates. */
    CHECK_ERR("[radio]\ndwell_us = 1\ndwell_us = 2\n", NL_ERR_CONFLICT, 3,
              "duplicate key 'dwell_us' in [radio]");
    CHECK_ERR("[radio]\ndwell_us = 1\n[host]\n[radio]\ndwell_us = 2\n", NL_ERR_CONFLICT, 5,
              "duplicate key 'dwell_us'");
    CHECK_ERR("[radio]\ndwell_us = 1\ndwell = 2ms\n", NL_ERR_CONFLICT, 3,
              "'dwell' sets dwell_us");
    CHECK_ERR("[zone.3]\nsubghz_hz = 903000000\nsubghz_mhz = 903\n", NL_ERR_CONFLICT, 3,
              "'subghz_mhz' sets subghz_hz, which is already set in [zone.3]");
    CHECK_ERR("[zone.3]\nghz24_mhz = 2405\n[zone.3]\nghz24_hz = 2405000000\n",
              NL_ERR_CONFLICT, 4, "duplicate key 'ghz24_hz'");
    CHECK_ERR("[device]\nname = a\nname = b\n", NL_ERR_CONFLICT, 3, "duplicate key 'name'");

    /* The first error wins and later lines are not examined. */
    CHECK_ERR("[radio]\ntx_repeats = 2\ndwell_us = x\nbogus = 1\n", NL_ERR_ARG, 3,
              "invalid time");
}

static void test_errors_integers(void)
{
    CHECK_ERR("[device]\norigin_id = 8\n", NL_ERR_ARG, 2, "out of range (0..7)");
    CHECK_ERR("[device]\norigin_id = 255\n", NL_ERR_ARG, 2, "out of range");
    CHECK_ERR("[device]\norigin_id = 256\n", NL_ERR_ARG, 2, "out of range");
    CHECK_ERR("[device]\norigin_id = -1\n", NL_ERR_ARG, 2, "invalid integer '-1'");
    CHECK_ERR("[device]\norigin_id = +1\n", NL_ERR_ARG, 2, "invalid integer");
    CHECK_ERR("[device]\norigin_id = 1.5\n", NL_ERR_ARG, 2, "invalid integer");
    CHECK_ERR("[device]\norigin_id = 1 2\n", NL_ERR_ARG, 2, "invalid integer");
    CHECK_ERR("[device]\norigin_id = 0x\n", NL_ERR_ARG, 2, "invalid integer");
    CHECK_ERR("[device]\norigin_id = 0xg\n", NL_ERR_ARG, 2, "invalid integer");
    CHECK_ERR("[device]\norigin_id = 1a\n", NL_ERR_ARG, 2, "invalid integer");
    CHECK_ERR("[device]\norigin_id = 99999999999999999999999999\n", NL_ERR_ARG, 2,
              "out of range");
    CHECK_ERR("[device]\norigin_id =\n", NL_ERR_ARG, 2, "missing value for 'origin_id'");
    CHECK_ERR("[radio]\ntx_repeats = 0\n", NL_ERR_ARG, 2, "out of range (1..255)");
    CHECK_ERR("[radio]\ntx_repeats = 256\n", NL_ERR_ARG, 2, "out of range (1..255)");
    CHECK_ERR("[radio]\nmgmt_repeats = 256\n", NL_ERR_ARG, 2, "out of range (0..255)");
    CHECK_ERR("[host]\nannounce_ramp_steps = 17\n", NL_ERR_ARG, 2, "out of range (0..16)");
    CHECK_ERR("[host]\nmax_pull_per_poll = 0\n", NL_ERR_ARG, 2, "out of range (1..255)");
    CHECK_ERR("[host]\nmax_pull_per_poll = 300\n", NL_ERR_ARG, 2, "out of range");
    CHECK_ERR("[host]\nrand_seed = 4294967296\n", NL_ERR_ARG, 2, "out of range");
    CHECK_ERR("[host]\nrand_seed = 0x100000000\n", NL_ERR_ARG, 2, "out of range");
    CHECK_ERR("[host]\nrand_seed = 0xFFFFFFFFFFFFFFFFFFFF\n", NL_ERR_ARG, 2, "out of range");
    CHECK_ERR("[zone.2]\npriority = 9\n", NL_ERR_ARG, 2, "out of range (0..8)");
    CHECK_ERR("[zone.2]\npriority = 255\n", NL_ERR_ARG, 2, "out of range (0..8)");
}

static void test_errors_times(void)
{
    CHECK_ERR("[radio]\ndwell_us = 2147483648\n", NL_ERR_ARG, 2,
              "too large (max 2147483647 us)");
    CHECK_ERR("[radio]\ndwell_us = 2148s\n", NL_ERR_ARG, 2, "too large");
    CHECK_ERR("[radio]\ndwell_us = 2147.483648s\n", NL_ERR_ARG, 2, "too large");
    CHECK_ERR("[radio]\ndwell_us = 4294967296\n", NL_ERR_ARG, 2, "too large");
    CHECK_ERR("[radio]\ndwell_us = 99999999999999999999ms\n", NL_ERR_ARG, 2, "too large");
    CHECK_ERR("[host]\npeer_expiry = 1h\n", NL_ERR_ARG, 2, "unknown unit 'h'");
    CHECK_ERR("[radio]\ndwell_us = 2 sec\n", NL_ERR_ARG, 2, "unknown unit 'sec'");
    CHECK_ERR("[radio]\ndwell_us = 2MS\n", NL_ERR_ARG, 2, "unknown unit 'MS'");
    CHECK_ERR("[radio]\ndwell_us = 2ms5\n", NL_ERR_ARG, 2, "unknown unit");
    CHECK_ERR("[radio]\ndwell = 2000\n", NL_ERR_ARG, 2,
              "dwell needs a unit (us, ms, s); use dwell_us");
    CHECK_ERR("[host]\nannounce_interval = 2\n", NL_ERR_ARG, 2, "needs a unit");
    CHECK_ERR("[radio]\ndwell_us = 1.5\n", NL_ERR_ARG, 2, "not a whole number");
    CHECK_ERR("[radio]\ndwell_us = 0.5us\n", NL_ERR_ARG, 2, "not a whole number");
    CHECK_ERR("[radio]\ndwell_us = 1.0005ms\n", NL_ERR_ARG, 2, "not a whole number");
    CHECK_ERR("[radio]\ndwell_us = 1.0000001s\n", NL_ERR_ARG, 2, "not a whole number");
    CHECK_ERR("[radio]\ndwell_us = ms\n", NL_ERR_ARG, 2, "invalid time 'ms'");
    CHECK_ERR("[radio]\ndwell_us = .5ms\n", NL_ERR_ARG, 2, "invalid time");
    CHECK_ERR("[radio]\ndwell_us = 1.ms\n", NL_ERR_ARG, 2, "invalid time");
    CHECK_ERR("[radio]\ndwell_us = -1\n", NL_ERR_ARG, 2, "invalid time");
    CHECK_ERR("[radio]\ndwell_us = 0x10\n", NL_ERR_ARG, 2, "unknown unit 'x10'");
    CHECK_ERR("[radio]\ndwell_us =\n", NL_ERR_ARG, 2, "missing value for 'dwell_us'");
}

static void test_errors_frequencies(void)
{
    CHECK_ERR("[zone.0]\nsubghz_mhz = 299.999999\n", NL_ERR_ARG, 2,
              "subghz_mhz = 299.999999 is outside 300..1000 MHz");
    CHECK_ERR("[zone.0]\nsubghz_hz = 1000000001\n", NL_ERR_ARG, 2, "outside 300..1000 MHz");
    CHECK_ERR("[zone.0]\nsubghz_mhz = 2405\n", NL_ERR_ARG, 2, "outside 300..1000 MHz");
    CHECK_ERR("[zone.0]\nsubghz_hz = 903\n", NL_ERR_ARG, 2, "outside"); /* Hz, not MHz */
    CHECK_ERR("[zone.5]\nghz24_mhz = 2483.6\n", NL_ERR_ARG, 2,
              "outside 2400..2483.5 MHz");
    CHECK_ERR("[zone.5]\nghz24_mhz = 2399.999999\n", NL_ERR_ARG, 2, "outside 2400..2483.5");
    CHECK_ERR("[zone.5]\nghz24_hz = 5000000000\n", NL_ERR_ARG, 2, "outside");
    CHECK_ERR("[zone.5]\nghz24_mhz = 99999999999\n", NL_ERR_ARG, 2, "outside");
    CHECK_ERR("[zone.5]\nghz24_mhz = 903\n", NL_ERR_ARG, 2, "outside");
    CHECK_ERR("[zone.0]\nsubghz_mhz = 903.0000001\n", NL_ERR_ARG, 2, "finer than 1 Hz");
    CHECK_ERR("[zone.0]\nsubghz_mhz = 903MHz\n", NL_ERR_ARG, 2,
              "invalid frequency '903MHz' (MHz)");
    CHECK_ERR("[zone.0]\nsubghz_mhz = 903.\n", NL_ERR_ARG, 2, "invalid frequency");
    CHECK_ERR("[zone.0]\nsubghz_hz = 903.5\n", NL_ERR_ARG, 2, "invalid frequency '903.5' (Hz)");
    CHECK_ERR("[zone.0]\nsubghz_hz = 1ms\n", NL_ERR_ARG, 2, "invalid frequency");
    CHECK_ERR("[zone.0]\nghz24_mhz =\n", NL_ERR_ARG, 2, "missing value");
}

static void test_errors_other_values(void)
{
    CHECK_ERR("[host]\ncheck_remote_types = maybe\n", NL_ERR_ARG, 2,
              "expected true/false");
    CHECK_ERR("[host]\ncheck_remote_types = 2\n", NL_ERR_ARG, 2, "expected true/false");
    CHECK_ERR("[host]\ncheck_remote_types = truee\n", NL_ERR_ARG, 2, "expected true/false");
    CHECK_ERR("[host]\ncheck_remote_types = \n", NL_ERR_ARG, 2, "missing value");
    CHECK_ERR("[radio]\nband = 5g\n", NL_ERR_ARG, 2, "expected subghz, 2g4 or dual, got '5g'");
    CHECK_ERR("[radio]\nband = 1\n", NL_ERR_ARG, 2, "expected subghz");
    CHECK_ERR("[radio]\ntx_policy = later\n", NL_ERR_ARG, 2,
              "expected immediate or in_slot");
    CHECK_ERR("[radio]\ntx_policy = in-slot\n", NL_ERR_ARG, 2, "expected immediate");
    CHECK_ERR("[device]\nname =\n", NL_ERR_ARG, 2, "name must not be empty");
    CHECK_ERR("[device]\nname = \"\"\n", NL_ERR_ARG, 2, "name must not be empty");
    CHECK_ERR("[device]\nname = abcdefghijklmnopqrstuvwxy\n", NL_ERR_SIZE, 2,
              "name is 25 bytes long (max 24)");
    CHECK_ERR("[device]\nname = a\tb\n", NL_ERR_ARG, 2, "control character");
    CHECK_ERR("[device]\nname = a\x7f\n", NL_ERR_ARG, 2, "control character");
}

/* ---- The shipped example ------------------------------------------------ */

#ifndef NL_SOURCE_DIR
#error "NL_SOURCE_DIR must be defined (see tests/CMakeLists.txt)"
#endif

static char example[32768];
static size_t example_len;

static bool read_example(void)
{
    const char *path = NL_SOURCE_DIR "/config/nova_link.ini";
    FILE *f = fopen(path, "rb");
    if (f == NULL) {
        nl_test_fail(__FILE__, __LINE__, "cannot open %s", path);
        return false;
    }
    example_len = fread(example, 1, sizeof(example) - 1, f);
    bool eof = feof(f) != 0;
    fclose(f);
    if (!eof) {
        nl_test_fail(__FILE__, __LINE__, "%s is larger than the test buffer", path);
        return false;
    }
    example[example_len] = '\0';
    return true;
}

static void test_example_file(void)
{
    if (!read_example()) {
        return;
    }
    CHECK(example_len > 1000);
    int rc = nl_config_load(example, example_len, &g_host, &g_params, &g_plan, &g_err);
    if (rc != NL_OK) {
        nl_test_fail(__FILE__, __LINE__, "nova_link.ini line %d: %s", g_err.line,
                     g_err.msg);
    }
    CHECK_DEFAULTS();

    /* Every setting is present: adding any key again must be a duplicate. */
    static const char *const sections[] = {"device", "radio", "host", "zone.0",
                                           "zone.7"};
    static const char *const sample_keys[] = {"origin_id", "dwell_us", "rand_seed",
                                              "subghz_hz", "ghz24_mhz"};
    for (size_t i = 0; i < NL_ARRAY_SIZE(sections); i++) {
        char extra[sizeof(example) + 64];
        int n = snprintf(extra, sizeof(extra), "%s\n[%s]\n%s = 0\n", example, sections[i],
                         sample_keys[i]);
        CHECK(n > 0 && (size_t)n < sizeof(extra));
        memset(&g_err, 0, sizeof(g_err));
        CHECK_EQ(nl_config_load(extra, (size_t)n, NULL, NULL, NULL, &g_err),
                 NL_ERR_CONFLICT);
    }

    /* The same file with CRLF line endings loads identically. */
    static char crlf[sizeof(example) * 2];
    size_t n = 0;
    for (size_t i = 0; i < example_len; i++) {
        if (example[i] == '\n') {
            crlf[n++] = '\r';
        }
        crlf[n++] = example[i];
    }
    CHECK_EQ(nl_config_load(crlf, n, &g_host, &g_params, &g_plan, &g_err), NL_OK);
    CHECK_DEFAULTS();
}

int main(void)
{
    RUN(test_ini_basic);
    RUN(test_ini_crlf_and_bom);
    RUN(test_ini_len_and_nul);
    RUN(test_ini_limits);
    RUN(test_ini_syntax_errors);
    RUN(test_ini_handler_stop);
    RUN(test_ini_args);
    RUN(test_default_plan);
    RUN(test_empty_is_default);
    RUN(test_every_key);
    RUN(test_partial_override);
    RUN(test_time_values);
    RUN(test_frequencies);
    RUN(test_bool_enum_int_forms);
    RUN(test_null_outputs_and_args);
    RUN(test_errors_structure);
    RUN(test_errors_integers);
    RUN(test_errors_times);
    RUN(test_errors_frequencies);
    RUN(test_errors_other_values);
    RUN(test_example_file);
    return nl_test_finish();
}
