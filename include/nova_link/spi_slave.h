#ifndef NOVA_LINK_SPI_SLAVE_H
#define NOVA_LINK_SPI_SLAVE_H

#include "nova_link/radio.h"

/** @file spi_slave.h Serialized native-frame SPI slave adapter boundary.
 * This helper performs no physical SPI I/O. Status and receipts are local C
 * outcomes, not serialized acknowledgments. A board driver must assemble one
 * complete request before calling exchange and define its own transfer timing.
 */
typedef struct {
    nl_radio *radio;
    nl_frame response;
    uint8_t bytes[NL_FRAME_MAX];
    size_t size;
    nl_pull_token receipt;
    nl_pull_token radio_receipt;
    nl_pull_token next_receipt;
    bool pending;
} nl_spi_slave;

/** Initialize stable caller-owned storage for one radio lifetime. Pending work
 * must be cancelled/drained before initializing either object again. */
nl_status nl_spi_slave_init(nl_spi_slave *slave, nl_radio *radio);
/** Process exactly one complete documented native frame. Malformed/partial
 * requests have no queue effects. PUSH success means local TX queue acceptance.
 * PULL copies a prepared immutable response and adapter-local receipt, retaining
 * RX ownership until commit. Repeated PULL returns that same staged receipt.
 * An insufficient response buffer has no queue effect and does not stage work.
 * Request storage is borrowed only for this call; response bytes are copied to
 * caller storage. Receipts are distinct for each newly staged response, even
 * after cancellation of the same queue head. Exhausted receipts return SIZE.
 * All outputs remain unchanged on failure. EMPTY has no response bytes.
 */
nl_status nl_spi_slave_exchange(nl_spi_slave *slave,
    const uint8_t *request, size_t request_size,
    uint8_t *response, size_t response_capacity, size_t *response_size,
    nl_pull_token *receipt);
/** Commit after the board adapter accepts ownership of the complete response.
 * Failed physical transfers must not call this. STALE/EMPTY invalidates only
 * the staged receipt; it never pops a coalesced replacement. This does not prove
 * the master decoded the response or that a peer acknowledged it. */
nl_status nl_spi_slave_commit(nl_spi_slave *slave, nl_pull_token receipt);
/** Abandon a staged response without removing its radio queue entry. A token
 * mismatch does not disturb current work. Call only after I/O is cancelled. */
nl_status nl_spi_slave_cancel(nl_spi_slave *slave, nl_pull_token receipt);
/** Pending response ownership must veto normal board adapter shutdown. */
bool nl_spi_slave_pending(const nl_spi_slave *slave);

#endif
