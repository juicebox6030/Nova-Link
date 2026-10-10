/**
 * @file gen_vectors.c
 * @brief Emit JSON test vectors from the C implementation.
 *
 * The Python tools in tools/novalink must reproduce every vector byte for
 * byte, so the C core stays the single source of truth for the wire formats.
 *
 *     gen_vectors --out DIR     write every vector file into DIR
 *     gen_vectors --check DIR   regenerate and compare with DIR (exit 1 on drift)
 *     gen_vectors --list        list the vector file names
 *     gen_vectors NAME          print one vector file (e.g. fragments.json)
 *
 * Output is fully deterministic: random-looking payloads come from the
 * core's xorshift PRNG with fixed seeds.
 */
#include "nova_link/nl_fragment.h"
#include "nova_link/nl_link.h"
#include "nova_link/nl_meta.h"
#include "nova_link/nl_segment.h"
#include "nova_link/nl_zone.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---- Minimal JSON writer ----------------------------------------------- */

#define JW_MAX_DEPTH 8

typedef struct {
    FILE *f;
    int depth;
    bool first[JW_MAX_DEPTH];
} jw_t;

static void jw_indent(jw_t *w, int depth)
{
    fputc('\n', w->f);
    for (int i = 0; i < depth; i++) {
        fputs("  ", w->f);
    }
}

/* Separator before a key or array element. Levels 1 and 2 (the top object
 * and the section arrays) get one entry per line; deeper levels are inline. */
static void jw_sep(jw_t *w)
{
    bool first = w->first[w->depth];
    if (!first) {
        fputc(',', w->f);
    }
    if (w->depth <= 2) {
        jw_indent(w, w->depth);
    } else if (!first) {
        fputc(' ', w->f);
    }
    w->first[w->depth] = false;
}

static void jw_open(jw_t *w, char ch)
{
    fputc(ch, w->f);
    if (w->depth + 1 >= JW_MAX_DEPTH) {
        fprintf(stderr, "gen_vectors: JSON nesting too deep\n");
        exit(2);
    }
    w->depth++;
    w->first[w->depth] = true;
}

static void jw_close(jw_t *w, char ch)
{
    if (w->depth <= 2 && !w->first[w->depth]) {
        jw_indent(w, w->depth - 1);
    }
    fputc(ch, w->f);
    w->depth--;
}

static void jw_key(jw_t *w, const char *key)
{
    jw_sep(w);
    fprintf(w->f, "\"%s\": ", key);
}

static void jw_val_u(jw_t *w, unsigned long v)
{
    fprintf(w->f, "%lu", v);
}

static void jw_val_hex(jw_t *w, const uint8_t *p, size_t n)
{
    fputc('"', w->f);
    for (size_t i = 0; i < n; i++) {
        fprintf(w->f, "%02x", p[i]);
    }
    fputc('"', w->f);
}

static void jw_val_str(jw_t *w, const char *s, size_t n)
{
    fputc('"', w->f);
    for (size_t i = 0; i < n; i++) {
        unsigned char c = (unsigned char)s[i];
        if (c == '"' || c == '\\') {
            fprintf(w->f, "\\%c", c);
        } else if (c < 0x20 || c >= 0x7F) {
            fprintf(w->f, "\\u%04x", (unsigned)c);
        } else {
            fputc(c, w->f);
        }
    }
    fputc('"', w->f);
}

static void jw_u(jw_t *w, const char *key, unsigned long v)
{
    jw_key(w, key);
    jw_val_u(w, v);
}

static void jw_hex(jw_t *w, const char *key, const uint8_t *p, size_t n)
{
    jw_key(w, key);
    jw_val_hex(w, p, n);
}

static void jw_str(jw_t *w, const char *key, const char *s)
{
    jw_key(w, key);
    jw_val_str(w, s, strlen(s));
}

/** Start a file: top-level object with generator and description fields. */
static void jw_begin(jw_t *w, FILE *f, const char *description)
{
    memset(w, 0, sizeof(*w));
    w->f = f;
    jw_open(w, '{');
    jw_str(w, "generator", "tests/gen_vectors.c");
    jw_str(w, "description", description);
}

static void jw_end(jw_t *w)
{
    jw_close(w, '}');
    fputc('\n', w->f);
}

static void jw_section(jw_t *w, const char *name)
{
    jw_key(w, name);
    jw_open(w, '[');
}

static void jw_item(jw_t *w)
{
    jw_sep(w);
    jw_open(w, '{');
}

static void jw_obj_elem(jw_t *w)
{
    jw_sep(w);
    jw_open(w, '{');
}

/* ---- Helpers ----------------------------------------------------------- */

static const char *st_name(int rc)
{
    switch (rc) {
    case NL_OK: return "ok";
    case NL_ERR_ARG: return "arg";
    case NL_ERR_SIZE: return "size";
    case NL_ERR_FULL: return "full";
    case NL_ERR_EMPTY: return "empty";
    case NL_ERR_PERM: return "perm";
    case NL_ERR_CONFLICT: return "conflict";
    case NL_ERR_NOT_FOUND: return "not_found";
    case NL_ERR_CRC: return "crc";
    case NL_ERR_PROTO: return "proto";
    case NL_ERR_IO: return "io";
    default: return rc > 0 ? "ok" : "unknown";
    }
}

static uint32_t g_rng;

static void rng_reset(uint32_t seed)
{
    g_rng = nl_rand_seed(seed);
}

static uint32_t rng_upto(uint32_t max)
{
    return nl_rand_upto(&g_rng, max);
}

static void rng_fill(uint8_t *p, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        p[i] = (uint8_t)nl_rand_next(&g_rng);
    }
}

static void die(const char *what, int rc)
{
    fprintf(stderr, "gen_vectors: %s failed: %s (%d)\n", what, nl_status_str(rc), rc);
    exit(2);
}

/* ---- crc8.json --------------------------------------------------------- */

static void crc_item(jw_t *w, const uint8_t *p, size_t n)
{
    jw_item(w);
    jw_hex(w, "data", p, n);
    jw_u(w, "crc", nl_crc8(0, p, n));
    jw_close(w, '}');
}

static void gen_crc8(FILE *f)
{
    jw_t w;
    uint8_t buf[256];
    rng_reset(0xC4C8u);
    jw_begin(&w, f, "CRC-8/SMBUS (poly 0x07, init 0x00, no reflection, no final XOR) "
                    "as computed by nl_crc8(0, data, len)");
    jw_section(&w, "crc8");
    crc_item(&w, NULL, 0);
    crc_item(&w, (const uint8_t *)"123456789", 9);
    const uint8_t singles[] = {0x00, 0x01, 0x07, 0x80, 0xAA, 0xFF};
    for (size_t i = 0; i < sizeof(singles); i++) {
        crc_item(&w, &singles[i], 1);
    }
    const uint8_t hdr_ping[] = {NL_CMD_PING, 0x00};
    const uint8_t hdr_push[] = {NL_CMD_PUSH, 0x03, 0x20, 0x05, 0x41};
    crc_item(&w, hdr_ping, sizeof(hdr_ping));
    crc_item(&w, hdr_push, sizeof(hdr_push));
    for (size_t i = 0; i < sizeof(buf); i++) {
        buf[i] = (uint8_t)i;
    }
    crc_item(&w, buf, sizeof(buf));
    const size_t lens[] = {2, 3, 17, 64, 130};
    for (size_t i = 0; i < NL_ARRAY_SIZE(lens); i++) {
        rng_fill(buf, lens[i]);
        crc_item(&w, buf, lens[i]);
    }
    jw_close(&w, ']');
    jw_end(&w);
}

/* ---- fragments.json ---------------------------------------------------- */

static void frag_fields(jw_t *w, const nl_fragment_t *fr)
{
    jw_u(w, "origin", fr->origin_id);
    jw_u(w, "zone", fr->zone_id);
    jw_u(w, "flags", fr->flags);
    jw_u(w, "seq", fr->seq);
    jw_hex(w, "payload", fr->payload, fr->payload_len);
}

static void frag_encode_item(jw_t *w, uint8_t origin, uint8_t zone, uint8_t flags,
                             uint8_t seq, const uint8_t *payload, uint8_t plen)
{
    nl_fragment_t fr = {origin, zone, flags, seq, payload, plen};
    uint8_t out[NL_MAX_FRAGMENT];
    int n = nl_fragment_encode(&fr, out, sizeof(out));
    if (n < 0) {
        die("nl_fragment_encode", n);
    }
    jw_item(w);
    frag_fields(w, &fr);
    jw_hex(w, "wire", out, (size_t)n);
    jw_close(w, '}');
}

static void gen_fragments(FILE *f)
{
    jw_t w;
    uint8_t payload[NL_MAX_PAYLOAD];
    uint8_t wire[NL_MAX_FRAGMENT + 8];
    rng_reset(0xF4A6u);
    jw_begin(&w, f, "DataFragment codec: nl_fragment_encode / nl_fragment_decode. "
                    "Header = origin<<5 | zone<<2 | flags (BURST 0x02, MGMT_LISTEN 0x01), "
                    "then seq, then 0..100 payload bytes");

    jw_section(&w, "encode");
    const uint8_t plens[] = {0, 1, 2, 3, 10, 50, 99, 100};
    for (uint8_t o = 0; o < NL_NUM_ORIGINS; o++) {
        for (uint8_t z = 0; z < NL_NUM_ZONES; z++) {
            uint8_t plen = plens[(o * 8u + z) % NL_ARRAY_SIZE(plens)];
            rng_fill(payload, plen);
            frag_encode_item(&w, o, z, (uint8_t)((o + z) & 3u),
                             (uint8_t)(o * 37u + z * 11u), payload, plen);
        }
    }
    frag_encode_item(&w, 0, 0, 0, 0x00, NULL, 0);
    frag_encode_item(&w, 7, 7, 3, 0xFF, NULL, 0);
    memset(payload, 0xAA, sizeof(payload));
    frag_encode_item(&w, 5, 2, NL_FLAG_BURST, 0xAA, payload, NL_MAX_PAYLOAD);
    jw_close(&w, ']');

    jw_section(&w, "encode_errors");
    {
        struct {
            uint8_t origin, zone, flags, len;
        } bad[] = {
            {8, 0, 0, 0}, {0, 8, 0, 0}, {0, 0, 4, 0}, {0, 0, 0x80, 0},
            {255, 0, 0, 0}, {0, 0, 0, 101}, {1, 1, 1, 255},
        };
        memset(payload, 0, sizeof(payload));
        uint8_t big[256] = {0};
        for (size_t i = 0; i < NL_ARRAY_SIZE(bad); i++) {
            nl_fragment_t fr = {bad[i].origin, bad[i].zone, bad[i].flags, 0, big, bad[i].len};
            int rc = nl_fragment_encode(&fr, wire, sizeof(wire));
            if (rc >= 0) {
                die("nl_fragment_encode error case", rc);
            }
            jw_item(&w);
            jw_u(&w, "origin", bad[i].origin);
            jw_u(&w, "zone", bad[i].zone);
            jw_u(&w, "flags", bad[i].flags);
            jw_u(&w, "payload_len", bad[i].len);
            jw_str(&w, "status", st_name(rc));
            jw_close(&w, '}');
        }
    }
    jw_close(&w, ']');

    jw_section(&w, "decode");
    for (unsigned h = 0; h < 256; h++) {
        size_t len = 2 + h % 5u;
        wire[0] = (uint8_t)h;
        wire[1] = (uint8_t)(h ^ 0x5Au);
        rng_fill(&wire[2], len - 2);
        nl_fragment_t fr;
        int rc = nl_fragment_decode(wire, len, &fr);
        if (rc != NL_OK) {
            die("nl_fragment_decode", rc);
        }
        jw_item(&w);
        jw_hex(&w, "wire", wire, len);
        frag_fields(&w, &fr);
        jw_close(&w, '}');
    }
    {
        wire[0] = 0x3F;
        wire[1] = 0x80;
        rng_fill(&wire[2], NL_MAX_PAYLOAD);
        nl_fragment_t fr;
        int rc = nl_fragment_decode(wire, NL_MAX_FRAGMENT, &fr);
        if (rc != NL_OK) {
            die("nl_fragment_decode", rc);
        }
        jw_item(&w);
        jw_hex(&w, "wire", wire, NL_MAX_FRAGMENT);
        frag_fields(&w, &fr);
        jw_close(&w, '}');
    }
    jw_close(&w, ']');

    jw_section(&w, "decode_errors");
    {
        const size_t lens[] = {0, 1, NL_MAX_FRAGMENT + 1, NL_MAX_FRAGMENT + 8};
        memset(wire, 0x21, sizeof(wire));
        for (size_t i = 0; i < NL_ARRAY_SIZE(lens); i++) {
            nl_fragment_t fr;
            int rc = nl_fragment_decode(wire, lens[i], &fr);
            if (rc == NL_OK) {
                die("nl_fragment_decode error case", rc);
            }
            jw_item(&w);
            jw_hex(&w, "wire", wire, lens[i]);
            jw_str(&w, "status", st_name(rc));
            jw_close(&w, '}');
        }
    }
    jw_close(&w, ']');
    jw_end(&w);
}

/* ---- link_frames.json -------------------------------------------------- */

#define STREAM_CAP 512

typedef struct {
    uint8_t b[STREAM_CAP];
    size_t n;
} stream_t;

static void s_byte(stream_t *s, uint8_t v)
{
    if (s->n >= STREAM_CAP) {
        fprintf(stderr, "gen_vectors: stream overflow\n");
        exit(2);
    }
    s->b[s->n++] = v;
}

static void s_bytes(stream_t *s, const uint8_t *p, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        s_byte(s, p[i]);
    }
}

static void s_fill(stream_t *s, uint8_t v, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        s_byte(s, v);
    }
}

/** Append a valid frame; @return its offset in the stream. */
static size_t s_frame(stream_t *s, uint8_t cmd, const uint8_t *data, size_t len)
{
    uint8_t tmp[NL_LINK_FRAME_MAX];
    int n = nl_link_encode(cmd, data, len, tmp, sizeof(tmp));
    if (n < 0) {
        die("nl_link_encode", n);
    }
    size_t at = s->n;
    s_bytes(s, tmp, (size_t)n);
    return at;
}

static const uint8_t k_cmds[] = {NL_CMD_PING, NL_CMD_PULL, NL_CMD_PUSH,
                                 NL_CMD_STATUS, NL_CMD_ZONE_CONFIG, NL_CMD_RADIO_CONFIG,
                                 NL_RSP_FRAGMENT, NL_RSP_PONG, NL_RSP_STATUS};

static void fuzz_stream(stream_t *s)
{
    uint8_t data[NL_LINK_MAX_DATA];
    s->n = 0;
    uint32_t parts = 3 + rng_upto(6);
    for (uint32_t p = 0; p < parts; p++) {
        uint32_t kind = rng_upto(6);
        uint8_t cmd = k_cmds[rng_upto(NL_ARRAY_SIZE(k_cmds) - 1u)];
        size_t len = rng_upto(7) == 0 ? rng_upto(NL_LINK_MAX_DATA) : rng_upto(23);
        rng_fill(data, len);
        switch (kind) {
        case 0:
        case 1:
            s_frame(s, cmd, data, len);
            break;
        case 2:
            for (uint32_t k = 1 + rng_upto(7); k > 0; k--) {
                s_byte(s, (uint8_t)nl_rand_next(&g_rng));
            }
            break;
        case 3: {
            /* Two draws: sequence them (argument order is unspecified and
             * differs between gcc and clang). Count first, as gcc did when
             * the vectors were generated. */
            size_t count = 1 + rng_upto(7);
            uint8_t fill = rng_upto(1) ? 0xFF : 0x00;
            s_fill(s, fill, count);
            break;
        }
        case 4:
            s_byte(s, NL_LINK_SYNC);
            if (rng_upto(1)) {
                s_byte(s, (uint8_t)nl_rand_next(&g_rng));
            }
            break;
        case 5: {
            size_t at = s_frame(s, cmd, data, len);
            size_t flen = s->n - at;
            if (rng_upto(1)) {
                /* corrupt one bit */
                size_t i = at + rng_upto((uint32_t)flen - 1u);
                s->b[i] = (uint8_t)(s->b[i] ^ (1u << rng_upto(7)));
            } else {
                /* truncate */
                s->n = at + 1 + rng_upto((uint32_t)flen - 2u);
            }
            break;
        }
        default:
            break;
        }
    }
}

typedef struct {
    const char *name;
    stream_t s;
} named_stream_t;

#define MAX_STREAMS 48

static size_t build_streams(named_stream_t *out)
{
    size_t k = 0;
    const uint8_t abc[] = {'a', 'b', 'c', 'd'};
    const uint8_t frag[] = {0x24, 0x07, 0x01, 0xAA, 0x03};
    uint8_t big[NL_LINK_MAX_DATA];
    named_stream_t *t;

#define NEW(nm) (t = &out[k++], t->name = (nm), t->s.n = 0, &t->s)

    stream_t *s = NEW("empty");
    (void)s;

    s = NEW("ping");
    s_frame(s, NL_CMD_PING, NULL, 0);

    s = NEW("zero_filler_around_frame");
    s_fill(s, 0, 5);
    s_frame(s, NL_RSP_FRAGMENT, frag, sizeof(frag));
    s_fill(s, 0, 5);

    s = NEW("stray_sync_in_filler");
    s_fill(s, 0, 3);
    s_byte(s, NL_LINK_SYNC);
    s_fill(s, 0, 3);
    s_frame(s, NL_RSP_FRAGMENT, frag, sizeof(frag));
    s_fill(s, 0, 4);

    s = NEW("bad_crc_only");
    s_frame(s, NL_CMD_STATUS, NULL, 0);
    s->b[s->n - 1] ^= 0x01;

    s = NEW("bad_crc_then_good");
    s_frame(s, NL_CMD_PUSH, abc, sizeof(abc));
    s->b[s->n - 1] ^= 0x80;
    s_frame(s, NL_CMD_PULL, NULL, 0);

    s = NEW("truncated");
    s_frame(s, NL_CMD_PUSH, abc, sizeof(abc));
    s->n -= 1;

    s = NEW("phantom_aa000000_in_zeros");
    s_fill(s, 0, 5);
    s_byte(s, NL_LINK_SYNC);
    s_fill(s, 0, 10);

    s = NEW("sync_then_ff_filler");
    s_byte(s, NL_LINK_SYNC);
    s_fill(s, 0xFF, 6);

    s = NEW("len_too_big");
    s_byte(s, NL_LINK_SYNC);
    s_byte(s, NL_CMD_PUSH);
    s_byte(s, NL_LINK_MAX_DATA + 1);
    s_fill(s, 0, 8);
    s_frame(s, NL_CMD_PING, NULL, 0);

    s = NEW("double_sync");
    s_byte(s, NL_LINK_SYNC);
    s_frame(s, NL_CMD_STATUS, NULL, 0);

    s = NEW("triple_sync");
    s_fill(s, NL_LINK_SYNC, 2);
    s_frame(s, NL_RSP_PONG, abc, sizeof(abc));

    s = NEW("two_frames");
    s_frame(s, NL_CMD_PUSH, frag, sizeof(frag));
    s_frame(s, NL_CMD_PULL, NULL, 0);

    s = NEW("embedded_frame_in_corrupt_outer");
    {
        stream_t inner = {{0}, 0};
        s_frame(&inner, NL_CMD_PING, NULL, 0);
        s_bytes(&inner, abc, 3);
        s_frame(s, NL_CMD_PUSH, inner.b, inner.n);
        s->b[s->n - 1] ^= 0x01;
    }

    s = NEW("spurious_sync_swallows_frame");
    s_byte(s, NL_LINK_SYNC);
    s_byte(s, NL_CMD_PUSH);
    s_byte(s, 0x05);
    s_frame(s, NL_CMD_PING, NULL, 0);
    s_fill(s, 0, 4);
    s_frame(s, NL_CMD_PULL, NULL, 0);

    s = NEW("len_byte_is_sync");
    s_byte(s, NL_LINK_SYNC);
    s_byte(s, NL_CMD_PUSH);
    s_frame(s, NL_CMD_PING, NULL, 0);

    s = NEW("cmd_0xaa_frame");
    s_frame(s, NL_LINK_SYNC, NULL, 0);

    s = NEW("max_len_frame");
    for (size_t i = 0; i < sizeof(big); i++) {
        big[i] = (uint8_t)(0xAAu ^ i);
    }
    s_frame(s, NL_RSP_FRAGMENT, big, sizeof(big));

    s = NEW("empty_pull_response");
    s_fill(s, 0, 2);
    s_frame(s, NL_RSP_FRAGMENT, NULL, 0);

    s = NEW("all_ff");
    s_fill(s, 0xFF, 12);

    static char names[16][16];
    for (int i = 0; i < 16; i++) {
        snprintf(names[i], sizeof(names[i]), "fuzz_%02d", i);
        s = NEW(names[i]);
        fuzz_stream(s);
    }
#undef NEW
    if (k > MAX_STREAMS) {
        fprintf(stderr, "gen_vectors: too many streams\n");
        exit(2);
    }
    return k;
}

static void link_encode_item(jw_t *w, uint8_t cmd, const uint8_t *data, size_t len)
{
    uint8_t out[NL_LINK_FRAME_MAX];
    int n = nl_link_encode(cmd, data, len, out, sizeof(out));
    if (n < 0) {
        die("nl_link_encode", n);
    }
    jw_item(w);
    jw_u(w, "cmd", cmd);
    jw_hex(w, "data", data, len);
    jw_hex(w, "frame", out, (size_t)n);
    jw_close(w, '}');
}

static void gen_link(FILE *f)
{
    jw_t w;
    uint8_t data[NL_LINK_MAX_DATA + 1];
    rng_reset(0x11A4u);
    jw_begin(&w, f, "Host<->radio link frames: 0xAA CMD LEN DATA CRC8, CRC-8/SMBUS over "
                    "CMD, LEN, DATA. 'decode' repeats nl_link_decode on the remaining "
                    "bytes until it stops returning ok (the radio's SPI loop). "
                    "'parser' feeds every byte through nl_link_parser_feed; 'at' is "
                    "the index of the byte that completed a frame");

    jw_section(&w, "encode");
    const size_t lens[] = {0, 1, 4, 32, NL_LINK_MAX_DATA};
    for (size_t i = 0; i < NL_ARRAY_SIZE(k_cmds); i++) {
        size_t len = lens[i % NL_ARRAY_SIZE(lens)];
        rng_fill(data, len);
        link_encode_item(&w, k_cmds[i], data, len);
    }
    {
        const uint8_t push[] = {0x20, 0x05, 0x41};
        link_encode_item(&w, NL_CMD_PUSH, push, sizeof(push));
        memset(data, NL_LINK_SYNC, sizeof(data));
        link_encode_item(&w, NL_CMD_PUSH, data, 7);
        link_encode_item(&w, 0x7F, NULL, 0);
        link_encode_item(&w, NL_LINK_SYNC, NULL, 0);
        rng_fill(data, NL_LINK_MAX_DATA);
        link_encode_item(&w, NL_RSP_FRAGMENT, data, NL_LINK_MAX_DATA);
    }
    jw_close(&w, ']');

    jw_section(&w, "encode_errors");
    {
        uint8_t out[NL_LINK_FRAME_MAX + 8];
        int rc = nl_link_encode(NL_CMD_PUSH, data, NL_LINK_MAX_DATA + 1, out, sizeof(out));
        if (rc >= 0) {
            die("nl_link_encode error case", rc);
        }
        jw_item(&w);
        jw_u(&w, "cmd", NL_CMD_PUSH);
        jw_u(&w, "data_len", NL_LINK_MAX_DATA + 1);
        jw_str(&w, "status", st_name(rc));
        jw_close(&w, '}');
    }
    jw_close(&w, ']');

    static named_stream_t streams[MAX_STREAMS];
    size_t ns = build_streams(streams);

    jw_section(&w, "decode");
    for (size_t i = 0; i < ns; i++) {
        const stream_t *s = &streams[i].s;
        jw_item(&w);
        jw_str(&w, "name", streams[i].name);
        jw_hex(&w, "input", s->b, s->n);
        jw_key(&w, "results");
        jw_open(&w, '[');
        size_t off = 0;
        do {
            nl_link_frame_t fr;
            size_t used = 0;
            int rc = nl_link_decode(&s->b[off], s->n - off, &fr, &used);
            jw_obj_elem(&w);
            jw_str(&w, "status", st_name(rc));
            if (rc == NL_OK) {
                jw_u(&w, "cmd", fr.cmd);
                jw_hex(&w, "data", fr.data, fr.len);
            }
            jw_u(&w, "consumed", (unsigned long)used);
            jw_close(&w, '}');
            if (rc != NL_OK) {
                break;
            }
            off += used;
        } while (off < s->n);
        jw_close(&w, ']');
        jw_close(&w, '}');
    }
    jw_close(&w, ']');

    jw_section(&w, "parser");
    for (size_t i = 0; i < ns; i++) {
        const stream_t *s = &streams[i].s;
        nl_link_parser_t p;
        nl_link_parser_init(&p);
        jw_item(&w);
        jw_str(&w, "name", streams[i].name);
        jw_hex(&w, "input", s->b, s->n);
        jw_key(&w, "frames");
        jw_open(&w, '[');
        for (size_t b = 0; b < s->n; b++) {
            if (nl_link_parser_feed(&p, s->b[b]) == 1) {
                jw_obj_elem(&w);
                jw_u(&w, "at", (unsigned long)b);
                jw_u(&w, "cmd", p.frame.cmd);
                jw_hex(&w, "data", p.frame.data, p.frame.len);
                jw_close(&w, '}');
            }
        }
        jw_close(&w, ']');
        jw_u(&w, "crc_errors", p.crc_errors);
        jw_u(&w, "len_errors", p.len_errors);
        jw_u(&w, "cmd_errors", p.cmd_errors);
        jw_u(&w, "state", p.state);
        jw_close(&w, '}');
    }
    jw_close(&w, ']');
    jw_end(&w);
}

/* ---- params.json ------------------------------------------------------- */

static void frame_field(jw_t *w, uint8_t cmd, const uint8_t *data, size_t len)
{
    uint8_t out[NL_LINK_FRAME_MAX];
    int n = nl_link_encode(cmd, data, len, out, sizeof(out));
    if (n < 0) {
        die("nl_link_encode", n);
    }
    jw_hex(w, "frame", out, (size_t)n);
}

static void params_item(jw_t *w, const char *name, const nl_radio_params_t *in)
{
    uint8_t wire[NL_RADIO_PARAMS_WIRE_SIZE];
    int n = nl_radio_params_encode(in, wire, sizeof(wire));
    if (n != NL_RADIO_PARAMS_WIRE_SIZE) {
        die("nl_radio_params_encode", n);
    }
    nl_radio_params_t p;
    int rc = nl_radio_params_decode(wire, (size_t)n, &p);
    if (rc != NL_OK) {
        die("nl_radio_params_decode", rc);
    }
    jw_item(w);
    jw_str(w, "name", name);
    jw_u(w, "origin_id", p.origin_id);
    jw_u(w, "band", p.band);
    jw_u(w, "tx_policy", p.tx_policy);
    jw_u(w, "tx_repeats", p.tx_repeats);
    jw_u(w, "dwell_us", p.dwell_us);
    jw_u(w, "burst_extend_us", p.burst_extend_us);
    jw_u(w, "mgmt_hold_us", p.mgmt_hold_us);
    jw_u(w, "repeat_interval_us", p.repeat_interval_us);
    jw_u(w, "tracker_stale_us", p.tracker_stale_us);
    jw_u(w, "repeat_jitter_us", p.repeat_jitter_us);
    jw_u(w, "discovery_interval_us", p.discovery_interval_us);
    jw_u(w, "mgmt_repeats", p.mgmt_repeats);
    jw_u(w, "cca_backoff_us", p.cca_backoff_us);
    jw_hex(w, "wire", wire, (size_t)n);
    frame_field(w, NL_CMD_RADIO_CONFIG, wire, (size_t)n);
    jw_close(w, '}');
}

static void decode_error_item(jw_t *w, const uint8_t *wire, size_t len, int rc)
{
    if (rc == NL_OK) {
        die("decode error case", rc);
    }
    jw_item(w);
    jw_hex(w, "wire", wire, len);
    jw_str(w, "status", st_name(rc));
    jw_close(w, '}');
}

static void plan_item(jw_t *w, const char *name, const nl_zone_plan_t *in)
{
    uint8_t wire[NL_ZONE_PLAN_WIRE_SIZE];
    int n = nl_zone_plan_encode(in, wire, sizeof(wire));
    if (n != NL_ZONE_PLAN_WIRE_SIZE) {
        die("nl_zone_plan_encode", n);
    }
    nl_zone_plan_t plan;
    int rc = nl_zone_plan_decode(wire, (size_t)n, &plan);
    if (rc != NL_OK) {
        die("nl_zone_plan_decode", rc);
    }
    jw_item(w);
    jw_str(w, "name", name);
    jw_key(w, "zones");
    jw_open(w, '[');
    for (int z = 0; z < NL_NUM_ZONES; z++) {
        jw_obj_elem(w);
        jw_u(w, "priority", plan.zone[z].priority);
        jw_u(w, "subghz_hz", plan.zone[z].subghz_hz);
        jw_u(w, "ghz24_hz", plan.zone[z].ghz24_hz);
        jw_close(w, '}');
    }
    jw_close(w, ']');
    jw_hex(w, "wire", wire, (size_t)n);
    frame_field(w, NL_CMD_ZONE_CONFIG, wire, (size_t)n);
    jw_close(w, '}');
}

static void status_item(jw_t *w, const char *name, const nl_radio_status_t *in)
{
    uint8_t wire[NL_RADIO_STATUS_WIRE_SIZE];
    int n = nl_radio_status_encode(in, wire, sizeof(wire));
    if (n != NL_RADIO_STATUS_WIRE_SIZE) {
        die("nl_radio_status_encode", n);
    }
    nl_radio_status_t s;
    int rc = nl_radio_status_decode(wire, (size_t)n, &s);
    if (rc != NL_OK) {
        die("nl_radio_status_decode", rc);
    }
    jw_item(w);
    jw_str(w, "name", name);
    jw_u(w, "proto_version", s.proto_version);
    jw_u(w, "flags", s.flags);
    jw_u(w, "rx_queue_len", s.rx_queue_len);
    jw_u(w, "tx_queue_len", s.tx_queue_len);
    jw_u(w, "rx_ok", s.rx_ok);
    jw_u(w, "rx_dup", s.rx_dup);
    jw_u(w, "rx_dropped", s.rx_dropped);
    jw_u(w, "rx_ignored", s.rx_ignored);
    jw_u(w, "tx_sent", s.tx_sent);
    jw_u(w, "tx_dropped", s.tx_dropped);
    jw_hex(w, "wire", wire, (size_t)n);
    frame_field(w, NL_RSP_STATUS, wire, (size_t)n);
    jw_close(w, '}');
}

static void pong_item(jw_t *w, const nl_link_pong_t *in)
{
    uint8_t wire[NL_PONG_WIRE_SIZE];
    int n = nl_link_pong_encode(in, wire, sizeof(wire));
    if (n != NL_PONG_WIRE_SIZE) {
        die("nl_link_pong_encode", n);
    }
    nl_link_pong_t p;
    int rc = nl_link_pong_decode(wire, (size_t)n, &p);
    if (rc != NL_OK) {
        die("nl_link_pong_decode", rc);
    }
    jw_item(w);
    jw_u(w, "proto_version", p.proto_version);
    jw_u(w, "fw_major", p.fw_major);
    jw_u(w, "fw_minor", p.fw_minor);
    jw_u(w, "fw_patch", p.fw_patch);
    jw_hex(w, "wire", wire, (size_t)n);
    frame_field(w, NL_RSP_PONG, wire, (size_t)n);
    jw_close(w, '}');
}

static void gen_params(FILE *f)
{
    jw_t w;
    uint8_t wire[96];
    int rc;
    rng_reset(0x9A4Au);
    jw_begin(&w, f, "Link payload codecs: radio params (NL_CMD_RADIO_CONFIG, 33 bytes), "
                    "zone plan (NL_CMD_ZONE_CONFIG, 72 bytes), radio status "
                    "(NL_RSP_STATUS, 28 bytes), pong (NL_RSP_PONG, 4 bytes). "
                    "Multi-byte fields are little-endian. 'frame' is the full link frame");

    jw_section(&w, "radio_params");
    {
        nl_radio_params_t p;
        nl_radio_params_default(&p);
        params_item(&w, "default", &p);

        p.origin_id = 3;
        p.band = NL_BAND_DUAL;
        p.tx_policy = NL_TX_IN_SLOT;
        p.tx_repeats = 2;
        p.dwell_us = 1234;
        p.burst_extend_us = 5678;
        p.mgmt_hold_us = 100000;
        p.repeat_interval_us = 2500;
        p.tracker_stale_us = 750000;
        p.repeat_jitter_us = 333;
        p.discovery_interval_us = 0;
        p.mgmt_repeats = 0;
        p.cca_backoff_us = 3000;
        params_item(&w, "custom", &p);

        p.origin_id = 7;
        p.band = NL_BAND_2G4;
        p.tx_policy = NL_TX_IN_SLOT;
        p.tx_repeats = 255;
        p.dwell_us = UINT32_MAX;
        p.burst_extend_us = 0x01020304u;
        p.mgmt_hold_us = 0x80000000u;
        p.repeat_interval_us = 0xDEADBEEFu;
        p.tracker_stale_us = 1;
        p.repeat_jitter_us = UINT32_MAX;
        p.discovery_interval_us = 0xA5A5A5A5u;
        p.mgmt_repeats = 255;
        p.cca_backoff_us = 0x7F000001u;
        params_item(&w, "max", &p);

        memset(&p, 0, sizeof(p));
        p.tx_repeats = 1;
        params_item(&w, "min", &p);
    }
    jw_close(&w, ']');

    jw_section(&w, "radio_params_decode_errors");
    {
        nl_radio_params_t def, p;
        nl_radio_params_default(&def);
        const struct {
            uint8_t idx, val;
        } bad[] = {{0, 8}, {0, 0xFF}, {1, 3}, {2, 2}, {3, 0}};
        for (size_t i = 0; i < NL_ARRAY_SIZE(bad); i++) {
            nl_radio_params_encode(&def, wire, sizeof(wire));
            wire[bad[i].idx] = bad[i].val;
            rc = nl_radio_params_decode(wire, NL_RADIO_PARAMS_WIRE_SIZE, &p);
            decode_error_item(&w, wire, NL_RADIO_PARAMS_WIRE_SIZE, rc);
        }
        nl_radio_params_encode(&def, wire, sizeof(wire));
        wire[NL_RADIO_PARAMS_WIRE_SIZE] = 0;
        const size_t lens[] = {0, 24, NL_RADIO_PARAMS_WIRE_SIZE - 1,
                               NL_RADIO_PARAMS_WIRE_SIZE + 1};
        for (size_t i = 0; i < NL_ARRAY_SIZE(lens); i++) {
            rc = nl_radio_params_decode(wire, lens[i], &p);
            decode_error_item(&w, wire, lens[i], rc);
        }
    }
    jw_close(&w, ']');

    jw_section(&w, "zone_plan");
    {
        nl_zone_plan_t plan;
        memset(&plan, 0, sizeof(plan));
        plan_item(&w, "zero", &plan);
        for (uint32_t z = 0; z < NL_NUM_ZONES; z++) {
            plan.zone[z].priority = (uint8_t)(z == 0 ? 0 : (z % 4u) + 1u);
            plan.zone[z].subghz_hz = 902500000u + z * 500000u;
            plan.zone[z].ghz24_hz = z % 3u == 2u ? 0u : 2405000000u + z * 5000000u;
        }
        plan_item(&w, "typical", &plan);
        for (uint32_t z = 0; z < NL_NUM_ZONES; z++) {
            plan.zone[z].priority = (uint8_t)(0xF8u + z);
            plan.zone[z].subghz_hz = UINT32_MAX - z;
            plan.zone[z].ghz24_hz = nl_rand_next(&g_rng);
        }
        plan_item(&w, "extreme", &plan);
    }
    jw_close(&w, ']');

    jw_section(&w, "zone_plan_decode_errors");
    {
        nl_zone_plan_t plan;
        memset(wire, 0x11, sizeof(wire));
        const size_t lens[] = {0, 71, 73};
        for (size_t i = 0; i < NL_ARRAY_SIZE(lens); i++) {
            rc = nl_zone_plan_decode(wire, lens[i], &plan);
            decode_error_item(&w, wire, lens[i], rc);
        }
    }
    jw_close(&w, ']');

    jw_section(&w, "status");
    {
        nl_radio_status_t s;
        memset(&s, 0, sizeof(s));
        status_item(&w, "zero", &s);
        s.proto_version = NL_LINK_PROTOCOL_VERSION;
        s.flags = NL_STATUS_F_RX_PENDING | NL_STATUS_F_CONFIGURED;
        s.rx_queue_len = 3;
        s.tx_queue_len = 12;
        s.rx_ok = 123456;
        s.rx_dup = 7890;
        s.rx_dropped = 2;
        s.rx_ignored = 44;
        s.tx_sent = 0x00ABCDEFu;
        s.tx_dropped = 1;
        status_item(&w, "typical", &s);
        s.proto_version = 0xFF;
        s.flags = 0xFC;
        s.rx_queue_len = 0xFF;
        s.tx_queue_len = 0x80;
        s.rx_ok = UINT32_MAX;
        s.rx_dup = 0x80000000u;
        s.rx_dropped = 0x01020304u;
        s.rx_ignored = 0xA1B2C3D4u;
        s.tx_sent = 0xFFFFFFFEu;
        s.tx_dropped = 0x7FFFFFFFu;
        status_item(&w, "extreme", &s);
    }
    jw_close(&w, ']');

    jw_section(&w, "status_decode_errors");
    {
        nl_radio_status_t s;
        memset(wire, 0x22, sizeof(wire));
        const size_t lens[] = {0, 27, 29, 32};
        for (size_t i = 0; i < NL_ARRAY_SIZE(lens); i++) {
            rc = nl_radio_status_decode(wire, lens[i], &s);
            decode_error_item(&w, wire, lens[i], rc);
        }
    }
    jw_close(&w, ']');

    jw_section(&w, "pong");
    {
        nl_link_pong_t p = {NL_LINK_PROTOCOL_VERSION, NL_VERSION_MAJOR, NL_VERSION_MINOR,
                            NL_VERSION_PATCH};
        pong_item(&w, &p);
        nl_link_pong_t q = {2, 10, 20, 255};
        pong_item(&w, &q);
    }
    jw_close(&w, ']');

    jw_section(&w, "pong_decode_errors");
    {
        nl_link_pong_t p;
        memset(wire, 0x33, sizeof(wire));
        const size_t lens[] = {0, 3, 5};
        for (size_t i = 0; i < NL_ARRAY_SIZE(lens); i++) {
            rc = nl_link_pong_decode(wire, lens[i], &p);
            decode_error_item(&w, wire, lens[i], rc);
        }
    }
    jw_close(&w, ']');
    jw_end(&w);
}

/* ---- meta.json --------------------------------------------------------- */

typedef struct {
    uint8_t b[NL_META_QUEUE_BYTES + 8];
    size_t n;
} pbuf_t;

static void p_tlv(pbuf_t *p, uint8_t type, const uint8_t *v, size_t len)
{
    p->b[p->n++] = type;
    p->b[p->n++] = (uint8_t)len;
    for (size_t i = 0; i < len; i++) {
        p->b[p->n++] = v[i];
    }
}

static void tlv_item(jw_t *w, const char *name, const uint8_t *buf, size_t len)
{
    nl_meta_iter_t it;
    uint8_t type, vlen;
    const uint8_t *v;
    int rc;
    nl_meta_iter_init(&it, buf, len);
    jw_item(w);
    jw_str(w, "name", name);
    jw_hex(w, "payload", buf, len);
    jw_key(w, "records");
    jw_open(w, '[');
    while ((rc = nl_meta_iter_next(&it, &type, &v, &vlen)) == 1) {
        jw_obj_elem(w);
        jw_u(w, "type", type);
        jw_hex(w, "value", v, vlen);
        jw_close(w, '}');
    }
    jw_close(w, ']');
    jw_str(w, "status", st_name(rc));
    jw_close(w, '}');
}

static void device_item(jw_t *w, uint8_t pv, uint8_t ma, uint8_t mi, uint8_t pa,
                        const char *name, size_t name_bytes)
{
    nl_meta_device_t dev;
    memset(&dev, 0, sizeof(dev));
    dev.proto_version = pv;
    dev.fw_major = ma;
    dev.fw_minor = mi;
    dev.fw_patch = pa;
    memcpy(dev.name, name, name_bytes);
    uint8_t v[NL_META_MAX_VALUE];
    int n = nl_meta_encode_device(&dev, v, sizeof(v));
    if (n < 0) {
        die("nl_meta_encode_device", n);
    }
    nl_meta_device_t out;
    int rc = nl_meta_decode_device(v, (size_t)n, &out);
    if (rc != NL_OK) {
        die("nl_meta_decode_device", rc);
    }
    jw_item(w);
    jw_u(w, "proto_version", out.proto_version);
    jw_u(w, "fw_major", out.fw_major);
    jw_u(w, "fw_minor", out.fw_minor);
    jw_u(w, "fw_patch", out.fw_patch);
    jw_key(w, "name");
    jw_val_str(w, name, name_bytes);
    jw_str(w, "decoded_name", out.name);
    jw_hex(w, "value", v, (size_t)n);
    jw_close(w, '}');
}

static void claims_item(jw_t *w, const nl_meta_claim_t *c, size_t count)
{
    uint8_t v[NL_META_MAX_VALUE];
    int n = nl_meta_encode_claims(c, count, v, sizeof(v));
    if (n < 0) {
        die("nl_meta_encode_claims", n);
    }
    nl_meta_claim_t out[NL_META_MAX_VALUE / NL_META_CLAIM_WIRE_SIZE];
    int m = nl_meta_decode_claims(v, (size_t)n, out, NL_ARRAY_SIZE(out));
    if (m != (int)count) {
        die("nl_meta_decode_claims", m);
    }
    jw_item(w);
    jw_key(w, "claims");
    jw_open(w, '[');
    for (int i = 0; i < m; i++) {
        jw_obj_elem(w);
        jw_u(w, "zone", out[i].zone);
        jw_u(w, "mode", out[i].mode);
        jw_u(w, "plugin_type", out[i].plugin_type);
        jw_close(w, '}');
    }
    jw_close(w, ']');
    jw_hex(w, "value", v, (size_t)n);
    jw_close(w, '}');
}

/* One step of a metadata queue scenario. */
typedef enum { Q_PUSH, Q_REMOVE, Q_PACK } qop_kind_t;

typedef struct {
    qop_kind_t kind;
    uint8_t type;   /* PUSH / REMOVE */
    uint8_t fill;   /* PUSH: value byte pattern seed */
    uint16_t len;   /* PUSH: value length; PACK: cap */
} qop_t;

static void queue_item(jw_t *w, const char *name, const qop_t *ops, size_t nops)
{
    nl_meta_queue_t q;
    nl_meta_queue_init(&q);
    jw_item(w);
    jw_str(w, "name", name);
    jw_key(w, "ops");
    jw_open(w, '[');
    for (size_t i = 0; i < nops; i++) {
        jw_obj_elem(w);
        if (ops[i].kind == Q_PUSH) {
            uint8_t v[NL_META_MAX_VALUE + 8];
            for (size_t k = 0; k < ops[i].len; k++) {
                v[k] = (uint8_t)(ops[i].fill + k);
            }
            int rc = nl_meta_queue_push(&q, ops[i].type, v, ops[i].len);
            jw_str(w, "op", "push");
            jw_u(w, "type", ops[i].type);
            jw_hex(w, "value", v, ops[i].len);
            jw_str(w, "status", st_name(rc));
        } else if (ops[i].kind == Q_REMOVE) {
            nl_meta_queue_remove_type(&q, ops[i].type);
            jw_str(w, "op", "remove_type");
            jw_u(w, "type", ops[i].type);
        } else {
            uint8_t out[NL_META_QUEUE_BYTES];
            size_t n = nl_meta_queue_pack(&q, out, ops[i].len);
            jw_str(w, "op", "pack");
            jw_u(w, "cap", ops[i].len);
            jw_hex(w, "payload", out, n);
        }
        jw_u(w, "used", q.used);
        jw_close(w, '}');
    }
    jw_close(w, ']');
    jw_u(w, "dropped", q.dropped);
    jw_close(w, '}');
}

static void gen_meta(FILE *f)
{
    jw_t w;
    pbuf_t p;
    uint8_t v[NL_MAX_PAYLOAD];
    rng_reset(0x3E7Au);
    jw_begin(&w, f, "Zone 0 metadata: TLV records [type u8][len u8][value]. 'tlv' is "
                    "nl_meta_iter_next over a payload; 'device'/'claims' use "
                    "nl_meta_encode_* then nl_meta_decode_*; 'plugin_data' and "
                    "'congestion' values are built exactly like nl_host.c; 'queue' "
                    "replays nl_meta_queue_push/remove_type/pack");

    jw_section(&w, "tlv");
    p.n = 0;
    tlv_item(&w, "empty", p.b, 0);
    p.n = 0;
    p_tlv(&p, NL_META_DEVICE_ANNOUNCE, NULL, 0);
    tlv_item(&w, "zero_length_value", p.b, p.n);
    p.n = 0;
    {
        const uint8_t dev[] = {1, 0, 1, 0, 'n', 'o', 'v', 'a'};
        const uint8_t claims[] = {1, NL_CLAIM_EXCLUSIVE, 0x34, 0x12, 2, NL_CLAIM_SHARED, 0xFF, 0xFF};
        p_tlv(&p, NL_META_DEVICE_ANNOUNCE, dev, sizeof(dev));
        p_tlv(&p, NL_META_CLAIM_ANNOUNCE, claims, sizeof(claims));
        p_tlv(&p, NL_META_DEBUG_TEXT, (const uint8_t *)"hi there", 8);
        tlv_item(&w, "three_records", p.b, p.n);
    }
    p.n = 0;
    p_tlv(&p, NL_META_DEBUG_TEXT, (const uint8_t *)"hi", 2);
    p.b[p.n++] = 0x07;
    tlv_item(&w, "trailing_type_byte", p.b, p.n);
    p.n = 0;
    p.b[p.n++] = NL_META_PLUGIN_DATA;
    p.b[p.n++] = 5;
    p.b[p.n++] = 0x01;
    p.b[p.n++] = 0x02;
    tlv_item(&w, "truncated_value", p.b, p.n);
    p.n = 0;
    p.b[p.n++] = NL_META_DEVICE_ANNOUNCE;
    tlv_item(&w, "single_byte", p.b, p.n);
    p.n = 0;
    {
        const uint8_t ven[] = {0xAA, 0xBB, 0xCC};
        p_tlv(&p, NL_META_VENDOR_BASE, ven, sizeof(ven));
        p_tlv(&p, 0xFF, NULL, 0);
        p_tlv(&p, 0x7F, ven, 1);
        tlv_item(&w, "vendor_and_unknown", p.b, p.n);
    }
    p.n = 0;
    rng_fill(v, NL_META_MAX_VALUE);
    p_tlv(&p, NL_META_VENDOR_BASE + 1, v, NL_META_MAX_VALUE);
    tlv_item(&w, "max_record", p.b, p.n);
    p.n = 0;
    {
        const uint8_t cong[] = {0x06, 0x10, 0x00};
        p_tlv(&p, NL_META_CONGESTION, cong, sizeof(cong));
        p.b[p.n++] = 0;
        p.b[p.n++] = 0;
        p.b[p.n++] = 0;
        p.b[p.n++] = 0;
        tlv_item(&w, "zero_padding_reads_as_type0", p.b, p.n);
    }
    p.n = 0;
    p.b[p.n++] = NL_META_DEBUG_TEXT;
    p.b[p.n++] = 0xFF;
    p.b[p.n++] = 'x';
    tlv_item(&w, "len_ff_overrun", p.b, p.n);
    jw_close(&w, ']');

    jw_section(&w, "device");
    device_item(&w, 1, 0, 1, 0, "", 0);
    device_item(&w, 1, 0, 1, 0, "a", 1);
    device_item(&w, NL_LINK_PROTOCOL_VERSION, NL_VERSION_MAJOR, NL_VERSION_MINOR,
                NL_VERSION_PATCH, "NOVA-LINK host", 14);
    device_item(&w, 9, 255, 128, 7, "abcdefghijklmnopqrstuvwx", 24);
    device_item(&w, 1, 2, 3, 4, "XXXXXXXXXXXXXXXXXXXXXXXXX", 25); /* truncated to 24 */
    device_item(&w, 1, 2, 3, 4, "stage\0left", 10);                /* NUL ends the name */
    jw_close(&w, ']');

    jw_section(&w, "device_decode_errors");
    {
        nl_meta_device_t dev;
        memset(v, 'n', sizeof(v));
        const size_t lens[] = {0, 3, 29, NL_META_MAX_VALUE};
        for (size_t i = 0; i < NL_ARRAY_SIZE(lens); i++) {
            int rc = nl_meta_decode_device(v, lens[i], &dev);
            decode_error_item(&w, v, lens[i], rc);
        }
    }
    jw_close(&w, ']');

    jw_section(&w, "claims");
    {
        nl_meta_claim_t c[NL_META_MAX_VALUE / NL_META_CLAIM_WIRE_SIZE];
        claims_item(&w, c, 0);
        c[0] = (nl_meta_claim_t){3, NL_CLAIM_EXCLUSIVE, 0x0102};
        claims_item(&w, c, 1);
        c[1] = (nl_meta_claim_t){4, NL_CLAIM_SHARED, NL_PLUGIN_TYPE_ANY};
        c[2] = (nl_meta_claim_t){7, NL_CLAIM_READ_ONLY, 0};
        claims_item(&w, c, 3);
        for (size_t i = 0; i < NL_ARRAY_SIZE(c); i++) {
            c[i].zone = (uint8_t)(1u + i % 7u);
            c[i].mode = (uint8_t)(i % 4u);
            c[i].plugin_type = (uint16_t)nl_rand_next(&g_rng);
        }
        claims_item(&w, c, NL_ARRAY_SIZE(c));
    }
    jw_close(&w, ']');

    jw_section(&w, "claims_errors");
    {
        nl_meta_claim_t c[32];
        memset(c, 0, sizeof(c));
        uint8_t out[160];
        int rc = nl_meta_encode_claims(c, 25, out, sizeof(out));
        if (rc >= 0) {
            die("nl_meta_encode_claims error case", rc);
        }
        jw_item(&w);
        jw_str(&w, "op", "encode");
        jw_u(&w, "count", 25);
        jw_str(&w, "status", st_name(rc));
        jw_close(&w, '}');
        memset(v, 0x01, sizeof(v));
        const size_t lens[] = {1, 5, 7};
        for (size_t i = 0; i < NL_ARRAY_SIZE(lens); i++) {
            rc = nl_meta_decode_claims(v, lens[i], c, NL_ARRAY_SIZE(c));
            if (rc >= 0) {
                die("nl_meta_decode_claims error case", rc);
            }
            jw_item(&w);
            jw_str(&w, "op", "decode");
            jw_hex(&w, "value", v, lens[i]);
            jw_str(&w, "status", st_name(rc));
            jw_close(&w, '}');
        }
    }
    jw_close(&w, ']');

    jw_section(&w, "plugin_data");
    {
        const struct {
            uint16_t type;
            size_t len;
        } pd[] = {{0x0001, 0}, {0x1234, 5}, {0xFFFF, NL_META_MAX_VALUE - 2u}};
        for (size_t i = 0; i < NL_ARRAY_SIZE(pd); i++) {
            nl_put_u16le(v, pd[i].type);
            rng_fill(&v[2], pd[i].len);
            jw_item(&w);
            jw_u(&w, "plugin_type", pd[i].type);
            jw_hex(&w, "data", &v[2], pd[i].len);
            jw_hex(&w, "value", v, pd[i].len + 2u);
            jw_close(&w, '}');
        }
    }
    jw_close(&w, ']');

    jw_section(&w, "congestion");
    {
        const struct {
            uint8_t mask;
            uint16_t dropped;
        } cg[] = {{0x00, 0}, {0x06, 17}, {0xFE, 0xFFFF}};
        for (size_t i = 0; i < NL_ARRAY_SIZE(cg); i++) {
            v[0] = cg[i].mask;
            nl_put_u16le(&v[1], cg[i].dropped);
            jw_item(&w);
            jw_u(&w, "zone_mask", cg[i].mask);
            jw_u(&w, "dropped", cg[i].dropped);
            jw_hex(&w, "value", v, 3);
            jw_close(&w, '}');
        }
    }
    jw_close(&w, ']');

    jw_section(&w, "queue");
    {
        const qop_t announce[] = {
            {Q_PUSH, NL_META_DEVICE_ANNOUNCE, 0x30, 12},
            {Q_PUSH, NL_META_CLAIM_ANNOUNCE, 0x01, 8},
            {Q_PUSH, NL_META_DEBUG_TEXT, 0x41, 5},
            {Q_PACK, 0, 0, NL_MAX_PAYLOAD},
            {Q_PACK, 0, 0, NL_MAX_PAYLOAD},
        };
        queue_item(&w, "announce_fits_one_payload", announce, NL_ARRAY_SIZE(announce));

        const qop_t split[] = {
            {Q_PUSH, NL_META_DEBUG_TEXT, 0x61, 30},
            {Q_PUSH, NL_META_DEBUG_TEXT, 0x62, 30},
            {Q_PUSH, NL_META_DEBUG_TEXT, 0x63, 30},
            {Q_PUSH, NL_META_PLUGIN_DATA, 0x00, 40},
            {Q_PUSH, NL_META_CONGESTION, 0x06, 3},
            {Q_PUSH, NL_META_VENDOR_BASE, 0x90, 60},
            {Q_PACK, 0, 0, NL_MAX_PAYLOAD},
            {Q_PACK, 0, 0, NL_MAX_PAYLOAD},
            {Q_PACK, 0, 0, NL_MAX_PAYLOAD},
            {Q_PACK, 0, 0, NL_MAX_PAYLOAD},
        };
        queue_item(&w, "fifo_split_across_payloads", split, NL_ARRAY_SIZE(split));

        const qop_t maxrec[] = {
            {Q_PUSH, NL_META_VENDOR_BASE, 0x00, NL_META_MAX_VALUE},
            {Q_PUSH, NL_META_VENDOR_BASE, 0x00, NL_META_MAX_VALUE + 1u},
            {Q_PUSH, NL_META_DEBUG_TEXT, 0x30, 1},
            {Q_PACK, 0, 0, NL_MAX_PAYLOAD - 1u},
            {Q_PACK, 0, 0, NL_MAX_PAYLOAD},
            {Q_PACK, 0, 0, NL_MAX_PAYLOAD},
        };
        queue_item(&w, "max_record_and_small_cap", maxrec, NL_ARRAY_SIZE(maxrec));

        const qop_t replace[] = {
            {Q_PUSH, NL_META_DEVICE_ANNOUNCE, 0x10, 6},
            {Q_PUSH, NL_META_CLAIM_ANNOUNCE, 0x20, 4},
            {Q_PUSH, NL_META_DEBUG_TEXT, 0x30, 3},
            {Q_PUSH, NL_META_DEVICE_ANNOUNCE, 0x40, 6},
            {Q_REMOVE, NL_META_DEVICE_ANNOUNCE, 0, 0},
            {Q_PUSH, NL_META_DEVICE_ANNOUNCE, 0x50, 6},
            {Q_REMOVE, 0x99, 0, 0},
            {Q_PACK, 0, 0, NL_MAX_PAYLOAD},
        };
        queue_item(&w, "remove_type_replaces_snapshot", replace, NL_ARRAY_SIZE(replace));

        qop_t full[16];
        for (size_t i = 0; i < 14; i++) {
            full[i] = (qop_t){Q_PUSH, NL_META_DEBUG_TEXT, (uint8_t)i, 40};
        }
        full[14] = (qop_t){Q_PUSH, NL_META_DEBUG_TEXT, 0x77, 0};
        full[15] = (qop_t){Q_PACK, 0, 0, NL_MAX_PAYLOAD};
        queue_item(&w, "queue_full_drops", full, NL_ARRAY_SIZE(full));
    }
    jw_close(&w, ']');
    jw_end(&w);
}

/* ---- segments.json ----------------------------------------------------- */

typedef struct {
    uint8_t seq;
    uint8_t seg;    /* segment index to build from the message */
    int raw;        /* >= 0: use raw payload table entry instead */
} feed_t;

static void reasm_item(jw_t *w, const char *name, size_t cap, const uint8_t *msg,
                       size_t msg_len, const feed_t *feeds, size_t nfeeds)
{
    static uint8_t rbuf[NL_SEG_MAX_MESSAGE];
    static uint8_t raw[5][NL_MAX_PAYLOAD + 1];
    static const size_t raw_len[5] = {0, 1, 51, 1, NL_MAX_PAYLOAD + 1};
    raw[1][0] = 0x10; /* index 1 > last 0 */
    raw[2][0] = 0x01; /* index 0 < last 1 but short */
    memset(&raw[2][1], 0x55, 50);
    raw[3][0] = 0x11; /* last segment of a 2-segment message with no data */
    raw[4][0] = 0x00;
    memset(&raw[4][1], 0x66, NL_MAX_PAYLOAD);

    nl_reasm_t r;
    nl_reasm_init(&r, rbuf, cap);
    jw_item(w);
    jw_str(w, "name", name);
    jw_u(w, "cap", (unsigned long)cap);
    jw_key(w, "feeds");
    jw_open(w, '[');
    for (size_t i = 0; i < nfeeds; i++) {
        uint8_t pl[NL_MAX_PAYLOAD + 1];
        size_t plen;
        if (feeds[i].raw >= 0) {
            plen = raw_len[feeds[i].raw];
            memcpy(pl, raw[feeds[i].raw], plen);
        } else {
            int n = nl_seg_build(msg, msg_len, feeds[i].seg, pl, sizeof(pl));
            if (n < 0) {
                die("nl_seg_build", n);
            }
            plen = (size_t)n;
        }
        const uint8_t *out = NULL;
        size_t out_len = 0;
        int rc = nl_reasm_feed(&r, feeds[i].seq, pl, plen, &out, &out_len);
        jw_obj_elem(w);
        jw_u(w, "seq", feeds[i].seq);
        jw_hex(w, "payload", pl, plen);
        jw_str(w, "result", rc == 1 ? "complete" : rc == 0 ? "more" : st_name(rc));
        if (rc == 1) {
            jw_hex(w, "message", out, out_len);
        }
        jw_close(w, '}');
    }
    jw_close(w, ']');
    jw_u(w, "completed", r.completed);
    jw_u(w, "aborted", r.aborted);
    jw_close(w, '}');
}

static void gen_segments(FILE *f)
{
    jw_t w;
    static uint8_t msg[NL_SEG_MAX_MESSAGE + 16];
    uint8_t pl[NL_MAX_PAYLOAD];
    rng_reset(0x5E6Au);
    jw_begin(&w, f, "Segmented messages: each segment payload starts with "
                    "index<<4 | (count-1), then up to 99 data bytes; all but the last "
                    "segment carry exactly 99. 'reasm' replays nl_reasm_feed");

    jw_section(&w, "count");
    {
        const size_t lens[] = {0, 1, 98, 99, 100, 197, 198, 199, 512, 1485, 1486,
                               NL_SEG_MAX_MESSAGE, NL_SEG_MAX_MESSAGE + 1, 2000};
        for (size_t i = 0; i < NL_ARRAY_SIZE(lens); i++) {
            int c = nl_seg_count(lens[i]);
            jw_item(&w);
            jw_u(&w, "msg_len", (unsigned long)lens[i]);
            if (c >= 0) {
                jw_u(&w, "count", (unsigned long)c);
            } else {
                jw_str(&w, "status", st_name(c));
            }
            jw_close(&w, '}');
        }
    }
    jw_close(&w, ']');

    jw_section(&w, "build");
    {
        const size_t lens[] = {0, 1, 98, 99, 100, 198, 512, NL_SEG_MAX_MESSAGE};
        for (size_t i = 0; i < NL_ARRAY_SIZE(lens); i++) {
            rng_fill(msg, lens[i]);
            int c = nl_seg_count(lens[i]);
            jw_item(&w);
            jw_hex(&w, "message", msg, lens[i]);
            jw_key(&w, "segments");
            jw_open(&w, '[');
            for (int s = 0; s < c; s++) {
                int n = nl_seg_build(msg, lens[i], (uint8_t)s, pl, sizeof(pl));
                if (n < 0) {
                    die("nl_seg_build", n);
                }
                jw_sep(&w);
                jw_val_hex(&w, pl, (size_t)n);
            }
            jw_close(&w, ']');
            jw_close(&w, '}');
        }
    }
    jw_close(&w, ']');

    jw_section(&w, "build_errors");
    {
        const struct {
            size_t len;
            uint8_t index;
        } bad[] = {{10, 1}, {0, 1}, {NL_SEG_MAX_MESSAGE, 16}, {NL_SEG_MAX_MESSAGE + 1, 0}};
        for (size_t i = 0; i < NL_ARRAY_SIZE(bad); i++) {
            int rc = nl_seg_build(msg, bad[i].len, bad[i].index, pl, sizeof(pl));
            if (rc >= 0) {
                die("nl_seg_build error case", rc);
            }
            jw_item(&w);
            jw_u(&w, "msg_len", (unsigned long)bad[i].len);
            jw_u(&w, "index", bad[i].index);
            jw_str(&w, "status", st_name(rc));
            jw_close(&w, '}');
        }
    }
    jw_close(&w, ']');

    jw_section(&w, "reasm");
    {
        const size_t full = NL_SEG_MAX_MESSAGE;

        rng_fill(msg, 512);
        const feed_t in_order[] = {{10, 0, -1}, {11, 1, -1}, {12, 2, -1},
                                   {13, 3, -1}, {14, 4, -1}, {15, 5, -1}};
        reasm_item(&w, "dmx_universe_in_order", full, msg, 512, in_order,
                   NL_ARRAY_SIZE(in_order));

        rng_fill(msg, 5);
        const feed_t single[] = {{200, 0, -1}};
        reasm_item(&w, "single_segment", full, msg, 5, single, NL_ARRAY_SIZE(single));

        rng_fill(msg, 250);
        const feed_t lost[] = {{0, 0, -1}, {1, 1, -1}, {5, 0, -1}, {6, 1, -1}, {7, 2, -1}};
        reasm_item(&w, "lost_segment_restarts", full, msg, 250, lost, NL_ARRAY_SIZE(lost));

        const feed_t ooo[] = {{42, 2, -1}, {40, 0, -1}, {41, 1, -1}};
        reasm_item(&w, "out_of_order", full, msg, 250, ooo, NL_ARRAY_SIZE(ooo));

        const feed_t dup[] = {{9, 0, -1}, {9, 0, -1}, {10, 1, -1}, {11, 2, -1}};
        reasm_item(&w, "duplicate_segment", full, msg, 250, dup, NL_ARRAY_SIZE(dup));

        rng_fill(msg, 350);
        const feed_t wrap[] = {{0xFE, 0, -1}, {0xFF, 1, -1}, {0x00, 2, -1}, {0x01, 3, -1}};
        reasm_item(&w, "seq_wraparound", full, msg, 350, wrap, NL_ARRAY_SIZE(wrap));

        const feed_t bad[] = {{1, 0, 0}, {2, 0, 1}, {3, 0, 2}, {4, 0, 3}, {5, 0, 4}};
        reasm_item(&w, "malformed", full, msg, 350, bad, NL_ARRAY_SIZE(bad));

        rng_fill(msg, 198);
        const feed_t small[] = {{20, 0, -1}, {21, 1, -1}, {20, 0, -1}};
        reasm_item(&w, "buffer_too_small", 150, msg, 198, small, NL_ARRAY_SIZE(small));

        rng_fill(msg, 250);
        reasm_item(&w, "zero_length_message", full, msg, 0, (const feed_t[]){{77, 0, -1}}, 1);
        /* Same base seq but a different segment count restarts the message. */
        static uint8_t msg2[NL_SEG_MAX_MESSAGE];
        memcpy(msg2, msg, 250);
        nl_reasm_t r;
        static uint8_t rbuf[NL_SEG_MAX_MESSAGE];
        nl_reasm_init(&r, rbuf, full);
        jw_item(&w);
        jw_str(&w, "name", "count_change_restarts");
        jw_u(&w, "cap", (unsigned long)full);
        jw_key(&w, "feeds");
        jw_open(&w, '[');
        const struct {
            size_t len;
            uint8_t seq, seg;
        } cc[] = {{250, 30, 0}, {150, 30, 0}, {150, 31, 1}};
        for (size_t i = 0; i < NL_ARRAY_SIZE(cc); i++) {
            int n = nl_seg_build(msg2, cc[i].len, cc[i].seg, pl, sizeof(pl));
            if (n < 0) {
                die("nl_seg_build", n);
            }
            const uint8_t *out = NULL;
            size_t out_len = 0;
            int rc = nl_reasm_feed(&r, cc[i].seq, pl, (size_t)n, &out, &out_len);
            jw_obj_elem(&w);
            jw_u(&w, "seq", cc[i].seq);
            jw_hex(&w, "payload", pl, (size_t)n);
            jw_str(&w, "result", rc == 1 ? "complete" : rc == 0 ? "more" : st_name(rc));
            if (rc == 1) {
                jw_hex(&w, "message", out, out_len);
            }
            jw_close(&w, '}');
        }
        jw_close(&w, ']');
        jw_u(&w, "completed", r.completed);
        jw_u(&w, "aborted", r.aborted);
        jw_close(&w, '}');
    }
    jw_close(&w, ']');
    jw_end(&w);
}

/* ---- Driver ------------------------------------------------------------ */

typedef struct {
    const char *name;
    void (*gen)(FILE *f);
} vec_file_t;

static const vec_file_t k_files[] = {
    {"crc8.json", gen_crc8},
    {"fragments.json", gen_fragments},
    {"link_frames.json", gen_link},
    {"params.json", gen_params},
    {"meta.json", gen_meta},
    {"segments.json", gen_segments},
};

static void join(char *out, size_t cap, const char *dir, const char *name)
{
    int n = snprintf(out, cap, "%s/%s", dir, name);
    if (n < 0 || (size_t)n >= cap) {
        fprintf(stderr, "gen_vectors: path too long\n");
        exit(2);
    }
}

static int write_all(const char *dir)
{
    for (size_t i = 0; i < NL_ARRAY_SIZE(k_files); i++) {
        char path[1024];
        join(path, sizeof(path), dir, k_files[i].name);
        FILE *f = fopen(path, "wb");
        if (f == NULL) {
            fprintf(stderr, "gen_vectors: cannot write %s\n", path);
            return 2;
        }
        k_files[i].gen(f);
        if (fclose(f) != 0) {
            fprintf(stderr, "gen_vectors: error writing %s\n", path);
            return 2;
        }
        printf("wrote %s\n", path);
    }
    return 0;
}

/** Compare a regenerated file against the committed copy. @return 0 if equal. */
static int check_one(const char *dir, const vec_file_t *vf)
{
    char path[1024];
    join(path, sizeof(path), dir, vf->name);
    FILE *want = fopen(path, "rb");
    if (want == NULL) {
        fprintf(stderr, "DRIFT %s: committed file missing\n", path);
        return 1;
    }
    FILE *got = tmpfile();
    if (got == NULL) {
        fclose(want);
        fprintf(stderr, "gen_vectors: tmpfile() failed\n");
        return 2;
    }
    vf->gen(got);
    rewind(got);
    unsigned long line = 1;
    int rc = 0;
    for (;;) {
        int a = fgetc(got);
        int b = fgetc(want);
        if (b == '\r') { /* tolerate CRLF checkouts */
            b = fgetc(want);
        }
        if (a != b) {
            fprintf(stderr,
                    "DRIFT %s: line %lu differs from the C implementation; "
                    "regenerate with: gen_vectors --out tests/vectors\n",
                    path, line);
            rc = 1;
            break;
        }
        if (a == EOF) {
            break;
        }
        if (a == '\n') {
            line++;
        }
    }
    fclose(got);
    fclose(want);
    if (rc == 0) {
        printf("ok %s\n", path);
    }
    return rc;
}

static void usage(void)
{
    fprintf(stderr, "usage: gen_vectors --out DIR | --check DIR | --list | NAME\n");
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--list") == 0) {
        for (size_t i = 0; i < NL_ARRAY_SIZE(k_files); i++) {
            printf("%s\n", k_files[i].name);
        }
        return 0;
    }
    if (argc == 3 && strcmp(argv[1], "--out") == 0) {
        return write_all(argv[2]);
    }
    if (argc == 3 && strcmp(argv[1], "--check") == 0) {
        int rc = 0;
        for (size_t i = 0; i < NL_ARRAY_SIZE(k_files); i++) {
            int r = check_one(argv[2], &k_files[i]);
            if (r > rc) {
                rc = r;
            }
        }
        return rc;
    }
    if (argc == 2 && argv[1][0] != '-') {
        for (size_t i = 0; i < NL_ARRAY_SIZE(k_files); i++) {
            if (strcmp(argv[1], k_files[i].name) == 0) {
                k_files[i].gen(stdout);
                return 0;
            }
        }
        fprintf(stderr, "gen_vectors: unknown vector file '%s'\n", argv[1]);
        return 2;
    }
    usage();
    return 2;
}
