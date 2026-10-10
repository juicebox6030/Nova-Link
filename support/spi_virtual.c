/* SPDX-License-Identifier: GPL-3.0-only */
#include <string.h>
#include "nova_link/spi_virtual.h"

static nl_status advance(nl_spi_virtual *d, uint64_t now)
{
    if (now < d->now_us) return NL_ERR_ARGUMENT;
    d->now_us = now;
    return NL_OK;
}

nl_status nl_spi_virtual_init(nl_spi_virtual *d, nl_spi_slave *slave, uint64_t delay_us)
{
    if (d == NULL || slave == NULL || slave->radio == NULL) return NL_ERR_ARGUMENT;
    if (nl_spi_slave_pending(slave)) return NL_ERR_BUSY;
    memset(d, 0, sizeof(*d));
    d->slave = slave;
    d->delay_us = delay_us;
    d->connected = true;
    return NL_OK;
}

static nl_status start(void *context)
{
    nl_spi_virtual *d = context;
    if (d->started || d->active || d->retained || nl_spi_slave_pending(d->slave))
        return NL_ERR_BUSY;
    d->now_us = 0;
    d->started = true;
    return NL_OK;
}

static void stop(void *context)
{
    nl_spi_virtual *d = context;
    if (d->retained) (void)nl_spi_slave_cancel(d->slave, d->receipt);
    if (d->active || d->retained) ++d->stats.canceled;
    d->active = d->retained = d->started = false;
    d->receipt = 0;
}

bool nl_spi_virtual_drained(const nl_spi_virtual *d)
{
    return d != NULL && !d->active && !d->retained && !nl_spi_slave_pending(d->slave);
}

static nl_status can_stop(void *context)
{
    return nl_spi_virtual_drained(context) ? NL_OK : NL_ERR_BUSY;
}

static nl_status ready(void *context, bool *result)
{
    nl_spi_virtual *d = context;
    if (result == NULL) return NL_ERR_ARGUMENT;
    if (!d->started) return NL_ERR_NOT_FOUND;
    if (!d->connected) { ++d->stats.offline; return NL_ERR_BUSY; }
    *result = nl_radio_ready(d->slave->radio);
    return NL_OK;
}

static nl_status begin(void *context, const uint8_t *request, size_t size,
                       nl_spi_transaction transaction, uint64_t now)
{
    nl_spi_virtual *d = context;
    nl_frame decoded;
    nl_status status;
    if (request == NULL || transaction == 0u) return NL_ERR_ARGUMENT;
    if (!d->started) return NL_ERR_NOT_FOUND;
    if (d->active || d->retained) return NL_ERR_BUSY;
    status = advance(d, now);
    if (status != NL_OK) return status;
    if (!d->connected) { ++d->stats.offline; return NL_ERR_BUSY; }
    if (size > sizeof(d->request) || now > UINT64_MAX - d->delay_us) return NL_ERR_SIZE;
    status = nl_frame_decode(request, size, &decoded);
    if (status != NL_OK) return status;
    memcpy(d->request, request, size);
    d->request_size = size;
    d->transaction = transaction;
    d->complete_at = now + d->delay_us;
    d->fault = NL_SPI_VIRTUAL_CLEAN;
    if (d->next_fault <= NL_SPI_VIRTUAL_REQUEST_LENGTH ||
        (d->next_fault >= NL_SPI_VIRTUAL_PUSH_UNCERTAIN && decoded.command == NL_COMMAND_PUSH) ||
        (d->next_fault >= NL_SPI_VIRTUAL_RESPONSE_SHORT && d->next_fault <= NL_SPI_VIRTUAL_RESPONSE_PAYLOAD && decoded.command == NL_COMMAND_PULL)) {
        d->fault = d->next_fault;
        d->next_fault = NL_SPI_VIRTUAL_CLEAN;
    }
    d->active = true;
    ++d->stats.begins;
    return NL_OK;
}

static nl_status finish(void *context, nl_spi_transaction transaction, uint64_t now,
                        uint8_t *response, size_t capacity, size_t *size,
                        nl_pull_token *receipt, bool *uncertain)
{
    nl_spi_virtual *d = context;
    nl_status status;
    size_t request_size;
    if (response == NULL || size == NULL || receipt == NULL || uncertain == NULL) return NL_ERR_ARGUMENT;
    *uncertain = false;
    if (!d->active || transaction != d->transaction) return NL_ERR_STALE;
    status = advance(d, now);
    if (status != NL_OK) { d->active = false; return status; }
    if (!d->connected) { ++d->stats.offline; return NL_ERR_BUSY; }
    if (now < d->complete_at) { ++d->stats.delayed; return NL_ERR_BUSY; }
    if (capacity < NL_FRAME_MAX) { d->active = false; return NL_ERR_SIZE; }
    if (d->fault == NL_SPI_VIRTUAL_PUSH_UNCERTAIN_BEFORE_ACCEPT ||
        d->fault == NL_SPI_VIRTUAL_PUSH_REJECTED) {
        d->active = false;
        ++d->stats.completed;
        *size = 0;
        *receipt = 0;
        *uncertain = d->fault == NL_SPI_VIRTUAL_PUSH_UNCERTAIN_BEFORE_ACCEPT;
        return *uncertain ? NL_ERR_FORMAT : NL_ERR_FULL;
    }
    request_size = d->request_size;
    if (d->fault == NL_SPI_VIRTUAL_REQUEST_SHORT) --request_size;
    if (d->fault == NL_SPI_VIRTUAL_REQUEST_LENGTH) d->request[1] = 0;
    d->response_size = 0;
    d->receipt = 0;
    status = nl_spi_slave_exchange(d->slave, d->request, request_size,
        d->response, sizeof(d->response), &d->response_size, &d->receipt);
    d->active = false;
    ++d->stats.completed;
    if (status != NL_OK) {
        if (d->fault == NL_SPI_VIRTUAL_REQUEST_SHORT || d->fault == NL_SPI_VIRTUAL_REQUEST_LENGTH)
            ++d->stats.malformed_requests;
        *size = 0;
        *receipt = 0;
        return status;
    }
    if (d->fault == NL_SPI_VIRTUAL_PUSH_UNCERTAIN) {
        *size = 0;
        *receipt = 0;
        *uncertain = true;
        return NL_ERR_FORMAT;
    }
    if (d->response_size != 0u) {
        d->retained = true;
        ++d->stats.pull_responses;
        if (d->fault == NL_SPI_VIRTUAL_RESPONSE_SHORT) --d->response_size;
        if (d->fault == NL_SPI_VIRTUAL_RESPONSE_LENGTH) d->response[1] = 0;
        if (d->fault == NL_SPI_VIRTUAL_RESPONSE_PAYLOAD && d->response_size > 5u)
            d->response[d->response_size - 1u] ^= 1u;
        if (d->fault >= NL_SPI_VIRTUAL_RESPONSE_SHORT) ++d->stats.response_faults;
    }
    memcpy(response, d->response, d->response_size);
    *size = d->response_size;
    *receipt = d->receipt;
    return NL_OK;
}

static nl_status settle(void *context, nl_pull_token receipt, bool consume)
{
    nl_spi_virtual *d = context;
    nl_status status;
    if (!d->retained || receipt != d->receipt) return NL_ERR_STALE;
    if (!d->connected) { ++d->stats.offline; return NL_ERR_BUSY; }
    if (d->commit_failures != 0u) {
        --d->commit_failures;
        ++d->stats.commit_retries;
        return NL_ERR_BUSY;
    }
    status = consume ? nl_spi_slave_commit(d->slave, receipt) : nl_spi_slave_cancel(d->slave, receipt);
    if (status == NL_OK || status == NL_ERR_STALE || status == NL_ERR_EMPTY) {
        d->retained = false;
        d->receipt = 0;
        if (consume && status == NL_OK) ++d->stats.commits;
        if (!consume) ++d->stats.canceled;
    }
    return status;
}

nl_spi_driver nl_spi_virtual_driver(nl_spi_virtual *device)
{
    nl_spi_driver driver = {.start = start, .stop = stop, .can_stop = can_stop,
        .ready = ready, .begin = begin, .finish = finish, .settle = settle,
        .context = device};
    return driver;
}

void nl_spi_virtual_set_connected(nl_spi_virtual *d, bool connected)
{
    if (d != NULL) d->connected = connected;
}

nl_status nl_spi_virtual_fault_next(nl_spi_virtual *d, nl_spi_virtual_fault fault)
{
    if (d == NULL || fault < NL_SPI_VIRTUAL_CLEAN || fault > NL_SPI_VIRTUAL_PUSH_REJECTED)
        return NL_ERR_ARGUMENT;
    if (d->next_fault != NL_SPI_VIRTUAL_CLEAN) return NL_ERR_BUSY;
    d->next_fault = fault;
    return NL_OK;
}

void nl_spi_virtual_fail_commits(nl_spi_virtual *d, uint32_t attempts)
{
    if (d != NULL) d->commit_failures = attempts;
}

nl_status nl_spi_virtual_air_init(nl_spi_virtual_air *air, uint64_t delay_us)
{
    if (air == NULL) return NL_ERR_ARGUMENT;
    memset(air, 0, sizeof(*air));
    air->delay_us = delay_us;
    return NL_OK;
}

nl_status nl_spi_virtual_air_step(nl_spi_virtual_air *air, nl_radio *sender,
                                 nl_radio *receiver, uint64_t now, bool connected)
{
    nl_fragment current, decoded, popped;
    nl_window window;
    uint8_t bytes[NL_FRAGMENT_MAX];
    size_t size;
    nl_status status;
    if (air == NULL || sender == NULL || receiver == NULL || sender == receiver || now < air->now_us)
        return NL_ERR_ARGUMENT;
    if (air->pending && (air->sender != sender || air->receiver != receiver)) return NL_ERR_BUSY;
    air->now_us = now;
    if (!connected) { ++air->blocked; return NL_ERR_BUSY; }
    if (!air->pending) {
        if (now > UINT64_MAX - air->delay_us) return NL_ERR_SIZE;
        status = nl_radio_next_window(sender, now, &window);
        if (status != NL_OK) return status;
        status = nl_radio_prepare_tx(sender, now, &current, &window);
        if (status != NL_OK) return status;
        status = nl_fragment_encode(&current, air->original_bytes, sizeof(air->original_bytes), &air->original_size);
        if (status != NL_OK) return status;
        air->original = air->outgoing = current;
        air->sender = sender;
        air->receiver = receiver;
        air->complete_at = now + air->delay_us;
        air->pending = true;
        return NL_ERR_BUSY;
    }
    if (now < air->complete_at) return NL_ERR_BUSY;
    status = nl_radio_peek_tx(sender, air->original.zone, &current);
    if (status != NL_OK) return status;
    status = nl_fragment_encode(&current, bytes, sizeof(bytes), &size);
    if (status != NL_OK) return status;
    if (size != air->original_size || memcmp(bytes, air->original_bytes, size) != 0) return NL_ERR_STALE;
    status = nl_fragment_encode(&air->outgoing, bytes, sizeof(bytes), &size);
    if (status == NL_OK) status = nl_fragment_decode(bytes, size, &decoded);
    if (status == NL_OK) status = nl_radio_receive(receiver, &decoded, now);
    if (status == NL_ERR_FULL || status == NL_ERR_BUSY) { ++air->blocked; return status; }
    if (status != NL_OK && status != NL_ERR_DUPLICATE && status != NL_ERR_STALE && status != NL_ERR_ACCESS)
        return status;
    if (status != NL_OK) ++air->rejected;
    status = nl_radio_pop_tx(sender, air->original.zone, &popped);
    if (status != NL_OK) return status;
    air->pending = false;
    ++air->completed;
    return NL_OK;
}
