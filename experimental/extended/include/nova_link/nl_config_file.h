/**
 * @file nl_config_file.h
 * @brief Load a device's full setup (host config, radio parameters, zone
 *        plan) from INI text. See config/nova_link.ini for a commented
 *        example listing every key with its default.
 *
 * Sections and keys:
 *
 * | Section    | Keys                                                        |
 * |------------|-------------------------------------------------------------|
 * | [device]   | origin_id (0..7), name (1..24 bytes)                        |
 * | [radio]    | band (subghz, 2g4, dual), tx_policy (immediate, in_slot),   |
 * |            | tx_repeats (1..255), dwell_us, burst_extend_us,             |
 * |            | mgmt_hold_us, repeat_interval_us, tracker_stale_us,         |
 * |            | repeat_jitter_us, discovery_interval_us,                    |
 * |            | mgmt_repeats (0..255, 0 = tx_repeats), cca_backoff_us       |
 * | [host]     | announce_interval_us, announce_jitter_us,                   |
 * |            | announce_boot_spread_us, announce_ramp_steps (0..16),       |
 * |            | rand_seed,                                                  |
 * |            | meta_interval_us, meta_lead_us, mgmt_flag_hold_us,          |
 * |            | status_interval_us, remote_claim_expiry_us, peer_expiry_us, |
 * |            | tracker_stale_us, check_remote_types, max_pull_per_poll     |
 * | [zone.N]   | priority (0..8), subghz_hz or subghz_mhz,                   |
 * |            | ghz24_hz or ghz24_mhz  (N = 0..7)                           |
 *
 * The device's origin_id and name live in [device] only; origin_id is
 * written to both nl_host_config_t and nl_radio_params_t.
 *
 * Value rules:
 *
 * - Integers are decimal or 0x-prefixed hex, without a sign.
 * - Booleans: true/false, yes/no, on/off, 1/0 (case-insensitive).
 * - Times: a key `<name>_us` takes a plain integer in microseconds, or a
 *   number with a unit suffix `us`, `ms`, or `s` (`dwell_us = 2ms`). The
 *   short key `<name>` (without `_us`) is an alias that *requires* a unit
 *   (`dwell = 2ms`, `announce_interval = 2s`); a bare number there is an
 *   error because it would be ambiguous. Suffixed values may have a
 *   fraction (`1.5ms`) as long as the result is a whole number of
 *   microseconds. Times must not exceed 2147483647 us (~35.8 min) because
 *   timestamps wrap and are compared as signed 32-bit differences.
 * - Frequencies: `*_hz` takes an integer in Hz, `*_mhz` a decimal in MHz
 *   (`903.5`, at most Hz resolution). Sub-GHz must be 300..1000 MHz and
 *   2.4 GHz 2400..2483.5 MHz; 0 means "no frequency on that band" (the
 *   radio then skips the zone on that band).
 * - priority is capped at 8 by the radio scheduler, so 9..255 are rejected
 *   rather than silently capped.
 * - Each setting may appear once per file; `subghz_hz` and `subghz_mhz`, or
 *   `dwell_us` and `dwell`, name the same setting.
 *
 * Errors: unknown sections and keys, syntax errors, bad or out-of-range
 * values, and duplicates are all fatal. Loading stops at the first error and
 * nl_config_error_t gives its line and a message. Outputs are only written
 * when the whole file is valid.
 */
#ifndef NL_CONFIG_FILE_H
#define NL_CONFIG_FILE_H

#include "nl_common.h"
#include "nl_host.h"
#include "nl_link.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Size of nl_config_error_t::msg, including the terminating NUL. */
#ifndef NL_CONFIG_ERR_MSG_LEN
#define NL_CONFIG_ERR_MSG_LEN 96
#endif

/** Highest zone priority the radio scheduler honours (see nl_radio.c). */
#define NL_CONFIG_MAX_PRIORITY 8u

/** Largest time value in microseconds (INT32_MAX; see nl_time_diff()). */
#define NL_CONFIG_MAX_TIME_US 2147483647u

/** Description of the first error found by nl_config_load(). */
typedef struct {
    int status; /**< Same value nl_config_load() returned (NL_OK if none). */
    int line;   /**< 1-based line of the error; 0 if none or not line-specific. */
    char msg[NL_CONFIG_ERR_MSG_LEN]; /**< Human-readable message ("" if none). */
} nl_config_error_t;

/**
 * Default zone plan: every priority 0, zone z on 903 + 3*z MHz (sub-GHz) and
 * 2405 + 10*z MHz (2.4 GHz).
 */
void nl_config_zone_plan_default(nl_zone_plan_t *plan);

/**
 * Load a configuration. Defaults come from nl_host_config_default(),
 * nl_radio_params_default(), and nl_config_zone_plan_default(); the text
 * then overrides individual settings.
 *
 * @param text    INI text (need not be NUL-terminated; parsing also stops
 *                at a NUL byte). May be NULL when @p len is 0.
 * @param len     Length of @p text in bytes.
 * @param host    Optional output; NULL to validate without storing.
 * @param params  Optional output; NULL to validate without storing.
 * @param plan    Optional output; NULL to validate without storing.
 * @param err     Optional; receives the first error.
 * @return NL_OK, or the first error:
 *         - NL_ERR_ARG: invalid argument, or a value that is malformed,
 *           out of range, or not allowed for the key;
 *         - NL_ERR_SIZE: line, section, key, or name too long;
 *         - NL_ERR_PROTO: INI syntax error;
 *         - NL_ERR_NOT_FOUND: unknown section or key;
 *         - NL_ERR_CONFLICT: a setting given more than once.
 *         Outputs are left unchanged on error.
 */
int nl_config_load(const char *text, size_t len, nl_host_config_t *host,
                   nl_radio_params_t *params, nl_zone_plan_t *plan,
                   nl_config_error_t *err);

#ifdef __cplusplus
}
#endif

#endif /* NL_CONFIG_FILE_H */
