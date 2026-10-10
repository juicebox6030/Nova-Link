/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef NOVA_LINK_SPI_VIRTUAL_H
#define NOVA_LINK_SPI_VIRTUAL_H

#include "nova_link/spi_backend.h"
#include "nova_link/spi_slave.h"

/** @file spi_virtual.h Deterministic developer support for the actual framed
 * host/slave adapters. Logical time, local C statuses and local receipts do not
 * define physical SPI acknowledgements, timings or Multiverse RF compatibility.
 * Caller-owned storage; serialized calls. Use FIFO native queues.
 */
typedef enum {
    NL_SPI_VIRTUAL_CLEAN,
    NL_SPI_VIRTUAL_REQUEST_SHORT,
    NL_SPI_VIRTUAL_REQUEST_LENGTH,
    NL_SPI_VIRTUAL_RESPONSE_SHORT,
    NL_SPI_VIRTUAL_RESPONSE_LENGTH,
    NL_SPI_VIRTUAL_RESPONSE_PAYLOAD,
    NL_SPI_VIRTUAL_PUSH_UNCERTAIN,
    NL_SPI_VIRTUAL_PUSH_UNCERTAIN_BEFORE_ACCEPT,
    NL_SPI_VIRTUAL_PUSH_REJECTED
} nl_spi_virtual_fault;

typedef struct {
    uint64_t begins, completed, canceled, delayed, offline, malformed_requests;
    uint64_t pull_responses, commits, commit_retries, response_faults;
} nl_spi_virtual_stats;

typedef struct {
    nl_spi_slave *slave;
    nl_spi_virtual_stats stats;
    uint8_t request[NL_FRAME_MAX], response[NL_FRAME_MAX];
    size_t request_size, response_size;
    uint64_t now_us, complete_at, transaction, delay_us;
    nl_pull_token receipt;
    nl_spi_virtual_fault next_fault, fault;
    uint32_t commit_failures;
    bool started, connected, active, retained;
} nl_spi_virtual;

/** Initialize before driver registration. No storage may own pending work. */
nl_status nl_spi_virtual_init(nl_spi_virtual *device, nl_spi_slave *slave,
                             uint64_t delay_us);
/** Complete driver callbacks for the actual host transport plugin. Successful
 * start begins a fresh logical clock epoch; the slave receipt history survives.
 */
nl_spi_driver nl_spi_virtual_driver(nl_spi_virtual *device);
void nl_spi_virtual_set_connected(nl_spi_virtual *device, bool connected);
/** One fault per next matching transaction: request faults apply to any command;
 * response faults wait for PULL; PUSH faults wait for PUSH. PUSH_UNCERTAIN is
 * after native enqueue, BEFORE_ACCEPT is before enqueue, and REJECTED certifies
 * no enqueue. Corruption does not invent a transport CRC.
 */
nl_status nl_spi_virtual_fault_next(nl_spi_virtual *device, nl_spi_virtual_fault fault);
void nl_spi_virtual_fail_commits(nl_spi_virtual *device, uint32_t attempts);
bool nl_spi_virtual_drained(const nl_spi_virtual *device);

typedef struct {
    nl_radio *sender, *receiver;
    nl_fragment original, outgoing;
    uint8_t original_bytes[NL_FRAGMENT_MAX];
    size_t original_size;
    uint64_t now_us, complete_at, delay_us, completed, blocked, rejected;
    bool pending;
} nl_spi_virtual_air;

/** Separate deterministic logical air path. Serializes actual native queue
 * heads, freezes bytes for a delayed transfer, retains FIFO on congestion and
 * only pops after receiver ownership. No RF profile or airtime claim.
 */
nl_status nl_spi_virtual_air_init(nl_spi_virtual_air *air, uint64_t delay_us);
nl_status nl_spi_virtual_air_step(nl_spi_virtual_air *air, nl_radio *sender,
                                 nl_radio *receiver, uint64_t now_us,
                                 bool connected);

#endif
