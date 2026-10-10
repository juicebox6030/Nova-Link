/**
 * @file nl_spi_link.c
 * @brief Host-side SPI master driver for the link protocol.
 */
#include "nova_link/nl_spi_link.h"
#include "nova_link/nl_log.h"

#include <string.h>

void nl_spi_link_init(nl_spi_link_t *l, const nl_spi_hal_t *hal)
{
    memset(l, 0, sizeof(*l));
    l->hal = *hal;
    l->turnaround_us = NL_SPI_DEFAULT_TURNAROUND_US;
    l->retries = 2;
    l->read_retries = NL_SPI_DEFAULT_READ_RETRIES;
}

static int xfer(nl_spi_link_t *l, size_t len)
{
    l->stats.transactions++;
    if (l->hal.transfer(l->hal.ctx, l->tx, l->rx, len) < 0) {
        l->stats.io_errors++;
        return NL_ERR_IO;
    }
    return NL_OK;
}

static int send_request(nl_spi_link_t *l, uint8_t cmd, const uint8_t *data, size_t len)
{
    int n = nl_link_encode(cmd, data, len, l->tx, sizeof(l->tx));
    if (n < 0) {
        return n;
    }
    return xfer(l, (size_t)n);
}

/**
 * Clock out @p data_cap + overhead filler bytes and decode the response.
 * @p frame points into l->rx, valid until the next transfer.
 *
 * A read that returns only filler (the radio has not answered yet: it
 * defers request handling to its main loop, see nl_radio_poll()) or a
 * response to some other command (a stale reply to an abandoned request,
 * which this read has now drained) is read again, without re-sending the
 * request, up to read_retries times one turnaround apart. Re-sending would
 * be wrong for PULL: the radio dequeues when it answers. A checksum
 * failure is not re-read: the response was clocked out and is gone.
 */
static int read_response(nl_spi_link_t *l, uint8_t expect, size_t data_cap,
                         nl_link_view_t *frame)
{
    size_t len = data_cap + NL_LINK_OVERHEAD;
    for (unsigned i = 0;; i++) {
        if (l->hal.delay_us != NULL && l->turnaround_us != 0) {
            l->hal.delay_us(l->hal.ctx, l->turnaround_us);
        }
        memset(l->tx, 0, len);
        int rc = xfer(l, len);
        if (rc < 0) {
            return rc;
        }
        rc = nl_link_find(l->rx, len, frame, NULL);
        if (rc == NL_ERR_CRC) {
            l->stats.crc_errors++;
            return rc;
        }
        if (rc == NL_OK && frame->cmd == expect) {
            return NL_OK;
        }
        if (i >= l->read_retries) {
            l->stats.proto_errors++;
            return NL_ERR_PROTO;
        }
        l->stats.read_retries++;
    }
}

static int request(nl_spi_link_t *l, uint8_t cmd, uint8_t expect, size_t data_cap,
                   nl_link_view_t *frame, unsigned attempts)
{
    int rc = NL_ERR_PROTO;
    for (unsigned i = 0; i < attempts; i++) {
        if (i > 0) {
            l->stats.retries++;
        }
        rc = send_request(l, cmd, NULL, 0);
        if (rc == NL_OK) {
            rc = read_response(l, expect, data_cap, frame);
        }
        if (rc == NL_OK) {
            break;
        }
    }
    return rc;
}

int nl_spi_link_ping(nl_spi_link_t *l, nl_link_pong_t *out)
{
    nl_link_view_t f;
    int rc = request(l, NL_CMD_PING, NL_RSP_PONG, NL_PONG_WIRE_SIZE, &f,
                     l->retries + 1u);
    if (rc < 0) {
        return rc;
    }
    return nl_link_pong_decode(f.data, f.len, out);
}

int nl_spi_link_push(nl_spi_link_t *l, const uint8_t *frag, size_t len)
{
    if (frag == NULL || len < NL_FRAGMENT_HEADER_SIZE || len > NL_MAX_FRAGMENT) {
        return NL_ERR_ARG;
    }
    return send_request(l, NL_CMD_PUSH, frag, len);
}

int nl_spi_link_pull(nl_spi_link_t *l, uint8_t *buf, size_t cap)
{
    nl_link_view_t f;
    int rc = request(l, NL_CMD_PULL, NL_RSP_FRAGMENT, NL_MAX_FRAGMENT, &f, 1);
    if (rc < 0) {
        return rc;
    }
    if (f.len == 0) {
        return 0;
    }
    if (f.len > cap || f.len < NL_FRAGMENT_HEADER_SIZE) {
        l->stats.proto_errors++;
        return NL_ERR_SIZE;
    }
    memcpy(buf, f.data, f.len);
    return f.len;
}

int nl_spi_link_status(nl_spi_link_t *l, nl_radio_status_t *out)
{
    nl_link_view_t f;
    int rc = request(l, NL_CMD_STATUS, NL_RSP_STATUS, NL_RADIO_STATUS_WIRE_SIZE, &f,
                     l->retries + 1u);
    if (rc < 0) {
        return rc;
    }
    return nl_radio_status_decode(f.data, f.len, out);
}

int nl_spi_link_configure(nl_spi_link_t *l, const nl_radio_params_t *params,
                          const nl_zone_plan_t *plan)
{
    /* Encode the payload where nl_link_encode puts DATA (it uses memmove,
     * so in place is fine) rather than in a NL_LINK_MAX_DATA stack buffer. */
    uint8_t *buf = &l->tx[3];
    const size_t cap = sizeof(l->tx) - NL_LINK_OVERHEAD;
    int n, rc;
    if (params != NULL) {
        n = nl_radio_params_encode(params, buf, cap);
        if (n < 0) {
            return n;
        }
        rc = send_request(l, NL_CMD_RADIO_CONFIG, buf, (size_t)n);
        if (rc < 0) {
            return rc;
        }
    }
    if (plan != NULL) {
        if (params != NULL && l->hal.delay_us != NULL && l->turnaround_us != 0) {
            l->hal.delay_us(l->hal.ctx, l->turnaround_us);
        }
        n = nl_zone_plan_encode(plan, buf, cap);
        if (n < 0) {
            return n;
        }
        rc = send_request(l, NL_CMD_ZONE_CONFIG, buf, (size_t)n);
        if (rc < 0) {
            return rc;
        }
    }
    return NL_OK;
}

/* ---- nl_link_ops_t adapters -------------------------------------------- */

static int ops_push(void *ctx, const uint8_t *frag, size_t len)
{
    return nl_spi_link_push(ctx, frag, len);
}

static int ops_pull(void *ctx, uint8_t *buf, size_t cap)
{
    return nl_spi_link_pull(ctx, buf, cap);
}

static bool ops_rx_pending(void *ctx)
{
    nl_spi_link_t *l = ctx;
    return l->hal.int_ready(l->hal.ctx);
}

static int ops_configure(void *ctx, const nl_radio_params_t *params,
                         const nl_zone_plan_t *plan)
{
    return nl_spi_link_configure(ctx, params, plan);
}

static int ops_status(void *ctx, nl_radio_status_t *st)
{
    return nl_spi_link_status(ctx, st);
}

void nl_spi_link_ops(nl_spi_link_t *l, nl_link_ops_t *ops)
{
    ops->push = ops_push;
    ops->pull = ops_pull;
    ops->rx_pending = l->hal.int_ready != NULL ? ops_rx_pending : NULL;
    ops->configure = ops_configure;
    ops->status = ops_status;
    ops->ctx = l;
}
