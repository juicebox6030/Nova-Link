/**
 * @file nl_sim.h
 * @brief Discrete-time RF network simulator for the NOVA-LINK core.
 *
 * Every simulated device runs the real, unmodified host core, SPI master
 * driver, SPI slave handler and radio scheduler, wired together through an
 * in-process SPI loopback. Only the RF hardware is modelled:
 *
 * - Airtime: preamble + sync + length + fragment + CRC at the band bitrate,
 *   plus an RX->TX turnaround during which the radio is deaf.
 * - Half-duplex: a transmitting radio hears nothing.
 * - Sync: a receiver gets a packet only if it was listening on that
 *   frequency from the packet's start (tuning in late loses it). With
 *   finish_rx (default) the platform completes a packet in progress before
 *   acting on the next scheduler decision; without it, switching away
 *   mid-packet loses the packet.
 * - Collisions: two overlapping transmissions on one frequency destroy each
 *   other at every receiver that can hear both. No capture effect.
 * - Loss: a global packet error rate plus a per-link loss matrix; a link
 *   loss of 1.0 means the two devices cannot hear each other at all
 *   (hidden terminals).
 * - Clocks: every device gets a random 32-bit clock offset so wrap handling
 *   is exercised, and devices boot at configurable times.
 *
 * Not modelled: adjacent-channel interference, frequency offset, RSSI,
 * capture, SPI bus timing (SPI transactions complete instantly) and CPU
 * load. Results are therefore an upper bound for scheduling behaviour, not
 * a link budget.
 */
#ifndef NL_SIM_H
#define NL_SIM_H

#include "nova_link/nl_host.h"
#include "nova_link/nl_radio.h"
#include "nova_link/nl_spi_link.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define NL_SIM_MAX_NODES NL_NUM_ORIGINS
#define NL_SIM_MAX_AIR 64          /**< Concurrent transmissions tracked. */
#define NL_SIM_LAT_BUCKET_US 100u  /**< Latency histogram resolution. */
#define NL_SIM_LAT_BUCKETS 20000u  /**< 2 s range; later samples clamp. */
#define NL_SIM_MAX_FREQS 32        /**< Distinct frequencies tracked for stats. */
#define NL_SIM_PAYLOAD_HDR 9       /**< Test payload header (see nl_sim.c). */

/** PHY timing for one band. */
typedef struct {
    uint32_t bitrate_bps;
    uint8_t preamble_bytes;
    uint8_t sync_bytes;
    uint8_t length_bytes; /**< PHY length field. */
    uint8_t crc_bytes;
    uint32_t turnaround_us; /**< Synth settle / RX->TX switch before each TX. */
} nl_sim_phy_t;

/**
 * Defaults: sub-GHz 200 kbps 2-GFSK, 2.4 GHz 250 kbps (CC1352R proprietary
 * PHYs). The sub-GHz rate is an assumption: at 50 kbps the default traffic
 * (4 devices x 20 Hz x 32 B x 3 repeats on one zone) offers about 160% of
 * the channel's capacity and cannot work; see docs/simulation.adoc.
 */
void nl_sim_phy_default(nl_sim_phy_t *phy, uint8_t band);

/** On-air time of a fragment of @p len bytes, excluding turnaround. */
uint32_t nl_sim_airtime_us(const nl_sim_phy_t *phy, size_t len);

/** Periodic traffic one device sends on one zone. */
typedef struct {
    uint8_t zone;         /**< 1..7; 0 = no traffic. */
    uint32_t period_us;   /**< Mean gap between sends. */
    uint32_t jitter_us;   /**< Uniform random 0..N us added to each gap. */
    uint8_t payload_len;  /**< NL_SIM_PAYLOAD_HDR..NL_MAX_PAYLOAD. */
    uint8_t flags;        /**< e.g. NL_FLAG_BURST. */
    uint16_t burst;       /**< Fragments sent back to back per period (>= 1). */
} nl_sim_traffic_t;

/** Per-device configuration. */
typedef struct {
    bool enabled;
    uint8_t listen_mask;    /**< Zones 1..7 this device claims (bit n = zone n). */
    uint8_t priority[NL_NUM_ZONES]; /**< Zone priority overrides (0 = default 1). */
    nl_sim_traffic_t traffic[2];
    uint64_t boot_us;       /**< Power-up time. */
} nl_sim_node_cfg_t;

/** A complete simulation. Fill with nl_sim_scenario_default() and edit. */
typedef struct {
    uint8_t nodes;            /**< Devices 0..nodes-1 use originIDs 0..nodes-1. */
    uint64_t duration_us;
    uint64_t warmup_us;       /**< Traffic sent before this is not counted. */
    uint32_t tick_us;         /**< Simulation step. */
    uint32_t host_poll_us;    /**< Host main-loop period. */
    uint32_t seed;
    nl_sim_phy_t phy[2];      /**< Indexed by NL_BAND_SUBGHZ / NL_BAND_2G4. */
    nl_radio_params_t params; /**< origin_id is overridden per device. */
    nl_host_config_t host;    /**< origin_id and name overridden per device. */
    nl_zone_plan_t plan;
    double per;               /**< Packet error rate on every link. */
    double link_loss[NL_SIM_MAX_NODES][NL_SIM_MAX_NODES]; /**< [tx][rx] extra loss. */
    double spi_fault_rate;    /**< Probability a SPI transfer response is corrupted. */
    bool wake_on_push;        /**< Platform re-plans RX when the host pushes TX. */
    bool finish_rx;           /**< Platform finishes a packet whose sync word it
                                   detected before starting the next action
                                   (otherwise a slot change aborts it). */
    nl_sim_node_cfg_t node[NL_SIM_MAX_NODES];
} nl_sim_scenario_t;

/**
 * Defaults: @p nodes devices booting 0..5 ms apart, each listening on and
 * sending to zone 1 at 20 Hz with 32-byte payloads, sub-GHz, default core
 * parameters, no loss, 5 s run with 1 s warm-up.
 */
void nl_sim_scenario_default(nl_sim_scenario_t *sc, uint8_t nodes);

/** Results of one run. */
typedef struct {
    uint64_t sent;          /**< Measured fragments the hosts accepted. */
    uint64_t send_failed;   /**< nl_host_send() errors (e.g. link down). */
    uint64_t expected;      /**< sent x receivers claiming the zone. */
    uint64_t delivered;     /**< Unique measured fragments delivered to plugins. */
    uint64_t duplicates;    /**< Delivered more than once (dedup failure). */
    uint64_t reordered;     /**< Delivered after a later one from the same flow. */
    uint64_t late;          /**< Latency beyond the histogram range. */
    uint32_t lat_p50_us, lat_p90_us, lat_p99_us, lat_max_us;
    double lat_mean_us;

    uint64_t air_tx;        /**< RF transmissions (incl. repeats, meta). */
    uint64_t air_rx_ok;     /**< Packet receptions handed to a radio. */
    uint64_t air_collided;  /**< Receptions destroyed by an overlap. */
    uint64_t air_missed;    /**< Receiver not listening for the full packet. */
    uint64_t air_lost;      /**< Dropped by the loss model. */
    uint64_t air_deferred;  /**< Transmissions put off by a busy clear-channel
                                 check (cca_backoff_us != 0). */
    double busiest_channel_util; /**< Fraction of time the busiest frequency
                                      was occupied. */

    uint32_t radio_tx_dropped;  /**< Sum of radio TX queue evictions. */
    uint32_t radio_rx_dropped;  /**< Sum of radio RX queue overflows. */
    uint32_t spi_errors;        /**< CRC + protocol + I/O errors on all links. */
    uint32_t radio_resets;
    int64_t discovery_us;       /**< When every device first knew every other
                                     (from the last boot), or -1 if never. */
} nl_sim_result_t;

/** Opaque-ish simulator state (large; allocate statically or on the heap). */
typedef struct nl_sim nl_sim_t;

/** Size of nl_sim_t, for callers that allocate it. */
size_t nl_sim_size(void);

/** Run a scenario to completion. */
int nl_sim_run(const nl_sim_scenario_t *sc, nl_sim_result_t *res);

/** Step-wise API used by tests. */
int nl_sim_init(nl_sim_t *sim, const nl_sim_scenario_t *sc);
void nl_sim_advance(nl_sim_t *sim, uint64_t until_us);
void nl_sim_result(const nl_sim_t *sim, nl_sim_result_t *res);
nl_host_t *nl_sim_host(nl_sim_t *sim, uint8_t node);
nl_radio_t *nl_sim_radio(nl_sim_t *sim, uint8_t node);
/** Received measured fragments at @p rx sent by @p tx (all zones). */
uint64_t nl_sim_flow_delivered(const nl_sim_t *sim, uint8_t tx, uint8_t rx);

#ifdef __cplusplus
}
#endif

#endif /* NL_SIM_H */
