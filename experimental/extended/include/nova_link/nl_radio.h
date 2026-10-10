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
 * SPI requests are handled in one of two ways:
 *
 * - Deferred (recommended): the SPI ISR only copies the received bytes into
 *   a small handoff buffer and preloads the next reply; the main loop
 *   handles the request. Nothing in the ISR touches the queues, logs or
 *   takes longer than a bounded memcpy:
 *
 * @code
 * void spi_isr(void) {                       // transaction complete (CS high)
 *     nl_radio_spi_isr(&radio, spi_rx_buf, spi_rx_count());
 *     size_t n;
 *     const uint8_t *p = nl_radio_spi_arm(&radio, &n);
 *     spi_load_tx(p, n);                     // NULL / 0: clock out 0x00 filler
 * }
 * // in the main loop, next to nl_radio_next_action():
 * if (nl_radio_poll(&radio, now_us())) {
 *     spi_irq_disable();                     // nested-safe masking also works
 *     if (spi_bus_idle()) {                  // not mid-transaction
 *         size_t n;
 *         const uint8_t *p = nl_radio_spi_arm(&radio, &n);
 *         if (p != NULL) spi_load_tx(p, n);
 *     }
 *     spi_irq_enable();
 * }
 * @endcode
 *
 *   The host sees an empty read until the main loop has run; nl_spi_link
 *   re-reads (see nl_spi_link.h). If more than NL_RADIO_SPI_SLOTS requests
 *   arrive between two polls the extra ones are dropped and counted in
 *   spi_overruns.
 *
 * - Direct: after every SPI transaction the platform calls
 *   nl_radio_spi_complete() with the bytes it received, then preloads
 *   nl_radio_outbox() into the SPI TX buffer for the next transaction.
 *   Simplest when everything runs in one context.
 *
 * Concurrency: nl_radio_next_action(), nl_radio_tx_busy(),
 * nl_radio_rx_packet(), nl_radio_queue_tx(), nl_radio_configure() and
 * nl_radio_poll() belong to one context (the main loop). Only
 * nl_radio_spi_isr() and nl_radio_spi_arm() may run in an interrupt; the
 * handoff slots are a lock-free single-producer/single-consumer ring
 * ordered by NL_COMPILER_BARRIER(), which assumes a single-core MCU (or a
 * port that defines the barrier as __DMB()), and the outbox hand-over
 * uses NL_CRITICAL_ENTER/EXIT (nl_config.h). Those critical sections also
 * guard the RX queue head/count and the params/plan swap, so the
 * direct path can run nl_radio_spi_complete() in the SPI ISR provided the
 * SPI interrupt is masked around nl_radio_next_action() and
 * nl_radio_tx_busy(): a PUSH into a full TX queue evicts and shifts
 * entries the scheduler may be indexing.
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
    volatile uint8_t outbox_state; /**< Deferred path: NL_OUTBOX_* owner. */

    /* Deferred SPI handoff (nl_radio_spi_isr() -> nl_radio_poll()).
     * spi_wr is written only by the ISR, spi_rd only by the main loop;
     * both run freely and wrap, so the fill level is (uint8_t)(wr - rd). */
    uint8_t spi_slot[NL_RADIO_SPI_SLOTS][NL_LINK_FRAME_MAX];
    uint8_t spi_slot_len[NL_RADIO_SPI_SLOTS];
    volatile uint8_t spi_wr;
    volatile uint8_t spi_rd;
    bool spi_deferred; /**< Handling a polled request: replies must claim. */
    bool reply_made;   /**< The polled request produced a reply. */

    /* Radio-local SPI counters (not part of the wire status). */
    volatile uint32_t spi_overruns; /**< Requests dropped: handoff full. */
    uint32_t spi_reply_busy; /**< Replies skipped: previous one still armed. */
    uint32_t spi_crc_errors; /**< Request frames with a bad checksum. */
    uint32_t spi_rejected;   /**< Bad PUSH/config payloads, unknown commands. */

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

/** nl_radio_t::outbox_state on the deferred path. */
#define NL_OUTBOX_EMPTY 0u /**< Main loop may write a reply. */
#define NL_OUTBOX_READY 1u /**< Reply written, not yet loaded into SPI TX. */
#define NL_OUTBOX_ARMED 2u /**< Loaded; owned by SPI until clocked out. */

/**
 * Direct path: process the bytes received in one SPI transaction (host
 * request) and prepare the outbox for the next transaction.
 *
 * Recommended pattern: call it from the main loop, or use the deferred
 * path (nl_radio_spi_isr() + nl_radio_poll()) when SPI completes in an
 * interrupt. Calling it from the SPI ISR is possible with NL_CRITICAL_*
 * defined, NL_ISR_BUILD set (rejected frames are then only counted, not
 * logged) and the SPI interrupt masked around nl_radio_next_action() and
 * nl_radio_tx_busy(); see the file comment. Do not mix it with the
 * deferred path on one radio.
 */
void nl_radio_spi_complete(nl_radio_t *r, const uint8_t *rx, size_t len,
                           nl_time_us_t now);

/**
 * Deferred path, SPI ISR side: hand the bytes of one completed transaction
 * to the main loop. Releases the outbox the transaction clocked out, then
 * copies from the first sync byte on (at most NL_LINK_FRAME_MAX bytes)
 * into a free handoff slot. Pure filler (a response read) is not queued.
 * With all NL_RADIO_SPI_SLOTS slots full the request is dropped and
 * spi_overruns is incremented. O(len), no locks, no logging.
 */
void nl_radio_spi_isr(nl_radio_t *r, const uint8_t *rx, size_t len);

/**
 * Deferred path: take the reply the main loop prepared, for loading into
 * SPI TX. Call at the end of the SPI ISR and, after nl_radio_poll()
 * returned 1, from the main loop with the SPI interrupt masked while the
 * bus is idle. The buffer belongs to SPI until the next nl_radio_spi_isr().
 * @return The frame and its length, or NULL (*len = 0) if none is ready.
 */
const uint8_t *nl_radio_spi_arm(nl_radio_t *r, size_t *len);

/**
 * Deferred path, main loop side: handle one request queued by
 * nl_radio_spi_isr(), with the same effect as nl_radio_spi_complete().
 * A request that needs a reply while the previous reply is still armed
 * (the host has not clocked it out) gets none and is counted in
 * spi_reply_busy; a PULL then leaves its fragment queued.
 * @return 1 if a request was handled (call nl_radio_spi_arm()), 0 if
 *         nothing was pending.
 */
int nl_radio_poll(nl_radio_t *r, nl_time_us_t now);

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
