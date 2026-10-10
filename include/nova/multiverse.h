/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef NOVA_MULTIVERSE_H
#define NOVA_MULTIVERSE_H

#include "nova/dmx.h"
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/** @file multiverse.h
 * Allocation-free, hardware-independent DMX stream model for Multiverse work.
 * These are normalized SOFTWARE packets, not the proprietary on-air format.
 * A verified adapter must translate PHY/integrity/control/session information
 * into this model. No SHoW ID/Key, hopping, FEC, RDM or RF driver is implemented.
 * Each instance owns one universe/session; use separate instances per stream.
 * Calls must be serialized, with nondecreasing extended microsecond timestamps.
 * Initialize before use, treat state fields as private, and do not alias output
 * or packet/frame arguments with engine storage. No callbacks or heap are used.
 */

typedef enum {
    NOVA_MV_OK = 0, NOVA_MV_PACKET_READY, NOVA_MV_FRAME_READY, NOVA_MV_IDLE,
    NOVA_MV_DUPLICATE, NOVA_MV_STALE, NOVA_MV_FILTERED, NOVA_MV_NEED_FULL,
    NOVA_MV_BAD_PACKET, NOVA_MV_UNVERIFIED, NOVA_MV_INVALID_ARGUMENT,
    NOVA_MV_INVALID_TIME, NOVA_MV_INVALID_TOKEN, NOVA_MV_EXHAUSTED,
    NOVA_MV_BUFFER_TOO_SMALL
} nova_mv_result_t;

typedef enum { NOVA_MV_FULL = 0, NOVA_MV_DELTA = 1 } nova_mv_kind_t;
typedef enum { NOVA_MV_INTEGRITY_OK = 0, NOVA_MV_INTEGRITY_BAD,
               NOVA_MV_INTEGRITY_UNKNOWN } nova_mv_integrity_t;
typedef enum { NOVA_MV_WAIT_FULL = 0, NOVA_MV_LIVE,
               NOVA_MV_RECOVERING, NOVA_MV_LOST } nova_mv_link_t;

/** One chunk of a normalized update. Slot offsets are zero-based (channel 1 = 0).
 * FULL covers [0, slot_count); DELTA replaces one contiguous span of the last
 * committed base_sequence. All chunks share the same metadata and sequence.
 * offset is relative to span_start. Empty spans carry exactly one empty chunk.
 * A FULL uses base_sequence = 0. DELTA never changes slot_count.
 * Sessions are explicitly bound locally; unknown sessions cannot rebind RX.
 */
typedef struct {
    nova_mv_kind_t kind;
    uint16_t universe;
    uint32_t session;
    uint16_t sequence, base_sequence;
    uint16_t slot_count, span_start, span_count, offset, count;
    uint8_t levels[NOVA_DMX_MAX_SLOTS];
} nova_mv_packet_t;

typedef struct {
    uint16_t universe;             /**< 1..63999, logical universe identifier. */
    uint32_t session;              /**< Local model session, not a SHoW Key. */
    uint16_t chunk_slots;          /**< 1..512; synthetic/model payload budget. */
    uint64_t interval_us;          /**< Nonzero refresh interval. */
    uint64_t full_interval_us;     /**< >= interval_us; periodic resync bound. */
} nova_mv_tx_config_t;

typedef struct {
    uint64_t updates, packets, retries;
    uint64_t coalesced; /**< Changed unsent host snapshots superseded before TX. */
} nova_mv_tx_stats_t;

typedef struct {
    nova_mv_tx_config_t config;
    nova_dmx_frame_t desired, baseline, frozen;
    nova_mv_packet_t pending;
    nova_mv_tx_stats_t stats;
    uint64_t last_now, last_sent, last_full, next_token, token;
    uint16_t sequence;
    bool initialized, has_desired, has_baseline, active, in_flight, force_full;
} nova_mv_tx_t;

nova_mv_result_t nova_mv_packet_validate(const nova_mv_packet_t *packet);
nova_mv_result_t nova_mv_tx_init(nova_mv_tx_t *tx, const nova_mv_tx_config_t *config);
/** Copy latest host levels. Updates during transmission do not alter frozen chunks. */
nova_mv_result_t nova_mv_tx_submit(nova_mv_tx_t *tx, const nova_dmx_frame_t *frame);
/** Request a full update after the current transmission; does not cancel ownership. */
void nova_mv_tx_force_full(nova_mv_tx_t *tx);
/** Prepare/retry one immutable chunk. Repeated prepares before completion return
 * the same token and bytes. The adapter owns submission and RF completion.
 * No sequence/baseline advance occurs until every chunk completes successfully.
 */
nova_mv_result_t nova_mv_tx_prepare(nova_mv_tx_t *tx, uint64_t now_us,
                                  nova_mv_packet_t *packet, uint64_t *token);
/** Complete the matching submission. Failure retains the chunk for retry with
 * a new token. Success means local RF completion, NOT peer acknowledgment.
 * Packet loss is repaired by periodic FULL updates or an explicit force_full.
 */
nova_mv_result_t nova_mv_tx_complete(nova_mv_tx_t *tx, uint64_t token,
                                   bool success, uint64_t now_us);

typedef struct {
    uint16_t universe;
    uint32_t session;
    uint64_t loss_timeout_us;      /**< Nonzero hold-last-state timeout. */
    uint64_t assembly_timeout_us;  /**< Nonzero; incomplete chunks do not refresh it. */
} nova_mv_rx_config_t;

typedef struct {
    uint64_t frames, packets, duplicates, stale, filtered, bad, unverified;
    uint64_t missing_base, abandoned, losses;
} nova_mv_rx_stats_t;

typedef struct {
    nova_mv_rx_config_t config;
    nova_mv_rx_stats_t stats;
    nova_dmx_frame_t frame, assembling;
    nova_mv_packet_t header;
    uint8_t covered[NOVA_DMX_MAX_SLOTS];
    uint16_t sequence, received;
    uint64_t last_now, last_frame, assembly_started;
    nova_mv_link_t link;
    bool initialized, has_frame, has_sequence, synchronized, active;
} nova_mv_rx_t;

nova_mv_result_t nova_mv_rx_init(nova_mv_rx_t *rx, const nova_mv_rx_config_t *config);
/** Explicit discovery/restart action. Discards all levels, assembly and sequence
 * history, preserves counters/clock, and requires a FULL in the new session.
 */
nova_mv_result_t nova_mv_rx_bind(nova_mv_rx_t *rx, uint32_t session);
/** Expire assembly and hold-last-state. Assembly expiry discards partial work
 * while preserving any synchronized committed base. Link-loss expiry requires
 * a new FULL; no expiry fabricates blackout levels or delivers a partial frame.
 * Sequence history survives loss so duplicates cannot revive an expired link.
 */
nova_mv_result_t nova_mv_rx_tick(nova_mv_rx_t *rx, uint64_t now_us);
/** Only verified integrity is accepted. New frames commit atomically once all
 * chunks arrive. Out-of-order chunks are allowed; conflicting overlaps fail.
 * Sequence ordering uses a 16-bit half-range; larger jumps need explicit bind.
 * completed is written only on FRAME_READY. NULL completed is allowed.
 */
nova_mv_result_t nova_mv_rx_receive(nova_mv_rx_t *rx, const nova_mv_packet_t *packet,
                                  nova_mv_integrity_t integrity, uint64_t now_us,
                                  nova_dmx_frame_t *completed);
/** Read the last complete, unexpired frame, including during recovery.
 * Returns NEED_FULL after loss or before initial synchronization; output untouched.
 */
nova_mv_result_t nova_mv_rx_get(nova_mv_rx_t *rx, uint64_t now_us,
                              nova_dmx_frame_t *frame);
const char *nova_mv_result_name(nova_mv_result_t result);
const char *nova_mv_link_name(nova_mv_link_t link);

#ifdef __cplusplus
}
#endif
#endif
