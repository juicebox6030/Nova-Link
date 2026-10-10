/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef NOVA_LINK_MULTIVERSE_PLUGIN_H
#define NOVA_LINK_MULTIVERSE_PLUGIN_H

#include "nova_link/host.h"
#include "nova_link/module.h"
#include "nova/multiverse.h"

/** @file multiverse_plugin.h
 * Compiled DMX stream plugin for native NOVA-LINK hosts. NLM1 is a local
 * application protocol, NOT Multiverse RF or the test-only NVS1 codec.
 * Allocation-free; serialize all calls with the owning host's event loop.
 * Keep context and descriptor alive until unregister. Treat state as private.
 * RX must use FIFO queues: latest-per-stream coalescing destroys chunk groups.
 * Native stream deduplication requires fragments in native sequence order.
 */
#define NL_MULTIVERSE_HEADER_BYTES 28u
#define NL_MULTIVERSE_CHUNK_SLOTS (NL_PAYLOAD_MAX - NL_MULTIVERSE_HEADER_BYTES)

typedef enum { NL_MULTIVERSE_TX, NL_MULTIVERSE_RX } nl_multiverse_role;
typedef struct {
    nl_multiverse_role role;
    uint8_t zone;              /**< 1..7, exclusive TX or read-only RX claim. */
    uint8_t peer_origin;       /**< RX origin 0..7, different from local host. */
    uint16_t universe;         /**< Logical universe 1..63999. */
    uint32_t session;          /**< Explicit stream epoch; no automatic discovery. */
    uint64_t interval_us;      /**< TX refresh interval, nonzero. */
    uint64_t full_interval_us; /**< TX full refresh bound, >= interval_us. */
    uint64_t loss_timeout_us;  /**< RX hold-last timeout, nonzero. */
    uint64_t assembly_timeout_us; /**< RX assembly timeout, nonzero. */
    uint8_t chunks_per_tick;   /**< TX budget 1..8; stops on first send failure. */
} nl_multiverse_config;

typedef struct {
    uint64_t backpressure, send_errors, bad_payloads, filtered_origins, bad_flags;
} nl_multiverse_stats;

typedef struct {
    nl_multiverse_config config;
    nl_module_zone module_zone;
    nova_mv_tx_t tx;
    nova_mv_rx_t rx;
    nl_multiverse_stats stats;
    nl_host *owner;
    nl_plugin_id id;
    nl_status last_send_status;
    nova_mv_result_t last_result;
    bool initialized, active, stopped;
} nl_multiverse_context;

/** Initialize before registration. Do not reinitialize an active context.
 * Stopped contexts require reinitialization before registering again. Drain
 * old transport ownership first and use a new session for a new TX lifetime.
 * Only timing/budget fields for the configured role are required.
 */
nova_mv_result_t nl_multiverse_init(nl_multiverse_context *context,
                                  const nl_multiverse_config *config);
nl_plugin nl_multiverse_plugin(nl_multiverse_context *context);
/** Construct after init, before registration. Default name multiverse;
 * requires radio-link. Returned metadata may be
 * customized before registration to support several streams/providers.
 */
nl_module nl_multiverse_module(nl_multiverse_context *context);
/** Copy latest TX levels; may be called before registration or between ticks.
 * A tick accepts up to chunks_per_tick fragments into the host transport.
 * Engine completion here means QUEUE ACCEPTANCE, not RF completion or peer ACK.
 * Queue failure retains identical chunk bytes; refresh repairs downstream loss.
 */
nova_mv_result_t nl_multiverse_submit(nl_multiverse_context *context,
                                    const nova_dmx_frame_t *frame);
void nl_multiverse_force_full(nl_multiverse_context *context);
/** Return FRAME_READY with the last complete RX frame. Output untouched before acquisition/after
 * loss or stop; use rx.stats.frames to observe commits and rx.link for status.
 * Poll nl_host_tick even through silence. No implicit blackout is generated.
 */
nova_mv_result_t nl_multiverse_get(nl_multiverse_context *context, uint64_t now_us,
                                 nova_dmx_frame_t *frame);
/** Explicit RX restart/rebind, between host callbacks. This resets only this
 * plugin's levels/model history, not shared native host/radio stream trackers.
 * Drain old queues and reset native origin tracking separately when the peer's
 * native sequence restarts. Unknown sessions can never bind automatically.
 */
nova_mv_result_t nl_multiverse_bind(nl_multiverse_context *context,
                                  uint8_t peer_origin, uint32_t session);

/** NLM1 payload: magic[4], kind[1], reserved-zero[1], universe[2], session[4],
 * sequence[2], base[2], slots[2], span-start[2], span-count[2], offset[2],
 * levels[0..72], CRC-32/ISO-HDLC[4]. Integers and CRC are little-endian.
 * Chunk count is payload length minus 28. CRC detects corruption, not spoofing.
 * Outputs untouched on error except *written=0. Arguments must not alias.
 */
nova_mv_result_t nl_multiverse_payload_encode(const nova_mv_packet_t *packet,
                                            uint8_t *output, size_t capacity,
                                            size_t *written);
nova_mv_result_t nl_multiverse_payload_decode(const uint8_t *bytes, size_t size,
                                            nova_mv_packet_t *packet);

#endif
