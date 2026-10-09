/**
 * @file nl_config_file.c
 * @brief INI configuration loader: maps keys onto nl_host_config_t,
 *        nl_radio_params_t, and nl_zone_plan_t.
 */
#include "nova_link/nl_config_file.h"
#include "nova_link/nl_ini.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

/* ---- Key table --------------------------------------------------------- */

enum { SEC_NONE, SEC_DEVICE, SEC_RADIO, SEC_HOST, SEC_ZONE };

enum {
    KIND_U8,        /* integer into a uint8_t field */
    KIND_U32,       /* integer into a uint32_t field */
    KIND_TIME,      /* microseconds (uint32_t), unit suffixes allowed */
    KIND_BOOL,      /* bool field */
    KIND_BAND,      /* nl_band_t into a uint8_t field */
    KIND_TX_POLICY, /* nl_tx_policy_t into a uint8_t field */
    KIND_NAME,      /* nl_host_config_t::name */
    KIND_FREQ,      /* Hz (uint32_t); also settable in MHz via mhz_key */
};

enum { TGT_HOST, TGT_PARAMS, TGT_ZONE };

typedef struct {
    const char *key;     /**< Canonical key (always the struct field name). */
    const char *mhz_key; /**< KIND_FREQ: decimal-MHz spelling, else NULL. */
    uint8_t section;
    uint8_t kind;
    uint8_t target;
    uint16_t offset;
    uint32_t min;
    uint32_t max;
} key_def_t;

#define HOST_F(f) #f, NULL, SEC_HOST
#define DEV_F(f) #f, NULL, SEC_DEVICE
#define RADIO_F(f) #f, NULL, SEC_RADIO
#define AT_HOST(f) TGT_HOST, (uint16_t)offsetof(nl_host_config_t, f)
#define AT_PARAMS(f) TGT_PARAMS, (uint16_t)offsetof(nl_radio_params_t, f)
#define AT_ZONE(f) TGT_ZONE, (uint16_t)offsetof(nl_zone_rf_t, f)
#define TIME_RANGE 0u, NL_CONFIG_MAX_TIME_US

#define RADIO_TIME(f) {RADIO_F(f), KIND_TIME, AT_PARAMS(f), TIME_RANGE}
#define HOST_TIME(f) {HOST_F(f), KIND_TIME, AT_HOST(f), TIME_RANGE}

static const key_def_t keys[] = {
    {DEV_F(origin_id), KIND_U8, AT_HOST(origin_id), 0u, NL_NUM_ORIGINS - 1u},
    {DEV_F(name), KIND_NAME, AT_HOST(name), 1u, sizeof(((nl_host_config_t *)0)->name) - 1u},

    {RADIO_F(band), KIND_BAND, AT_PARAMS(band), 0u, 0u},
    {RADIO_F(tx_policy), KIND_TX_POLICY, AT_PARAMS(tx_policy), 0u, 0u},
    {RADIO_F(tx_repeats), KIND_U8, AT_PARAMS(tx_repeats), 1u, 255u},
    RADIO_TIME(dwell_us),
    RADIO_TIME(burst_extend_us),
    RADIO_TIME(mgmt_hold_us),
    RADIO_TIME(repeat_interval_us),
    RADIO_TIME(tracker_stale_us),
    RADIO_TIME(repeat_jitter_us),
    RADIO_TIME(discovery_interval_us),
    {RADIO_F(mgmt_repeats), KIND_U8, AT_PARAMS(mgmt_repeats), 0u, 255u},
    RADIO_TIME(cca_backoff_us),

    HOST_TIME(announce_interval_us),
    HOST_TIME(announce_jitter_us),
    HOST_TIME(announce_boot_spread_us),
    {HOST_F(announce_ramp_steps), KIND_U8, AT_HOST(announce_ramp_steps), 0u, 16u},
    {HOST_F(rand_seed), KIND_U32, AT_HOST(rand_seed), 0u, UINT32_MAX},
    HOST_TIME(meta_interval_us),
    HOST_TIME(meta_lead_us),
    HOST_TIME(mgmt_flag_hold_us),
    HOST_TIME(status_interval_us),
    HOST_TIME(remote_claim_expiry_us),
    HOST_TIME(peer_expiry_us),
    HOST_TIME(tracker_stale_us),
    {HOST_F(check_remote_types), KIND_BOOL, AT_HOST(check_remote_types), 0u, 1u},
    {HOST_F(max_pull_per_poll), KIND_U8, AT_HOST(max_pull_per_poll), 1u, 255u},

    {"priority", NULL, SEC_ZONE, KIND_U8, AT_ZONE(priority), 0u, NL_CONFIG_MAX_PRIORITY},
    {"subghz_hz", "subghz_mhz", SEC_ZONE, KIND_FREQ, AT_ZONE(subghz_hz), 300000000u,
     1000000000u},
    {"ghz24_hz", "ghz24_mhz", SEC_ZONE, KIND_FREQ, AT_ZONE(ghz24_hz), 2400000000u,
     2483500000u},
};

#define NUM_KEYS NL_ARRAY_SIZE(keys)

static const char *const section_names[] = {"", "device", "radio", "host", "zone.N"};

/** How a key was spelled. */
enum { FORM_CANONICAL, FORM_SHORT_TIME, FORM_MHZ };

/* ---- Loader state ------------------------------------------------------ */

typedef struct {
    nl_host_config_t host;
    nl_radio_params_t params;
    nl_zone_plan_t plan;
    uint8_t section;
    uint8_t zone;
    uint8_t seen[NUM_KEYS]; /**< Bit z for [zone.z] keys, bit 0 otherwise. */
    nl_config_error_t err;
} load_ctx_t;

#if defined(__GNUC__)
__attribute__((format(printf, 4, 5)))
#endif
static int cfg_fail(load_ctx_t *c, int line, int status, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(c->err.msg, sizeof(c->err.msg), fmt, ap);
    va_end(ap);
    c->err.status = status;
    c->err.line = line;
    return status;
}

/* ---- Small string / number helpers ------------------------------------- */

static bool is_digit(char ch)
{
    return ch >= '0' && ch <= '9';
}

static int hex_digit(char ch)
{
    if (is_digit(ch)) {
        return ch - '0';
    }
    if (ch >= 'a' && ch <= 'f') {
        return ch - 'a' + 10;
    }
    if (ch >= 'A' && ch <= 'F') {
        return ch - 'A' + 10;
    }
    return -1;
}

static char lower(char ch)
{
    return (ch >= 'A' && ch <= 'Z') ? (char)(ch - 'A' + 'a') : ch;
}

/** Case-insensitive ASCII equality (strcasecmp is not C99). */
static bool str_ieq(const char *a, const char *b)
{
    while (*a != '\0' && lower(*a) == lower(*b)) {
        a++;
        b++;
    }
    return lower(*a) == lower(*b);
}

enum { NUM_OK, NUM_SYNTAX, NUM_RANGE, NUM_INEXACT };

/** Plain unsigned integer: decimal or 0x hex, whole string. */
static int parse_uint(const char *s, uint64_t *out)
{
    unsigned base = 10;
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X')) {
        base = 16;
        s += 2;
    }
    if (*s == '\0') {
        return NUM_SYNTAX;
    }
    uint64_t v = 0;
    for (; *s != '\0'; s++) {
        int d = hex_digit(*s);
        if (d < 0 || (unsigned)d >= base) {
            return NUM_SYNTAX;
        }
        if (v <= UINT32_MAX) { /* saturates above UINT32_MAX; no u64 overflow */
            v = v * base + (unsigned)d;
        }
    }
    *out = v;
    return v > UINT32_MAX ? NUM_RANGE : NUM_OK;
}

/** Decimal number with an optional fraction, e.g. "903.5". */
typedef struct {
    uint64_t whole; /**< Integer part, saturated just above UINT32_MAX. */
    uint32_t micro; /**< First six fraction digits, in millionths. */
    bool dot;       /**< A fraction was written. */
    bool fine;      /**< Non-zero digits beyond the sixth fraction digit. */
} number_t;

/** Scan a decimal number. @return Pointer past it, or NULL if malformed. */
static const char *scan_number(const char *s, number_t *n)
{
    memset(n, 0, sizeof(*n));
    if (!is_digit(*s)) {
        return NULL;
    }
    for (; is_digit(*s); s++) {
        if (n->whole <= UINT32_MAX) {
            n->whole = n->whole * 10u + (uint64_t)(*s - '0');
        }
    }
    if (*s != '.') {
        return s;
    }
    s++;
    if (!is_digit(*s)) {
        return NULL;
    }
    n->dot = true;
    uint32_t place = 100000u;
    for (; is_digit(*s); s++) {
        uint32_t d = (uint32_t)(*s - '0');
        if (place > 0) {
            n->micro += d * place;
            place /= 10u;
        } else if (d != 0) {
            n->fine = true;
        }
    }
    return s;
}

/** n * scale as an integer; @p scale is 1, 1000, or 1000000. */
static int number_scale(const number_t *n, uint32_t scale, uint64_t *out)
{
    if (n->whole > UINT32_MAX) {
        return NUM_RANGE;
    }
    uint64_t frac = (uint64_t)n->micro * scale;
    if (n->fine || frac % 1000000u != 0) {
        return NUM_INEXACT;
    }
    *out = n->whole * scale + frac / 1000000u;
    return NUM_OK;
}

/** Format Hz as MHz without trailing zeros ("2483.5"). */
static void fmt_mhz(char *buf, size_t cap, uint32_t hz)
{
    unsigned long whole = (unsigned long)(hz / 1000000u);
    unsigned long frac = (unsigned long)(hz % 1000000u);
    if (frac == 0) {
        snprintf(buf, cap, "%lu", whole);
        return;
    }
    int digits = 6;
    while (frac % 10u == 0) {
        frac /= 10u;
        digits--;
    }
    snprintf(buf, cap, "%lu.%0*lu", whole, digits, frac);
}

/* ---- Value parsers (each reports its own error) ------------------------ */

static int parse_time(load_ctx_t *c, const key_def_t *k, int form, const char *key,
                      const char *value, int line, uint32_t *out)
{
    number_t n;
    const char *p = scan_number(value, &n);
    if (p == NULL) {
        return cfg_fail(c, line, NL_ERR_ARG, "%s: invalid time '%s'", key, value);
    }
    while (*p == ' ' || *p == '\t') {
        p++;
    }
    uint32_t scale;
    if (*p == '\0') {
        if (form == FORM_SHORT_TIME) {
            return cfg_fail(c, line, NL_ERR_ARG,
                            "%s needs a unit (us, ms, s); use %s for plain microseconds",
                            key, k->key);
        }
        scale = 1u;
    } else if (strcmp(p, "us") == 0) {
        scale = 1u;
    } else if (strcmp(p, "ms") == 0) {
        scale = 1000u;
    } else if (strcmp(p, "s") == 0) {
        scale = 1000000u;
    } else {
        return cfg_fail(c, line, NL_ERR_ARG, "%s: unknown unit '%s' (use us, ms or s)", key,
                        p);
    }
    uint64_t v = 0;
    int rc = number_scale(&n, scale, &v);
    if (rc == NUM_INEXACT) {
        return cfg_fail(c, line, NL_ERR_ARG,
                        "%s = %s is not a whole number of microseconds", key, value);
    }
    if (rc == NUM_RANGE || v > k->max) {
        return cfg_fail(c, line, NL_ERR_ARG, "%s = %s is too large (max %lu us)", key,
                        value, (unsigned long)k->max);
    }
    *out = (uint32_t)v;
    return NL_OK;
}

static int parse_freq(load_ctx_t *c, const key_def_t *k, int form, const char *key,
                      const char *value, int line, uint32_t *out)
{
    uint64_t v = 0;
    int rc;
    if (form == FORM_MHZ) {
        number_t n;
        const char *p = scan_number(value, &n);
        if (p == NULL || *p != '\0') {
            return cfg_fail(c, line, NL_ERR_ARG, "%s: invalid frequency '%s' (MHz)", key,
                            value);
        }
        rc = number_scale(&n, 1000000u, &v);
        if (rc == NUM_INEXACT) {
            return cfg_fail(c, line, NL_ERR_ARG, "%s = %s is finer than 1 Hz", key, value);
        }
    } else {
        rc = parse_uint(value, &v);
        if (rc == NUM_SYNTAX) {
            return cfg_fail(c, line, NL_ERR_ARG, "%s: invalid frequency '%s' (Hz)", key,
                            value);
        }
    }
    if (rc == NUM_RANGE || (v != 0 && (v < k->min || v > k->max))) {
        char lo[24];
        char hi[24];
        fmt_mhz(lo, sizeof(lo), k->min);
        fmt_mhz(hi, sizeof(hi), k->max);
        return cfg_fail(c, line, NL_ERR_ARG,
                        "%s = %s is outside %s..%s MHz (0 = band unused)", key, value, lo,
                        hi);
    }
    *out = (uint32_t)v;
    return NL_OK;
}

static int parse_name(load_ctx_t *c, const key_def_t *k, const char *key,
                      const char *value, int line)
{
    size_t n = strlen(value);
    if (n < k->min) {
        return cfg_fail(c, line, NL_ERR_ARG, "%s must not be empty", key);
    }
    if (n > k->max) {
        return cfg_fail(c, line, NL_ERR_SIZE, "%s is %lu bytes long (max %lu)", key,
                        (unsigned long)n, (unsigned long)k->max);
    }
    for (size_t i = 0; i < n; i++) {
        uint8_t ch = (uint8_t)value[i];
        if (ch < 0x20u || ch == 0x7Fu) {
            return cfg_fail(c, line, NL_ERR_ARG, "%s contains a control character", key);
        }
    }
    memset(c->host.name, 0, sizeof(c->host.name));
    memcpy(c->host.name, value, n);
    return NL_OK;
}

/** Parse @p value for key @p k into *out (not used by KIND_NAME). */
static int parse_value(load_ctx_t *c, const key_def_t *k, int form, const char *key,
                       const char *value, int line, uint32_t *out)
{
    switch (k->kind) {
    case KIND_TIME: return parse_time(c, k, form, key, value, line, out);
    case KIND_FREQ: return parse_freq(c, k, form, key, value, line, out);
    case KIND_BOOL:
        if (str_ieq(value, "true") || str_ieq(value, "yes") || str_ieq(value, "on") ||
            strcmp(value, "1") == 0) {
            *out = 1;
            return NL_OK;
        }
        if (str_ieq(value, "false") || str_ieq(value, "no") || str_ieq(value, "off") ||
            strcmp(value, "0") == 0) {
            *out = 0;
            return NL_OK;
        }
        return cfg_fail(c, line, NL_ERR_ARG,
                        "%s: expected true/false, yes/no, on/off or 1/0, got '%s'", key,
                        value);
    case KIND_BAND:
        if (str_ieq(value, "subghz")) {
            *out = NL_BAND_SUBGHZ;
        } else if (str_ieq(value, "2g4")) {
            *out = NL_BAND_2G4;
        } else if (str_ieq(value, "dual")) {
            *out = NL_BAND_DUAL;
        } else {
            return cfg_fail(c, line, NL_ERR_ARG,
                            "%s: expected subghz, 2g4 or dual, got '%s'", key, value);
        }
        return NL_OK;
    case KIND_TX_POLICY:
        if (str_ieq(value, "immediate")) {
            *out = NL_TX_IMMEDIATE;
        } else if (str_ieq(value, "in_slot")) {
            *out = NL_TX_IN_SLOT;
        } else {
            return cfg_fail(c, line, NL_ERR_ARG,
                            "%s: expected immediate or in_slot, got '%s'", key, value);
        }
        return NL_OK;
    default: { /* KIND_U8, KIND_U32 */
        uint64_t v = 0;
        int rc = parse_uint(value, &v);
        if (rc == NUM_SYNTAX) {
            return cfg_fail(c, line, NL_ERR_ARG, "%s: invalid integer '%s'", key, value);
        }
        if (rc == NUM_RANGE || v < k->min || v > k->max) {
            return cfg_fail(c, line, NL_ERR_ARG, "%s = %s is out of range (%lu..%lu)", key,
                            value, (unsigned long)k->min, (unsigned long)k->max);
        }
        *out = (uint32_t)v;
        return NL_OK;
    }
    }
}

static void store(load_ctx_t *c, const key_def_t *k, uint32_t v)
{
    uint8_t *base;
    switch (k->target) {
    case TGT_HOST: base = (uint8_t *)&c->host; break;
    case TGT_PARAMS: base = (uint8_t *)&c->params; break;
    default: base = (uint8_t *)&c->plan.zone[c->zone]; break;
    }
    uint8_t *dst = base + k->offset;
    switch (k->kind) {
    case KIND_U8:
    case KIND_BAND:
    case KIND_TX_POLICY: {
        uint8_t b = (uint8_t)v;
        memcpy(dst, &b, sizeof(b));
        break;
    }
    case KIND_BOOL: {
        bool b = v != 0;
        memcpy(dst, &b, sizeof(b));
        break;
    }
    default:
        memcpy(dst, &v, sizeof(v));
        break;
    }
}

/* ---- INI callbacks ----------------------------------------------------- */

static int enter_section(load_ctx_t *c, const char *name, int line)
{
    if (strcmp(name, "device") == 0) {
        c->section = SEC_DEVICE;
    } else if (strcmp(name, "radio") == 0) {
        c->section = SEC_RADIO;
    } else if (strcmp(name, "host") == 0) {
        c->section = SEC_HOST;
    } else if (strncmp(name, "zone.", 5) == 0 && name[5] >= '0' &&
               name[5] < '0' + NL_NUM_ZONES && name[6] == '\0') {
        c->section = SEC_ZONE;
        c->zone = (uint8_t)(name[5] - '0');
    } else if (strncmp(name, "zone", 4) == 0) {
        return cfg_fail(c, line, NL_ERR_NOT_FOUND,
                        "unknown section [%s] (zones are [zone.0] .. [zone.%d])", name,
                        NL_NUM_ZONES - 1);
    } else {
        return cfg_fail(c, line, NL_ERR_NOT_FOUND, "unknown section [%s]", name);
    }
    return NL_OK;
}

/** True if @p key is @p canonical without its "_us" suffix. */
static bool is_short_time_key(const char *key, const char *canonical)
{
    size_t n = strlen(key);
    return strlen(canonical) == n + 3 && strncmp(key, canonical, n) == 0 &&
           strcmp(canonical + n, "_us") == 0;
}

/** Find @p key in @p section. @return Table index or -1. */
static int find_key(uint8_t section, const char *key, int *form)
{
    for (size_t i = 0; i < NUM_KEYS; i++) {
        const key_def_t *k = &keys[i];
        if (k->section != section) {
            continue;
        }
        if (strcmp(key, k->key) == 0) {
            *form = FORM_CANONICAL;
            return (int)i;
        }
        if (k->kind == KIND_TIME && is_short_time_key(key, k->key)) {
            *form = FORM_SHORT_TIME;
            return (int)i;
        }
        if (k->mhz_key != NULL && strcmp(key, k->mhz_key) == 0) {
            *form = FORM_MHZ;
            return (int)i;
        }
    }
    return -1;
}

static int unknown_key(load_ctx_t *c, const char *section, const char *key, int line)
{
    int form;
    for (uint8_t s = SEC_DEVICE; s <= SEC_ZONE; s++) {
        if (find_key(s, key, &form) >= 0) {
            return cfg_fail(c, line, NL_ERR_NOT_FOUND,
                            "unknown key '%s' in [%s]; it belongs in [%s]", key, section,
                            section_names[s]);
        }
    }
    return cfg_fail(c, line, NL_ERR_NOT_FOUND, "unknown key '%s' in [%s]", key, section);
}

static int on_ini_entry(void *user, const char *section, const char *key,
                        const char *value, int line)
{
    load_ctx_t *c = (load_ctx_t *)user;
    if (key == NULL) {
        return enter_section(c, section, line);
    }
    if (c->section == SEC_NONE) {
        return cfg_fail(c, line, NL_ERR_NOT_FOUND, "key '%s' is outside of any [section]",
                        key);
    }
    int form = FORM_CANONICAL;
    int idx = find_key(c->section, key, &form);
    if (idx < 0) {
        return unknown_key(c, section, key, line);
    }
    const key_def_t *k = &keys[idx];

    uint8_t bit = (uint8_t)(c->section == SEC_ZONE ? 1u << c->zone : 1u);
    if (c->seen[idx] & bit) {
        if (form == FORM_CANONICAL) {
            return cfg_fail(c, line, NL_ERR_CONFLICT, "duplicate key '%s' in [%s]", key,
                            section);
        }
        return cfg_fail(c, line, NL_ERR_CONFLICT,
                        "'%s' sets %s, which is already set in [%s]", key, k->key, section);
    }

    int rc;
    if (k->kind == KIND_NAME) {
        rc = parse_name(c, k, key, value, line);
    } else if (value[0] == '\0') {
        rc = cfg_fail(c, line, NL_ERR_ARG, "missing value for '%s'", key);
    } else {
        uint32_t v = 0;
        rc = parse_value(c, k, form, key, value, line, &v);
        if (rc == NL_OK) {
            store(c, k, v);
        }
    }
    if (rc == NL_OK) {
        c->seen[idx] = (uint8_t)(c->seen[idx] | bit);
    }
    return rc;
}

/* ---- Public API -------------------------------------------------------- */

void nl_config_zone_plan_default(nl_zone_plan_t *plan)
{
    memset(plan, 0, sizeof(*plan));
    for (uint32_t z = 0; z < NL_NUM_ZONES; z++) {
        plan->zone[z].priority = 0;
        plan->zone[z].subghz_hz = 903000000u + 3000000u * z;
        plan->zone[z].ghz24_hz = 2405000000u + 10000000u * z;
    }
}

int nl_config_load(const char *text, size_t len, nl_host_config_t *host,
                   nl_radio_params_t *params, nl_zone_plan_t *plan,
                   nl_config_error_t *err)
{
    load_ctx_t c;
    memset(&c, 0, sizeof(c));
    nl_host_config_default(&c.host);
    nl_radio_params_default(&c.params);
    nl_config_zone_plan_default(&c.plan);

    int rc;
    if (text == NULL && len != 0) {
        rc = cfg_fail(&c, 0, NL_ERR_ARG, "text is NULL");
    } else {
        nl_ini_error_t ierr;
        rc = nl_ini_parse(text, len, on_ini_entry, &c, &ierr);
        if (rc != NL_OK && c.err.status == NL_OK) {
            /* Syntax error from the parser rather than a rejected value. */
            cfg_fail(&c, ierr.line, rc, "%s", ierr.msg);
        }
    }

    if (rc == NL_OK) {
        c.params.origin_id = c.host.origin_id;
        if (host != NULL) {
            memcpy(host, &c.host, sizeof(*host));
        }
        if (params != NULL) {
            memcpy(params, &c.params, sizeof(*params));
        }
        if (plan != NULL) {
            memcpy(plan, &c.plan, sizeof(*plan));
        }
    }
    if (err != NULL) {
        memcpy(err, &c.err, sizeof(*err));
    }
    return rc;
}
