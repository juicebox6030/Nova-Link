/**
 * @file nl_link.h
 * @brief Host <-> radio link protocol (SPI or UART).
 *
 * Every message on the link is a frame:
 *
 *     +------+-----+-----+-----------+------+
 *     | 0xAA | CMD | LEN | DATA[LEN] | CRC8 |
 *     +------+-----+-----+-----------+------+
 *
 * - SYNC (0xAA) lets the receiver skip SPI filler bytes and resynchronise a
 *   UART stream.
 * - CRC8 is CRC-8/SMBUS (poly 0x07, init 0x00) over CMD, LEN, and DATA.
 *
 * The SPI exchange is two-phase because an SPI slave can only clock out
 * bytes it prepared *before* the transaction started:
 *
 * 1. Host sends a request frame. The radio parses it and prepares the
 *    response in its outbox.
 * 2. For commands that have a response, the host runs a second
 *    transaction (sending filler zeros) and reads the response frame.
 *
 * Commands 0x01..0x04 and response 0xD0 come from docs/spi_protocol.adoc.
 * 0x05/0x06 and responses 0xD1/0xD4 are additions defined here.
 */
#ifndef NL_LINK_H
#define NL_LINK_H

#include "nl_common.h"

#ifdef __cplusplus
extern "C" {
#endif

#define NL_LINK_SYNC 0xAAu
#define NL_LINK_OVERHEAD 4u /**< SYNC + CMD + LEN + CRC */
#define NL_LINK_FRAME_MAX (NL_LINK_MAX_DATA + NL_LINK_OVERHEAD)

/**
 * CMD bytes that are never valid. An idle SPI/UART line reads as 0x00 or
 * 0xFF, and with a zero-initialised CRC-8 the bytes "AA 00 00 00" form a
 * frame with a correct checksum, so a stray SYNC in zero filler would
 * otherwise decode as a phantom frame. Decoders reject these CMD values.
 */
#define NL_LINK_CMD_INVALID(c) ((c) == 0x00u || (c) == 0xFFu)

/** Link command / response codes. */
typedef enum {
    NL_CMD_PING = 0x01,         /**< Host->radio: ready check. Response 0xD1. */
    NL_CMD_PULL = 0x02,         /**< Host->radio: fetch an RX fragment. Response 0xD0. */
    NL_CMD_PUSH = 0x03,         /**< Host->radio: queue fragment for TX. No response. */
    NL_CMD_STATUS = 0x04,       /**< Host->radio: status request. Response 0xD4. */
    NL_CMD_ZONE_CONFIG = 0x05,  /**< Host->radio: zone frequency/priority plan. No response. */
    NL_CMD_RADIO_CONFIG = 0x06, /**< Host->radio: scheduler parameters. No response. */
    NL_RSP_FRAGMENT = 0xD0,     /**< Radio->host: DataFragment (LEN 0 = none pending). */
    NL_RSP_PONG = 0xD1,         /**< Radio->host: ping reply (nl_link_pong_t). */
    NL_RSP_STATUS = 0xD4,       /**< Radio->host: status (nl_radio_status_t). */
} nl_link_cmd_t;

/** One decoded link frame. */
typedef struct {
    uint8_t cmd;
    uint8_t len;
    uint8_t data[NL_LINK_MAX_DATA];
} nl_link_frame_t;

/** CRC-8/SMBUS over @p len bytes, continuing from @p crc (start with 0). */
uint8_t nl_crc8(uint8_t crc, const uint8_t *data, size_t len);

/**
 * Build a frame.
 * @return Total encoded bytes, or a negative nl_status_t.
 */
int nl_link_encode(uint8_t cmd, const uint8_t *data, size_t len, uint8_t *out,
                   size_t cap);

/**
 * Find and decode the first valid frame in a buffer, skipping filler bytes
 * and candidate SYNC bytes that do not lead to a valid frame (including
 * those followed by an NL_LINK_CMD_INVALID command byte).
 * @param buf       Received bytes.
 * @param len       Number of bytes in @p buf.
 * @param frame     Set to the decoded frame (data is copied).
 * @param consumed  Optional; set to the number of bytes up to the end of the
 *                  decoded frame (or the whole buffer if none was found).
 * @return NL_OK, NL_ERR_EMPTY if no frame was found, or NL_ERR_CRC if the
 *         only candidate frame had a bad checksum.
 */
int nl_link_decode(const uint8_t *buf, size_t len, nl_link_frame_t *frame,
                   size_t *consumed);

/** A frame found in place: @c data points into the scanned buffer. */
typedef struct {
    uint8_t cmd;
    uint8_t len;
    const uint8_t *data;
} nl_link_view_t;

/**
 * nl_link_decode() without the copy: same scan, same results and
 * @p consumed, but @p frame->data points into @p buf and is only valid
 * while @p buf is. Avoids a NL_LINK_MAX_DATA-sized frame on the stack.
 */
int nl_link_find(const uint8_t *buf, size_t len, nl_link_view_t *frame,
                 size_t *consumed);

/** Streaming parser for byte-oriented transports (UART). */
typedef struct {
    uint8_t state;
    uint8_t pos;
    nl_link_frame_t frame;
    uint32_t crc_errors;  /**< Frames dropped for checksum mismatch. */
    uint32_t len_errors;  /**< Frames dropped for LEN > NL_LINK_MAX_DATA. */
    uint32_t cmd_errors;  /**< SYNC bytes followed by an invalid CMD byte. */
} nl_link_parser_t;

void nl_link_parser_init(nl_link_parser_t *p);

/**
 * Feed one byte.
 * @return 1 when a complete valid frame is available in p->frame, else 0.
 */
int nl_link_parser_feed(nl_link_parser_t *p, uint8_t byte);

/* ------------------------------------------------------------------------ */
/* Payload structures carried by the link                                   */
/* ------------------------------------------------------------------------ */

/** RF band selection. */
typedef enum {
    NL_BAND_SUBGHZ = 0, /**< Sub-GHz only. */
    NL_BAND_2G4 = 1,    /**< 2.4 GHz only. */
    NL_BAND_DUAL = 2,   /**< TX on both bands, RX alternates per visit. */
} nl_band_t;

/** When the radio transmits queued fragments. */
typedef enum {
    /** Transmit as soon as the current action ends, regardless of rotation. */
    NL_TX_IMMEDIATE = 0,
    /** Transmit only during the zone's own rotation slot. */
    NL_TX_IN_SLOT = 1,
} nl_tx_policy_t;

/** RF parameters of one zone. */
typedef struct {
    uint8_t priority;   /**< Rotation weight 1..8; 0 = not in rotation. */
    uint32_t subghz_hz; /**< Sub-GHz centre frequency in Hz. */
    uint32_t ghz24_hz;  /**< 2.4 GHz centre frequency in Hz. */
} nl_zone_rf_t;

/** Full zone plan (NL_CMD_ZONE_CONFIG). Zone 0 priority = slots when active. */
typedef struct {
    nl_zone_rf_t zone[NL_NUM_ZONES];
} nl_zone_plan_t;

#define NL_ZONE_PLAN_WIRE_SIZE (NL_NUM_ZONES * 9)

/** Scheduler parameters (NL_CMD_RADIO_CONFIG). */
typedef struct {
    uint8_t origin_id;           /**< This device's originID (own echoes ignored). */
    uint8_t band;                /**< nl_band_t */
    uint8_t tx_policy;           /**< nl_tx_policy_t */
    uint8_t tx_repeats;          /**< Transmissions per fragment (>= 1). */
    uint32_t dwell_us;           /**< Listen time per rotation slot. */
    uint32_t burst_extend_us;    /**< Extra dwell after hearing BURST. */
    uint32_t mgmt_hold_us;       /**< Zone 0 stays in rotation this long after MGMT_LISTEN. */
    uint32_t repeat_interval_us; /**< Minimum gap between repeats of a fragment. */
    uint32_t tracker_stale_us;   /**< Dedup entry expiry (sender reboot recovery). */
    uint32_t repeat_jitter_us;   /**< Random extra 0..N us added to each repeat gap,
                                      so devices that boot together do not keep
                                      transmitting in lockstep. */
    uint32_t discovery_interval_us; /**< Listen on zone 0 at least once per this
                                         period even with no MGMT_LISTEN heard,
                                         so silent devices find each other
                                         (0 = only when pulled by MGMT_LISTEN). */
    uint8_t mgmt_repeats;        /**< Transmissions per zone 0 fragment
                                      (0 = tx_repeats). Zone 0 is low-rate but
                                      must reach devices that only visit it
                                      briefly, so it gets more repeats than
                                      data by default. */
    uint32_t cca_backoff_us;     /**< Listen before talk: TX actions ask the
                                      platform for a clear-channel check, and a
                                      busy channel defers the transmission by a
                                      random 1..N us (0 = off, transmit
                                      blindly). See nl_radio_tx_busy(). */
} nl_radio_params_t;

#define NL_RADIO_PARAMS_WIRE_SIZE 37

/** Radio status (NL_RSP_STATUS). Counters are free-running and wrap. */
typedef struct {
    uint8_t proto_version;
    uint8_t flags;        /**< NL_STATUS_F_* */
    uint8_t rx_queue_len; /**< Fragments waiting for the host. */
    uint8_t tx_queue_len; /**< Fragments waiting for transmission (all zones). */
    uint32_t rx_ok;       /**< New fragments accepted. */
    uint32_t rx_dup;      /**< Duplicates / stale fragments discarded. */
    uint32_t rx_dropped;  /**< Accepted but dropped because the RX queue was full. */
    uint32_t rx_ignored;  /**< Malformed, own-origin, or unsubscribed zone. */
    uint32_t tx_sent;     /**< RF transmissions (each repeat counts). */
    uint32_t tx_dropped;  /**< Fragments evicted from a full TX queue. */
} nl_radio_status_t;

#define NL_STATUS_F_RX_PENDING 0x01u
#define NL_STATUS_F_CONFIGURED 0x02u
#define NL_RADIO_STATUS_WIRE_SIZE 28

/** Ping reply (NL_RSP_PONG). */
typedef struct {
    uint8_t proto_version;
    uint8_t fw_major;
    uint8_t fw_minor;
    uint8_t fw_patch;
} nl_link_pong_t;

#define NL_PONG_WIRE_SIZE 4

int nl_zone_plan_encode(const nl_zone_plan_t *plan, uint8_t *out, size_t cap);
int nl_zone_plan_decode(const uint8_t *buf, size_t len, nl_zone_plan_t *plan);
int nl_radio_params_encode(const nl_radio_params_t *p, uint8_t *out, size_t cap);
int nl_radio_params_decode(const uint8_t *buf, size_t len, nl_radio_params_t *p);
int nl_radio_status_encode(const nl_radio_status_t *s, uint8_t *out, size_t cap);
int nl_radio_status_decode(const uint8_t *buf, size_t len, nl_radio_status_t *s);
int nl_link_pong_encode(const nl_link_pong_t *p, uint8_t *out, size_t cap);
int nl_link_pong_decode(const uint8_t *buf, size_t len, nl_link_pong_t *p);

/** Default scheduler parameters (also documented in config/nova_link.ini). */
void nl_radio_params_default(nl_radio_params_t *p);

/* LEN is one byte (nl_link_encode would truncate a larger length); buffers
 * sized from NL_LINK_MAX_DATA must hold a whole fragment (nl_spi_link reads
 * PULL responses into them) and every config payload. */
#if NL_LINK_MAX_DATA > 255
#error "NL_LINK_MAX_DATA must be at most 255 (one LEN byte)"
#endif
#if NL_LINK_MAX_DATA < NL_MAX_FRAGMENT || NL_LINK_MAX_DATA < NL_ZONE_PLAN_WIRE_SIZE || \
    NL_LINK_MAX_DATA < NL_RADIO_PARAMS_WIRE_SIZE || NL_LINK_MAX_DATA < NL_RADIO_STATUS_WIRE_SIZE
#error "NL_LINK_MAX_DATA is too small for a fragment or a config/status payload"
#endif

#ifdef __cplusplus
}
#endif

#endif /* NL_LINK_H */
