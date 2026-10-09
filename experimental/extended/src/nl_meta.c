/**
 * @file nl_meta.c
 * @brief Zone 0 TLV records and metadata queue.
 */
#include "nova_link/nl_meta.h"

#include <string.h>

/* strnlen() is POSIX, not C99; keep the core strictly portable. */
static size_t bounded_strlen(const char *s, size_t max)
{
    size_t n = 0;
    while (n < max && s[n] != '\0') {
        n++;
    }
    return n;
}

void nl_meta_queue_init(nl_meta_queue_t *q)
{
    memset(q, 0, sizeof(*q));
}

int nl_meta_queue_push(nl_meta_queue_t *q, uint8_t type, const uint8_t *value,
                       size_t len)
{
    if (q == NULL || (len > 0 && value == NULL)) {
        return NL_ERR_ARG;
    }
    if (len > NL_META_MAX_VALUE) {
        return NL_ERR_SIZE;
    }
    if ((size_t)q->used + NL_META_TLV_OVERHEAD + len > sizeof(q->buf)) {
        q->dropped++;
        return NL_ERR_FULL;
    }
    uint8_t *p = &q->buf[q->used];
    p[0] = type;
    p[1] = (uint8_t)len;
    if (len > 0) {
        memcpy(&p[2], value, len);
    }
    q->used = (uint16_t)(q->used + NL_META_TLV_OVERHEAD + len);
    return NL_OK;
}

void nl_meta_queue_remove_type(nl_meta_queue_t *q, uint8_t type)
{
    size_t rd = 0, wr = 0;
    while (rd < q->used) {
        size_t rec = NL_META_TLV_OVERHEAD + q->buf[rd + 1];
        if (q->buf[rd] != type) {
            memmove(&q->buf[wr], &q->buf[rd], rec);
            wr += rec;
        }
        rd += rec;
    }
    q->used = (uint16_t)wr;
}

size_t nl_meta_queue_pack(nl_meta_queue_t *q, uint8_t *out, size_t cap)
{
    size_t taken = 0;
    while (taken < q->used) {
        size_t rec = NL_META_TLV_OVERHEAD + q->buf[taken + 1];
        if (taken + rec > cap) {
            break;
        }
        taken += rec;
    }
    if (taken == 0) {
        return 0;
    }
    memcpy(out, q->buf, taken);
    memmove(q->buf, &q->buf[taken], q->used - taken);
    q->used = (uint16_t)(q->used - taken);
    return taken;
}

void nl_meta_iter_init(nl_meta_iter_t *it, const uint8_t *buf, size_t len)
{
    it->buf = buf;
    it->len = buf ? len : 0;
    it->pos = 0;
}

int nl_meta_iter_next(nl_meta_iter_t *it, uint8_t *type, const uint8_t **value,
                      uint8_t *len)
{
    if (it->pos >= it->len) {
        return 0;
    }
    if (it->pos + NL_META_TLV_OVERHEAD > it->len ||
        it->pos + NL_META_TLV_OVERHEAD + it->buf[it->pos + 1] > it->len) {
        it->pos = it->len;
        return NL_ERR_PROTO;
    }
    *type = it->buf[it->pos];
    *len = it->buf[it->pos + 1];
    *value = &it->buf[it->pos + NL_META_TLV_OVERHEAD];
    it->pos += NL_META_TLV_OVERHEAD + *len;
    return 1;
}

int nl_meta_encode_claims(const nl_meta_claim_t *claims, size_t count,
                          uint8_t *out, size_t cap)
{
    if ((count > 0 && claims == NULL) || out == NULL) {
        return NL_ERR_ARG;
    }
    size_t need = count * NL_META_CLAIM_WIRE_SIZE;
    if (need > cap || need > NL_META_MAX_VALUE) {
        return NL_ERR_SIZE;
    }
    for (size_t i = 0; i < count; i++) {
        uint8_t *p = &out[i * NL_META_CLAIM_WIRE_SIZE];
        p[0] = claims[i].zone;
        p[1] = claims[i].mode;
        nl_put_u16le(&p[2], claims[i].plugin_type);
    }
    return (int)need;
}

int nl_meta_decode_claims(const uint8_t *value, size_t len,
                          nl_meta_claim_t *claims, size_t max)
{
    if ((len > 0 && value == NULL) || claims == NULL) {
        return NL_ERR_ARG;
    }
    if (len % NL_META_CLAIM_WIRE_SIZE != 0) {
        return NL_ERR_PROTO;
    }
    size_t count = len / NL_META_CLAIM_WIRE_SIZE;
    if (count > max) {
        return NL_ERR_SIZE;
    }
    for (size_t i = 0; i < count; i++) {
        const uint8_t *p = &value[i * NL_META_CLAIM_WIRE_SIZE];
        claims[i].zone = p[0];
        claims[i].mode = p[1];
        claims[i].plugin_type = nl_get_u16le(&p[2]);
    }
    return (int)count;
}

int nl_meta_encode_device(const nl_meta_device_t *dev, uint8_t *out, size_t cap)
{
    if (dev == NULL || out == NULL) {
        return NL_ERR_ARG;
    }
    size_t name_len = bounded_strlen(dev->name, sizeof(dev->name) - 1);
    if (cap < 4 + name_len) {
        return NL_ERR_SIZE;
    }
    out[0] = dev->proto_version;
    out[1] = dev->fw_major;
    out[2] = dev->fw_minor;
    out[3] = dev->fw_patch;
    memcpy(&out[4], dev->name, name_len);
    return (int)(4 + name_len);
}

int nl_meta_decode_device(const uint8_t *value, size_t len, nl_meta_device_t *dev)
{
    if (value == NULL || dev == NULL) {
        return NL_ERR_ARG;
    }
    if (len < 4 || len - 4 > sizeof(dev->name) - 1) {
        return NL_ERR_PROTO;
    }
    dev->proto_version = value[0];
    dev->fw_major = value[1];
    dev->fw_minor = value[2];
    dev->fw_patch = value[3];
    memcpy(dev->name, &value[4], len - 4);
    dev->name[len - 4] = '\0';
    return NL_OK;
}
