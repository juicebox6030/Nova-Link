#include <string.h>
#include "nova_link/spi_slave.h"

nl_status nl_spi_slave_init(nl_spi_slave *slave, nl_radio *radio)
{
    if (slave == NULL || radio == NULL) return NL_ERR_ARGUMENT;
    memset(slave, 0, sizeof(*slave));
    slave->radio = radio;
    slave->next_receipt = 1u;
    return NL_OK;
}

nl_status nl_spi_slave_exchange(nl_spi_slave *slave,
    const uint8_t *request, size_t request_size,
    uint8_t *response, size_t response_capacity, size_t *response_size,
    nl_pull_token *receipt)
{
    nl_frame frame;
    nl_frame prepared;
    nl_pull_token token = 0;
    uint8_t bytes[NL_FRAME_MAX];
    size_t size = 0;
    nl_status status;
    if (slave == NULL || slave->radio == NULL || response_size == NULL ||
        receipt == NULL || (response == NULL && response_capacity != 0u))
        return NL_ERR_ARGUMENT;
    status = nl_frame_decode(request, request_size, &frame);
    if (status != NL_OK) return status;
    if (frame.command == NL_COMMAND_PULL) {
        if (slave->pending) {
            if (response_capacity < slave->size) return NL_ERR_SIZE;
            if (response == NULL) return NL_ERR_ARGUMENT;
            memcpy(response, slave->bytes, slave->size);
            *response_size = slave->size;
            *receipt = slave->receipt;
            return NL_OK;
        }
        status = nl_radio_prepare_pull(slave->radio, &prepared, &token);
        if (status != NL_OK) return status;
        if (slave->next_receipt == 0u) return NL_ERR_SIZE;
        status = nl_frame_encode(&prepared, bytes, sizeof(bytes), &size);
        if (status != NL_OK) return status;
        if (response_capacity < size) return NL_ERR_SIZE;
        if (response == NULL) return NL_ERR_ARGUMENT;
        slave->response = prepared;
        memcpy(slave->bytes, bytes, size);
        slave->size = size;
        slave->radio_receipt = token;
        slave->receipt = slave->next_receipt;
        slave->next_receipt = slave->next_receipt == UINT64_MAX
            ? 0u : slave->next_receipt + 1u;
        slave->pending = true;
        memcpy(response, bytes, size);
        *response_size = size;
        *receipt = slave->receipt;
        return NL_OK;
    }
    status = nl_radio_handle_frame(slave->radio, &frame, NULL, NULL);
    if (status != NL_OK) return status;
    *response_size = 0;
    *receipt = 0;
    return NL_OK;
}

nl_status nl_spi_slave_commit(nl_spi_slave *slave, nl_pull_token receipt)
{
    nl_status status;
    if (slave == NULL || slave->radio == NULL) return NL_ERR_ARGUMENT;
    if (!slave->pending || receipt == 0u || receipt != slave->receipt)
        return NL_ERR_STALE;
    status = nl_radio_commit_pull(slave->radio, &slave->response,
        slave->radio_receipt);
    if (status == NL_OK || status == NL_ERR_STALE || status == NL_ERR_EMPTY) {
        slave->pending = false;
        slave->size = 0;
        slave->receipt = 0;
        slave->radio_receipt = 0;
    }
    return status;
}

nl_status nl_spi_slave_cancel(nl_spi_slave *slave, nl_pull_token receipt)
{
    if (slave == NULL || slave->radio == NULL) return NL_ERR_ARGUMENT;
    if (!slave->pending || receipt == 0u || receipt != slave->receipt)
        return NL_ERR_STALE;
    slave->pending = false;
    slave->size = 0;
    slave->receipt = 0;
    slave->radio_receipt = 0;
    return NL_OK;
}

bool nl_spi_slave_pending(const nl_spi_slave *slave)
{
    return slave != NULL && slave->radio != NULL && slave->pending;
}
