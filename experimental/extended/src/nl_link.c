/**
 * @file nl_link.c
 * @brief Host <-> radio link framing and payload codecs.
 */
#include "nova_link/nl_link.h"

#include <string.h>

enum { P_SYNC = 0, P_CMD, P_LEN, P_DATA, P_CRC };

/* CRC-8 of (i << 4) shifted four times through poly 0x07: lets nl_crc8 do a
 * nibble per step instead of a bit, with a 16-byte table. */
static const uint8_t crc8_nibble[16] = {
    0x00, 0x07, 0x0E, 0x09, 0x1C, 0x1B, 0x12, 0x15,
    0x38, 0x3F, 0x36, 0x31, 0x24, 0x23, 0x2A, 0x2D,
};

uint8_t nl_crc8(uint8_t crc, const uint8_t *data, size_t len)
{
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        crc = (uint8_t)((unsigned)crc << 4) ^ crc8_nibble[crc >> 4];
        crc = (uint8_t)((unsigned)crc << 4) ^ crc8_nibble[crc >> 4];
    }
    return crc;
}

int nl_link_encode(uint8_t cmd, const uint8_t *data, size_t len, uint8_t *out,
                   size_t cap)
{
    if (out == NULL || (len > 0 && data == NULL)) {
        return NL_ERR_ARG;
    }
    if (len > NL_LINK_MAX_DATA || cap < len + NL_LINK_OVERHEAD) {
        return NL_ERR_SIZE;
    }
    out[0] = NL_LINK_SYNC;
    out[1] = cmd;
    out[2] = (uint8_t)len;
    if (len > 0) {
        memmove(&out[3], data, len);
    }
    out[3 + len] = nl_crc8(0, &out[1], len + 2);
    return (int)(len + NL_LINK_OVERHEAD);
}

int nl_link_find(const uint8_t *buf, size_t len, nl_link_view_t *frame,
                 size_t *consumed)
{
    if (buf == NULL || frame == NULL) {
        return NL_ERR_ARG;
    }
    int result = NL_ERR_EMPTY;
    for (size_t i = 0; i + NL_LINK_OVERHEAD <= len; i++) {
        if (buf[i] != NL_LINK_SYNC || NL_LINK_CMD_INVALID(buf[i + 1])) {
            continue;
        }
        size_t dlen = buf[i + 2];
        if (dlen > NL_LINK_MAX_DATA || i + dlen + NL_LINK_OVERHEAD > len) {
            continue;
        }
        if (nl_crc8(0, &buf[i + 1], dlen + 2) != buf[i + 3 + dlen]) {
            result = NL_ERR_CRC;
            continue;
        }
        frame->cmd = buf[i + 1];
        frame->len = (uint8_t)dlen;
        frame->data = &buf[i + 3];
        if (consumed != NULL) {
            *consumed = i + dlen + NL_LINK_OVERHEAD;
        }
        return NL_OK;
    }
    if (consumed != NULL) {
        *consumed = len;
    }
    return result;
}

int nl_link_decode(const uint8_t *buf, size_t len, nl_link_frame_t *frame,
                   size_t *consumed)
{
    if (frame == NULL) {
        return NL_ERR_ARG;
    }
    nl_link_view_t v;
    int rc = nl_link_find(buf, len, &v, consumed);
    if (rc == NL_OK) {
        frame->cmd = v.cmd;
        frame->len = v.len;
        memcpy(frame->data, v.data, v.len);
    }
    return rc;
}

void nl_link_parser_init(nl_link_parser_t *p)
{
    memset(p, 0, sizeof(*p));
}

int nl_link_parser_feed(nl_link_parser_t *p, uint8_t byte)
{
    switch (p->state) {
    case P_SYNC:
        if (byte == NL_LINK_SYNC) {
            p->state = P_CMD;
        }
        return 0;
    case P_CMD:
        if (NL_LINK_CMD_INVALID(byte)) {
            p->cmd_errors++;
            p->state = P_SYNC;
            return 0;
        }
        if (byte == NL_LINK_SYNC) {
            /* "AA AA ..." - treat the second byte as the real SYNC. */
            return 0;
        }
        p->frame.cmd = byte;
        p->state = P_LEN;
        return 0;
    case P_LEN:
        if (byte > NL_LINK_MAX_DATA) {
            p->len_errors++;
            /* The rejected LEN byte may itself be the start of a frame. */
            p->state = (byte == NL_LINK_SYNC) ? P_CMD : P_SYNC;
            return 0;
        }
        p->frame.len = byte;
        p->pos = 0;
        p->state = byte ? P_DATA : P_CRC;
        return 0;
    case P_DATA:
        p->frame.data[p->pos++] = byte;
        if (p->pos == p->frame.len) {
            p->state = P_CRC;
        }
        return 0;
    case P_CRC: {
        uint8_t hdr[2] = {p->frame.cmd, p->frame.len};
        uint8_t crc = nl_crc8(nl_crc8(0, hdr, 2), p->frame.data, p->frame.len);
        p->state = P_SYNC;
        if (crc != byte) {
            p->crc_errors++;
            return 0;
        }
        return 1;
    }
    default:
        p->state = P_SYNC;
        return 0;
    }
}

/* ------------------------------------------------------------------------ */

int nl_zone_plan_encode(const nl_zone_plan_t *plan, uint8_t *out, size_t cap)
{
    if (plan == NULL || out == NULL) {
        return NL_ERR_ARG;
    }
    if (cap < NL_ZONE_PLAN_WIRE_SIZE) {
        return NL_ERR_SIZE;
    }
    for (int z = 0; z < NL_NUM_ZONES; z++) {
        uint8_t *p = &out[z * 9];
        p[0] = plan->zone[z].priority;
        nl_put_u32le(&p[1], plan->zone[z].subghz_hz);
        nl_put_u32le(&p[5], plan->zone[z].ghz24_hz);
    }
    return NL_ZONE_PLAN_WIRE_SIZE;
}

int nl_zone_plan_decode(const uint8_t *buf, size_t len, nl_zone_plan_t *plan)
{
    if (buf == NULL || plan == NULL) {
        return NL_ERR_ARG;
    }
    if (len != NL_ZONE_PLAN_WIRE_SIZE) {
        return NL_ERR_SIZE;
    }
    for (int z = 0; z < NL_NUM_ZONES; z++) {
        const uint8_t *p = &buf[z * 9];
        plan->zone[z].priority = p[0];
        plan->zone[z].subghz_hz = nl_get_u32le(&p[1]);
        plan->zone[z].ghz24_hz = nl_get_u32le(&p[5]);
    }
    return NL_OK;
}

void nl_radio_params_default(nl_radio_params_t *p)
{
    memset(p, 0, sizeof(*p));
    p->origin_id = 0;
    p->band = NL_BAND_SUBGHZ;
    p->tx_policy = NL_TX_IMMEDIATE;
    p->tx_repeats = 3;
    p->dwell_us = 2000;
    p->burst_extend_us = 4000;
    p->mgmt_hold_us = 250000;
    p->repeat_interval_us = 1500;
    p->tracker_stale_us = 500000;
    p->repeat_jitter_us = 1000;
    p->discovery_interval_us = 20000;
    p->mgmt_repeats = 6;
    p->cca_backoff_us = 2000;
}

int nl_radio_params_encode(const nl_radio_params_t *p, uint8_t *out, size_t cap)
{
    if (p == NULL || out == NULL) {
        return NL_ERR_ARG;
    }
    if (cap < NL_RADIO_PARAMS_WIRE_SIZE) {
        return NL_ERR_SIZE;
    }
    out[0] = p->origin_id;
    out[1] = p->band;
    out[2] = p->tx_policy;
    out[3] = p->tx_repeats;
    nl_put_u32le(&out[4], p->dwell_us);
    nl_put_u32le(&out[8], p->burst_extend_us);
    nl_put_u32le(&out[12], p->mgmt_hold_us);
    nl_put_u32le(&out[16], p->repeat_interval_us);
    nl_put_u32le(&out[20], p->tracker_stale_us);
    nl_put_u32le(&out[24], p->repeat_jitter_us);
    nl_put_u32le(&out[28], p->discovery_interval_us);
    out[32] = p->mgmt_repeats;
    nl_put_u32le(&out[33], p->cca_backoff_us);
    return NL_RADIO_PARAMS_WIRE_SIZE;
}

int nl_radio_params_decode(const uint8_t *buf, size_t len, nl_radio_params_t *p)
{
    if (buf == NULL || p == NULL) {
        return NL_ERR_ARG;
    }
    if (len != NL_RADIO_PARAMS_WIRE_SIZE) {
        return NL_ERR_SIZE;
    }
    if (buf[0] >= NL_NUM_ORIGINS || buf[1] > NL_BAND_DUAL || buf[2] > NL_TX_IN_SLOT ||
        buf[3] == 0) {
        return NL_ERR_ARG;
    }
    p->origin_id = buf[0];
    p->band = buf[1];
    p->tx_policy = buf[2];
    p->tx_repeats = buf[3];
    p->dwell_us = nl_get_u32le(&buf[4]);
    p->burst_extend_us = nl_get_u32le(&buf[8]);
    p->mgmt_hold_us = nl_get_u32le(&buf[12]);
    p->repeat_interval_us = nl_get_u32le(&buf[16]);
    p->tracker_stale_us = nl_get_u32le(&buf[20]);
    p->repeat_jitter_us = nl_get_u32le(&buf[24]);
    p->discovery_interval_us = nl_get_u32le(&buf[28]);
    p->mgmt_repeats = buf[32];
    p->cca_backoff_us = nl_get_u32le(&buf[33]);
    return NL_OK;
}

int nl_radio_status_encode(const nl_radio_status_t *s, uint8_t *out, size_t cap)
{
    if (s == NULL || out == NULL) {
        return NL_ERR_ARG;
    }
    if (cap < NL_RADIO_STATUS_WIRE_SIZE) {
        return NL_ERR_SIZE;
    }
    out[0] = s->proto_version;
    out[1] = s->flags;
    out[2] = s->rx_queue_len;
    out[3] = s->tx_queue_len;
    nl_put_u32le(&out[4], s->rx_ok);
    nl_put_u32le(&out[8], s->rx_dup);
    nl_put_u32le(&out[12], s->rx_dropped);
    nl_put_u32le(&out[16], s->rx_ignored);
    nl_put_u32le(&out[20], s->tx_sent);
    nl_put_u32le(&out[24], s->tx_dropped);
    return NL_RADIO_STATUS_WIRE_SIZE;
}

int nl_radio_status_decode(const uint8_t *buf, size_t len, nl_radio_status_t *s)
{
    if (buf == NULL || s == NULL) {
        return NL_ERR_ARG;
    }
    if (len != NL_RADIO_STATUS_WIRE_SIZE) {
        return NL_ERR_SIZE;
    }
    s->proto_version = buf[0];
    s->flags = buf[1];
    s->rx_queue_len = buf[2];
    s->tx_queue_len = buf[3];
    s->rx_ok = nl_get_u32le(&buf[4]);
    s->rx_dup = nl_get_u32le(&buf[8]);
    s->rx_dropped = nl_get_u32le(&buf[12]);
    s->rx_ignored = nl_get_u32le(&buf[16]);
    s->tx_sent = nl_get_u32le(&buf[20]);
    s->tx_dropped = nl_get_u32le(&buf[24]);
    return NL_OK;
}

int nl_link_pong_encode(const nl_link_pong_t *p, uint8_t *out, size_t cap)
{
    if (p == NULL || out == NULL) {
        return NL_ERR_ARG;
    }
    if (cap < NL_PONG_WIRE_SIZE) {
        return NL_ERR_SIZE;
    }
    out[0] = p->proto_version;
    out[1] = p->fw_major;
    out[2] = p->fw_minor;
    out[3] = p->fw_patch;
    return NL_PONG_WIRE_SIZE;
}

int nl_link_pong_decode(const uint8_t *buf, size_t len, nl_link_pong_t *p)
{
    if (buf == NULL || p == NULL) {
        return NL_ERR_ARG;
    }
    if (len != NL_PONG_WIRE_SIZE) {
        return NL_ERR_SIZE;
    }
    p->proto_version = buf[0];
    p->fw_major = buf[1];
    p->fw_minor = buf[2];
    p->fw_patch = buf[3];
    return NL_OK;
}
