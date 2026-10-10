/* Compile/startup check for the native CC1352R radio-side SPI boundary.
 * No pins, SPI transfers, RF settings, or physical acknowledgments are chosen.
 * The vendor RTOS startup invokes mainThread in its normal task context.
 */
#include <string.h>
#include "nova_link/spi_slave.h"

static nl_radio radio;
static nl_spi_slave slave;
static uint8_t request[NL_FRAME_MAX];
static uint8_t response[NL_FRAME_MAX];

/* Inspect with a debugger only after validating deployment board configuration.
 * Compile success does not establish that this check executed on hardware. */
volatile nl_status nova_cc1352r_check_status = NL_ERR_BUSY;

nl_status nova_cc1352r_run_check(void)
{
    nl_fragment input = {0};
    nl_fragment output;
    nl_frame frame;
    nl_frame decoded;
    nl_pull_token receipt;
    size_t request_size, response_size;
    nl_status status;
    const uint8_t pull[] = {NL_TRANSPORT_SYNC, 1u, NL_COMMAND_PULL};
    status = nl_radio_init(&radio, 2u, 1000u, 0u, 0u);
    if (status != NL_OK) return status;
    status = nl_spi_slave_init(&slave, &radio);
    if (status != NL_OK) return status;
    input.origin = 1u;
    input.zone = 1u;
    input.sequence = 7u;
    input.payload_size = 3u;
    input.payload[0] = 0u;
    input.payload[1] = NL_TRANSPORT_SYNC;
    input.payload[2] = 0xFFu;
    status = nl_frame_from_fragment(NL_COMMAND_PUSH, &input, &frame);
    if (status != NL_OK) return status;
    status = nl_frame_encode(&frame, request, sizeof(request), &request_size);
    if (status != NL_OK) return status;
    status = nl_spi_slave_exchange(&slave, request, request_size, response,
        sizeof(response), &response_size, &receipt);
    if (status != NL_OK) return status;
    if (response_size != 0u || receipt != 0u) return NL_ERR_CONFLICT;
    /* Local model loopback; this deliberately submits no radio operation. */
    status = nl_radio_pop_tx(&radio, input.zone, &output);
    if (status != NL_OK) return status;
    status = nl_radio_receive(&radio, &output, 0u);
    if (status != NL_OK) return status;
    status = nl_spi_slave_exchange(&slave, pull, sizeof(pull), response,
        sizeof(response), &response_size, &receipt);
    if (status != NL_OK) return status;
    status = nl_frame_decode(response, response_size, &decoded);
    if (status != NL_OK) return status;
    if (decoded.command != NL_COMMAND_FRAGMENT) return NL_ERR_FORMAT;
    status = nl_frame_to_fragment(&decoded, &output);
    if (status != NL_OK) return status;
    if (input.origin != output.origin || input.zone != output.zone ||
        input.sequence != output.sequence || input.flags != output.flags ||
        input.payload_size != output.payload_size ||
        memcmp(input.payload, output.payload, input.payload_size) != 0)
        return NL_ERR_CONFLICT;
    status = nl_spi_slave_commit(&slave, receipt);
    if (status != NL_OK) return status;
    return nl_radio_ready(&radio) || nl_spi_slave_pending(&slave)
        ? NL_ERR_CONFLICT : NL_OK;
}

void *mainThread(void *argument)
{
    (void)argument;
    nova_cc1352r_check_status = nova_cc1352r_run_check();
    return NULL;
}
