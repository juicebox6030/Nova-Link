/**
 * @file nl_radio.h
 * @brief Portable radio co-processor core (runs on the CC1352R).
 *
 * The radio core owns the zone scheduler, per-zone TX queues, RX
 * deduplication, the queue of fragments waiting for the host, and the SPI
 * slave command handler. It never touches hardware. The platform layer
 * drives it with a simple loop:
 *
 * @code
 * for (;;) {
 *     nl_radio_action_t act;
 *     nl_radio_next_action(&radio, now_us(), &act);
 *     switch (act.type) {
 *     case NL_ACT_TX:   if (act.cca && rf_channel_busy(act.freq_hz)) {
 *                           nl_radio_tx_busy(&radio, now_us()); // retry later
 *                       } else {
 *                           rf_transmit(act.freq_hz, act.data, act.len);
 *                       }
 *                       break;
 *     case NL_ACT_RX:   // listen on act.freq_hz until act.until; for each
 *                       // packet call nl_radio_rx_packet(), then loop
 *                       break;
 *     case NL_ACT_IDLE: sleep_until(act.until); break;
 *     }
 *     gpio_set(INT_READY, nl_radio_int_ready(&radio));
 * }
 * @endcode
 *
 * After every SPI transaction the platform calls nl_radio_spi_complete()
 * with the bytes it received, then preloads nl_radio_outbox() into the SPI
 * TX buffer for the next transaction.
 *
 * Scheduling model:
 * - Each listen slot goes to the zone chosen by smooth weighted round-robin
 *   over the zone priorities, so a priority-2 zone gets twice the slots of a
 *   priority-1 zone, evenly interleaved. Weights are evaluated every slot,
 *   so zones can join and leave the rotation at any time.
 * - Zone 0 with priority 0 joins the rotation (weight 1) only while it is
 *   "active": a zone 0 fragment is queued for TX, or a MGMT_LISTEN flag was
 *   heard within mgmt_hold_us. Give zone 0 a priority to listen always.
 *   With nothing else enabled the radio listens on zone 0 for discovery.
 * - In NL_TX_IN_SLOT mode a priority-0 zone with queued TX also joins with
 *   weight 1, so its fragments get a slot.
 * - A zone with no frequency for the selected band is never scheduled.
 * - Hearing a BURST fragment on the current zone extends its slot.
 * - Queued fragments are sent tx_repeats times (zone 0: mgmt_repeats),
 *   repeat_interval_us apart,
 *   cycling through all queued fragments of a zone on each pass. Zones 1..7
 *   always go before zone 0.
 */
#ifndef NL_RADIO_H
#define NL_RADIO_H

#include "nl_common.h"
#include "nl_link.h"
#include "nl_stream_tracker.h"

#ifdef __cplusplus
extern "C" {
#endif

/** What the RF hardware should do next. */
typedef enum {
    NL_ACT_IDLE = 0, /**< Nothing to do until @c until. */
    NL_ACT_TX = 1,   /**< Transmit @c data / @c len on @c freq_hz. */
    NL_ACT_RX = 2,   /**< Listen on @c freq_hz until @c until. */
} nl_radio_action_type_t;

typedef struct {
    uint8_t type;          /**< nl_radio_action_type_t */
    uint8_t zone;          /**< Zone of the TX/RX. */
    uint8_t band;          /**< NL_BAND_SUBGHZ or NL_BAND_2G4. */
    uint32_t freq_hz;      /**< Centre frequency. */
    const uint8_t *data;   /**< TX: fragment bytes (valid until the next call). */
    uint8_t len;           /**< TX: fragment length. */
    bool cca;              /**< TX: check the channel first; if it is busy,
                                call nl_radio_tx_busy() instead of sending. */
    nl_time_us_t until;    /**< RX / IDLE: end of the action. */
} nl_radio_action_t;

/** One fragment waiting to be transmitted. */
typedef struct {
    uint8_t data[NL_MAX_FRAGMENT];
    uint8_t len;
    uint8_t sends;        /**< Completed transmissions. */
    uint8_t repeats_left; /**< Transmissions still to do. */
    uint8_t second_band;  /**< DUAL band: 2.4 GHz copy still owed. */
    uint8_t defers;       /**< Failed clear-channel checks in a row. */
    nl_time_us_t next_due;
} nl_radio_txq_entry_t;

/** Radio core state. Treat as opaque; sized for static allocation. */
typedef struct {
    nl_radio_params_t params;
    nl_zone_plan_t plan;
    uint8_t config_flags;

    nl_stream_tracker_t tracker;

    nl_radio_txq_entry_t txq[NL_NUM_ZONES][NL_RADIO_TXQ_DEPTH];
    uint8_t txq_len[NL_NUM_ZONES];
    uint8_t tx_rr; /**< Round-robin cursor for fairness between zones. */
    uint8_t tx_scratch[NL_MAX_FRAGMENT];

    uint8_t rxq[NL_RADIO_RXQ_DEPTH][NL_MAX_FRAGMENT];
    uint8_t rxq_lens[NL_RADIO_RXQ_DEPTH];
    uint8_t rxq_head;
    uint8_t rxq_count;

    int16_t swrr_cw[NL_NUM_ZONES]; /**< Smooth weighted round-robin state. */
    uint8_t cur_zone;
    bool slot_active;
    nl_time_us_t slot_end;
    uint8_t rx_band_toggle; /**< Bit n: next RX visit of zone n uses 2.4 GHz. */
    uint8_t cur_band;
    bool mgmt_heard; /**< Zone 0 in rotation: MGMT_LISTEN heard or zone 0 TX. */
    nl_time_us_t mgmt_until;
    uint32_t rng; /**< Repeat jitter PRNG state. */
    nl_time_us_t last_meta_slot; /**< Start of the last zone 0 listen slot. */

    uint8_t outbox[NL_LINK_FRAME_MAX];
    uint8_t outbox_len;

    /* The last TX action as it was before being emitted, so
     * nl_radio_tx_busy() can take it back. */
    bool undo_valid;
    bool undo_removed;    /**< The emit finished the entry and removed it. */
    uint8_t undo_zone;
    uint8_t undo_idx;
    nl_radio_txq_entry_t undo_entry;
    uint32_t cca_busy;    /**< Transmissions deferred by a busy channel. */
    bool rx_hold;         /**< No TX before rx_hold_until (packet just heard). */
    nl_time_us_t rx_hold_until;

    nl_radio_status_t stats;
    nl_link_pong_t fw;
} nl_radio_t;

/** Config-received bits (nl_radio_t::config_flags). */
#define NL_RADIO_CFG_PARAMS 0x01u
#define NL_RADIO_CFG_PLAN 0x02u

/** Initialise with default parameters and no zones enabled. */
void nl_radio_init(nl_radio_t *r);

/**
 * Mix hardware entropy (e.g. a TRNG word) into the jitter PRNG. Optional:
 * without it the sequence is derived from the originID, which already
 * differs between devices of one network.
 */
void nl_radio_seed(nl_radio_t *r, uint32_t entropy);

/** Apply parameters and plan directly (equivalent to the two config commands). */
void nl_radio_configure(nl_radio_t *r, const nl_radio_params_t *params,
                        const nl_zone_plan_t *plan);

/** Decide what the RF should do next. */
void nl_radio_next_action(nl_radio_t *r, nl_time_us_t now, nl_radio_action_t *act);

/**
 * The platform found the channel busy for the TX action just returned by
 * nl_radio_next_action() (only when its @c cca flag is set) and did not
 * transmit. The fragment is put back, retried after a random 1..cca_backoff_us
 * and the attempt is not counted. Call before the next nl_radio_next_action().
 * @return NL_OK, or NL_ERR_EMPTY if there is no TX action to take back.
 */
int nl_radio_tx_busy(nl_radio_t *r, nl_time_us_t now);

/** Report a packet received during an RX action. */
void nl_radio_rx_packet(nl_radio_t *r, const uint8_t *data, size_t len,
                        nl_time_us_t now);

/** Queue a fragment for transmission (what NL_CMD_PUSH does). */
int nl_radio_queue_tx(nl_radio_t *r, const uint8_t *frag, size_t len,
                      nl_time_us_t now);

/** True while fragments wait for the host (drives the INT_READY GPIO). */
static inline bool nl_radio_int_ready(const nl_radio_t *r)
{
    return r->rxq_count > 0;
}

/**
 * Process the bytes received in one SPI transaction (host request) and
 * prepare the outbox for the next transaction.
 */
void nl_radio_spi_complete(nl_radio_t *r, const uint8_t *rx, size_t len,
                           nl_time_us_t now);

/** Bytes to clock out on the next transaction (pad with 0x00 after). */
static inline const uint8_t *nl_radio_outbox(const nl_radio_t *r, size_t *len)
{
    *len = r->outbox_len;
    return r->outbox;
}

/** Snapshot the status counters. */
void nl_radio_get_status(const nl_radio_t *r, nl_radio_status_t *out);

/** Total fragments waiting in all TX queues. */
uint8_t nl_radio_tx_pending(const nl_radio_t *r);

#ifdef __cplusplus
}
#endif

#endif /* NL_RADIO_H */
