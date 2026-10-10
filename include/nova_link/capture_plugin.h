#ifndef NOVA_LINK_CAPTURE_PLUGIN_H
#define NOVA_LINK_CAPTURE_PLUGIN_H

#include "nova_link/module.h"

/** @file capture_plugin.h Portable observation logging, not an RF decoder.
 * Serialise calls with the host. Capture from a task, not an RF interrupt.
 * No heap allocation or I/O is performed except the caller's output callback.
 */
typedef enum { NL_CAPTURE_CRC_UNKNOWN, NL_CAPTURE_CRC_OK, NL_CAPTURE_CRC_BAD } nl_capture_crc;

/** Atomic output contract: NL_OK means the entire JSONL record was accepted.
 * Any error must accept no bytes. The callback must not retain the pointer or
 * re-enter capture/host APIs. Adapt partial-write streams using an external
 * queue which atomically copies a complete record, then drains its own offset.
 */
typedef nl_status (*nl_capture_output_fn)(void *context, const char *jsonl, size_t length);

typedef struct {
    char *buffer;
    size_t capacity; /**< Includes trailing NUL, which is not passed to output. */
    nl_capture_output_fn output;
    void *output_context;
} nl_capture_config;

typedef struct {
    uint64_t timestamp_us; /**< Extended monotonic receiver timestamp. */
    uint32_t frequency_hz; /**< Actual tuning, 2400000000..2483500000 Hz. */
    const char *profile; /**< Nonblank, valid UTF-8 configuration identifier. */
    const char *stimulus; /**< NULL selects "unspecified"; otherwise nonblank UTF-8. */
    const uint8_t *payload; /**< Exact bytes returned by the candidate receiver. */
    size_t payload_length;
    nl_capture_crc crc; /**< Candidate PHY result; never inferred from bytes. */
    bool has_rssi;
    int16_t rssi_dbm; /**< Measured integral dBm, ignored when has_rssi is false. */
} nl_capture_observation;

/** Caller-owned storage. Treat fields as read-only after initialization. The
 * configuration is copied; keep its buffer and callback context alive throughout registration.
 * Do not modify the buffer while registered, even when no record is pending.
 */
typedef struct {
    nl_capture_config config;
    nl_host *host;
    nl_plugin_id plugin;
    size_t pending_length;
    uint64_t last_timestamp_us;
    nl_status last_status; /**< Most recent flush result, including poll errors. */
    bool have_timestamp;
    bool pending;
    bool outputting;
} nl_capture_context;

/** Initialize inactive storage. Never reinitialize a registered context. */
nl_status nl_capture_init(nl_capture_context *capture, const nl_capture_config *config);
/** Copy one observation into the bounded buffer. NL_OK means staged, not
 * output/committed. BUSY retains the existing immutable record. SIZE leaves no
 * partial record and leaves timestamp history unchanged. Inputs must not
 * overlap the output buffer or context. Equal timestamps are permitted.
 */
nl_status nl_capture_submit(nl_capture_context *capture, const nl_capture_observation *observation);
/** Output a staged record once; EMPTY if none. Errors retain exact JSONL bytes.
 * NL_OK is the only output-acceptance result. Host polling also tries once.
 */
nl_status nl_capture_flush(nl_capture_context *capture);
bool nl_capture_pending(const nl_capture_context *capture);
/** Pending output vetoes ordinary stop. Startup rollback cancels locally
 * staged output without invoking the sink. Stop clears timestamp history.
 */
nl_plugin nl_capture_plugin(nl_capture_context *capture);
/** Service manifest named "capture", version "1", no dependencies. */
nl_module nl_capture_module(nl_capture_context *capture);

#endif
